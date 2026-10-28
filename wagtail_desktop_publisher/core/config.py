# core/config.py — конфигурация publisher v2.
# Файл конфига: ~/.wagtail_publisher.json (0600, токен — секрет).
import datetime
import json
import os

CONFIG_FILE = os.path.expanduser("~/.wagtail_publisher.json")

# Тема привязана к домену так же, как в blog.middleware.ThemePaletteMiddleware.
# Позволяет publisher подхватывать «системную тему» сайта при публикации.
SITE_THEMES = {
    "vs-svet.ru": "nova",
    "zenway.ru": "zenway",
    "floppygames.ru": "floppy",
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_config(cfg):
    fd = os.open(CONFIG_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def theme_for_host(host):
    """Тема сайта по домену: nova / zenway / floppy (дефолт nova)."""
    host = (host or "").lower().split(":")[0]
    for domain, theme in SITE_THEMES.items():
        if domain in host:
            return theme
    return "nova"


CACHE_FILE = os.path.expanduser("~/.wagtail_publisher_cache.json")


def load_site_cache(site: str) -> dict:
    """Кэш справочников сайта (рубрики, теги) — JSON, обновляется из API."""
    if not site or not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data.get(site, {})
    except (json.JSONDecodeError, OSError):
        return {}


def save_site_cache(site: str, categories: list, tags: list):
    if not site:
        return
    data = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}
    data[site] = {
        "categories": categories,
        "tags": tags,
        "fetched_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
