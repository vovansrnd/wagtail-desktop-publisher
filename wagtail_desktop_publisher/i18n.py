# i18n.py — мультиязычность publisher'а (gettext).
#
# Каталоги: locale/<lang>/LC_MESSAGES/wagtail_desktop_publisher.{po,mo}
# Языки: en (базовый), ru, de, es, fr, it, pt_BR, nl, pl, tr, zh_CN, ja, ko.
# Пересборка .mo: python scripts/build_locales.py
import gettext
import os

LOCALE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "locale")
)

SUPPORTED_LANGUAGES = [
    ("en", "English"),
    ("ru", "Русский"),
    ("de", "Deutsch"),
    ("es", "Español"),
    ("fr", "Français"),
    ("it", "Italiano"),
    ("pt_BR", "Português (Brasil)"),
    ("nl", "Nederlands"),
    ("pl", "Polski"),
    ("tr", "Türkçe"),
    ("zh_CN", "简体中文"),
    ("ja", "日本語"),
    ("ko", "한국어"),
]


def detect_language() -> str:
    """Язык системы (напр. ru_RU → ru), с фолбэком на en."""
    lang = os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or ""
    if not lang:
        try:
            import locale

            lang = locale.getdefaultlocale()[0] or ""
        except Exception:
            lang = ""
    lang = (lang or "en").split(".")[0].replace("-", "_")
    base = lang.split("_")[0]
    known = {code for code, _name in SUPPORTED_LANGUAGES}
    return lang if lang in known else base


def get_translation(lang: str | None = None):
    """Возвращает gettext-функцию; отсутствующие строки падают на en."""
    if not lang:
        lang = detect_language()
    translation = gettext.translation(
        "wagtail_desktop_publisher", LOCALE_DIR, languages=[lang, "en"], fallback=True
    )
    return translation.gettext
