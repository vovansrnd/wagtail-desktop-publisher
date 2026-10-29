# wagtail-desktop-publisher

**Published on PyPI:** versions 0.3.0–0.3.2 are live at
https://pypi.org/project/wagtail-desktop-publisher/ — `pip install wagtail-desktop-publisher`
installs the current release. Source: https://github.com/vovansrnd/wagtail-desktop-publisher

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Português (Brasil)](README.pt-BR.md) · [Nederlands](README.nl.md) · [Polski](README.pl.md) · [Türkçe](README.tr.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

**Publish Markdown articles from your desktop to a Wagtail site.** The package provides a command-line interface (`wagtail-publisher`) and a native GUI (`wagtail-publisher-gui`). Write content in any local Markdown editor, keep article images beside the Markdown file, and sync pages and images over Wagtail's v3 API.

The local Markdown document remains editable: relative image paths are preserved in the file, while the publisher substitutes uploaded image URLs in the API payload. A content hash allows unchanged files to be skipped, reducing unnecessary API calls and Wagtail page revisions.

## Features

- Create or update a page from Markdown and YAML frontmatter; publish it or leave it as a draft.
- Upload local images and reuse them when their SHA-256 content is unchanged.
- Track the Wagtail page ID, content hash, publication state, image map, slug, and URL in frontmatter.
- Recursively process directories; inspect local sync state offline; refresh metadata from the server; unpublish pages.
- GUI with OS dark/light appearance, site/parent selection from the API, scan-and-sync flow, background network operations, logs, and 13 UI locales.
- Configuration stored in `~/.wagtail_publisher.json` with owner-only file permissions and atomic replacement.

## Audit/release status


## Requirements

The package depends on `requests`, `python-frontmatter`, `markdown`, and `customtkinter`. It targets Wagtail's v3 API with write support. The original package documentation states Wagtail 7.0+ and reports verification against Wagtail 8.0; do not treat that as a guarantee for every later version. Verify the API endpoints and writable fields on your site before production use.

## Installation

```bash
pip install wagtail-desktop-publisher
```




The package installs two commands:

```bash
wagtail-publisher --help
wagtail-publisher-gui
```

A desktop environment is required for the GUI. The CLI is preferable for SSH sessions, automation, and CI jobs.

## Article layout and frontmatter

A typical local layout is:

```text
articles/
└── 2026/rca-connectors/
    ├── index.md
    └── images/
        ├── front.png
        └── rear.png
```

Example `index.md`:

```markdown
---
title: "Budget RCA connectors"
slug: rca-connectors
excerpt: "Short summary."
date: 2026-10-28
year: 2026
tags: [audio, diy]
category_ids: [12]
---

Article text with a local image:

> The optional desktop GUI is implemented in `wagtail_desktop_publisher/gui/`. This source bundle does not include a GUI screenshot.
```

`slug` is required because the publisher needs a stable target URL. The available fields depend on your page model and API configuration. Use the same Markdown file for later updates; do not delete the synchronization metadata from frontmatter unless you intentionally want to rebind the article.

## CLI quick start

Initialize the API connection (use your site's real API URL and a token created by a Wagtail administrator):

```bash
wagtail-publisher init --url https://example.com/api/v3 --token YOUR_TOKEN --site example.com
```

Create or update a draft under the Wagtail parent page with ID `42`:

```bash
wagtail-publisher publish articles/2026/rca-connectors/index.md --parent 42
```

Publish it immediately:

```bash
wagtail-publisher publish articles/2026/rca-connectors/index.md --parent 42 --publish
```

Other commands:

```text
wagtail-publisher status articles/       # local/offline status
wagtail-publisher pull articles/         # refresh metadata from Wagtail
wagtail-publisher unpublish article.md   # unpublish a bound page
wagtail-publisher publish articles/ --json
```

`publish` walks a directory recursively and processes `.md` files except `README.md`. `--force` sends an article even if its content hash matches. `--type` selects the page type, and `--year` overrides the image directory year for the operation.

## Prepare the Wagtail site

The target site must expose the v3 API and allow token-authenticated write requests. Check all of the following in staging:

1. Mount Wagtail's API under `/api/v3/`.
2. Create a token for a user that has permission to create/update the target pages and upload images.
3. Mark the intended page API fields writable using the API mechanism supported by your Wagtail version. Typical fields include the rich-text body, excerpt, main image, publication date, tags, and categories; actual field names differ by project.
4. Configure the image upload endpoint. This publisher currently posts files to `/api/v3/publisher-images/`. The source project contains `vsproject/api_images.py` as a reference implementation. Copy/adapt and register that endpoint in your own project, or adapt the client to your existing secure image-upload endpoint. Do not assume a stock Wagtail API installation automatically provides this custom route.
5. If you use `wagtail-image-directories`, make sure the endpoint sets the image `year`/`slug` fields and uses that model's collection/path behavior.

Do not expose a write-capable token in scripts committed to Git or share it in logs. Use a token with only the privileges needed to publish to the intended site and rotate it if it leaks.

## Configuration and local files

The API URL, token, site, and optional default parent are stored in `~/.wagtail_publisher.json`. The file is written with mode `0600` where supported. Treat it as a secret because it contains a bearer token. The publisher also maintains a separate site metadata cache in the user's home directory; it contains category/tag lookup data, not a replacement for the authoritative site database.

The publisher resolves local image paths relative to the article directory and rejects paths that escape that directory. Missing image files are reported rather than silently converted to arbitrary local filesystem paths.

## Storage and revisions

Wagtail creates revisions when page content is updated. The publisher skips unchanged articles by comparing a content hash that includes relevant metadata and local image bytes. Images are reused when their hashes match. A change to a local image should therefore trigger upload even if the Markdown body does not change.

Before bulk publishing, run `status`, test a small sample, and back up the target database and media. Review the number of revisions and uploaded originals after the first run. The publisher does not automatically prune old Wagtail page revisions or unused image renditions.

## Recommended combinations

- **`wagtail-image-directories`** is the closest companion: it can organize publisher uploads into `year/slug` paths, but the target site's custom `/api/v3/publisher-images/` endpoint must explicitly integrate with that plugin.
- **`wagtail-prose-editor-images`** improves editing in Wagtail's admin; it is not required by the desktop publisher.
- Comments and forum packages are independent of Markdown synchronization.

## Troubleshooting

- `401`/`403`: verify the token and the user's API/page/image permissions.
- `404` on `publisher-images/`: install or register the custom endpoint, or configure the client to use your own endpoint.
- Missing/wrong fields: inspect the page model's v3 API schema and writable field configuration.
- Unexpected duplicate uploads: preserve the `images` map in frontmatter and do not edit the image file metadata manually; the publisher uses content hashes to determine reuse.
- Incorrect destination: verify the parent page ID, `site`, page type (`--type`), and `slug`.

## Development and license

```bash
pip install -e .
python scripts/build_locales.py
```

Run the CLI against a staging site before release. The source bundle does not include an automated test suite, so GUI behavior, API write operations, error handling, and cross-version compatibility need explicit verification. MIT.
