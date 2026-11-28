"""Д67-C(P) Issue #7: согласованность raw-body со всеми этапами pipeline.

Единый source-of-truth тела: сканирование изображений, content_hash,
позиционная подстановка URL и Markdown→HTML работают по одному и тому же
raw-телу (YAML frontmatter, без content.strip() библиотеки). Сценарии —
из задания Issue #7; сеть и реальные сайты не используются.
"""
import os
import tempfile
from unittest import mock

from django.test import TestCase

import markdown as md_lib

from wagtail_desktop_publisher.core.sync import Article, SyncEngine, SyncError, WagtailAPI

from tests.test_sync_hardening import _png_bytes

MD_EXTENSIONS = ["extra", "sane_lists"]  # тот же набор, что в payload rendering


def _render(body):
    return md_lib.markdown(body, extensions=MD_EXTENSIONS)


class RawBodyConsistencyTests(TestCase):
    """Интеграционный репродюсер из Issue #7: тело начинается с
    четырёхпробельной строки ``` — literal indented code; сразу после неё
    обычное изображение. После content.strip() библиотеки текст начинается
    с ``` — прежний replacer считал изображение частью кода."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="wdp-issue7-")
        with open(os.path.join(self.dir, "photo.png"), "wb") as fh:
            fh.write(_png_bytes((7, 8, 9)))
        self.api = WagtailAPI("https://example.invalid/api/v3", "test-token")
        self.uploaded = []

        def fake_upload(path, year, slug, title):
            self.uploaded.append(os.path.basename(path))
            return {"id": 400, "download_url": "https://site/media/photo.png"}

        self.api.upload_image = fake_upload
        self.created = []
        self.api.create_page = lambda payload, page_type, parent_id, publish: (
            self.created.append(payload) or {"id": 601, "mode": "создана", "data": {}}
        )
        self.engine = SyncEngine(self.api, "test.local")
        self.md_path = os.path.join(self.dir, "sample.md")
        with open(self.md_path, "w", encoding="utf-8") as fh:
            fh.write(
                "---\ntitle: sample\nslug: sample\nyear: '2026'\n---\n\n"
                "    ```\n"
                "    literal code\n"
                "![photo](photo.png)\n"
                "```\n"
            )

    def test_image_uploaded_once_and_rendered_exactly_once(self):
        result = self.engine.sync(self.md_path, parent_id=1)
        self.assertTrue(result.ok)
        # upload ровно один раз
        self.assertEqual(self.uploaded, ["photo.png"])
        # конечный payload: <img src="server-url"> ровно один раз
        body = self.created[0]["body"]
        self.assertEqual(body.count('src="https://site/media/photo.png"'), 1)
        # literal code остаётся кодом, изображение не попало в код-блок
        self.assertIn("literal code", body)
        # локальный путь не остался в payload
        self.assertNotIn("(photo.png)", body)
        self.assertNotIn('src="photo.png"', body)

    def test_disk_preserves_original_body_after_sync(self):
        self.engine.sync(self.md_path, parent_id=1)
        on_disk = open(self.md_path, encoding="utf-8").read()
        # тело статьи (после frontmatter) сохранено с исходными отступами
        body = on_disk.split("---\n\n", 1)[1]
        self.assertIn("    ```\n", body)
        self.assertIn("    literal code\n", body)
        self.assertIn("![photo](photo.png)\n", body)
        # повторная загрузка файла не искажает тело
        body_lines_before = body.splitlines()
        second = self.engine.sync(self.md_path, parent_id=1)
        self.assertEqual(second["status"], "skipped")
        on_disk2 = open(self.md_path, encoding="utf-8").read()
        self.assertEqual(on_disk2.split("---\n\n", 1)[1].splitlines(),
                         body_lines_before)

    def test_raw_and_rendered_agree_on_image(self):
        """Arbiter-проверка: scanner и python-markdown (те же extensions,
        что в payload rendering) согласны, что photo.png — реальное
        изображение статьи."""
        article = Article(self.md_path)
        scanner_dests = [dest for _fs, _fe, _is, _ie, dest, _mode, _alt
                         in iter_image_destinations_safe(article)]
        rendered = _render(article.body)
        self.assertIn('src="photo.png"', rendered)
        self.assertIn("photo.png", scanner_dests)


def iter_image_destinations_safe(article):
    from wagtail_desktop_publisher.core.sync import iter_image_destinations

    return list(iter_image_destinations(article.body))


class HashDistinguishesLeadingIndentationTests(TestCase):
    """Два документа с одинаковым post.content после strip, но разными
    raw-семантикой (leading indentation), не считаются одинаковыми:
    content_hash различен, повторный sync возвращает update, а не skipped."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="wdp-issue7-hash-")
        with open(os.path.join(self.dir, "photo.png"), "wb") as fh:
            fh.write(_png_bytes((11, 12, 13)))
        self.api = WagtailAPI("https://example.invalid/api/v3", "test-token")
        self.uploaded = []

        def fake_upload(path, year, slug, title):
            self.uploaded.append(os.path.basename(path))
            return {"id": 500, "download_url": "https://site/media/hash.png"}

        self.api.upload_image = fake_upload
        self.created = []
        self.api.create_page = lambda payload, page_type, parent_id, publish: (
            self.created.append(payload) or {"id": 602, "mode": "создана", "data": {}}
        )
        self.api.update_page = mock.Mock(
            return_value={"id": 602, "mode": "обновлена", "data": {}}
        )
        self.engine = SyncEngine(self.api, "test.local")

    def test_same_stripped_content_different_raw_semantics_differ(self):
        # doc A: 4-пробельная строка ``` — literal indented code; фото —
        # реальное изображение ПОСЛЕ код-блока
        doc_a = (
            "---\ntitle: t\nslug: t\nyear: '2026'\n---\n\n"
            "    ```\n"
            "    literal code\n"
            "```\n\n"
            "![photo](photo.png)\n"
        )
        # doc B: тот же frontmatter; после strip тело совпадает с A,
        # но фенс с 0 отступом — изображение ВНУТРИ fenced code
        doc_b = (
            "---\ntitle: t\nslug: t\nyear: '2026'\n---\n\n"
            "```\n"
            "    literal code\n"
            "```\n\n"
            "![photo](photo.png)\n"
        )
        # post.content после strip идентичен
        a = Article(self._write("a.md", doc_a))
        b = Article(self._write("b.md", doc_b))
        self.assertEqual(a.post.content, b.post.content)
        # raw-семантика различна → хэши различны
        self.assertNotEqual(a.body, b.body)
        self.assertNotEqual(a.content_hash("t", ""), b.content_hash("t", ""))

    def test_semantics_change_returns_update_not_skipped(self):
        """Статья, синхронизированная с doc A (изображение загружено и
        рендерится), затем файл заменён на doc B: post.content после strip
        ИДЕНТИЧЕН (различие — только ведущий отступ первой строки), но
        raw-семантика изменилась — sync обязан вернуть updated, а не
        skipped; в B изображение попадает в fenced code и не рендерится."""
        path = os.path.join(self.dir, "switch.md")
        doc_a = (
            "---\ntitle: t\nslug: t\nyear: '2026'\n---\n\n"
            "    ```\n"
            "    literal code\n"
            "![photo](photo.png)\n"
            "```\n"
        )
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(doc_a)
        first = self.engine.sync(path, parent_id=1)
        self.assertEqual(first["status"], "created")
        self.assertEqual(self.uploaded, ["photo.png"])
        # в A изображение рендерится: raw-пайплайн согласован с рендером
        self.assertIn('src="https://site/media/hash.png"', self.created[0]["body"])

        doc_b_body = "```\n    literal code\n![photo](photo.png)\n```\n"
        # замена ТОЛЬКО тела: frontmatter первого sync (wagtail_id,
        # content_hash от A) сохраняется — меняется семантика тела
        saved = open(path, encoding="utf-8").read()
        head = saved.split("---\n\n", 1)[0] + "---\n\n"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(head + doc_b_body)
        # post.content после strip идентичен для A и B (различие —
        # только ведущий отступ первой строки тела)
        a_after = Article(self._write("a-check.md", doc_a)).post.content
        b_check = head + doc_b_body
        b_after = Article(self._write("b-check.md", b_check)).post.content
        self.assertEqual(a_after, b_after)
        second = self.engine.sync(path, parent_id=1)
        # raw-семантика изменилась → update, а не skipped
        self.assertEqual(second["status"], "updated")
        self.api.update_page.assert_called_once()
        # в B изображение внутри fenced code: новой загрузки нет, в payload
        # server-URL для него не появляется
        self.assertEqual(self.uploaded, ["photo.png"])
        self.assertNotIn('src="https://site/media/photo.png"',
                         self.api.update_page.call_args[0][1]["body"])

    def _write(self, name, content):
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path


class ParagraphContinuationArbiterTests(TestCase):
    """Scanner сверяется с фактическим HTML того же Python-Markdown:
    indented code block не может прерывать абзац — четырёхпробельная
    строка с изображением внутри абзаца рендерится как inline image и
    обязана попасть в preflight. Контрольный кейс: пустая строка перед
    indented code block — изображение внутри literal code исключается."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="wdp-issue7-cont-")
        with open(os.path.join(self.dir, "real.png"), "wb") as fh:
            fh.write(_png_bytes((21, 22, 23)))
        self.api = WagtailAPI("https://example.invalid/api/v3", "test-token")
        self.uploaded = []
        self.api.upload_image = mock.Mock(
            side_effect=lambda path, year, slug, title: (
                self.uploaded.append(os.path.basename(path)) or
                {"id": 600, "download_url": "https://site/media/real.png"}
            )
        )
        self.created = []
        self.api.create_page = lambda payload, page_type, parent_id, publish: (
            self.created.append(payload) or {"id": 603, "mode": "создана", "data": {}}
        )
        self.engine = SyncEngine(self.api, "test.local")

    def _md(self, body):
        self.md_path = os.path.join(self.dir, "article.md")
        with open(self.md_path, "w", encoding="utf-8") as fh:
            fh.write("---\ntitle: t\nslug: t\nyear: '2026'\n---\n\n" + body)

    def test_paragraph_continuation_image_is_preflighted(self):
        body = "Paragraph first line\n    ![missing](missing.png)"
        self._md(body)
        # arbiter: тот же Python-Markdown рендерит inline image
        rendered = _render(body)
        self.assertIn('src="missing.png"', rendered)
        with self.assertRaises(SyncError) as ctx:
            self.engine.sync(self.md_path, parent_id=1)
        self.assertIn("missing.png", str(ctx.exception))
        self.api.upload_image.assert_not_called()
        self.assertEqual(self.created, [])

    def test_blank_line_indented_code_image_is_excluded(self):
        body = "Para\n\n    ![x](in-code.png)\n\n![real](real.png)"
        self._md(body)
        # arbiter: изображение внутри indented code НЕ рендерится как
        # <img> (литеральный текст в <pre><code> — ожидаемо)
        rendered = _render(body)
        self.assertNotIn('src="in-code.png"', rendered)
        self.assertIn('src="real.png"', rendered)
        result = self.engine.sync(self.md_path, parent_id=1)
        self.assertTrue(result.ok)
        self.assertEqual(self.uploaded, ["real.png"])
        body_html = self.created[0]["body"]
        self.assertNotIn('src="in-code.png"', body_html)
        self.assertIn('src="https://site/media/real.png"', body_html)

    def test_fences_zero_to_three_space_indent_still_work(self):
        """Контроль из Issue #7: фенсы с 0–3 пробелами и закрывающий фенс
        с 4 пробелами — прежние тесты сохранены; здесь быстрый arbiter-
        контроль смешанного кейса."""
        body = (
            "   ```\n"
            "   ![x](inside.png)\n"
            "   ```\n\n"
            "![real](real.png)"
        )
        self._md(body)
        rendered = _render(body)
        self.assertNotIn('src="inside.png"', rendered)
        self.assertIn('src="real.png"', rendered)
        result = self.engine.sync(self.md_path, parent_id=1)
        self.assertTrue(result.ok)
        self.assertEqual(self.uploaded, ["real.png"])
