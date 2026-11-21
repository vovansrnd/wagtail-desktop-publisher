"""Серверная часть publisher'а: Ninja-роутеры для Wagtail API v3.

Перенесено из основного проекта (vsproject/api_images.py + api_meta.py,
Д66) — ранее серверная часть существовала только в wagtail-blogs и
сторонний проект не мог включить приём публикаций.

Подключение в urls.py стороннего проекта — ДО первого обращения к
wagtail.api.v3.urls (Django Ninja запрещает add_router после доступа к
api.urls)::

    import wagtail_desktop_publisher.wagtail_api  # noqa: F401
    from wagtail.api.v3 import urls as wagtailapi_urls

    urlpatterns = [
        path("api/v3/", wagtailapi_urls.api.urls),
        ...
    ]

Эндпоинты: авторизация ЯВНО задана на каждом роутере через
BearerTokenAuth (токены Wagtail APIToken). Полагаться на глобальный auth
NinjaAPI нельзя: Wagtail создаёт api без глобального auth, штатные
read-endpoints Wagtail публичны по умолчанию — это поведение не
распространяется на кастомные маршруты publisher'а.
- POST /api/v3/images/                 — загрузка изображения в каталог
  year/slug: на сайте с wagtail-image-directories (поля year/slug у
  модели изображений + get_or_create_collection) используется схема
  директорий плагина; на голом Wagtail — нативные коллекции year/slug.
- GET  /api/v3/publisher-meta/categories/ — рубрики (на голом Wagtail —
  пустой список; на сайте с blog.Category — MPTT-дерево).
- GET  /api/v3/publisher-meta/tags/?search= — теги taggit.

Клиенты: CLI `wagtail-publisher` и GUI `wagtail-publisher-gui`.
"""
import logging
import os
import warnings

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.utils.text import slugify

from ninja import File, Form, Router
from ninja.files import UploadedFile

from wagtail.api.v3.auth import BearerTokenAuth
from wagtail.images import get_image_model

Image = get_image_model()

logger = logging.getLogger(__name__)

images_router = Router(tags=["publisher-images"])
meta_router = Router(tags=["publisher-meta"])

# --- изображения ----------------------------------------------------------


def _clean_directory_part(value, *, fallback="", max_length=255):
    cleaned = slugify(str(value or "").strip(), allow_unicode=True)
    return cleaned[:max_length] or fallback


def _validate_uploaded_image(upload):
    """Validate size, extension, decoded format and pixel count before saving."""
    try:
        from PIL import Image as PILImage
        from PIL import UnidentifiedImageError
    except ImportError:
        return "Image validation is unavailable on this server."

    max_size = int(getattr(settings, "PUBLISHER_IMAGE_MAX_UPLOAD_SIZE", 50 * 1024 * 1024))
    max_pixels = int(getattr(settings, "PUBLISHER_IMAGE_MAX_PIXELS", 89_478_485))
    size = getattr(upload, "size", None)
    if size is None or size <= 0:
        return "The uploaded image is empty or has no known size."
    if size > max_size:
        return f"Image exceeds the {max_size // (1024 * 1024)} MiB upload limit."

    name = getattr(upload, "name", "") or ""
    ext = os.path.splitext(name)[1].lower().lstrip(".")
    allowed_extensions = set(getattr(
        settings, "WAGTAILIMAGES_EXTENSIONS",
        ("bmp", "gif", "jpeg", "jpg", "png", "webp"),
    ))
    if ext not in allowed_extensions:
        return "This image file extension is not allowed."

    expected_format = PILImage.registered_extensions().get("." + ext)
    if not expected_format:
        return "This image file extension is not supported by the image decoder."
    file_obj = getattr(upload, "file", upload)
    try:
        file_obj.seek(0)
        with warnings.catch_warnings():
            warnings.simplefilter("error", PILImage.DecompressionBombWarning)
            with PILImage.open(file_obj) as image:
                if expected_format and image.format != expected_format:
                    return "The file extension does not match the image content."
                if image.width <= 0 or image.height <= 0:
                    return "The image dimensions are invalid."
                if max_pixels > 0 and image.width * image.height > max_pixels:
                    return "The image exceeds the configured pixel limit."
                image.verify()
    except (UnidentifiedImageError, OSError, ValueError, PILImage.DecompressionBombError,
            PILImage.DecompressionBombWarning):
        return "The uploaded file is not a valid supported image."
    finally:
        try:
            file_obj.seek(0)
        except Exception:
            pass
    return None


def _image_add_policy():
    from wagtail.permissions import policy_registry
    return policy_registry.get_by_type(Image)


def _native_collection(year, slug):
    """Находит/создаёт коллекцию путём year/slug на голом Wagtail."""
    from wagtail.models import Collection

    root = Collection.get_first_root_node()
    node = root
    for name in [str(year)] + ([str(slug)] if slug else []):
        child = node.get_children().filter(name=name).first()
        if child is None:
            child = node.add_child(name=name)
        node = child
    return node


def _image_to_dict(img, directory_scheme):
    data = {
        "id": img.id,
        "title": img.title,
        "url": img.file.url,
        "download_url": img.file.url,
        "width": getattr(img, "width", None),
        "height": getattr(img, "height", None),
        "file_size": img.get_file_size() if hasattr(img, "get_file_size") else None,
        "directory_scheme": "year/slug" if directory_scheme else "collections",
    }
    if directory_scheme:
        data["year"] = img.year
        data["slug"] = img.slug
    else:
        data["collection_id"] = img.collection_id
    return data


_HAS_DIRECTORY_FIELDS = all(
    any(f.name == name for f in Image._meta.get_fields())
    for name in ("year", "slug")
)
_HAS_GET_OR_CREATE_COLLECTION = hasattr(Image, "get_or_create_collection")
HAS_DIRECTORY_SCHEME = _HAS_DIRECTORY_FIELDS and _HAS_GET_OR_CREATE_COLLECTION


@images_router.post(
    "/",
    operation_id="publisher_images_upload",
    summary="Загрузить изображение (директория year/slug или коллекция)",
    auth=BearerTokenAuth(),
)
def upload_image(
    request,
    title: str = Form(...),
    file: UploadedFile = File(...),
    year: str = Form("misc"),
    slug: str = Form(""),
):
    validation_error = _validate_uploaded_image(file)
    if validation_error:
        return JsonResponse({"detail": validation_error}, status=400)

    # Normalize path components before they are used in collection names or
    # upload_to. A slash, backslash or dot segment must never become a path part.
    clean_year = _clean_directory_part(year, fallback="misc", max_length=50)
    clean_slug = _clean_directory_part(slug, fallback="", max_length=255)

    class _PublisherCollectionPermissionDenied(Exception):
        pass

    try:
        with transaction.atomic():
            if HAS_DIRECTORY_SCHEME:
                probe = Image(title="__permission_check__", year=clean_year, slug=clean_slug)
                probe.collection = probe.get_or_create_collection()
            else:
                target_collection = _native_collection(clean_year, clean_slug)
                probe = Image(title="__permission_check__", collection=target_collection)

            policy = _image_add_policy()
            if not policy.user_has_permission_for_instance(request.user, "add", probe):
                raise _PublisherCollectionPermissionDenied

            img = Image(title=(title or file.name).strip()[:255])
            img.file = file
            if HAS_DIRECTORY_SCHEME:
                img.year = clean_year
                img.slug = clean_slug
                img.collection = probe.collection
            else:
                img.collection = probe.collection
            img.save()
    except _PublisherCollectionPermissionDenied:
        return JsonResponse(
            {"detail": "Недостаточно прав для загрузки в эту коллекцию."}, status=403
        )
    except Exception:
        # Let Django's exception handlers log and report unexpected server errors;
        # do not disguise storage/DB failures as client-side 400 responses.
        logger.exception("Publisher image upload failed")
        raise

    return _image_to_dict(img, HAS_DIRECTORY_SCHEME)


# --- справочные данные (рубрики, теги) -------------------------------------


@meta_router.get(
    "/categories/",
    operation_id="publisher_categories",
    summary="Рубрики сайта (id, имя, родитель, уровень)",
    auth=BearerTokenAuth(),
)
def categories(request):
    try:
        from blog.models import Category
    except ImportError:
        return {"meta": {"total_count": 0}, "items": []}

    items = []
    for cat in Category.objects.all().order_by("tree_id", "lft"):
        items.append({
            "id": cat.id,
            "name": cat.name,
            "parent_id": cat.parent_id,
            "level": cat.level,
        })
    return {"meta": {"total_count": len(items)}, "items": items}


@meta_router.get(
    "/tags/",
    operation_id="publisher_tags",
    summary="Теги сайта (поиск для автодополнения)",
    auth=BearerTokenAuth(),
)
def tags(request, search: str = None, limit: int = 50):
    from taggit.models import Tag

    qs = Tag.objects.all().order_by("name")
    if search:
        qs = qs.filter(name__icontains=search)
    items = [
        {"id": t.id, "name": t.name}
        for t in qs[: max(1, min(limit, 200))]
    ]
    return {"meta": {"total_count": qs.count()}, "items": items}
