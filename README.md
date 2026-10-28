# wagtail-desktop-publisher

A standalone desktop & CLI utility to write articles in local Markdown editors
(Zettlr, Obsidian, MarkText, VS Code, Joplin — anything that writes `.md`) and
sync them into a Wagtail CMS site: automated image uploading, page metadata
(title, slug, tags, categories, main image, excerpt, date), draft/publish
control, and re-sync of already published articles.

Works against the **Wagtail v3 API** (Wagtail ≥ 7.0) over HTTP — the CMS does
not need to run on the same machine.

- GUI: `wagtail-publisher-gui` (NiceGUI, follows the OS dark/light theme,
  13 UI languages)
- CLI: `wagtail-publisher` (scriptable, JSON output)

---

## 1. How the workflow looks

```
~/articles/2026/rca-connectors/
    index.md          ← you write this (frontmatter + Markdown)
    images/
        shot1.png     ← pictures live next to the article
        shot2.png
```

`index.md`:

```markdown
---
title: "Budget RCA connectors"
slug: rca-connectors          # required: stable URL of the article
excerpt: "Short description."
date: 2026-10-28
tags: ["audio", "diy"]
category_ids: [12]            # optional: MPTT category ids of the site
---

Body text in Markdown.

![A photo](images/shot1.png)   ← local relative path stays local
```

Then:

```bash
wagtail-publisher publish ~/articles/2026/rca-connectors/index.md --parent 42
```

What happens:

1. Local images are uploaded once and mapped in the frontmatter
   (`images:` section, with a per-file hash). Re-syncs **reuse** them —
   a changed file is detected by hash and re-uploaded.
2. The Markdown body is converted to HTML (the CMS stores rich text)
   with **server image URLs substituted only in the outgoing payload** —
   your local `.md` keeps relative paths, so your local editor preview
   keeps working forever.
3. `main_image` is set automatically (first uploaded image unless you
   provide `main_image_id`).
4. A `content_hash` is stored. Re-running publish on an unchanged article
   performs **zero API calls** — Wagtail creates a page revision on every
   update, so this keeps the database from bloating.
5. `wagtail_id`, `slug`, `content_hash`, the image map and the public URL
   are written back into the `.md` frontmatter.

### Editing an already published article

Keep editing the same `.md` and run `publish` again — the article is
updated (draft or published, your choice). `pull` refreshes the
frontmatter meta (published state, URL) from the server without touching
your text.

## 2. CLI reference

```
wagtail-publisher init    --url https://site/api/v3 --token <token> [--site site.tld]
wagtail-publisher publish <file.md | dir/> [--parent ID] [--publish]
                          [--year 2026] [--force] [--json]
wagtail-publisher status  <file.md | dir/>      # local, no network
wagtail-publisher pull    <file.md | dir/>      # refresh meta from the server
wagtail-publisher unpublish <file.md>
```

- `publish` on a directory walks it recursively and syncs every `.md`.
- `status` compares the local `content_hash` — prints
  `synced / modified / unbound`.
- `--force` sends the article even if the hash matches (e.g. after
  changing fields on the server side).

Configuration is stored in `~/.wagtail_publisher.json` (chmod 600):

```json
{
  "api_url": "https://example.com/api/v3",
  "token": "wagtail_…",
  "site": "example.com",
  "default_parent_id": 42
}
```

## 3. GUI

```
wagtail-publisher-gui
```

Opens `http://localhost:8333`. Connect (URL + token), pick a site and a
section from the live page tree, pick the article, press Sync. The theme
follows the OS dark/light setting; the UI language follows the system
locale or is chosen in the header (en, ru, de, es, fr, it, pt-BR, nl, pl,
tr, zh-CN, ja, ko).

## 4. Requirements for the target Wagtail site

The publisher talks to the **v3 API with write support** (Wagtail ≥ 7.0,
verified on 8.0). The target site needs:

1. **Mount the API** in the project `urls.py`:

   ```python
   from wagtail.api.v3 import urls as wagtailapi_v3_urls
   # if you use the bundled publisher-images endpoint, import it first:
   # import <project>.api  # registers the upload endpoint on the API

   urlpatterns = [
       path("api/v3/", wagtailapi_v3_urls.api.urls),
       # …
   ]
   ```

2. **An API token** for your user: Wagtail admin → Settings → API tokens
   (or `APIToken.create_token(user=…, name=…)` from a shell).

3. **Writable page fields**: declare on the page model what the API may
   write. Fields listed as plain strings are read-only in the v3 API —
   use `APIField(..., writable=True)`:

   ```python
   from wagtail.api import APIField

   class BlogPage(Page):
       api_fields = [
           APIField("body", writable=True),
           APIField("excerpt", writable=True),
           APIField("main_image", writable=True),
           APIField("date_published", writable=True),
           APIField("tags", writable=True),
           APIField("categories", writable=True),
       ]
   ```

   Notes: a rich-text/Prose field is written as an **HTML string**
   (this tool converts Markdown → HTML before sending); a foreign key is
   written under its `…_id` name; `tags` is a list of tag names;
   `categories` a list of ids.

4. **Images endpoint** — two supported setups, detected automatically:

   - **Bare Wagtail**: nothing extra. Uploaded images land in a
     Wagtail-native collection tree `year/slug` (e.g. `2026/my-article`).
   - **wagtail-image-directories** (fields `year`/`slug` on the image
     model): the same endpoint fills the directory fields and reuses the
     plugin's `get_or_create_collection()`.

   The publisher ships a small upload endpoint for this
   (`/api/v3/publisher-images/`, see `vsproject/api_images.py` for a
   reference implementation — copy it into your project and register it
   on the v3 API router). Plain `POST /api/v3/images/` (Wagtail ≥ 8.0)
   also works if you pass `collection` yourself.

### Quick checklist that a site is ready

```bash
curl -H "Authorization: Bearer $TOKEN" https://site/api/v3/whoami/        # → your user
curl -H "Authorization: Bearer $TOKEN" "https://site/api/v3/pages/1/?fields=body"  # → fields present?
```

## 5. Revisions and database size

Wagtail stores a page revision on every update. The publisher minimises
noise: unchanged articles are skipped via `content_hash`, images are not
re-uploaded. For old revisions housekeeping, prune them periodically
(e.g. keep the last 10 per page) — a management command in the spirit of
`prune_unused_renditions` is a good companion on the server.

## 6. Development

```bash
pip install -e .
python scripts/build_locales.py   # rebuild .mo after editing strings
pytest                            # (planned)
```

License: MIT.
