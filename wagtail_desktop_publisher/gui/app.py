# gui/app.py — нативный GUI publisher v2 на CustomTkinter.
#
# Запуск: wagtail-publisher-gui
# Тема: следует системной настройке ОС (тёмная/светлая) —
#       customtkinter.set_appearance_mode("system").
# Язык: системный или из конфига (ключ "language"); 13 языков.
from __future__ import annotations

import os
import threading

import customtkinter as ctk
import frontmatter

from wagtail_desktop_publisher.core.config import load_config, save_config
from wagtail_desktop_publisher.core.sync import Article, SyncEngine, SyncError, WagtailAPI
from wagtail_desktop_publisher.i18n import SUPPORTED_LANGUAGES, get_translation

PAGE_TYPE = "blog.BlogPage"
CFG = load_config()
LANG = CFG.get("language") or None


def _(key: str) -> str:
    return get_translation(LANG)(key)


class PublisherApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("system")   # тема как в ОС
        ctk.set_default_color_theme("blue")
        self.title(_("Wagtail Desktop Publisher"))
        self.geometry("980x720")
        self.minsize(880, 640)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        self.cfg = dict(CFG)
        self.api: WagtailAPI | None = None
        self.sites: list = []
        self.site_id = None
        self.parent_id = None
        self.article_path = (self.cfg.get("last_article") or "").strip()

        self._build()
        if self.cfg.get("token"):
            self.after(300, self._connect)

    # ---------------- построение интерфейса ----------------

    def _build(self):
        # --- подключение ---
        conn = ctk.CTkFrame(self)
        conn.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        conn.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(conn, text=_("API URL")).grid(row=0, column=0, sticky="w", padx=10, pady=6)
        self.url_in = ctk.CTkEntry(conn, width=340)
        self.url_in.insert(0, self.cfg.get("api_url", ""))
        self.url_in.grid(row=0, column=1, sticky="ew", padx=6, pady=6)

        ctk.CTkLabel(conn, text=_("Token")).grid(row=0, column=2, sticky="w", padx=6)
        self.token_in = ctk.CTkEntry(conn, width=240, show="•")
        self.token_in.insert(0, self.cfg.get("token", ""))
        self.token_in.grid(row=0, column=3, sticky="ew", padx=6, pady=6)

        self.connect_btn = ctk.CTkButton(conn, text=_("Connect"), command=self._connect, width=120)
        self.connect_btn.grid(row=0, column=4, padx=10, pady=6)

        # --- сайт и раздел ---
        site = ctk.CTkFrame(self)
        site.grid(row=1, column=0, sticky="ew", padx=12, pady=6)
        site.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(site, text=_("Site")).grid(row=0, column=0, sticky="w", padx=10, pady=6)
        self.site_box = ctk.CTkComboBox(site, width=380, state="readonly",
                                        command=self._on_site)
        self.site_box.set("—")
        self.site_box.grid(row=0, column=1, sticky="ew", padx=6, pady=6)
        ctk.CTkLabel(site, text=_("Section")).grid(row=1, column=0, sticky="w", padx=10, pady=6)
        self.section_box = ctk.CTkComboBox(site, width=380, state="readonly",
                                           command=self._on_section)
        self.section_box.set("—")
        self.section_box.grid(row=1, column=1, sticky="ew", padx=6, pady=6)

        # --- статья ---
        art = ctk.CTkFrame(self)
        art.grid(row=2, column=0, sticky="ew", padx=12, pady=6)
        art.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(art, text=_("Article file (.md)")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 2))
        self.path_in = ctk.CTkEntry(art, width=560, placeholder_text=_("Path to the article"))
        self.path_in.insert(0, self.article_path)
        self.path_in.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10)
        self.path_in.bind("<Return>", lambda _e: self._scan())
        ctk.CTkButton(art, text=_("Scan"), width=90, command=self._scan).grid(
            row=1, column=2, padx=8)

        ctk.CTkLabel(art, text=_("Title")).grid(row=2, column=0, sticky="w", padx=10, pady=4)
        self.title_in = ctk.CTkEntry(art, width=340)
        self.title_in.grid(row=2, column=1, sticky="ew", padx=6, pady=4)
        ctk.CTkLabel(art, text=_("Slug (URL)")).grid(row=3, column=0, sticky="w", padx=10, pady=4)
        self.slug_in = ctk.CTkEntry(art, width=220)
        self.slug_in.grid(row=3, column=1, sticky="w", padx=6, pady=4)

        year_frame = ctk.CTkFrame(art, fg_color="transparent")
        year_frame.grid(row=3, column=1, sticky="e", padx=6)
        ctk.CTkLabel(year_frame, text=_("Year")).pack(side="left", padx=4)
        self.year_in = ctk.CTkEntry(year_frame, width=90)
        self.year_in.insert(0, self.cfg.get("year", "2026"))
        self.year_in.pack(side="left")

        self.images_lbl = ctk.CTkLabel(art, text=f"{_('Images')}: —", text_color="grey")
        self.images_lbl.grid(row=4, column=0, columnspan=3, sticky="w", padx=10, pady=(2, 10))

        # --- опции ---
        opts = ctk.CTkFrame(self, fg_color="transparent")
        opts.grid(row=3, column=0, sticky="ew", padx=12)
        self.publish_var = ctk.BooleanVar(value=bool(self.cfg.get("last_published", False)))
        ctk.CTkSwitch(opts, text=_("Publish immediately (otherwise save as draft)"),
                      variable=self.publish_var).pack(side="left", padx=10)
        ctk.CTkLabel(opts, text=f"{_('Language')}: {self._lang_label()}").pack(side="right", padx=10)

        # --- кнопка и лог ---
        self.sync_btn = ctk.CTkButton(self, text=_("Sync article to Wagtail"),
                                      height=42, command=self._sync)
        self.sync_btn.grid(row=4, column=0, sticky="ew", padx=12, pady=8)

        self.log_box = ctk.CTkTextbox(self, height=200)
        self.log_box.grid(row=5, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.log_box.configure(state="disabled")

    # ---------------- служебное ----------------

    def _lang_label(self):
        code = (LANG or os.environ.get("LANG", "en")[:2])
        return dict(SUPPORTED_LANGUAGES).get(code, code)

    def _log(self, msg):
        def append():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", f"{msg}\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.after(0, append)

    def _scan(self):
        self.article_path = self.path_in.get().strip()
        if not self.article_path or not os.path.exists(self.article_path):
            self._log("404")
            return
        post = frontmatter.load(self.article_path)
        self.title_in.delete(0, "end")
        self.title_in.insert(0, post.get("title", ""))
        self.slug_in.delete(0, "end")
        self.slug_in.insert(0, post.get("slug", ""))
        year = str(post.get("year", "2026"))
        self.year_in.delete(0, "end")
        self.year_in.insert(0, year)
        imgs = Article(self.article_path).local_images()
        missing = sum(1 for _rel, p in imgs if p is None)
        self.images_lbl.configure(
            text=f"{_('Images')}: {len(imgs)}" + (f" ({missing} ⚠️)" if missing else ""))
        self.cfg["last_article"] = self.article_path
        self.cfg["year"] = year
        save_config(self.cfg)
        self._log(self.article_path)

    # ---------------- подключение ----------------

    def _connect(self):
        self.connect_btn.configure(state="disabled")

        def worker():
            try:
                api = WagtailAPI(self.url_in.get().strip(), self.token_in.get().strip())
                sites = api.sites()
            except SyncError as e:
                self._log(f"❌ {e}")
                self.after(0, lambda: self.connect_btn.configure(state="normal"))
                return

            self.api = api
            self.sites = sites
            options = [
                (s.get("site_name") or s.get("hostname") or f"site {s['id']}", s["root_page_id"])
                for s in self.sites
            ]
            self.site_id = options[0][1] if options else None

            def fill():
                self.cfg["api_url"] = self.url_in.get().strip()
                self.cfg["token"] = self.token_in.get().strip()
                save_config(self.cfg)
                self.site_box.configure(values=[o[0] for o in options])
                self.site_box.set(options[0][0] if options else "—")
                self._fill_sections(self.site_id)
                self.connect_btn.configure(state="normal")
            self.after(0, fill)

        threading.Thread(target=worker, daemon=True).start()

    def _fill_sections(self, root_id):
        options = [(f"★ id {root_id}", root_id)]
        try:
            for p in self.api.pages(child_of=root_id, limit=100).get("items", []):
                options.append((p["title"], p["id"]))
        except SyncError:
            pass
        self.section_box.configure(values=[o[0] for o in options])
        self.section_box.set(options[0][0] if options else "—")
        self.parent_id = options[0][1] if options else None

    def _site_options(self):
        return [
            (s.get("site_name") or s.get("hostname") or f"site {s['id']}", s["root_page_id"])
            for s in self.sites
        ]

    def _on_site(self, choice):
        for label, root_id in self._site_options():
            if label == choice:
                self.site_id = root_id
                self._fill_sections(root_id)
                break

    def _on_section(self, choice):
        for title, page_id in self._section_options():
            if title == choice:
                self.parent_id = page_id
                break

    # ---------------- синхронизация ----------------

    def _sync(self):
        self.article_path = self.path_in.get().strip()
        if not self.article_path or not self.api:
            return
        self.sync_btn.configure(state="disabled")
        year = self.year_in.get().strip()
        parent = self.parent_id
        publish = self.publish_var.get()
        title = self.title_in.get().strip() or None
        slug = self.slug_in.get().strip() or None

        def worker():
            try:
                engine = SyncEngine(self.api, self.cfg.get("site", ""),
                                    page_type=self.cfg.get("page_type", PAGE_TYPE))
                res = engine.sync(self.article_path, parent_id=parent, publish=publish,
                                  title=title, slug=slug, year=year, log=self._log)
                self._log(f"✅ {res.get('mode')} (id {res.get('id')})")
                self.cfg["last_published"] = publish
                save_config(self.cfg)
            except SyncError as e:
                self._log(f"❌ {e}")
            except Exception as e:  # сеть и прочее — GUI не падает
                self._log(f"❌ {e.__class__.__name__}: {e}")
            finally:
                self.after(0, lambda: self.sync_btn.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()


def main():
    app = PublisherApp()
    app.mainloop()


if __name__ == "__main__":
    main()
