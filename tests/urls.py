"""URLConf тестов: монтирование роутеров publisher на Wagtail API v3.

Как в реальном хост-проекте: роутеры добавляются на инстанс api ДО
обращения к api.urls (Django Ninja запрещает add_router после).
"""
from wagtail.api.v3.api import api  # noqa: E402
from wagtail_desktop_publisher.wagtail_api import (  # noqa: E402
    images_router, meta_router,
)

api.add_router("/publisher-images/", images_router)
api.add_router("/publisher-meta/", meta_router)

from django.urls import path  # noqa: E402

urlpatterns = [
    path("api/v3/", api.urls),
]
