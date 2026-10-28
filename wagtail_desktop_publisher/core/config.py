# core/config.py — конфигурация publisher v2.
# Файл конфига: ~/.wagtail_publisher.json (0600, токен — секрет).
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
