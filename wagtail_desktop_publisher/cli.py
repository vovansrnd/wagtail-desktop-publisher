import sys
import argparse
from wagtail_desktop_publisher.core.client import WagtailClient
from wagtail_desktop_publisher.gui.app import load_config


def main():
    parser = argparse.ArgumentParser(description="Публикация Markdown в Wagtail CMS")
    parser.add_argument("file", help="Путь к файлу .md")
    parser.add_argument("--parent", type=int, help="ID родительской страницы")
    parser.add_argument("--publish", action="store_true", help="Опубликовать сразу")
    args = parser.parse_args()

    cfg = load_config()
    if not cfg.get("token"):
        print("Ошибка: Токен не настроен. Запустите GUI через wagtail-publisher-gui для первой настройки.")
        sys.exit(1)

    client = WagtailClient(cfg.get("api_url"), cfg.get("token"))
    parent_id = args.parent or 3

    print(f"Синхронизация {args.file} в раздел ID {parent_id}...")
    res = client.sync_article(args.file, parent_id, publish_now=args.publish)

    if res.get("success"):
        print(f"✅ Успешно! ID: {res.get('id')}, Статус: {res.get('status')}")
    else:
        print(f"❌ Ошибка: {res.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
