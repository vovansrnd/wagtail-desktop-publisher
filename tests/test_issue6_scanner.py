"""Д67-C(P) Issue #6: два дефекта scanner/replacer.

1. Порядок токенов: inline, full/collapsed и shortcut формы собираются в
   единый набор и обрабатываются строго в порядке исходных позиций —
   reference-style ПЕРЕД inline и любые смешения не повреждают payload.
2. CommonMark отступ фенса: максимум 3 пробела; строка с 4+ пробелами и ```
   — indented code block, не фенс; изображение после неё видно preflight.
"""
import os
import tempfile
import unittest
from unittest import mock

from django.test import TestCase

from wagtail_desktop_publisher.core.sync import (
    SyncEngine,
    SyncError,
    WagtailAPI,
    iter_image_destinations,
    replace_image_destinations,
)

from tests.test_sync_hardening import _png_bytes


class TokenOrderTests(unittest.TestCase):
    """Порядок токенов строго по исходным позициям при любых смешениях форм."""

    def _positions(self, content):
        return [
            (fs, fe, dest, mode)
            for fs, fe, _is, _ie, dest, mode, _alt
            in iter_image_destinations(content)
        ]

    def _dests(self, content):
        return [
            dest for _fs, _fe, _is, _ie, dest, _mode, _alt
            in iter_image_destinations(content)
        ]

    def test_reference_before_inline_yields_document_order(self):
        content = "![ref][r]\n\n[ro]: placeholder\n[r]: r.png\n\nТекст между.\n\n![inline](i.png)"
        positions = self._positions(content)
        # оба токена, строго по возрастанию позиций
        self.assertEqual([dest for _s, _e, dest, _m in positions], ["r.png", "i.png"])
        starts = [fs for fs, _fe, _d, _m in positions]
        self.assertEqual(starts, sorted(starts))
        self.assertEqual([mode for _s, _e, _d, mode in positions], ["ref", "inline"])

    def test_inline_before_reference_yields_document_order(self):
        content = "![inline](i.png)\n\nТекст между.\n\n![ref][r]\n\n[r]: r.png"
        positions = self._positions(content)
        self.assertEqual([dest for _s, _e, dest, _m in positions], ["i.png", "r.png"])
        self.assertEqual([mode for _s, _e, _d, mode in positions], ["inline", "ref"])

    def test_mixed_forms_all_collected_in_order(self):
        content = (
            "![shortcut]\n\n[shortcut]: s.png\n"
            "![collapsed][]\n\n[collapsed]: c.png\n"
            "![full][f]\n\n[f]: f.png\n"
            "![inline](i.png)\n"
        )
        dests = self._dests(content)
        self.assertEqual(dests, ["s.png", "c.png", "f.png", "i.png"])

    def test_replacement_preserves_text_and_order_when_mixed(self):
        content = (
            "Первый абзац.\n\n"
            "![ref][r]\n\n[r]: r.png\n\n"
            "Средний абзац с словами.\n\n"
            "![inline](i.png)\n\n"
            "Хвостовой абзац."
        )
        urls = {"r.png": "https://site/media/1.png", "i.png": "https://site/media/2.png"}
        out = replace_image_destinations(content, urls.get)
        # все три URL присутствуют
        self.assertIn("![ref](https://site/media/1.png)", out)
        self.assertIn("![inline](https://site/media/2.png)", out)
        # исходный текст/абзацы не потеряны и не переставлены
        for marker in ("Первый абзац.", "Средний абзац с словами.", "Хвостовой абзац."):
            self.assertIn(marker, out)
        self.assertLess(
            out.index("Первый абзац."), out.index("Средний абзац с словами.")
        )
        self.assertLess(
            out.index("Средний абзац с словами."), out.index("Хвостовой абзац.")
        )
        # локальные destinations не остались в payload
        self.assertNotIn("(r.png)", out)
        self.assertNotIn("(i.png)", out)
        # сегмент между картинками не задублирован
        self.assertEqual(out.count("Средний абзац с словами."), 1)
        self.assertEqual(out.count("Хвостовой абзац."), 1)

    def test_local_ref_and_remote_ref_coexist_with_inline(self):
        content = (
            "![local][lr]\n\n[lr]: lr.png\n\n"
            "![ext][er]\n\n[er]: https://example.com/x.png\n\n"
            "![inline](i.png)"
        )
        urls = {"lr.png": "https://site/media/1.png", "i.png": "https://site/media/2.png"}
        out = replace_image_destinations(content, urls.get)
        # локальная ref заменилась на server URL
        self.assertIn("![local](https://site/media/1.png)", out)
        # inline заменилась на свой URL
        self.assertIn("![inline](https://site/media/2.png)", out)
        # remote ref остался нетронутым (Markdown сам резолвит definition)
        self.assertIn("![ext][er]", out)
        # дубликатов нет
        self.assertEqual(out.count("https://site/media/1.png"), 1)
        self.assertEqual(out.count("https://site/media/2.png"), 1)
        self.assertEqual(out.count("![ext][er]"), 1)


class FenceIndentCommonMarkTests(unittest.TestCase):
    def _dests(self, content):
        return [
            dest for _fs, _fe, _is, _ie, dest, _mode, _alt
            in iter_image_destinations(content)
        ]

    def test_four_space_indent_does_not_open_fence(self):
        """4+ пробела + ``` — indented code block, НЕ фенс: следующее
        настоящее изображение собирается (Issue #6, минимальный case)."""
        content = (
            "    ```\n"
            "    literal code\n"
            "![missing](missing.png)\n"
            "```\n"
        )
        self.assertEqual(self._dests(content), ["missing.png"])

    def test_four_space_indent_does_not_close_fence(self):
        """Закрывающий маркер с 4+ пробелами не закрывает настоящий фенс:
        изображение после него остаётся внутри кода и не собирается."""
        content = (
            "```\n"
            "![x](inside.png)\n"
            "    ```\n"
            "![y](after.png)\n"
            "```\n"
            "![real](real.png)\n"
        )
        # inside.png — содержимое фенса (исключён); 4-пробельный маркер НЕ
        # закрыл фенс → after.png тоже внутри кода; real — после валидного
        # закрытия
        self.assertEqual(self._dests(content), ["real.png"])

    def test_zero_to_three_space_fences_still_recognized(self):
        for indent in ("", " ", "  ", "   "):
            content = (
                f"{indent}```\n"
                f"{indent}![x](inside.png)\n"
                f"{indent}```\n"
                "![real](real.png)\n"
            )
            self.assertEqual(self._dests(content), ["real.png"], repr(indent))

    def test_image_inside_indented_code_not_collected(self):
        content = (
            "Обычный текст.\n\n"
            "    ![indented](indented.png)\n"
            "    продолжение кода\n\n"
            "![real](real.png)\n"
        )
        self.assertEqual(self._dests(content), ["real.png"])


class PreflightSeesImageAfterIndentedFenceTests(TestCase):
    """Интеграционная проверка минимального кейса Issue #6: sync завершается
    SyncError на preflight (missing.png), а не уходит в синхронизацию."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="wdp-issue6-")
        self.api = WagtailAPI("https://example.invalid/api/v3", "test-token")
        self.api.upload_image = mock.Mock(
            side_effect=AssertionError("upload не должен вызываться")
        )
        self.created = []
        self.api.create_page = lambda payload, page_type, parent_id, publish: (
            self.created.append(payload) or {"id": 558, "mode": "создана", "data": {}}
        )
        self.engine = SyncEngine(self.api, "test.local")

    def test_missing_image_after_indented_fence_fails_closed(self):
        md_path = os.path.join(self.dir, "article.md")
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write(
                "---\ntitle: t\nslug: t\nyear: '2026'\n---\n\n"
                "    ```\n"
                "    literal code\n"
                "![missing](missing.png)\n"
                "```\n"
            )
        with self.assertRaises(SyncError) as ctx:
            self.engine.sync(md_path, parent_id=1)
        self.assertIn("missing.png", str(ctx.exception))
        self.api.upload_image.assert_not_called()
        self.assertEqual(self.created, [])
