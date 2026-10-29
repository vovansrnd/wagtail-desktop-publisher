import os
import re
import datetime
import requests
import frontmatter


class WagtailClient:
    def __init__(self, api_base_url, token):
        self.api_base_url = api_base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {token}",
        }

    def get_sites(self):
        """Получает список сайтов из Wagtail."""
        url = f"{self.api_base_url}/sites/"
        resp = requests.get(url, timeout=30, headers=self.headers)
        if resp.status_code == 200:
            return resp.json().get("items", [])
        return []

    def get_child_sections(self, parent_page_id):
        """Получает разделы или страницы внутри родителя."""
        url = f"{self.api_base_url}/pages/?child_of={parent_page_id}&limit=50"
        resp = requests.get(url, timeout=30, headers=self.headers)
        if resp.status_code == 200:
            return resp.json().get("items", [])
        return []

    def upload_image(self, file_path, year, slug):
        """Загружает картинку в Wagtail через API в папку year/slug."""
        if not os.path.exists(file_path):
            return None

        url = f"{self.api_base_url}/images/"
        filename = os.path.basename(file_path)

        with open(file_path, "rb") as f:
            files = {"file": (filename, f)}
            data = {
                "title": os.path.splitext(filename)[0],
                "year": str(year),
                "slug": str(slug),
            }
            resp = requests.post(url, timeout=120, headers=self.headers, files=files, data=data)

        if resp.status_code in (200, 201):
            return resp.json()
        return None

    def find_local_images(self, md_path):
        """Находит все локальные картинки в тексте Markdown."""
        if not os.path.exists(md_path):
            return []

        base_dir = os.path.dirname(os.path.abspath(md_path))
        post = frontmatter.load(md_path)
        img_pattern = re.compile(r"!\[(.*?)\]\((.*?)\)")
        matches = img_pattern.findall(post.content)

        found = []
        for alt_text, img_rel_path in matches:
            if not img_rel_path.startswith(("http://", "https://")):
                full_p = self._resolve_local_image(base_dir, img_rel_path)
                found.append((img_rel_path, full_p, bool(full_p)))
        return found

    def _resolve_local_image(self, base_dir, img_rel_path):
        """Путь внутри папки статьи; пути вида ../../ или /etc/ отбрасываются."""
        full_p = os.path.normpath(os.path.join(base_dir, img_rel_path))
        if not full_p.startswith(os.path.abspath(base_dir) + os.sep):
            return None
        return full_p if os.path.exists(full_p) else None

    def sync_article(self, md_path, parent_id, custom_title=None, custom_slug=None, custom_year=None, publish_now=False):
        """Синхронизирует Markdown-статью с Wagtail."""
        base_dir = os.path.dirname(os.path.abspath(md_path))
        post = frontmatter.load(md_path)

        title = custom_title or post.get("title", "Без названия")
        slug = custom_slug or post.get("slug", "")
        wagtail_id = post.get("wagtail_id")
        year = custom_year or post.get("year", datetime.datetime.now().year)

        content = post.content

        # 1. Загрузка картинок
        img_pattern = re.compile(r"!\[(.*?)\]\((.*?)\)")
        matches = img_pattern.findall(content)
        uploaded_count = 0

        uploaded = {}
        for alt_text, img_rel_path in matches:
            if not img_rel_path.startswith(("http://", "https://")):
                if img_rel_path in uploaded:
                    server_url = uploaded[img_rel_path]
                    content = content.replace(f"]({img_rel_path})", f"]({server_url})")
                    continue
                local_path = self._resolve_local_image(base_dir, img_rel_path)
                if local_path:
                    res = self.upload_image(local_path, year, slug or "misc")
                    if res:
                        # Получаем URL созданного изображения
                        server_url = res.get("meta", {}).get("download_url") or res.get("url")
                        if server_url:
                            uploaded[img_rel_path] = server_url
                            content = content.replace(f"]({img_rel_path})", f"]({server_url})")
                            uploaded_count += 1

        # 2. Формируем запрос
        payload = {
            "title": title,
            "body": {
                "format": "db_markdown",
                "content": content,
            },
        }

        if slug:
            payload["slug"] = slug

        if post.get("excerpt"):
            payload["excerpt"] = post.get("excerpt")

        # 3. Отправка
        action = "publish" if publish_now else None

        if wagtail_id:
            # Обновление существующей страницы (PATCH)
            if action:
                payload["meta"] = {"action": action}
            url = f"{self.api_base_url}/pages/{wagtail_id}/"
            resp = requests.patch(url, timeout=60, headers=self.headers, json=payload)
            mode = "обновлена"
        else:
            # Создание новой страницы (POST)
            meta = {
                "type": "blog.BlogPage",
                "parent_id": int(parent_id),
            }
            if action:
                meta["action"] = action
            payload["meta"] = meta

            url = f"{self.api_base_url}/pages/"
            resp = requests.post(url, timeout=120, headers=self.headers, json=payload)
            mode = "создана"

        if resp.status_code in (200, 201):
            data = resp.json()
            new_id = data.get("id")

            # Записываем wagtail_id, title и slug обратно в исходный .md файл!
            post["wagtail_id"] = new_id or wagtail_id
            post["title"] = title
            if slug:
                post["slug"] = slug
            post["year"] = year

            with open(md_path, "w", encoding="utf-8") as f:
                frontmatter.dump(post, f)

            return {
                "success": True,
                "id": new_id or wagtail_id,
                "mode": mode,
                "uploaded_images": uploaded_count,
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {resp.status_code}: {resp.text}",
            }
