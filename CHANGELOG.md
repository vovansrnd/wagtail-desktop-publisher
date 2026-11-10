# Changelog — wagtail-desktop-publisher

All notable changes for this package are documented here. Version numbers below are **prepared release candidates** in this audit bundle; they are not a claim that those versions have already been uploaded to PyPI.

## [0.3.4] — 2026-11-10 — prepared, release pending owner approval

- Server-side routers moved into the package (`wagtail_desktop_publisher.
  wagtail_api`): a third-party Wagtail project can now enable receiving
  publications without copying code from the originating site. Mounted on
  the shared Wagtail API v3 instance before `wagtail.api.v3.urls` is
  accessed (see module docstring): `POST /api/v3/images/` (year/slug
  directories when the host uses wagtail-image-directories, native
  collections otherwise), `GET /api/v3/publisher-meta/categories/` and
  `/tags/`.
- `page_type` is configurable end to end: CLI publish respects the
  `page_type` config key, `pull_meta` passes the engine's page type, GUI
  pull passes the configured value, and `WagtailAPI.get_page` accepts a
  `page_type` argument (was hardcoded to `blog.BlogPage`).
- GUI localization files (13 languages, gettext .mo/.po) are included in
  the wheel (PyPI's 0.3.3 wheel shipped 12 files and lost the whole
  `locale/` directory; fixed earlier at commit 20eb4a9, now released).
- `core/client.py` marked deprecated: entry points (CLI, GUI) use
  `core/sync.py`; kept for import compatibility only.
- Rollback: `pip install wagtail-desktop-publisher==0.3.3` (PyPI).
- Tested with: Wagtail 8.1 (foreign `wagtail start` project), Django
  6.0.9, Python 3.14.

## [0.3.1] — 2026-10-29 — prepared, not yet published

- Harden content/image hashing and configuration handling; clarify API write permissions, custom image endpoint integration and safe bulk-sync procedure.
- Expanded installation, security, troubleshooting, storage/integration and multi-language documentation.
- Added translated README files for English, Russian, German, Spanish, French, Italian, Brazilian Portuguese, Dutch, Polish, Turkish, Simplified Chinese, Japanese and Korean.
- Static syntax/packaging checks are included in the release bundle. Complete Django/Wagtail integration tests and live storage/permission checks remain a release gate.

## Previous releases

See the package's release history on PyPI and its source repository, where available.

## 2026-10-29 — follow-up audit

No additional code changes were made to this package in the current follow-up pass. See the original audit/release-overlay notes and complete the package's own compatibility and publisher API tests before release.
