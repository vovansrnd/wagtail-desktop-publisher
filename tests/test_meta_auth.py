"""Д67-C(P): регрессионные тесты H1 — анонимный доступ к metadata API.

H1 (Issue #1, коммент #7069596825): Wagtail v3 NinjaAPI создаётся без
глобального auth (wagtail/api/v3/api.py — проверено по исходникам 8.1),
кастомные meta-роутеры publisher не задавали собственную аутентификацию →
categories/tags были доступны анонимно на любом сайте, подключившем
wagtail_api.

Проверки:
- anonymous GET categories/tags → отказ (401);
- missing/invalid/revoked токен → отказ на обоих эндпоинтах;
- валидный APIToken → 200 в ожидаемом формате (endpoint-уровень auth);
- доказательство, что отказ даёт ИМЕННО endpoint-auth, а не middleware
  URLConf: штатный публичный /pages/ Wagtail анонимно возвращает 200,
  meta-роутеры при том же URLConf — 401;
- upload endpoint: аноним → 401; валидный токен БЕЗ права add на коллекцию
  → 403 (токен не является универсальной авторизацией).

Модель доступа (зафиксировано для отчёта): BearerTokenAuth проверяет
действительность Wagtail APIToken (digest, revoked_at, активный
пользователь) и подставляет его пользователя. Рубрики/теги — общая
таксономия сайта: дополнительная per-object policy на чтение не
применяется (фактическая область видимости Tag.objects.all() — глобальная;
вынесено отдельным пунктом отчёта).
"""
import io

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from wagtail.images import get_image_model
from wagtail.models import APIToken
from PIL import Image as PILImage

User = get_user_model()


class MetaEndpointAuthTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.editor = User.objects.create_user(
            username="wdp-editor", password="pw", is_staff=True
        )
        instance, plaintext = APIToken.create_token(
            user=cls.editor, name="regression-valid"
        )
        cls.token = plaintext

        revoked_instance, revoked_plain = APIToken.create_token(
            user=cls.editor, name="regression-revoked"
        )
        revoked_instance.revoke()
        cls.revoked_token = revoked_plain

    def _get(self, path, token=None):
        headers = {}
        if token is not None:
            headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        return Client().get(path, **headers)

    # --- 1/2: anonymous → отказ ---
    def test_anonymous_categories_rejected(self):
        response = self._get("/api/v3/publisher-meta/categories/")
        self.assertEqual(response.status_code, 401)

    def test_anonymous_tags_rejected(self):
        response = self._get("/api/v3/publisher-meta/tags/")
        self.assertEqual(response.status_code, 401)

    # --- 3: missing/invalid/revoked → отказ ---
    def test_missing_token_rejected_on_both_endpoints(self):
        self.assertEqual(
            self._get("/api/v3/publisher-meta/categories/", token="").status_code, 401
        )
        self.assertEqual(
            self._get("/api/v3/publisher-meta/tags/", token="").status_code, 401
        )

    def test_invalid_token_rejected_on_both_endpoints(self):
        for path in ("/api/v3/publisher-meta/categories/",
                     "/api/v3/publisher-meta/tags/"):
            self.assertEqual(
                self._get(path, token="wagtail_totally_invalid_token_value").status_code,
                401,
            )

    def test_revoked_token_rejected_on_both_endpoints(self):
        for path in ("/api/v3/publisher-meta/categories/",
                     "/api/v3/publisher-meta/tags/"):
            self.assertEqual(
                self._get(path, token=self.revoked_token).status_code, 401
            )

    # --- 4: валидный токен → 200 в ожидаемом формате ---
    def test_valid_token_gets_categories_in_expected_format(self):
        response = self._get("/api/v3/publisher-meta/categories/", token=self.token)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # тест-настройки без blog.models → пустой список, но формат контракта
        self.assertIn("meta", data)
        self.assertIn("items", data)
        self.assertEqual(data["meta"]["total_count"], len(data["items"]))

    def test_valid_token_gets_tags_in_expected_format(self):
        response = self._get("/api/v3/publisher-meta/tags/", token=self.token)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("meta", data)
        self.assertIn("items", data)

    # --- 5: отказ даёт endpoint-auth, а не middleware URLConf ---
    def test_endpoint_auth_is_not_urlconf_wide_protection(self):
        """Штатный публичный /pages/ Wagtail анонимно доступен (200) —
        значит 401 на meta-роутерах даёт их собственная auth-конфигурация,
        а не защита всего тестового URLConf."""
        pages = self._get("/api/v3/pages/")
        self.assertEqual(pages.status_code, 200)
        cats = self._get("/api/v3/publisher-meta/categories/")
        self.assertEqual(cats.status_code, 401)
        tags = self._get("/api/v3/publisher-meta/tags/")
        self.assertEqual(tags.status_code, 401)

    def test_meta_operations_declare_bearer_auth_in_registry(self):
        """Операции meta-роутеров декларируют BearerTokenAuth в реестре
        Ninja (не полагаемся только на поведение ответов)."""
        from wagtail.api.v3.urls import api as wagtail_api
        from ninja.security import HttpBearer

        # OpenAPI-схема: security requirements для publisher-meta операций
        declared = []
        schema = wagtail_api.get_openapi_schema()
        for path_item in schema.get("paths", {}).values():
            for op in path_item.values():
                if not isinstance(op, dict):
                    continue
                if "publisher" in (op.get("operationId") or ""):
                    declared.append(op.get("operationId"))
        self.assertIn("publisher_categories", declared)
        self.assertIn("publisher_tags", declared)
        for path_item in schema.get("paths", {}).values():
            for op in path_item.values():
                if not isinstance(op, dict):
                    continue
                op_id = op.get("operationId") or ""
                if op_id in ("publisher_categories", "publisher_tags"):
                    self.assertTrue(
                        op.get("security"),
                        f"{op_id} не декларирует security requirements",
                    )


class UploadEndpointAuthTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.no_rights = User.objects.create_user(
            username="wdp-no-rights", password="pw", is_staff=True
        )
        cls.superuser = User.objects.create_superuser(
            username="wdp-root", email="root@example.test", password="pw"
        )

    def _png(self):
        buf = io.BytesIO()
        PILImage.new("RGB", (40, 20), (5, 5, 5)).save(buf, format="PNG")
        return buf.getvalue()

    def _upload(self, token=None):
        headers = {}
        if token is not None:
            headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        client = Client()
        response = client.post(
            "/api/v3/publisher-images/",
            data={
                "title": "audit-upload",
                "year": "2026",
                "slug": "audit",
                "file": SimpleUpload(self._png(), name="a.png"),
            },
            **headers,
        )
        return response

    def test_anonymous_upload_rejected(self):
        response = self._upload()
        self.assertEqual(response.status_code, 401)
        self.assertEqual(get_image_model().objects.count(), 0)

    def test_valid_token_without_add_permission_gets_403(self):
        """Токен ≠ универсальная авторизация: валидный токен пользователя
        БЕЗ права add на коллекцию → 403, изображение не создаётся."""
        instance, plaintext = APIToken.create_token(
            user=self.no_rights, name="regression-no-rights"
        )
        response = self._upload(token=plaintext)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(get_image_model().objects.count(), 0)

    def test_superuser_token_uploads_image(self):
        instance, plaintext = APIToken.create_token(
            user=self.superuser, name="regression-super"
        )
        response = self._upload(token=plaintext)
        self.assertIn(response.status_code, (200, 201))
        data = response.json()
        self.assertTrue(data["id"])
        self.assertTrue(data["download_url"])
        self.assertEqual(data["directory_scheme"], "collections")


def SimpleUpload(content, name):
    """Тонкая обёртка над Django UploadedFile для ninja File(...)."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    return SimpleUploadedFile(name, content, content_type="image/png")
