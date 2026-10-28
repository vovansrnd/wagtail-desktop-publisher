# gui/app.py — GUI publisher v2 на NiceGUI.
#
# Запуск: wagtail-publisher-gui (открывает http://localhost:8333)
# Тема: следует системной настройке ОС (тёмная/светлая) автоматически.
# Языки: системный язык или выбор в шапке (13 языков).
from __future__ import annotations

import os
import threading

import frontmatter
from nicegui import ui

from wagtail_desktop_publisher.core.config import load_config, save_config
from wagtail_desktop_publisher.core.sync import Article, SyncEngine, SyncError, WagtailAPI
from wagtail_desktop_publisher.i18n import SUPPORTED_LANGUAGES, get_translation

PAGE_TYPE = "blog.BlogPage"
CFG = load_config()
STATE = {"lang": CFG.get("language") or None}


class UIState:
    """Состояние сессии браузера."""

    def __init__(self):
        self.cfg = load_config()
        self.api: WagtailAPI | None = None
        self.sites: list = []
        self.site_id: int | None = None
        self.parent_id: int | None = None
        self.article_path: str = (self.cfg.get("last_article") or "").strip()


@ui.page("/")
async def build_index():
    st = UIState()
    _ = get_translation(STATE["lang"])

    with ui.header().classes("items-center justify-between"):
        ui.label(_("Wagtail Desktop Publisher")).classes("text-lg font-bold")
        ui.select(
            {code: name for code, name in SUPPORTED_LANGUAGES},
            value=STATE["lang"] if STATE["lang"] in {c for c, _ in SUPPORTED_LANGUAGES} else None,
            on_change=lambda e: (save_lang(e.value or None), ui.navigate.reload()),
            label=_("Language"),
        ).props("dense outlined")

    with ui.splitter(value=40).classes("w-full") as splitter:
        # ---------------- ЛЕВАЯ КОЛОНКА: подключение и статья ----------------
        with splitter.before:
            with ui.card().classes("w-full"):
                ui.label(_("Connect")).classes("text-md font-bold")
                url_in = ui.input(_("API URL"), value=st.cfg.get("api_url", "")).classes("w-full")
                token_in = ui.input(
                    _("Token"), value=st.cfg.get("token", ""),
                    password=True, password_toggle_button=True,
                ).classes("w-full")
                site_sel = ui.select({}, label=_("Site"), with_input=True).classes("w-full")
                section_sel = ui.select({}, label=_("Section"), with_input=True).classes("w-full")

                def do_connect():
                    _ = get_translation(STATE["lang"])
                    try:
                        st.api = WagtailAPI(url_in.value.strip(), token_in.value.strip())
                        st.sites = st.api.sites()
                    except SyncError as e:
                        ui.notify(f"{_('Connection error')}: {e}", type="negative")
                        return
                    options = {
                        s["root_page_id"]: (
                            s.get("site_name") or s.get("hostname") or f"site {s['id']}"
                        )
                        for s in st.sites
                    }
                    site_sel.options = options
                    site_sel.value = list(options)[0] if options else None
                    site_sel.update()
                    st.cfg["api_url"] = url_in.value.strip()
                    st.cfg["token"] = token_in.value.strip()
                    save_config(st.cfg)
                    ui.notify(f"OK: {len(st.sites)}", type="positive")

                ui.button(_("Connect"), on_click=do_connect).props("outline")

                def on_site_change(e):
                    st.site_id = e.value
                    if not (st.api and e.value):
                        return
                    resp = st.api.pages(child_of=e.value, limit=100)
                    opts = {e.value: f"★ id {e.value}"}
                    for p in resp.get("items", []):
                        opts[p["id"]] = p["title"]
                    section_sel.options = opts
                    section_sel.value = e.value

                site_sel.on_value_change(on_site_change)
                section_sel.on_value_change(lambda e: setattr(st, "parent_id", e.value))

            with ui.card().classes("w-full"):
                ui.label(_("Article file (.md)")).classes("text-md font-bold")
                path_in = ui.input(_("Path to the article"), value=st.article_path).classes("w-full")
                title_in = ui.input(_("Title")).classes("w-full")
                slug_in = ui.input(_("Slug (URL)")).classes("w-full")
                year_in = ui.input(_("Year"), value="2026").classes("w-32")
                info_label = ui.label("").classes("text-xs text-grey-7")

                def on_path_change(e):
                    st.article_path = (e.value or "").strip()

                path_in.on_value_change(on_path_change)

                def on_scan():
                    _ = get_translation(STATE["lang"])
                    st.article_path = path_in.value.strip()
                    if not st.article_path or not os.path.exists(st.article_path):
                        ui.notify("404", type="negative")
                        return
                    post = frontmatter.load(st.article_path)
                    title_in.value = post.get("title", "")
                    slug_in.value = post.get("slug", "")
                    year_in.value = str(post.get("year", "2026"))
                    imgs = Article(st.article_path).local_images()
                    missing = sum(1 for _rel, p in imgs if p is None)
                    info_label.text = (
                        f"{_('Images')}: {len(imgs)}"
                        + (f" ({missing} ⚠️)" if missing else "")
                    )
                    st.cfg["last_article"] = st.article_path
                    save_config(st.cfg)

                ui.button(_("Scan"), on_click=on_scan).props("flat dense")

                publish_switch = ui.switch(
                    _("Publish immediately (otherwise save as draft)"),
                    value=bool(st.cfg.get("last_published", False)),
                )

        # ---------------- ПРАВАЯ КОЛОНКА: лог и кнопка ----------------
        with splitter.after:
            sync_btn = ui.button(_("Sync article to Wagtail")).classes("w-full")
            log_box = ui.log(max_lines=400).classes("w-full flex-grow")

        def do_sync():
            _ = get_translation(STATE["lang"])

            def worker():
                try:
                    engine = SyncEngine(st.api, st.cfg.get("site", ""))
                    res = engine.sync(
                        st.article_path,
                        parent_id=st.parent_id,
                        publish=publish_switch.value,
                        title=title_in.value or None,
                        slug=slug_in.value or None,
                        year=year_in.value or None,
                        log=lambda m: log_box.push(m),
                    )
                    log_box.push(
                        f"{_('Article synced successfully')}: id {res.get('id')} ({res.get('mode')})"
                    )
                    st.cfg["last_published"] = publish_switch.value
                    save_config(st.cfg)
                except SyncError as e:
                    log_box.push(f"❌ {e}")
                except Exception as e:  # сеть/сервер — показываем в логе, GUI не падает
                    log_box.push(f"❌ {e.__class__.__name__}: {e}")

            threading.Thread(target=worker, daemon=True).start()

        sync_btn.on_click(do_sync)


def save_lang(lang):
    CFG["language"] = lang
    save_config(CFG)


def main():
    ui.run(
        title="Wagtail Desktop Publisher",
        port=int(os.environ.get("PUBLISHER_PORT", "8333")),
        dark=None,  # None = следовать системной теме ОС (тёмная/светлая)
        reload=False,
        show=False,
        storage_secret="wagtail-desktop-publisher",
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
