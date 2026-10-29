# core/config.py — конфигурация publisher v2.
# Файл конфига: ~/.wagtail_publisher.json (0600, токен — секрет).
import datetime
import json
import os
import tempfile
from urllib.parse import urlsplit

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
    """Atomically save secrets with owner-only permissions, even over old files."""
    config_dir = os.path.dirname(os.path.abspath(CONFIG_FILE))
    fd, tmp_path = tempfile.mkstemp(prefix=".wagtail-publisher-", dir=config_dir, text=True)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, CONFIG_FILE)
        try:
            os.chmod(CONFIG_FILE, 0o600)
        except OSError:
            pass
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def theme_for_host(host):
    """Select theme only for the configured host or one of its subdomains."""
    raw_host = (host or "").strip().lower()
    if "://" in raw_host:
        host = urlsplit(raw_host).hostname or ""
    else:
        # urlsplit also handles a normal host:port pair without substring matching.
        host = urlsplit("//" + raw_host).hostname or ""
    host = host.rstrip(".")
    for domain, theme in SITE_THEMES.items():
        if host == domain or host.endswith("." + domain):
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
