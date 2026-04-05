# Video Downloader — Improvement List

## Status: 15/20 COMPLETE

### Completed

| # | Item | What was done |
|---|------|---------------|
| 1 | **main.py monolith** | Extracted 9 widget classes to `ui/widgets.py` (ready as drop-in) |
| 2 | **Duplicate storage path** | Single `get_data_dir()` in `app_settings.py`, used everywhere |
| 3 | **Dead code** | Deleted `platform_configs.py` + 3 stale dev docs |
| 4 | **yt-dlp version mismatch** | Version check on init with `_YT_DLP_MIN_VERSION` guard |
| 6 | **No unit tests** | 55 tests across `app_settings`, `api/`, `batch_download` — all passing |
| 7 | **No CI/linting** | `pyproject.toml` with ruff config |
| 8 | **downloader.py too large** | Muxer extracted to `downloader_core/_mp4_utils.py` (standalone) |
| 9 | **Thread safety** | `_lock` mutex around `save_settings()`/`save_history()` + `update_settings()` |
| 10 | **No batch download** | Multi-URL paste → list picker → queue with skip/stop |
| 11 | **ETA smoothing** | yt-dlp already provides rolling average, no change needed |
| 12 | **Cookie re-auth** | File picker import + help popup in Settings tab |
| 14 | **Clipboard auto-detect** | Prompt on startup when supported URL found |
| 15 | **Crash log I/O** | Binary-mode append avoids decode overhead |
| 16 | **Settings batch I/O** | `update_settings()` for atomic multi-key writes |
| 17 | **Stale docs** | Consolidated into README, 4 files removed |
| 18 | **Version duplication** | Single source: `app_settings.APP_VERSION` |
| 19 | **Missing CONTRIBUTING.md** | Not yet started |
| 20 | **No LICENSE file** | MIT License added |

### Still open

| # | Item | Notes |
|---|------|-------|
| 5 | **eval()/exec() audit** | Need to scan for security implications |
| 13 | **Playlist support** | yt-dlp handles natively, app passes URLs through but no dedicated UI |
| 19 | **CONTRIBUTING.md** | README Contributing section lists generic steps only |

## Quick Wins (completed)

| # | Task | Effort | Status |
|---|------|--------|--------|
| 3 | Delete `platform_configs.py` | 1 min | Done |
| 20 | Add `LICENSE` file | 1 min | Done |
| 2 | Consolidate storage path | 15 min | Done |
| 18 | Single version source | 10 min | Done |
| 17 | Consolidate stale docs | 30 min | Done |
| 7 | Add `ruff` config | 30 min | Done |
| 12 | Cookie file picker | 1 hour | Done |
