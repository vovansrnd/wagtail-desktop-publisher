import datetime
import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import frontmatter

from wagtail_desktop_publisher.core.client import WagtailClient

CONFIG_FILE = os.path.expanduser("~/.wagtail_publisher.json")


DEFAULT_API_URL = "https://vs-svet.ru/api/v3"


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            # Повреждённый конфиг не должен затереть сохранённый токен
            return {"api_url": DEFAULT_API_URL, "token": "", "corrupted": True}
    return {"api_url": DEFAULT_API_URL, "token": ""}


def save_config(cfg):
    # Токен — секрет: файл только для владельца
    fd = os.open(CONFIG_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(cfg, f, indent=2)


class PublisherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Wagtail Desktop Publisher v0.2")
        self.root.geometry("720x680")
        self.root.minsize(680, 600)

        self.cfg = load_config()
        self.client = None
        self.sites = []
        self.current_file = None

        self._build_ui()

        if self.cfg.get("token"):
            self.root.after(100, self.connect_server)

    def _build_ui(self):
        pad = {"padx": 10, "pady": 4}

        # 1. Сервер
        conn_frame = ttk.LabelFrame(self.root, text="Подключение к Wagtail API")
        conn_frame.pack(fill="x", **pad)

        ttk.Label(conn_frame, text="URL:").grid(row=0, column=0, sticky="w", **pad)
        self.api_entry = ttk.Entry(conn_frame, width=32)
        self.api_entry.insert(0, self.cfg.get("api_url", "https://vs-svet.ru/api/v3"))
        self.api_entry.grid(row=0, column=1, sticky="ew", **pad)

        ttk.Label(conn_frame, text="Token:").grid(row=0, column=2, sticky="w", **pad)
        self.token_entry = ttk.Entry(conn_frame, show="*", width=25)
        self.token_entry.insert(0, self.cfg.get("token", ""))
        self.token_entry.grid(row=0, column=3, sticky="ew", **pad)

        ttk.Button(conn_frame, text="Подключиться", command=self.connect_server).grid(row=0, column=4, **pad)
        conn_frame.columnconfigure(1, weight=1)

        # 2. Выбор сайта и куда публиковать
        dest_frame = ttk.LabelFrame(self.root, text="Куда публиковать")
        dest_frame.pack(fill="x", **pad)

        ttk.Label(dest_frame, text="Сайт:").grid(row=0, column=0, sticky="w", **pad)
        self.site_combo = ttk.Combobox(dest_frame, state="readonly", width=35)
        self.site_combo.grid(row=0, column=1, sticky="ew", **pad)
        self.site_combo.bind("<<ComboboxSelected>>", self.on_site_selected)

        ttk.Label(dest_frame, text="Родительская страница:").grid(row=1, column=0, sticky="w", **pad)
        self.parent_combo = ttk.Combobox(dest_frame, state="readonly", width=35)
        self.parent_combo.grid(row=1, column=1, sticky="ew", **pad)
        dest_frame.columnconfigure(1, weight=1)

        # 3. Выбор файла статьи
        file_frame = ttk.LabelFrame(self.root, text="Файл статьи (.md)")
        file_frame.pack(fill="x", **pad)

        self.file_label = ttk.Label(file_frame, text="Файл не выбран", font=("Helvetica", 10, "bold"))
        self.file_label.pack(side="left", fill="x", expand=True, padx=10, pady=8)
        ttk.Button(file_frame, text="Выбрать файл…", command=self.select_file).pack(side="right", padx=10)

        # 4. Параметры статьи и картинок
        meta_frame = ttk.LabelFrame(self.root, text="Параметры статьи и загрузки картинок")
        meta_frame.pack(fill="x", **pad)

        ttk.Label(meta_frame, text="Заголовок:").grid(row=0, column=0, sticky="w", **pad)
        self.title_entry = ttk.Entry(meta_frame)
        self.title_entry.grid(row=0, column=1, columnspan=3, sticky="ew", **pad)

        ttk.Label(meta_frame, text="Slug (URL):").grid(row=1, column=0, sticky="w", **pad)
        self.slug_entry = ttk.Entry(meta_frame, width=25)
        self.slug_entry.grid(row=1, column=1, sticky="ew", **pad)

        ttk.Label(meta_frame, text="Папка года:").grid(row=1, column=2, sticky="w", **pad)
        self.year_entry = ttk.Entry(meta_frame, width=10)
        self.year_entry.insert(0, str(datetime.datetime.now().year))
        self.year_entry.grid(row=1, column=3, sticky="w", **pad)

        meta_frame.columnconfigure(1, weight=1)

        # Инфо о найденных картинках и привязке ID
        self.info_label = ttk.Label(meta_frame, text="Картинки: не просканировано", foreground="#007d7e")
        self.info_label.grid(row=2, column=0, columnspan=4, sticky="w", padx=10, pady=2)

        # 5. Опции
        opts_frame = ttk.Frame(self.root)
        opts_frame.pack(fill="x", padx=10, pady=2)

        self.publish_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            opts_frame,
            text="Опубликовать сразу на сайте (иначе сохранить как ЧЕРНОВИК)",
            variable=self.publish_var,
        ).pack(side="left")

        # 6. Консольный лог
        self.log_box = tk.Text(self.root, height=8, bg="#1a1a1a", fg="#98c379", font=("Monospace", 9))
        self.log_box.pack(fill="both", expand=True, padx=10, pady=5)

        # 7. Большая кнопка действия
        self.sync_btn = ttk.Button(
            self.root, text="Синхронизировать статью в Wagtail", command=self.run_sync, state="disabled"
        )
        self.sync_btn.pack(fill="x", padx=10, pady=8)

    def log(self, msg):
        self.log_box.insert("end", f"{msg}\n")
        self.log_box.see("end")

    def connect_server(self):
        url = self.api_entry.get().strip()
        token = self.token_entry.get().strip()
        if not url or not token:
            return

        self.cfg["api_url"] = url
        self.cfg["token"] = token
        save_config(self.cfg)

        self.client = WagtailClient(url, token)
        self.log("Подключение к серверу Wagtail API...")

        try:
            self.sites = self.client.get_sites()
            if not self.sites:
                self.log("❌ Ошибка: список сайтов пуст.")
                return

            self.site_combo["values"] = [
                f"{s.get('site_name') or s.get('hostname')} (Root ID: {s.get('root_page_id')})"
                for s in self.sites
            ]
            self.site_combo.current(0)
            self.log(f"✅ Успешно! Подключено сайтов: {len(self.sites)}")
            self.on_site_selected(None)
        except Exception as e:
            self.log(f"❌ Сбой соединения: {e}")

    def on_site_selected(self, event):
        idx = self.site_combo.current()
        if idx >= 0:
            site = self.sites[idx]
            root_id = site.get("root_page_id")
            site_name = site.get("site_name") or site.get("hostname")

            # В выпадающий список родителей первым делом ставим САМ КОРЕНЬ САЙТА!
            parent_options = [(f"★ [Корень сайта] {site_name} (ID: {root_id})", root_id)]

            # И добираем подразделы
            children = self.client.get_child_sections(root_id)
            for c in children:
                parent_options.append((f"  └─ {c.get('title')} (ID: {c.get('id')})", c.get("id")))

            self.parent_data = parent_options
            self.parent_combo["values"] = [p[0] for p in parent_options]
            self.parent_combo.current(0)

    def select_file(self):
        f = filedialog.askopenfilename(filetypes=[("Markdown files", "*.md"), ("All files", "*.*")])
        if not f:
            return

        self.current_file = f
        self.file_label.config(text=os.path.basename(f), foreground="#007d7e")

        # Читаем frontmatter
        post = frontmatter.load(f)
        title = post.get("title", os.path.splitext(os.path.basename(f))[0])
        slug = post.get("slug", "")
        wagtail_id = post.get("wagtail_id")
        year = post.get("year", datetime.datetime.now().year)

        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, title)

        self.slug_entry.delete(0, "end")
        self.slug_entry.insert(0, slug)

        self.year_entry.delete(0, "end")
        self.year_entry.insert(0, str(year))

        # Сканируем картинки
        images = self.client.find_local_images(f) if self.client else []
        valid_img = sum(1 for img in images if img[2])

        status_wagtail = f"Привязан к Wagtail ID: {wagtail_id} (режим ОБНОВЛЕНИЯ)" if wagtail_id else "Новая статья (режим СОЗДАНИЯ)"
        self.info_label.config(text=f"Статус: {status_wagtail} | Картинок в тексте: {len(images)} (готово к заливке: {valid_img})")

        self.sync_btn.config(state="normal")
        self.log(f"Выбран файл: {f}")
        if wagtail_id:
            self.log(f"Статья уже существует в Wagtail под ID {wagtail_id}. Повторная синхронизация обновит её.")

    def run_sync(self):
        if not self.current_file or not self.client:
            return

        title = self.title_entry.get().strip()
        slug = self.slug_entry.get().strip()
        year = self.year_entry.get().strip()

        parent_idx = self.parent_combo.current()
        parent_id = self.parent_data[parent_idx][1]
        publish_now = self.publish_var.get()

        self.log(f"\n--- Синхронизация '{title}' (папка: images/{year}/{slug or 'misc'}) ---")
        try:
            res = self.client.sync_article(
                self.current_file,
                parent_id,
                custom_title=title,
                custom_slug=slug,
                custom_year=year,
                publish_now=publish_now,
            )

            if res.get("success"):
                mode = res.get("mode").upper()
                wag_id = res.get("id")
                img_cnt = res.get("uploaded_images", 0)

                self.log(f"✅ УСПЕХ! Статья {mode} под ID {wag_id}!")
                self.log(f"Загружено локальных изображений на сервер: {img_cnt}")
                self.log("Файл .md на компьютере обновлен и синхронизирован.")

                self.select_file() # обновляем плашку статуса
                messagebox.showinfo("Успешно", f"Статья {mode} (ID: {wag_id})!\nЗагружено картинок: {img_cnt}")
            else:
                self.log(f"❌ ОШИБКА: {res.get('error')}")
                messagebox.showerror("Ошибка", res.get("error"))
        except Exception as e:
            self.log(f"❌ Исключение: {e}")
            messagebox.showerror("Сбой", str(e))


def main():
    root = tk.Tk()
    app = PublisherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
