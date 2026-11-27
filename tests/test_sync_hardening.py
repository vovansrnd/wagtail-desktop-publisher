"""Д67-C(P) партия hardening SyncEngine: M2/M3/M4/M5/M6.

Эксперименты только на временных файлах и mock-объектах; сеть и реальные
сайты не используются.
"""
import io
import os
import re
import tempfile
import unittest
from unittest import mock

import requests

from wagtail_desktop_publisher.core.paths import resolve_export_path
from wagtail_desktop_publisher.core.sync import (
    Article,
    SyncEngine,
    SyncError,
    WagtailAPI,
    iter_image_destinations,
    replace_image_destinations,
)


def _png_bytes(color=(1, 2, 3)):
    from PIL import Image as PILImage

    buf = io.BytesIO()
    PILImage.new("RGB", (40, 20), color).save(buf, format="PNG")
    return buf.getvalue()


# ==========================================================================
# M2 — атомарное сохранение Article
# ==========================================================================
class AtomicArticleSaveTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="wdp-m2-")

    def _path(self, name="статья-тест.md"):
        return os.path.join(self.dir, name)

    def _write(self, path, content):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)

    def _md(self, body="Текст статьи"):
        return "---\ntitle: Аудит\nslug: audit\n---\n\n" + body

    def test_save_preserves_frontmatter_and_body(self):
        path = self._path()
        self._write(path, self._md("Оригинальное тело"))
        article = Article(path)
        article.post["wagtail_id"] = 42
        article.save()
        reloaded = Article(path)
        self.assertEqual(reloaded.post.get("wagtail_id"), 42)
        self.assertEqual(reloaded.post.get("title"), "Аудит")
        self.assertEqual(reloaded.post.get("slug"), "audit")
        self.assertIn("Оригинальное тело", reloaded.post.content)

    def test_failed_replace_leaves_original_byte_identical(self):
        path = self._path()
        original = self._md("Оригинал")
        self._write(path, original)
        before = open(path, "rb").read()
        article = Article(path)
        article.post["wagtail_id"] = 1
        with mock.patch(
            "wagtail_desktop_publisher.core.sync.os.replace",
            side_effect=OSError("replace failed"),
        ):
            with self.assertRaises(OSError):
                article.save()
        # исходник байт-в-байт прежний
        self.assertEqual(open(path, "rb").read(), before)
        # временные файлы вычищены
        leftovers = [n for n in os.listdir(self.dir) if n.startswith(".wdp-save-")]
        self.assertEqual(leftovers, [])

    def test_unicode_filename_and_content(self):
        path = self._path("Статья №1 — отчёт.md")
        self._write(path, self._md("Юникод-тело: пруфы ✓ «цитата»"))
        article = Article(path)
        article.post["excerpt"] = "Аннотация ✓"
        article.save()
        reloaded = Article(path)
        self.assertEqual(reloaded.post["excerpt"], "Аннотация ✓")
        self.assertIn("пруфы ✓", reloaded.post.content)

    def test_original_mode_preserved(self):
        path = self._path()
        self._write(path, self._md())
        os.chmod(path, 0o600)
        article = Article(path)
        article.post["wagtail_id"] = 7
        article.save()
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)


# ==========================================================================
# M3 — безопасный путь экспорта GUI
# ==========================================================================
class ExportPathTests(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="wdp-m3-")

    def test_traversal_slug_stays_inside_base(self):
        path = resolve_export_path("../evil", self.base)
        self.assertTrue(
            os.path.commonpath((os.path.realpath(self.base), path))
            == os.path.realpath(self.base)
        )

    def test_absolute_slug_sanitized_into_base(self):
        path = resolve_export_path("/etc/passwd", self.base)
        self.assertTrue(path.startswith(os.path.realpath(self.base) + os.sep))

    def test_empty_slug_raises(self):
        with self.assertRaises(ValueError):
            resolve_export_path("", self.base)

    def test_dots_only_slug_raises(self):
        with self.assertRaises(ValueError):
            resolve_export_path("..", self.base)

    def test_unicode_and_space_slug_readable(self):
        path = resolve_export_path("Моя Статья №1", self.base)
        component = os.path.basename(path)
        self.assertNotIn("/", component)
        self.assertNotIn("..", component)
        self.assertTrue(
            os.path.commonpath((os.path.realpath(self.base), path))
            == os.path.realpath(self.base)
        )

    def test_symlink_directory_outside_raises_and_writes_nothing(self):
        outside = tempfile.mkdtemp(prefix="wdp-m3-outside-")
        inside_link = os.path.join(self.base, "link-out")
        os.symlink(outside, inside_link)
        # slug = имя symlink-каталога: realpath выведет наружу → отказ
        with self.assertRaises(ValueError):
            resolve_export_path("link-out", self.base)
        # по отказу ничего не записано вне базового каталога
        self.assertEqual(os.listdir(outside), [])


# ==========================================================================
# M4/L7 — разбор и подстановка image references
# ==========================================================================
class ImageTokenTests(unittest.TestCase):
    def _dests(self, content):
        return [dest for _fs, _fe, _is, _ie, dest in iter_image_destinations(content)]

    def test_plain_and_quoted_title(self):
        dests = self._dests(
            "![plain](img.png)\n![with title](sub/inner.png \"caption text\")"
        )
        self.assertEqual(dests, ["img.png", "sub/inner.png"])

    def test_angle_bracket_destination_with_spaces(self):
        dests = self._dests("![a](<sub/dir with spaces.png>)")
        self.assertEqual(dests, ["sub/dir with spaces.png"])

    def test_fenced_code_not_matched(self):
        content = "До\n```text\n![x](secret.png)\n```\nПосле ![real](real.png)"
        self.assertEqual(self._dests(content), ["real.png"])

    def test_inline_code_not_matched(self):
        content = "Пример: `![x](secret.png)` и ![real](real.png)"
        self.assertEqual(self._dests(content), ["real.png"])

    def test_tilde_fence_not_matched(self):
        content = "~~~\n![x](secret.png)\n~~~\n![real](real.png)"
        self.assertEqual(self._dests(content), ["real.png"])

    def test_positional_replace_no_cross_basename(self):
        content = "![a](one/img.png) ![b](two/img.png)"
        out = replace_image_destinations(
            content, lambda d: {"one/img.png": "https://s/1.png",
                                "two/img.png": "https://s/2.png"}.get(d)
        )
        self.assertIn("https://s/1.png", out)
        self.assertIn("https://s/2.png", out)
        self.assertNotIn("](one/img.png)", out)
        self.assertNotIn("](two/img.png)", out)

    def test_code_block_untouched_by_replace(self):
        content = "```text\n![x](img.png)\n```\n![real](img.png)"
        out = replace_image_destinations(content, lambda d: "https://s/1.png")
        self.assertIn("![x](img.png)", out)  # код не тронут
        self.assertIn("![real](https://s/1.png)", out)


class ArticleLocalImagesTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="wdp-m4-")

    def _write(self, rel, content):
        path = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(content)
        return path

    def _article(self, body):
        path = os.path.join(self.dir, "article.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("---\ntitle: t\nslug: t\n---\n\n" + body)
        return Article(path)

    def test_quoted_title_file_resolved(self):
        self._write("sub/inner.png", _png_bytes())
        a = self._article('![with title](sub/inner.png "caption text")')
        images = a.local_images()
        self.assertEqual(len(images), 1)
        rel, abs_path = images[0]
        # M4: файл разрешён несмотря на quoted title (в rel он НЕ попадает —
        # это текст ссылки в md, в payload подставится серверный URL)
        self.assertTrue(abs_path and os.path.isfile(abs_path))

    def test_fenced_reference_not_collected(self):
        a = self._article("```text\n![x](secret.png)\n```\n![real](real.png)")
        self.assertEqual(
            [rel for rel, _p in a.local_images()], ["real.png"]
        )


class SyncPayloadRoundtripTests(unittest.TestCase):
    """Полный sync с mock-API: исходный .md сохраняет относительные пути,
    payload получает серверные URL, одинаковые basename не кросс-меняются."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="wdp-sync-")
        os.makedirs(os.path.join(self.dir, "one"))
        os.makedirs(os.path.join(self.dir, "two"))
        for rel, color in (("one/img.png", (1, 0, 0)), ("two/img.png", (0, 1, 0))):
            with open(os.path.join(self.dir, rel), "wb") as fh:
                fh.write(_png_bytes(color))
        body = "![first](one/img.png)\n\n![second](two/img.png)"
        self.md_path = os.path.join(self.dir, "article.md")
        with open(self.md_path, "w", encoding="utf-8") as fh:
            fh.write("---\ntitle: t\nslug: t\nyear: '2026'\n---\n\n" + body)

        self.api = WagtailAPI("https://example.invalid/api/v3", "test-token")
        self.uploaded = []

        def fake_upload(path, year, slug, title):
            self.uploaded.append(os.path.relpath(path, self.dir))
            n = len(self.uploaded)
            return {"id": 100 + n, "download_url": f"https://site/media/{n}.png"}

        self.api.upload_image = fake_upload
        self.created = []
        self.api.create_page = lambda payload, page_type, parent_id, publish: (
            self.created.append(payload) or {"id": 555, "mode": "создана",
                                             "data": {"meta": {"html_url": "u"}}}
        )

    def test_sync_roundtrip(self):
        engine = SyncEngine(self.api, "test.local")
        result = engine.sync(self.md_path, parent_id=10, publish=False)
        self.assertTrue(result.ok)
        # обе картинки загружены (уникальные файлы)
        self.assertEqual(sorted(self.uploaded), ["one/img.png", "two/img.png"])
        # payload: каждый токен получил СВОЙ URL
        payload_body = self.created[0]["body"]  # Markdown уже конвертирован в HTML
        self.assertIn('src="https://site/media/1.png"', payload_body)
        self.assertIn('src="https://site/media/2.png"', payload_body)
        # исходный .md: ТЕЛО сохранило относительные пути (server-URL
        # допустимы только в frontmatter-карте images)
        on_disk = open(self.md_path, encoding="utf-8").read()
        body = on_disk.rsplit("---\n", 1)[-1]  # тело после закрывающего frontmatter
        self.assertIn("](one/img.png)", body)
        self.assertIn("](two/img.png)", body)
        self.assertNotIn("https://site/media", body)


# ==========================================================================
# M5 — fail closed на отсутствующие локальные файлы
# ==========================================================================
class MissingImagePreflightTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="wdp-m5-")
        with open(os.path.join(self.dir, "real.png"), "wb") as fh:
            fh.write(_png_bytes())
        self.api = WagtailAPI("https://example.invalid/api/v3", "test-token")
        self.api.upload_image = mock.Mock(
            side_effect=AssertionError("upload не должен вызываться при missing")
        )
        self.created = []
        self.api.create_page = lambda payload, page_type, parent_id, publish: (
            self.created.append(payload) or {"id": 555, "mode": "создана",
                                             "data": {}}
        )
        self.api.update_page = mock.Mock(
            side_effect=AssertionError("update_page не должен вызываться для новой статьи")
        )
        self.engine = SyncEngine(self.api, "test.local")

    def _md(self, body, wagtail_id=None):
        self.md_path = os.path.join(self.dir, "article.md")
        meta = "---\ntitle: t\nslug: t\nyear: '2026'\n"
        if wagtail_id:
            meta += f"wagtail_id: {wagtail_id}\n"
        with open(self.md_path, "w", encoding="utf-8") as fh:
            fh.write(meta + "---\n\n" + body)

    def test_missing_image_raises_sync_error_no_api_calls(self):
        self._md("![x](missing.png)")
        with self.assertRaises(SyncError) as ctx:
            self.engine.sync(self.md_path, parent_id=1)
        self.assertIn("missing.png", str(ctx.exception))
        self.assertIn("fail closed", str(ctx.exception))
        self.api.upload_image.assert_not_called()
        self.assertEqual(self.created, [])  # страница не создавалась
        self.api.update_page.assert_not_called()

    def test_one_missing_of_several_uploads_nothing(self):
        self._md("![ok](real.png)\n\n![bad](missing.png)")
        with self.assertRaises(SyncError):
            self.engine.sync(self.md_path, parent_id=1)
        self.api.upload_image.assert_not_called()

    def test_traversal_reference_raises_before_api(self):
        self._md("![x](../../outside.png)")
        with self.assertRaises(SyncError) as ctx:
            self.engine.sync(self.md_path, parent_id=1)
        self.assertIn("вне каталога", str(ctx.exception))
        self.api.upload_image.assert_not_called()

    def test_remote_media_static_not_treated_as_missing(self):
        self._md(
            "![r](https://example.com/x.png) ![m](/media/y.png) ![s](/static/z.png)"
        )
        # remote-ссылки не управляются publisher'ом: sync создаёт страницу,
        # ни одна локальная картинка не загружается
        result = self.engine.sync(self.md_path, parent_id=1)
        self.assertTrue(result.ok)
        self.api.upload_image.assert_not_called()
        self.assertEqual(len(self.created), 1)

    def test_unbound_article_without_images_uploads_nothing(self):
        self._md("Только текст")
        result = self.engine.sync(self.md_path, parent_id=1)
        self.assertTrue(result.ok)
        self.api.upload_image.assert_not_called()
        self.assertEqual(len(self.created), 1)


# ==========================================================================
# M6 — нормализация ошибочных API-ответов
# ==========================================================================
class FakeResponse:
    def __init__(self, status_code=200, text="", content_type="application/json",
                 payload=None):
        self.status_code = status_code
        self.text = text
        self.headers = {"Content-Type": content_type}
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class FakeSession:
    """Подменяет session.request; секретный токен «утапливается» в текст
    ответа для проверки, что SyncError его не раскрывает."""

    SECRET = "wagtail_SUPERSECRET_token_value"

    def __init__(self, response=None, exc=None):
        self.headers = {"Authorization": f"Bearer {self.SECRET}"}
        self.response = response
        self.exc = exc

    def request(self, method, url, timeout=None, **kwargs):
        if self.exc:
            raise self.exc
        return self.response


def _api_with(session):
    api = WagtailAPI("https://example.invalid/api/v3", FakeSession.SECRET)
    api.session = session
    return api


class MalformedResponseTests(unittest.TestCase):
    def test_502_html_raises_sync_error_without_token(self):
        html = "<html><body>502 Bad Gateway</body></html>"
        api = _api_with(FakeSession(FakeResponse(502, html, "text/html")))
        with self.assertRaises(SyncError) as ctx:
            api.sites()
        message = str(ctx.exception)
        self.assertIn("502", message)
        self.assertNotIn(FakeSession.SECRET, message)
        self.assertNotIn("Authorization", message)

    def test_200_empty_body_raises_sync_error_with_content_type(self):
        api = _api_with(FakeSession(FakeResponse(200, "", "text/html")))
        with self.assertRaises(SyncError) as ctx:
            api.sites()
        self.assertIn("не является JSON", str(ctx.exception))
        self.assertIn("text/html", str(ctx.exception))

    def test_200_invalid_json_raises_sync_error(self):
        api = _api_with(FakeSession(FakeResponse(200, "{not-json", "application/json")))
        with self.assertRaises(SyncError):
            api.get_page(1)

    def test_200_fragment_excerpt_bounded_200_chars(self):
        api = _api_with(FakeSession(FakeResponse(200, "x" * 5000, "text/html")))
        with self.assertRaises(SyncError) as ctx:
            api.sites()
        # в сообщении не может быть весь 5000-символьный фрагмент
        self.assertLess(len(str(ctx.exception)), 700)

    def test_timeout_normalized_to_sync_error_with_cause(self):
        api = _api_with(FakeSession(exc=requests.Timeout("too slow")))
        with self.assertRaises(SyncError) as ctx:
            api.sites()
        self.assertIn("сетевая ошибка", str(ctx.exception))
        self.assertIsInstance(ctx.exception.__cause__, requests.Timeout)

    def test_connection_error_normalized(self):
        api = _api_with(FakeSession(exc=requests.ConnectionError("refused")))
        with self.assertRaises(SyncError):
            api.tags()

    def test_page_write_error_includes_operation(self):
        api = _api_with(FakeSession(FakeResponse(500, "boom", "text/html")))
        with self.assertRaises(SyncError) as ctx:
            api.update_page(7, {"title": "x"}, publish=False, page_type="t.T")
        self.assertIn("update page 7", str(ctx.exception))

    def test_error_text_never_contains_bearer_header(self):
        api = _api_with(FakeSession(FakeResponse(500, "Authorization: Bearer xyz", "text/html")))
        with self.assertRaises(SyncError) as ctx:
            api.sites()
        # серверная ошибка может повторить тело, но ни заголовок запроса,
        # ни сам токен из session.headers не добавляются клиентом
        self.assertNotIn(FakeSession.SECRET, str(ctx.exception))
