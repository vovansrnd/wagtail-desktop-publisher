# core/paths.py — безопасное построение путей экспорта (M3).
#
# Slug приходит с сервера (ответ API) и не может использоваться в путях
# напрямую: ../, абсолютные пути и symlink-каталоги внутри базового
# каталога не должны позволять писать снаружи.
import os
import re

# Оставляем читаемые компоненты: unicode word-символы, дефис; пробелы и
# подчёркивания → дефис (как у Django slugify allow_unicode=True).
_UNSAFE_RE = re.compile(r"[^\w\s-]", re.UNICODE)
_SPACES_RE = re.compile(r"[\s_]+")


def _safe_component(value):
    """Server-provided значение → один безопасный компонент пути
    (читаемый slug) либо None, если безопасный компонент не строится."""
    value = str(value or "").strip()
    value = _UNSAFE_RE.sub("", value)
    value = _SPACES_RE.sub("-", value).strip("-")
    if not value or set(value) <= {"."}:
        return None
    return value[:150]


def resolve_export_path(slug, base_dir):
    """Каталог экспорта для server-controlled slug.

    Возвращает realpath-каталог ВНУТРИ base_dir или ValueError, если
    безопасный компонент не строится либо итоговый путь (после разрешения
    существующих symlink) выходит за base_dir. Запись в этом случае не
    выполняется вызывающим кодом.
    """
    base = os.path.realpath(os.path.expanduser(base_dir))
    component = _safe_component(slug)
    if not component:
        raise ValueError(
            f"Небезопасный slug для экспорта: {slug!r} — безопасный "
            f"компонент пути не строится"
        )
    candidate = os.path.join(base, component)
    resolved = os.path.realpath(candidate)
    try:
        inside = os.path.commonpath((base, resolved)) == base
    except ValueError:  # разные диски (Windows)
        inside = False
    if not inside:
        raise ValueError(
            f"Путь экспорта вне базового каталога (symlink?): "
            f"{slug!r} → {resolved}"
        )
    return resolved
