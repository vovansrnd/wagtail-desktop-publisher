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

import frontmatter
import markdown as md_lib
import requests

from .config import theme_for_host

IMG_MD_RE = re.compile(r"!\[(.*?)\]\((.*?)\)")
_LOCAL_SKIP = ("http://", "https://", "/media/", "/static/")


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


class Article:
    """Обёртка над .md файлом: frontmatter + путь."""

    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.base_dir = os.path.dirname(self.path)
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
        with open(self.path, "w", encoding="utf-8") as fh:
            frontmatter.dump(self.post, fh)

    def local_images(self):
        """Локальные картинки в тексте: [(md_path, abs_path|None)].
        Путь внутри директории статьи; ../ и абсолютные за её пределами
        отбрасываются (защита от выноса произвольных файлов)."""
        base = os.path.realpath(self.base_dir)
        found = []
        for _alt, rel in IMG_MD_RE.findall(self.post.content):
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
    """Тонкий клиент v3 API. Все вызовы синхронные."""

    def __init__(self, api_url, token, timeout=120):
        self.api_url = api_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"
        self.timeout = timeout

    def _url(self, path):
        return f"{self.api_url}/{path.lstrip('/')}"

    def sites(self):
        resp = self.session.get(self._url("sites/"), timeout=self.timeout)
        if resp.status_code != 200:
            raise SyncError(f"sites/ → HTTP {resp.status_code}: {resp.text[:200]}")
        return resp.json().get("items", [])

    def pages(self, **params):
        resp = self.session.get(self._url("pages/"), params=params, timeout=self.timeout)
        if resp.status_code != 200:
            raise SyncError(f"pages/ → HTTP {resp.status_code}")
        return resp.json()

    def categories(self):
        """Рубрики сайта (id, name, parent_id, level). Пусто, если у сайта их нет."""
        resp = self.session.get(self._url("publisher-meta/categories/"), timeout=self.timeout)
        if resp.status_code != 200:
            raise SyncError(f"categories/ → HTTP {resp.status_code}")
        return resp.json().get("items", [])

    def tags(self, search=None, limit=200):
        """Теги сайта (id, name), опционально с поиском по подстроке."""
        resp = self.session.get(
            self._url("publisher-meta/tags/"),
            params={"search": search, "limit": limit},
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            raise SyncError(f"tags/ → HTTP {resp.status_code}")
        return resp.json().get("items", [])

    def upload_image(self, path, year, slug, title):
        with open(path, "rb") as fh:
            resp = self.session.post(
                self._url("publisher-images/"),
                data={"title": title, "year": str(year), "slug": str(slug or "")},
                files={"file": (os.path.basename(path), fh)},
                timeout=self.timeout,
            )
        if resp.status_code not in (200, 201):
            raise SyncError(f"upload {os.path.basename(path)} → HTTP {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    def create_page(self, payload, page_type, parent_id, publish):
        payload = dict(payload)
        meta = {"type": page_type, "parent_id": int(parent_id)}
        # API принимает action="publish"; отсутствие action = черновик
        if publish:
            meta["action"] = "publish"
        payload["meta"] = meta
        resp = self.session.post(self._url("pages/"), json=payload, timeout=self.timeout)
        return self._page_response(resp, "создана")

    def update_page(self, page_id, payload, publish, page_type):
        payload = dict(payload)
        # meta.type обязателен: PATCH-схема собирается по типу страницы
        # (PageTypeInjectingBody), без него применяются только базовые поля
        meta = {"type": page_type}
        if publish:
            meta["action"] = "publish"
        payload["meta"] = meta
        resp = self.session.patch(self._url(f"pages/{page_id}/"), json=payload, timeout=self.timeout)
        return self._page_response(resp, "обновлена")

    def unpublish_page(self, page_id):
        resp = self.session.post(
            self._url(f"pages/{page_id}/actions/unpublish/"), timeout=self.timeout
        )
        if resp.status_code not in (200, 201):
            raise SyncError(f"unpublish → HTTP {resp.status_code}: {resp.text[:300]}")
        return True

    def get_page(self, page_id):
        resp = self.session.get(
            self._url(f"pages/{page_id}/"), params={"type": "blog.BlogPage"}, timeout=self.timeout
        )
        if resp.status_code != 200:
            raise SyncError(f"pages/{page_id} → HTTP {resp.status_code}")
        return resp.json()

    @staticmethod
    def _page_response(resp, mode):
        if resp.status_code not in (200, 201):
            raise SyncError(f"HTTP {resp.status_code}: {resp.text[:400]}")
        data = resp.json()
        return {"id": data.get("id"), "mode": mode, "data": data}


class SyncEngine:
    def __init__(self, api: WagtailAPI, site_host: str, page_type: str = "blog.BlogPage"):
        self.api = api
        self.site_host = site_host
        self.theme = theme_for_host(site_host)
        self.page_type = page_type

    # ---------- картинки ----------

    def _resolve_images(self, article: Article, year, slug, log):
        """Загружает/переиспользует картинки, возвращает:
        content с серверными URL (только для payload) и карту изображений."""
        images_map = article.post.get("images") or {}
        new_map = {}
        payload_content = article.post.content
        uploaded = reused = missing = 0

        for rel, abs_path in article.local_images():
            entry = images_map.get(rel)
            file_hash = _file_sha256(abs_path) if abs_path else None

            if entry and entry.get("file_hash") == file_hash and entry.get("url"):
                # картинка не менялась — переиспользуем
                new_map[rel] = entry
                payload_content = payload_content.replace(f"]({rel})", f"]({entry['url']})")
                reused += 1
                continue

            if not abs_path:
                missing += 1
                log(f"  ⚠️ файл не найден, оставлен как есть: {rel}")
                if entry:
                    new_map[rel] = entry
                continue

            title = os.path.splitext(os.path.basename(abs_path))[0]
            data = self.api.upload_image(abs_path, year, slug, title)
            entry = {
                "id": data["id"],
                "url": data["download_url"],
                "file_hash": file_hash,
            }
            new_map[rel] = entry
            payload_content = payload_content.replace(f"]({rel})", f"]({data['download_url']})")
            uploaded += 1
            log(f"  ⬆️ загружено: {rel} → id {data['id']} ({year}/{slug or 'misc'})")

        return payload_content, new_map, {"uploaded": uploaded, "reused": reused, "missing": missing}

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
        page = self.api.get_page(int(wagtail_id))
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
