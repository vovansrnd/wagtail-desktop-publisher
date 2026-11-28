"""Д67-C(P) follow-up Issue #5: закрытие пробелов после M2-M6.

1. M5-префлайт до fast-path content_hash;
2. redaction токена/Authorization в ошибках (единый путь, 200-лимит);
3. reference-style images (full/collapsed/shortcut) + CommonMark-фенсы;
4. дедуп повторных ссылок на один путь;
"""
import os
import tempfile
from unittest import mock

from django.test import TestCase

from wagtail_desktop_publisher.core.sync import (
    Article,
    SyncEngine,
    SyncError,
    WagtailAPI,
    iter_image_destinations,
)

from tests.test_meta_auth import SimpleUpload  # noqa: E402
from tests.test_sync_hardening import (  # noqa: E402
    FakeResponse,
    FakeSession,
    _png_bytes,
)


def _png(color=(1, 2, 3)):
    return _png_bytes(color)


class PreflightBeforeHashSkipTests(TestCase):
    """M5-префлайт обязан выполняться ДО fast-path content_hash: статья,
    «синхронизированная» прежней версией с сохранённым хэшем и отсутствующим
    файлом, не может уходить в skipped без проверки."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="wdp-fu1-")
        self.api = WagtailAPI("https://example.invalid/api/v3", "test-token")
        self.api.upload_image = mock.Mock(
            side_effect=AssertionError("upload не должен вызываться")
        )
        self.created = []
        self.api.create_page = lambda payload, page_type, parent_id, publish: (
            self.created.append(payload) or {"id": 555, "mode": "создана", "data": {}}
        )
        self.api.update_page = mock.Mock(
            side_effect=AssertionError("update_page не должен вызываться")
        )
        self.engine = SyncEngine(self.api, "test.local")

    def _write_old_synced_with_missing_image(self):
        """Статья с wagtail_id и валидным content_hash, рассчитанным по
        текущему состоянию С отсутствующим local image (как сохранила бы
        прежняя версияpublisher'а)."""
        path = os.path.join(self.dir, "old.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(
                "---\ntitle: t\nslug: t\nyear: '2026'\nwagtail_id: 777\n"
                "published: false\ncontent_hash: placeholder\n---\n\n"
                "![x](missing.png)\n"
            )
        article = Article(path)
        # хэш по текущему состоянию (файл отсутствует → sha256: null) —
        # ровно как сохранила бы прежняя версия publisher'а
        article.post["content_hash"] = article.content_hash("t", "")
        article.save()
        return path

    def test_hash_skip_cannot_bypass_missing_image_preflight(self):
        path = self._write_old_synced_with_missing_image()
        with self.assertRaises(SyncError) as ctx:
            self.engine.sync(path, parent_id=1)
        self.assertIn("missing.png", str(ctx.exception))
        self.api.upload_image.assert_not_called()
        self.api.update_page.assert_not_called()
        self.assertEqual(self.created, [])

    def test_fast_path_still_works_for_clean_article(self):
        # чистая статья без картинок: первая синхронизация, затем — skipped
        path = os.path.join(self.dir, "clean.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("---\ntitle: clean\nslug: clean\nyear: '2026'\n---\n\nТекст")
        first = self.engine.sync(path, parent_id=1)
        self.assertEqual(first["status"], "created")
        second = self.engine.sync(path, parent_id=1)
        self.assertEqual(second["status"], "skipped")
        self.assertEqual(len(self.created), 1)  # create_page только один раз


class TokenRedactionTests(TestCase):
    """M6: server/WAF может отражать Authorization: Bearer <token> —
    SyncError не должен содержать токен ни в каком виде; лимит фрагмента
    соблюдён; операция и статус сохранены; _page_response идёт тем же путём."""

    def setUp(self):
        self.api = WagtailAPI("https://example.invalid/api/v3", FakeSession.SECRET)

    def _assert_clean(self, message):
        self.assertNotIn(FakeSession.SECRET, message)
        self.assertNotIn("Authorization: Bearer", message)
        self.assertNotIn("[REDACTED_TOKEN]'s", message)  # sanity

    def test_401_reflected_header_is_redacted(self):
        body = f"Unauthorized. Echo: Authorization: Bearer {FakeSession.SECRET}"
        self.api.session = FakeSession(FakeResponse(401, body, "text/html"))
        with self.assertRaises(SyncError) as ctx:
            self.api.sites()
        message = str(ctx.exception)
        self._assert_clean(message)
        self.assertIn("401", message)
        self.assertIn("sites/", message)

    def test_500_reflected_header_is_redacted_on_page_write(self):
        body = f"boom. Echo: Authorization: Bearer {FakeSession.SECRET}"
        self.api.session = FakeSession(FakeResponse(500, body, "text/html"))
        with self.assertRaises(SyncError) as ctx:
            self.api.update_page(9, {"title": "x"}, publish=False, page_type="t.T")
        message = str(ctx.exception)
        self._assert_clean(message)
        self.assertIn("500", message)
        self.assertIn("update page 9", message)

    def test_raw_token_in_error_body_is_redacted(self):
        body = f"error near token {FakeSession.SECRET} — retry"
        self.api.session = FakeSession(FakeResponse(500, body, "text/html"))
        with self.assertRaises(SyncError) as ctx:
            self.api.categories()
        self._assert_clean(str(ctx.exception))

    def test_error_excerpt_bounded_200_chars(self):
        body = "y" * 5000 + f" {FakeSession.SECRET}"
        self.api.session = FakeSession(FakeResponse(500, body, "text/html"))
        with self.assertRaises(SyncError) as ctx:
            self.api.sites()
        # лимит: сообщение не содержит 5000-символьный фрагмент целиком
        self.assertNotIn("y" * 1000, str(ctx.exception))
        self.assertNotIn(FakeSession.SECRET, str(ctx.exception))


class ReferenceStyleImageTests(TestCase):
    """Reference-style images: full/collapsed/shortcut формы с локальной
    definition загружаются и получают server URL в payload; remote
    definition остаётся нетронутой; undefined label — не изображение."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="wdp-fu3-")
        os.makedirs(os.path.join(self.dir, "images"), exist_ok=True)
        with open(os.path.join(self.dir, "images/logo.png"), "wb") as fh:
            fh.write(_png((9, 9, 9)))
        self.api = WagtailAPI("https://example.invalid/api/v3", "test-token")
        self.uploaded = []

        def fake_upload(path, year, slug, title):
            self.uploaded.append(os.path.relpath(path, self.dir))
            return {"id": 200 + len(self.uploaded),
                    "download_url": f"https://site/media/{len(self.uploaded)}.png"}

        self.api.upload_image = fake_upload
        self.created = []
        self.api.create_page = lambda payload, page_type, parent_id, publish: (
            self.created.append(payload) or {"id": 556, "mode": "создана", "data": {}}
        )
        self.engine = SyncEngine(self.api, "test.local")

    def _write(self, body):
        self.md_path = os.path.join(self.dir, "ref.md")
        with open(self.md_path, "w", encoding="utf-8") as fh:
            fh.write("---\ntitle: ref\nslug: ref\nyear: '2026'\n---\n\n" + body)

    def test_full_reference_uploaded_and_replaced_in_payload(self):
        self._write("![logo][logo-ref]\n\n[logo-ref]: images/logo.png")
        result = self.engine.sync(self.md_path, parent_id=1)
        self.assertTrue(result.ok)
        self.assertEqual(self.uploaded, ["images/logo.png"])
        body = self.created[0]["body"]
        self.assertIn('src="https://site/media/1.png"', body)

    def test_collapsed_reference_uploaded(self):
        self._write("![logo][]\n\n[logo]: images/logo.png")
        result = self.engine.sync(self.md_path, parent_id=1)
        self.assertTrue(result.ok)
        self.assertEqual(self.uploaded, ["images/logo.png"])
        self.assertIn('src="https://site/media/1.png"', self.created[0]["body"])

    def test_shortcut_reference_uploaded(self):
        self._write("![logo]\n\n[logo]: images/logo.png")
        result = self.engine.sync(self.md_path, parent_id=1)
        self.assertTrue(result.ok)
        self.assertEqual(self.uploaded, ["images/logo.png"])
        self.assertIn('src="https://site/media/1.png"', self.created[0]["body"])

    def test_remote_reference_definition_untouched(self):
        self._write("![ext][ext-ref]\n\n[ext-ref]: https://example.com/x.png")
        result = self.engine.sync(self.md_path, parent_id=1)
        self.assertTrue(result.ok)
        self.assertEqual(self.uploaded, [])  # remote не управляется
        # remote definition не тронута: payload сохраняет ref-форму, и
        # Markdown резолвит её в remote URL (никакой загрузки не было)
        self.assertIn('src="https://example.com/x.png"', self.created[0]["body"])

    def test_undefined_label_is_not_an_image(self):
        self._write("![logo][undefined]")
        result = self.engine.sync(self.md_path, parent_id=1)
        self.assertTrue(result.ok)
        self.assertEqual(self.uploaded, [])

    def test_local_reference_definition_missing_file_fails_closed(self):
        self._write("![logo][logo-ref]\n\n[logo-ref]: images/absent.png")
        with self.assertRaises(SyncError) as ctx:
            self.engine.sync(self.md_path, parent_id=1)
        self.assertIn("images/absent.png", str(ctx.exception))
        self.api.upload_image = self.api.upload_image  # нет вызовов загрузки
        self.assertEqual(self.uploaded, [])


class FenceCommonMarkTests(TestCase):
    """Закрытие фенса по CommonMark: невалидная closing-строка (текст после
    маркера) не закрывает код-блок — изображение после неё остаётся внутри
    кода и не проходит preflight/local_images."""

    def _dests(self, content):
        return [
            dest for _fs, _fe, _is, _ie, dest, _mode, _alt
            in iter_image_destinations(content)
        ]

    def test_invalid_closing_fence_keeps_block_open(self):
        content = (
            "![before](before.png)\n"
            "```\n"
            "![x](inside.png)\n"
            "``` эта строка с текстом не закрывает фенс\n"
            "![y](still-inside.png)\n"
            "```\n"
            "![after](after.png)\n"
        )
        self.assertEqual(self._dests(content), ["before.png", "after.png"])

    def test_shorter_fence_does_not_close(self):
        content = (
            "````\n"
            "![x](inside.png)\n"
            "```\n"
            "![y](still-inside.png)\n"
            "````\n"
            "![after](after.png)\n"
        )
        # закрывающий ``` короче открывающего ```` — блок остаётся открытым
        self.assertEqual(self._dests(content), ["after.png"])

    def test_backtick_fence_with_backtick_info_not_opened(self):
        content = "` `` info ` `\n![real](real.png)\n"
        # строка с бэктиками в инфостроке не открывает фенс — парсер не
        # считает последующий контент кодом
        self.assertEqual(self._dests(content), ["real.png"])


class DuplicateReferenceDedupTests(TestCase):
    """Повторные ссылки на один и тот же локальный путь: upload ровно один
    раз, оба image tokens получают один и тот же server URL."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="wdp-fu4-")
        with open(os.path.join(self.dir, "same.png"), "wb") as fh:
            fh.write(_png((4, 4, 4)))
        self.api = WagtailAPI("https://example.invalid/api/v3", "test-token")
        self.upload_count = [0]

        def fake_upload(path, year, slug, title):
            self.upload_count[0] += 1
            return {"id": 300, "download_url": "https://site/media/same.png"}

        self.api.upload_image = fake_upload
        self.created = []
        self.api.create_page = lambda payload, page_type, parent_id, publish: (
            self.created.append(payload) or {"id": 557, "mode": "создана", "data": {}}
        )
        self.engine = SyncEngine(self.api, "test.local")

    def test_same_path_uploaded_once_both_tokens_same_url(self):
        md_path = os.path.join(self.dir, "dup.md")
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write(
                "---\ntitle: dup\nslug: dup\nyear: '2026'\n---\n\n"
                "![a](same.png)\n\n![a](same.png)\n\n![a](same.png)"
            )
        result = self.engine.sync(md_path, parent_id=1)
        self.assertTrue(result.ok)
        self.assertEqual(self.upload_count[0], 1)
        body = self.created[0]["body"]
        self.assertEqual(body.count('src="https://site/media/same.png"'), 3)
