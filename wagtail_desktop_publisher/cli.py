# cli.py — команды publisher v2.
#
#   wagtail-publisher init    --url https://... --token ... [--site vs-svet.ru]
#   wagtail-publisher publish article.md [--parent ID] [--publish] [--year 2026]
#   wagtail-publisher status  articles/
#   wagtail-publisher pull    article.md
#   wagtail-publisher unpublish article.md
#
# Локальные блоги доступны на :8000 — для теста:
#   wagtail-publisher init --url http://vs-svet.ru:8000/api/v3 --token ...
import argparse
import json
import os
import sys

import frontmatter

from .core.config import load_config, save_config
from .core.sync import SyncEngine, SyncError, WagtailAPI

PAGE_TYPE = "blog.BlogPage"


def _engine(cfg):
    api_url = cfg.get("api_url")
    token = cfg.get("token")
    if not api_url or not token:
        raise SyncError(
            "Нет конфигурации: запусти `wagtail-publisher init --url <API URL> --token <token>`"
        )
    return SyncEngine(WagtailAPI(api_url, token), cfg.get("site", ""))


def _iter_md(target):
    if os.path.isdir(target):
        for root, _dirs, files in os.walk(target):
            for name in sorted(files):
                if name.endswith(".md") and name != "README.md":
                    yield os.path.join(root, name)
    else:
        yield target


def cmd_init(args):
    cfg = load_config()
    cfg["api_url"] = args.url.rstrip("/")
    cfg["token"] = args.token
    if args.site:
        cfg["site"] = args.site
    save_config(cfg)
    print(f"Конфигурация сохранена: {args.url} (сайт: {cfg.get('site', '—')})")


def cmd_publish(args):
    cfg = load_config()
    engine = _engine(cfg)
    parent = args.parent or cfg.get("default_parent_id")
    results = []
    for md in _iter_md(args.target):
        try:
            res = engine.sync(
                md,
                parent_id=parent,
                publish=args.publish,
                year=args.year,
                force=args.force,
            )
            res["file"] = md
            results.append(res)
            icon = {"created": "✅ создана", "updated": "🔁 обновлена",
                    "skipped": "= пропущена (без изменений)"}.get(res["status"], res["status"])
            extra = ""
            if "images" in res:
                extra = f" | картинки: ⬆️{res['images']['uploaded']} ↩️{res['images']['reused']}"
                if res["images"]["missing"]:
                    extra += f" ⚠️{res['images']['missing']}"
            print(f"{icon}: {md}{extra}")
        except SyncError as e:
            results.append({"status": "error", "file": md})
            print(f"❌ {md}: {e}")
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
    return 0 if all(r.get("status") != "error" for r in results) else 1


def cmd_status(args):
    cfg = load_config()
    engine = _engine(cfg)
    for md in _iter_md(args.target):
        st = engine.status(md)
        print(f"{st['status']:10s} {md} — {st.get('detail', '')}")


def cmd_pull(args):
    cfg = load_config()
    engine = _engine(cfg)
    for md in _iter_md(args.target):
        try:
            engine.pull_meta(md)
        except SyncError as e:
            print(f"❌ {md}: {e}")


def cmd_unpublish(args):
    cfg = load_config()
    engine = _engine(cfg)
    post = frontmatter.load(args.target)
    wagtail_id = post.get("wagtail_id")
    if not wagtail_id:
        print("❌ Статья не привязана к Wagtail")
        return 1
    engine.api.unpublish_page(int(wagtail_id))
    post["published"] = False
    with open(args.target, "wb") as fh:
        frontmatter.dump(post, fh)
    print(f"⬇️ снята с публикации (id {wagtail_id})")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="wagtail-publisher",
        description="Синхронизация Markdown-статей с Wagtail (v2)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="сохранить URL API и токен")
    p_init.add_argument("--url", required=True)
    p_init.add_argument("--token", required=True)
    p_init.add_argument("--site", help="домен сайта, напр. vs-svet.ru")
    p_init.set_defaults(func=cmd_init)

    p_pub = sub.add_parser("publish", help="создать/обновить статью (или директорию)")
    p_pub.add_argument("target")
    p_pub.add_argument("--parent", type=int, help="ID родительской страницы (для новых)")
    p_pub.add_argument("--publish", action="store_true", help="опубликовать (иначе черновик)")
    p_pub.add_argument("--year", help="директория картинок (год)")
    p_pub.add_argument("--force", action="store_true", help="отправить даже без изменений")
    p_pub.add_argument("--json", action="store_true", help="вывести JSON-отчёт")
    p_pub.set_defaults(func=cmd_publish)

    p_status = sub.add_parser("status", help="статус статей (локально, без сети)")
    p_status.add_argument("target")
    p_status.set_defaults(func=cmd_status)

    p_pull = sub.add_parser("pull", help="подтянуть мета-состояние из Wagtail")
    p_pull.add_argument("target")
    p_pull.set_defaults(func=cmd_pull)

    p_unpub = sub.add_parser("unpublish", help="снять статью с публикации")
    p_unpub.add_argument("target")
    p_unpub.set_defaults(func=cmd_unpublish)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
