# gui/app.py — нативный GUI publisher v2 на CustomTkinter.
#
# Запуск: wagtail-publisher-gui
# Тема: следует системной настройке ОС (тёмная/светлая) —
#       customtkinter.set_appearance_mode("system").
# Язык: системный или из конфига (ключ "language"); 13 языков.
from __future__ import annotations

import os
import sys
import threading

import customtkinter as ctk
import frontmatter
import tkinter.filedialog as filedialog
from markdownify import markdownify as html_to_md

from wagtail_desktop_publisher.core.config import (
    load_config, load_site_cache, save_config, save_site_cache,
)
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
        self.grid_rowconfigure(6, weight=1)

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
        btn_row = ctk.CTkFrame(art, fg_color="transparent")
        btn_row.grid(row=1, column=2, padx=8)
        ctk.CTkButton(btn_row, text=_("Browse…"), width=80,
                      command=self._browse).pack(side="left", padx=2)
        ctk.CTkButton(btn_row, text=_("Scan"), width=70, command=self._scan).pack(side="left", padx=2)

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
        lang_menu = ctk.CTkOptionMenu(
            opts, width=90,
            values=[name for _c, name in SUPPORTED_LANGUAGES],
            command=lambda ch: self._change_language_by_name(ch))
        current_code = LANG or (os.environ.get("LANG", "en")[:2])
        for _c, name in SUPPORTED_LANGUAGES:
            if _c == current_code:
                lang_menu.set(name)
        lang_menu.pack(side="right", padx=10)

        # --- поиск уже опубликованных статей ---
        find_card = ctk.CTkFrame(self)
        find_card.grid(row=4, column=0, sticky="ew", padx=12, pady=6)
        find_card.grid_columnconfigure(0, weight=1)
        self.find_in = ctk.CTkEntry(find_card, placeholder_text=_("Find on site (by title)"))
        self.find_in.grid(row=0, column=0, sticky="ew", padx=8, pady=6)
        self.found_box = ctk.CTkComboBox(find_card, values=[], width=430, state="readonly")
        self.found_box.grid(row=1, column=0, sticky="ew", padx=8)
        self._found_pages = []

        def do_find():
            if not self.api:
                return
            resp = self.api.pages(search=self.find_in.get().strip(), type=PAGE_TYPE, limit=30)
            self._found_pages = resp.get("items", [])
            self.found_box.configure(values=[
                f"{p['id']} | {p['title']}" for p in self._found_pages] or [_("Nothing found")])
            self.found_box.set(self.found_box.cget("values")[0] if self._found_pages else "—")

        def do_save_md():
            if not self._found_pages:
                return
            idx = max(0, self.found_box.cget("values").index(self.found_box.get()) if self.found_box.get() in self.found_box.cget("values") else 0)
            page = self._found_pages[idx] if idx < len(self._found_pages) else None
            if not page:
                return
            detail = self.api.get_page(page["id"])
            slug = detail.get("slug", f"page-{page['id']}")
            body = detail.get("body")
            html = body.get("content") if isinstance(body, dict) else str(body or "")
            md = html_to_md(html)
            d = os.path.join(os.path.expanduser("~/articles"), slug)
            os.makedirs(d, exist_ok=True)
            post = frontmatter.Post(md, **{
                "title": detail.get("title", ""), "slug": slug,
                "wagtail_id": page["id"], "published": True,
            })
            path = os.path.join(d, "index.md")
            with open(path, "w", encoding="utf-8") as fh:
                frontmatter.dump(post, fh)
            self.path_in.delete(0, "end")
            self.path_in.insert(0, path)
            self._scan()
            self._log(f"⬇️ сохранено: {path} (теперь можно править и publish)")

        ctk.CTkButton(find_card, text=_("Save as .md"), command=do_save_md).grid(row=2, column=0, padx=8, pady=4, sticky="w")

        # --- кнопка ---
        self.sync_btn = ctk.CTkButton(self, text=_("Sync article to Wagtail"),
                                      height=42, command=self._sync)
        self.sync_btn.grid(row=5, column=0, sticky="ew", padx=12, pady=8)

        # --- табы: мета (рубрики/теги/главная картинка) и лог ---
        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=6, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.grid_rowconfigure(6, weight=1)
        self.tabs.add(_("Meta"))
        self.tabs.add("Log")

        meta_tab = self.tabs.tab(_("Meta"))
        self.meta_refresh = ctk.CTkButton(meta_tab, text="↻", width=34,
                                          command=self._refresh_meta)
        self.meta_refresh.place(relx=0.965, rely=0.02)
        ctk.CTkLabel(meta_tab, text=_("Categories of the selected site (shared Wagtail tree)")).pack(anchor="w", padx=8, pady=(6, 2))
        self.cat_filter = ctk.CTkEntry(meta_tab, placeholder_text=_("Filter"), width=200)
        self.cat_filter.pack(anchor="w", padx=8, pady=2)
        self.cat_filter.bind("KeyRelease", lambda _e: self._render_categories())
        self.cat_frame = ctk.CTkScrollableFrame(meta_tab, height=160)
        self.cat_frame.pack(fill="both", expand=True, padx=8)
        ctk.CTkLabel(meta_tab, text=_("Tags")).pack(anchor="w", padx=8, pady=(8, 2))
        self.tags_box = ctk.CTkComboBox(meta_tab, values=[], width=430)
        self.tags_box.set("")
        self.tags_box.pack(fill="x", padx=8)
        self.tags_box.bind("KeyRelease", self._tags_autocomplete)
        self.tags_box.configure(command=self._on_tag_pick)
        ctk.CTkLabel(meta_tab, text="Main image").pack(anchor="w", padx=8, pady=(8, 2))
        self.main_image_box = ctk.CTkComboBox(meta_tab, values=["(auto)"], width=430)
        self.main_image_box.set("(auto)")
        self.main_image_box.pack(fill="x", padx=8, pady=(0, 2))
        ctk.CTkLabel(meta_tab, text=_("Main image = first article image unless picked below (after Scan)"),
                     text_color="grey", wraplength=420, justify="left").pack(anchor="w", padx=8, pady=(0, 6))

        log_tab = self.tabs.tab("Log")
        self.log_box = ctk.CTkTextbox(log_tab)
        self.log_box.pack(fill="both", expand=True)
        self.log_box.configure(state="disabled")

        self._cat_vars: list = []
        self._tag_names: list = []
        self._image_map: dict = {}

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
        self._image_map = post.get("images") or {}
        self.main_image_box.configure(
            values=["(auto)"] + list(self._image_map.keys()))
        self.main_image_box.set("(auto)")
        self._log(self.article_path)

    # ---------------- мета: рубрики и теги ----------------

    def _render_categories(self):
        for w in self.cat_frame.winfo_children():
            w.destroy()
        self._cat_vars = []
        flt = self.cat_filter.get().strip().lower() if hasattr(self, "cat_filter") else ""
        for cat in getattr(self, "_all_categories", []):
            name = cat["name"]
            if flt and flt not in name.lower():
                continue
            var = ctk.BooleanVar(value=False)
            indent = "    " * (cat.get("level") or 0)
            box = ctk.CTkCheckBox(self.cat_frame, text=indent + name, variable=var)
            box.pack(anchor="w", padx=4, pady=1)
            self._cat_vars.append((cat["id"], var))

    def _populate_meta(self, categories, tags):
        for w in self.cat_frame.winfo_children():
            w.destroy()
        self._all_categories = categories
        self._render_categories()
        self._tag_names = [t["name"] for t in tags]
        self.tags_box.configure(values=self._tag_names)
        if not categories:
            self.cat_frame.configure(label="—")

    def _load_meta(self, force):
        site = self.cfg.get("site", "")
        cached = load_site_cache(site)
        if cached and not force:
            self.after(0, lambda: self._populate_meta(
                cached.get("categories", []), cached.get("tags", [])))
            self._log(f"рубрики/теги из кэша ({cached.get('fetched_at', '')})")

        def worker():
            try:
                cats = self.api.categories()
                tags = self.api.tags(limit=200)
            except SyncError as e:
                self._log(f"❌ мета: {e}")
                return
            save_site_cache(site, cats, tags)
            self.after(0, lambda: self._populate_meta(cats, tags))
            self._log(f"↻ рубрики: {len(cats)}, теги: {len(tags)}")

        threading.Thread(target=worker, daemon=True).start()

    def _refresh_meta(self):
        self._load_meta(force=True)

    def _tags_autocomplete(self, event=None):
        text = self.tags_box.get()
        fragment = text.rsplit(",", 1)[-1].strip().lower()
        if fragment:
            values = [t for t in self._tag_names if fragment.lower() in t.lower()][:60]
        else:
            values = self._tag_names
        self.tags_box.configure(values=values)

    def _on_tag_pick(self, chosen):
        current = self.tags_box.get()
        prefix = current.rsplit(",", 1)[0]
        new_value = (prefix.rstrip() + ", " if prefix.strip() else "") + chosen + ", "
        self.tags_box.set(new_value)
        self.tags_box.configure(values=self._tag_names)

    def _browse(self):
        path = filedialog.askopenfilename(
            filetypes=[("Markdown", "*.md"), ("All files", "*.*")])
        if path:
            self.path_in.delete(0, "end")
            self.path_in.insert(0, path)
            self._scan()

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
            self.cfg["site"] = (self.url_in.get().strip().split("/")[2]
                                if "/" in self.url_in.get().strip() else "")
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
                self._load_meta(force=False)
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
                category_ids = [cid for cid, var in self._cat_vars if var.get()] or None
                tags = [t.strip() for t in self.tags_box.get().split(",") if t.strip()] or None
                main_image_id = None
                sel = self.main_image_box.get()
                if sel != "(auto)" and sel in self._image_map:
                    main_image_id = self._image_map[sel].get("id")
                res = engine.sync(self.article_path, parent_id=parent, publish=publish,
                                  title=title, slug=slug, year=year, log=self._log,
                                  category_ids=category_ids, tags=tags,
                                  main_image_id=main_image_id)
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


if __name__ in {"__main__", "__mp_main__"}:
    main()
