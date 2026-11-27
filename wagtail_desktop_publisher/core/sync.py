# core/sync.py — движок синхронизации Markdown ↔ Wagtail (v2).
#
# Принципы:
# 1. Локальный .md — источник истины. Пути картинок в тексте остаются
#    относительными: серверные URL подставляются только в payload.
# 2. Frontmatter хранит состояние синхронизации: wagtail_id, content_hash,
#    карту картинок (путь → id/url/хэш файла), published, slug.
# 3. content_hash (sha256 от заголовка, текста и excerpt) позволяет
#    пропустить синхронизацию неизменённой статьи — Wagtail на каждый
#    PATCH создаёт ревизию, поэтому «холостые» отправки недопустимы.
# 4. Картинки дедуплицируются через карту в frontmatter + хэш файла.
import datetime
import hashlib
import json
import os
import re
import tempfile

import frontmatter
import markdown as md_lib
import requests

from .config import theme_for_host

_LOCAL_SKIP = ("http://", "https://", "/media/", "/static/")

# Markdown-изображения: обычная форма ![alt](dest), optional quoted title
# ![alt](dest "title") и angle-bracket destination ![alt](<path with spaces>).
# plain-destination не содержит пробелов — поэтому quoted title отделяется
# однозначно (исправление M4: прежний regex захватывал title в путь).
IMAGE_TOKEN_RE = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\(\s*"
    r"(?:<(?P<angle>[^>]*)>|(?P<plain>[^)\s]+))"
    r"(?:\s+\"(?P<title>[^\"]*)\")?\s*\)"
)
_FENCE_RE = re.compile(r"(`{3,}|~{3,})(.*)$")
_INLINE_CODE_RE = re.compile(r"`+[^`]*`+")
_REF_DEF_RE = re.compile(
    r"^\s{0,3}\[(?P<label>[^\]]+)\]:\s*"
    r"(?:<(?P<angle>[^>]*)>|(?P<plain>\S+))"
    r'(?:\s+\"(?P<title>[^\"]*)\")?\s*$'
)
_REF_IMAGE_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\[(?P<label>[^\]]*)\]")
_SHORTCUT_IMAGE_RE = re.compile(r"!\[(?P<alt>[^\]]+)\](?!\[)")


def _excluded_code_spans(text):
    """Диапазоны исходного текста, внутри которых image-токены игнорируются:
    ограждённые код-блоки и inline code span'ы. Закрытие фенса — по
    CommonMark: тот же символ, длина не меньше открывающей, после маркера
    только пробелы/табуляция; строка с текстом после маркера фенс НЕ
    закрывает (остаётся содержимым код-блока)."""
    spans = []
    offset = 0
    fence_char = None
    fence_len = 0
    for line in text.splitlines(keepends=True):
        # CommonMark: fenced block допускает отступ максимум в 3 пробела;
        # строка с 4+ пробелами — indented code block, а не фенс.
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.lstrip(" ")
        if fence_char is None:
            if indent >= 4:
                # содержимое indented code block — image-токены строки
                # исключаются целиком
                spans.append((offset, offset + len(line)))
            else:
                m = _FENCE_RE.match(stripped)
                if m:
                    marker, info = m.group(1), m.group(2) or ""
                    # бэктик-фенс с ` в инфостроке не открывается (CommonMark)
                    if not (marker[0] == "`" and "`" in info):
                        fence_char, fence_len = marker[0], len(marker)
                        spans.append((offset, offset + len(line)))
                else:
                    for cm in _INLINE_CODE_RE.finditer(line):
                        spans.append((offset + cm.start(), offset + cm.end()))
        else:
            spans.append((offset, offset + len(line)))
            # закрывающий фенс — тоже максимум 3 пробела отступа
            if indent <= 3:
                m = re.match(r"(`{3,}|~{3,})[ \t]*$", stripped)
                if m and m.group(1)[0] == fence_char and len(m.group(1)) >= fence_len:
                    fence_char = None
        offset += len(line)
    return spans


def _parse_definitions(text, excluded):
    """Словарь reference-определений `[label]: destination` (вне кода);
    ключ — label в нижнем регистре, значение — destination."""
    defs = {}
    offset = 0
    for line in text.splitlines(keepends=True):
        m = _REF_DEF_RE.match(line)
        if m:
            start, end = offset, offset + len(line)
            if not any(s <= start and end <= e for s, e in excluded):
                dest = m.group("angle") if m.group("angle") is not None else m.group("plain")
                defs[m.group("label").strip().lower()] = dest.strip()
        offset += len(line)
    return defs


def iter_image_destinations(text):
    """Yield (full_start, full_end, inner_start, inner_end, dest, mode, alt)
    для реальных image-ссылок вне кода. mode: "inline" — inner_* выделяет
    destination внутри скобок (замена по нему сохраняет alt/title);
    "ref" — reference-style image (full/collapsed/shortcut), разрешённая
    по определениям `[label]: dest`; заменяется весь токен на
    ![alt](server_url). Ссылка с неизвестным label пропускается
    (CommonMark рендерит её как текст)."""
    excluded = _excluded_code_spans(text)
    defs = _parse_definitions(text, excluded)

    def excluded_at(start, end):
        return any(s <= start and end <= e for s, e in excluded)

    # Единый набор токенов (Issue #6): inline, full/collapsed и shortcut
    # собираются вместе и сортируются по исходной позиции — потребитель
    # replace_image_destinations() предполагает монотонно возрастающие span'ы.
    tokens = []
    for m in IMAGE_TOKEN_RE.finditer(text):
        if excluded_at(*m.span()):
            continue
        if m.group("angle") is not None:
            inner_start, inner_end = m.span("angle")
            dest = m.group("angle")
        else:
            inner_start, inner_end = m.span("plain")
            dest = m.group("plain")
        tokens.append((m.start(), m.end(), inner_start, inner_end, dest,
                       "inline", m.group("alt")))

    for m in _REF_IMAGE_RE.finditer(text):
        if excluded_at(*m.span()):
            continue
        label = (m.group("label") or m.group("alt") or "").strip().lower()
        dest = defs.get(label)
        if not dest:
            continue
        dest = dest[1:-1] if dest.startswith("<") and dest.endswith(">") else dest
        tokens.append((m.start(), m.end(), m.start(), m.end(), dest,
                       "ref", m.group("alt")))

    for m in _SHORTCUT_IMAGE_RE.finditer(text):
        if excluded_at(*m.span()):
            continue
        label = m.group("alt").strip().lower()
        dest = defs.get(label)
        if not dest:
            continue
        dest = dest[1:-1] if dest.startswith("<") and dest.endswith(">") else dest
        tokens.append((m.start(), m.end(), m.start(), m.end(), dest,
                       "ref", m.group("alt")))

    # строгий порядок по позиции; пересекающиеся/дублирующие матчи
    # отбрасываются (токен с более ранним началом имеет приоритет)
    tokens.sort(key=lambda tk: (tk[0], tk[1]))
    accepted = []
    last_end = -1
    for tk in tokens:
        if tk[0] < last_end:
            continue
        accepted.append(tk)
        last_end = tk[1]
    yield from accepted


def replace_image_destinations(text, url_for):
    """Возвращает текст с подставленными server-URL: inline — замена по
    inner-span (alt/title сохраняются); reference-style — весь токен
    превращается в ![alt](server_url). Позиционная замена: одинаковые
    basename в разных каталогах не пересекаются, код-блоки не затрагиваются."""
    out = []
    last = 0
    for full_start, full_end, inner_start, inner_end, dest, mode, alt in iter_image_destinations(text):
        url = url_for(dest)
        if not url:
            continue
        if mode == "inline":
            out.append(text[last:inner_start])
            out.append(url)
            last = inner_end
        else:
            out.append(text[last:full_start])
            out.append(f"![{alt}]({url})")
            last = full_end
    out.append(text[last:])
    return "".join(out)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _file_sha256(path: str) -> str:
    """Hash a file in bounded memory, including very large local images."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class SyncError(Exception):
    pass


class SyncResult(dict):
    @property
    def ok(self):
        return self.get("status") in ("created", "updated", "skipped")


def _raw_body_after_frontmatter(text):
    """Тело файла после frontmatter-разделителя БЕЗ strip: python-frontmatter
    делает content.strip(), из-за чего отступ начала тела (например,
    indented code block с ```) терялся и scanner не видел истинные отступы."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return text
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r\n") == "---":
            return "".join(lines[i + 1:])
    return text


class Article:
    """Обёртка над .md файлом: frontmatter + путь."""

    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.base_dir = os.path.dirname(self.path)
        with open(self.path, encoding="utf-8") as fh:
            self.raw_body = _raw_body_after_frontmatter(fh.read())
        self.post = frontmatter.load(self.path)

    @property
    def slug(self):
        return self.post.get("slug") or ""

    @property
    def title(self):
        return self.post.get("title") or ""

    def content_hash(self, title, excerpt):
        """Hash every user-controlled field that affects a Wagtail page.

        Local image bytes are included as well as Markdown paths, otherwise an
        edited image could be silently skipped while the article text is unchanged.
        """
        metadata_keys = (
            "slug", "year", "date", "tags", "category_ids", "categories",
            "seo_description", "main_image_id", "published",
        )
        local_images = []
        for rel_path, abs_path in self.local_images():
            try:
                digest = _file_sha256(abs_path) if abs_path else None
            except OSError:
                digest = None
            local_images.append({"path": rel_path, "sha256": digest})

        signature = {
            "title": title or "",
            "content": self.post.content,
            "excerpt": excerpt or "",
            "metadata": {key: self.post.get(key) for key in metadata_keys},
            "local_images": local_images,
        }
        encoded = json.dumps(
            signature, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
        )
        return _sha256_text(encoded)

    def save(self):
        """Атомарная запись (M2): сериализация в память → temp-файл в том же
        каталоге → fsync → os.replace → fsync каталога. Сбой на любом шаге
        до подмены оставляет исходный файл байт-в-байт неизменным."""
        data = frontmatter.dumps(self.post)
        directory = os.path.dirname(self.path) or "."
        try:
            original_mode = os.stat(self.path).st_mode & 0o777
        except OSError:
            original_mode = None
        fd, tmp_path = tempfile.mkstemp(
            prefix=".wdp-save-", suffix=".md", dir=directory
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            if original_mode is not None:
                os.chmod(tmp_path, original_mode)
            os.replace(tmp_path, self.path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
        try:  # fsync каталога — best effort (не все платформы поддерживают)
            dir_fd = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass

    def local_images(self):
        """Локальные картинки в тексте: [(md_path, abs_path|None)].
        Путь внутри директории статьи; ../ и абсолютные за её пределами
        отбрасываются (защита от выноса произвольных файлов). Image-ссылки
        внутри код-блоков и inline code игнорируются (M4)."""
        base = os.path.realpath(self.base_dir)
        found = []
        for _fs, _fe, _is, _ie, rel, _mode, _alt in iter_image_destinations(self.raw_body):
            if rel.lower().startswith(_LOCAL_SKIP):
                continue
            candidate = os.path.realpath(os.path.join(self.base_dir, rel))
            try:
                inside_article_dir = os.path.commonpath((base, candidate)) == base
            except ValueError:  # Different drives on Windows.
                inside_article_dir = False
            if not inside_article_dir:
                found.append((rel, None))
                continue
            found.append((rel, candidate if os.path.isfile(candidate) else None))
        return found


class WagtailAPI:
    """Тонкий клиент v3 API. Все вызовы синхронные.

    M6: ответы нормализуются — не-JSON/пустые тела и сетевые сбои
    превращаются в SyncError с операцией и HTTP-статусом; в текст ошибки
    никогда не попадают Authorization/token/query-секреты.
    """

    def __init__(self, api_url, token, timeout=120):
        self.api_url = api_url.rstrip("/")
        self._token = token
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"
        self.timeout = timeout

    def _redact(self, text):
        """Убирает configured Bearer token и authorization-like значения из
        диагностических фрагментов (сервер/WAF может отражать заголовки)."""
        if not text:
            return ""
        text = str(text)
        if self._token:
            text = text.replace(self._token, "[REDACTED_TOKEN]")
        text = re.sub(
            r"(?i)(authorization\s*[:=]\s*)\S+",
            r"\1[REDACTED]",
            text,
        )
        text = re.sub(
            r"(?i)(bearer\s+)[A-Za-z0-9._\-]+",
            r"\1[REDACTED]",
            text,
        )
        return text

    def _url(self, path):
        return f"{self.api_url}/{path.lstrip('/')}"

    def _request(self, method, url, operation, **kwargs):
        """Сетевой вызов с нормализацией timeout/connection ошибок в
        SyncError (с сохранением exception chaining)."""
        try:
            return self.session.request(method, url, timeout=self.timeout, **kwargs)
        except requests.RequestException as exc:
            raise SyncError(
                f"{operation} → сетевая ошибка: {exc.__class__.__name__}"
            ) from exc

    def _json(self, resp, operation, ok=(200,)):
        """JSON-тело успешного ответа; иначе SyncError. Не-JSON тело
        (заглушки прокси/WAF) → SyncError с content-type и фрагментом
        ≤200 символов. Секреты в текст ошибки не включаются."""
        if resp.status_code not in ok:
            # Diagnostic excerpt: redacted + capped; строка не содержит
            # Authorization/token/query-секретов.
            excerpt = self._redact((resp.text or ""))[:200]
            raise SyncError(
                f"{operation} → HTTP {resp.status_code}: {excerpt!r}"
            )
        try:
            return resp.json()
        except ValueError as exc:
            content_type = resp.headers.get("Content-Type", "unspecified")
            excerpt = self._redact((resp.text or ""))[:200]
            raise SyncError(
                f"{operation} → HTTP {resp.status_code}: тело не является JSON "
                f"(content-type: {content_type}), фрагмент: {excerpt!r}"
            ) from exc

    def sites(self):
        resp = self._request("GET", self._url("sites/"), "sites/")
        return self._json(resp, "sites/").get("items", [])

    def pages(self, **params):
        resp = self._request("GET", self._url("pages/"), "pages/", params=params)
        return self._json(resp, "pages/")

    def categories(self):
        """Рубрики сайта (id, name, parent_id, level). Пусто, если у сайта их нет."""
        resp = self._request("GET", self._url("publisher-meta/categories/"), "categories/")
        return self._json(resp, "categories/").get("items", [])

    def tags(self, search=None, limit=200):
        """Теги сайта (id, name), опционально с поиском по подстроке."""
        resp = self._request(
            "GET", self._url("publisher-meta/tags/"), "tags/",
            params={"search": search, "limit": limit},
        )
        return self._json(resp, "tags/").get("items", [])

    def upload_image(self, path, year, slug, title):
        operation = f"upload {os.path.basename(path)}"
        with open(path, "rb") as fh:
            resp = self._request(
                "POST", self._url("publisher-images/"), operation,
                data={"title": title, "year": str(year), "slug": str(slug or "")},
                files={"file": (os.path.basename(path), fh)},
            )
        return self._json(resp, operation, ok=(200, 201))

    def create_page(self, payload, page_type, parent_id, publish):
        payload = dict(payload)
        meta = {"type": page_type, "parent_id": int(parent_id)}
        # API принимает action="publish"; отсутствие action = черновик
        if publish:
            meta["action"] = "publish"
        payload["meta"] = meta
        resp = self._request("POST", self._url("pages/"), "create page", json=payload)
        return self._page_response(resp, "создана", operation="create page")

    def update_page(self, page_id, payload, publish, page_type):
        payload = dict(payload)
        # meta.type обязателен: PATCH-схема собирается по типу страницы
        # (PageTypeInjectingBody), без него применяются только базовые поля
        meta = {"type": page_type}
        if publish:
            meta["action"] = "publish"
        payload["meta"] = meta
        resp = self._request(
            "PATCH", self._url(f"pages/{page_id}/"), f"update page {page_id}",
            json=payload,
        )
        return self._page_response(resp, "обновлена", operation=f"update page {page_id}")

    def unpublish_page(self, page_id):
        operation = f"unpublish {page_id}"
        resp = self._request(
            "POST", self._url(f"pages/{page_id}/actions/unpublish/"), operation
        )
        self._json(resp, operation, ok=(200, 201))
        return True

    def get_page(self, page_id, page_type="blog.BlogPage"):
        # page_type параметризован (Д66): чужой проект публикует в свой тип
        operation = f"get page {page_id}"
        resp = self._request(
            "GET", self._url(f"pages/{page_id}/"), operation,
            params={"type": page_type},
        )
        return self._json(resp, operation)

    def _page_response(self, resp, mode, operation):
        op_label = f"{operation} ({mode})"
        data = self._json(resp, op_label, ok=(200, 201))
        return {"id": data.get("id"), "mode": mode, "data": data}


class SyncEngine:
    def __init__(self, api: WagtailAPI, site_host: str, page_type: str = "blog.BlogPage"):
        self.api = api
        self.site_host = site_host
        self.theme = theme_for_host(site_host)
        self.page_type = page_type

    # ---------- картинки ----------

    def _preflight_local_images(self, article: Article):
        """M5, fail closed ДО любых API writes: каждая реальная локальная
        image-ссылка должна указывать на существующий файл внутри каталога
        статьи. Remote HTTP(S)/media/static ссылки не проверяются — они
        намеренно не управляются publisher'ом. Нарушение → SyncError с
        путём и причиной; ни одна картинка не загружается, страница не
        создаётся и не обновляется."""
        base = os.path.realpath(article.base_dir)
        for rel, abs_path in article.local_images():
            if abs_path is not None:
                continue
            candidate = os.path.realpath(os.path.join(article.base_dir, rel))
            try:
                inside = os.path.commonpath((base, candidate)) == base
            except ValueError:
                inside = False
            if not inside:
                raise SyncError(
                    f"путь изображения вне каталога статьи — синхронизация "
                    f"прервана (fail closed): {rel} → {candidate}"
                )
            if not os.path.exists(candidate):
                raise SyncError(
                    f"локальный файл изображения отсутствует — синхронизация "
                    f"прервана (fail closed): {rel}"
                )
            raise SyncError(
                f"локальная ссылка не является регулярным файлом — "
                f"синхронизация прервана: {rel}"
            )

    def _resolve_images(self, article: Article, year, slug, log):
        """Загружает/переиспользует картинки, возвращает:
        content с серверными URL (только для payload) и карту изображений.
        Замена позиционная (по токенам): одинаковые базовые имена в разных
        каталогах не пересекаются, код-блоки не затрагиваются (M4/L7)."""
        images_map = article.post.get("images") or {}
        new_map = {}
        uploaded = reused = 0

        seen_rels = set()
        for rel, abs_path in article.local_images():
            if rel in seen_rels:
                # повторная ссылка на тот же путь: запись уже посчитана/будет
                # получена в этой попытке — повторная загрузка недопустима
                reused += 1
                continue
            seen_rels.add(rel)

            entry = images_map.get(rel)
            file_hash = _file_sha256(abs_path) if abs_path else None

            if entry and entry.get("file_hash") == file_hash and entry.get("url"):
                # картинка не менялась — переиспользуем
                new_map[rel] = entry
                reused += 1
                continue

            title = os.path.splitext(os.path.basename(abs_path))[0]
            data = self.api.upload_image(abs_path, year, slug, title)
            entry = {
                "id": data["id"],
                "url": data["download_url"],
                "file_hash": file_hash,
            }
            new_map[rel] = entry
            uploaded += 1
            log(f"  ⬆️ загружено: {rel} → id {data['id']} ({year}/{slug or 'misc'})")

        def url_for(dest):
            entry = new_map.get(dest)
            return entry["url"] if entry else None

        payload_content = replace_image_destinations(article.post.content, url_for)
        return payload_content, new_map, {"uploaded": uploaded, "reused": reused}

    # ---------- основная операция ----------

    def sync(self, md_path, parent_id=None, publish=None, title=None, slug=None,
             year=None, force=False, log=print,
             category_ids=None, tags=None, main_image_id=None) -> SyncResult:
        article = Article(md_path)

        if not article.title and not title:
            raise SyncError("В frontmatter нет title и не передан --title")
        if not article.slug and not slug:
            raise SyncError(
                "slug обязателен (frontmatter slug: или --slug) — без него нельзя"
                " гарантировать стабильный URL статьи"
            )

        title = title or article.title
        slug = slug or article.slug
        year = str(year or article.post.get("year") or datetime.datetime.now().year)
        if publish is None:
            publish = bool(article.post.get("published", False))

        excerpt = article.post.get("excerpt") or ""

        # M5 (follow-up): префлайт ДО fast-path по content_hash — иначе статья,
        # синхронизированная прежней версией с content_hash при отсутствующем
        # файле, навсегда получала бы skipped без проверки (обход fail-closed).
        self._preflight_local_images(article)

        # Store the effective metadata in frontmatter too. Otherwise GUI-selected
        # tags/categories/main image can be sent once and then disappear from the
        # local sync state, while a metadata-only edit is wrongly skipped.
        article.post["title"] = title
        article.post["slug"] = slug
        article.post["year"] = str(year)
        article.post["published"] = bool(publish)
        if tags is not None:
            article.post["tags"] = list(tags)
        if category_ids is not None:
            article.post["category_ids"] = [int(c) for c in category_ids]
        if main_image_id is not None:
            article.post["main_image_id"] = int(main_image_id)

        new_hash = article.content_hash(title, excerpt)
        wagtail_id = article.post.get("wagtail_id")

        # Хэш-пропуск: неизменённую статью не отправляем вовсе
        if (
            not force
            and wagtail_id
            and article.post.get("content_hash") == new_hash
        ):
            log(f"= без изменений, синхронизация не требуется (id {wagtail_id})")
            return SyncResult(status="skipped", id=wagtail_id, mode="без изменений")

        payload_content, images_map, img_stats = self._resolve_images(
            article, year, slug, log
        )

        # ProseEditorField хранит HTML: конвертируем Markdown → HTML сами.
        # Серверные URL картинок уже подставлены в payload_content.
        payload = {
            "title": title,
            "slug": slug,
            "body": md_lib.markdown(payload_content, extensions=["extra", "sane_lists"]),
        }
        if excerpt:
            payload["excerpt"] = md_lib.markdown(excerpt, extensions=["extra"])
        if article.post.get("date"):
            payload["date_published"] = str(article.post.get("date"))

        # Теги: явное переопределение из GUI > frontmatter
        if tags is not None:
            payload["tags"] = list(tags)
        elif article.post.get("tags"):
            payload["tags"] = list(article.post.get("tags"))

        # Рубрики: GUI (ids) > frontmatter ids > frontmatter имена (резолв по сайту)
        if category_ids is not None:
            payload["categories"] = [int(c) for c in category_ids]
        elif article.post.get("category_ids"):
            payload["categories"] = [int(c) for c in article.post.get("category_ids")]
        elif article.post.get("categories"):
            names = list(article.post.get("categories"))
            payload["categories"] = self._resolve_category_names(names)
        if article.post.get("seo_description"):
            payload["seo_description"] = str(article.post.get("seo_description"))[:160]

        image_entries = [e for e in images_map.values() if e.get("id")]
        # Схема v3 принимает FK по имени _id
        if main_image_id is not None:
            payload["main_image_id"] = int(main_image_id)
        elif article.post.get("main_image_id"):
            payload["main_image_id"] = int(article.post.get("main_image_id"))
        elif image_entries:
            payload["main_image_id"] = image_entries[0]["id"]

        if wagtail_id:
            result = self.api.update_page(int(wagtail_id), payload, publish=publish, page_type=self.page_type)
            mode = "обновлена"
        else:
            if not parent_id:
                raise SyncError("Новая статья требует parent_id (раздел публикации)")
            result = self.api.create_page(payload, self.page_type, parent_id, publish=publish)
            mode = "создана"

        # Записываем состояние обратно в .md
        article.post["wagtail_id"] = result["id"]
        article.post["title"] = title
        article.post["slug"] = slug
        article.post["year"] = str(year)
        article.post["published"] = bool(publish)
        article.post["content_hash"] = new_hash
        article.post["images"] = images_map
        article.post["theme"] = self.theme
        article.post["synced_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        article.save()

        page_data = result.get("data") or {}
        url = page_data.get("meta", {}).get("html_url") or page_data.get("meta", {}).get("_html_url", "")
        if url:
            article.post["url"] = url
            article.save()

        return SyncResult(
            status="created" if mode == "создана" else "updated",
            id=result["id"],
            mode=mode,
            images=img_stats,
            url=url,
        )

    # ---------- вспомогательные операции ----------

    def _resolve_category_names(self, names):
        """Имена рубрик → id. Незнакомое имя — ошибка со списком доступных."""
        cats = self.api.categories()
        by_name = {c["name"]: c["id"] for c in cats}
        resolved, unknown = [], []
        for name in names:
            if name in by_name:
                resolved.append(by_name[name])
            else:
                unknown.append(name)
        if unknown:
            available = ", ".join(sorted(by_name)[:15])
            raise SyncError(
                f"Неизвестные рубрики: {', '.join(unknown)}. "
                f"Доступны (первые 15): {available}"
            )
        return resolved

    def pull_meta(self, md_path, log=print) -> SyncResult:
        """Обновляет мета-состояние .md из Wagtail (тело НЕ трогаем)."""
        article = Article(md_path)
        wagtail_id = article.post.get("wagtail_id")
        if not wagtail_id:
            raise SyncError("Статья не привязана к Wagtail (нет wagtail_id)")
        page = self.api.get_page(int(wagtail_id), page_type=self.page_type)
        meta = page.get("meta", {}) or {}
        article.post["title"] = page.get("title", article.title)
        article.post["slug"] = page.get("slug", article.slug)
        article.post["published"] = bool(meta.get("live"))
        url = meta.get("html_url") or meta.get("_html_url")
        if url:
            article.post["url"] = url
        article.post["synced_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        article.save()
        log(f"⬇️ мета обновлена из Wagtail (published: {article.post['published']})")
        return SyncResult(status="pulled", id=wagtail_id)

    def status(self, md_path) -> SyncResult:
        """Локальный статус без обращения к сети."""
        article = Article(md_path)
        if not article.post.get("wagtail_id"):
            return SyncResult(status="unbound", detail="не привязана (новая)")
        current = article.content_hash(article.title, article.post.get("excerpt") or "")
        if article.post.get("content_hash") == current:
            return SyncResult(status="synced", id=article.post["wagtail_id"],
                              detail="синхронизирована")
        return SyncResult(status="modified", id=article.post["wagtail_id"],
                          detail="изменена локально")
