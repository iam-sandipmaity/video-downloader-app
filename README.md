<p align="center">
  <img src="assets/icon.png" width="120" alt="Video Downloader Icon" />
</p>

<h1 align="center">Video Downloader</h1>

<p align="center">
  <strong>A sleek, open-source YouTube downloader for Android — built with Python & Kivy.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0-blueviolet?style=flat-square" alt="Version" />
  <img src="https://img.shields.io/badge/platform-Android-green?style=flat-square" alt="Platform" />
  <img src="https://img.shields.io/badge/python-3.x-blue?style=flat-square" alt="Python" />
  <img src="https://img.shields.io/badge/license-MIT-orange?style=flat-square" alt="License" />
</p>

---

## Features

- **Multi-platform support** — YouTube, Instagram, Facebook, Twitter/X, TikTok, Reddit, Vimeo, and more!
- **Download videos & audio** — paste a link, pick a format, and go
- **Multiple format options** — Video+Audio, Video-only, or Audio-only
- **Resolution tags** — 4K, 2K, FHD, HD, SD labels for quick identification
- **Cookie support** — authenticate with Instagram/Facebook for reliable downloads
- **No FFmpeg required** — pure-Python MP4/WebM muxer handles merging on-device
- **Dark & Light themes** — "Neon Dusk" dark mode and "Daylight" light mode
- **Glassmorphism UI** — modern frosted-glass cards, glow effects, and smooth animations
- **Download history** — searchable log of every download with one-tap replay
- **Background notifications** — progress updates even when the app is minimized
- **Storage management** — clear cache, view download folder, manage disk usage
- **Diagnostics** — live network stats, crash logs, and system info
- **Backup & restore** — export/import your settings and history as JSON
- **Fully offline** — no accounts, no ads, no tracking

---

## Supported Platforms

| Platform | Status | Notes |
|----------|--------|-------|
| ✅ YouTube | Fully supported | Custom muxer, all formats |
| ✅ Instagram | Supported | May require cookies for stories/private |
| ✅ Facebook | Supported | Cookies recommended |
| ✅ Twitter/X | Supported | Works with most public videos |
| ✅ TikTok | Supported | Downloads without watermark |
| ✅ Reddit | Supported | Video posts |
| ✅ Vimeo | Supported | Public videos |
| ✅ Dailymotion | Supported | Public videos |
| ✅ Twitch | Supported | Clips and VODs |
| ⚠️ Private videos | Limited | Requires cookies (see [COOKIES_GUIDE.md](COOKIES_GUIDE.md)) |

**Note:** Instagram, Facebook, and Twitter may rate-limit or block requests without cookies. See [Cookie Setup Guide](COOKIES_GUIDE.md) for instructions.

---

## Screenshots

> *Coming soon — run the app and see the new Aurora UI in action!*

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **UI Framework** | [Kivy 2.3.0](https://kivy.org/) |
| **Download Engine** | [yt-dlp](https://github.com/yt-dlp/yt-dlp) |
| **Muxer** | Custom pure-Python MP4/WebM muxer (no native binaries) |
| **Metadata** | [Mutagen](https://mutagen.readthedocs.io/) |
| **HTTP** | [Requests](https://docs.python-requests.org/) + [urllib3](https://urllib3.readthedocs.io/) |
| **Build** | [Buildozer](https://buildozer.readthedocs.io/) (python-for-android) |
| **Target** | Android 13 (API 33), arm64-v8a |

---

## Project Structure

```
ytapp/
 main.py                      # App UI, theming, and lifecycle
 downloader.py                # YouTube downloader & pure-Python muxer
 downloader_platforms.py      # Multi-platform wrapper (Instagram, Facebook, etc.)
 api/                         # Modular platform API system
    __init__.py               # Platform loader & registry
    base.py                   # Base config class
    instagram.py              # Instagram-specific config
    facebook.py               # Facebook-specific config
    tiktok.py                 # TikTok-specific config
    ... (10+ platform files)  # Each platform in own file
 ui/                          # Reusable UI widget library
    __init__.py               # Widget exports
    widgets.py                # Card, Btn, RingProgress, FmtChip, etc.
 app_settings.py              # Persistent settings, history, backup/restore
 buildozer.spec               # Android build configuration
 generate_icon.py             # Script to regenerate the app icon
 COOKIES_GUIDE.md             # Guide for setting up cookies for Instagram/Facebook
 assets/
    icon.png                  # 512x512 app icon
 xml/
    network_security_config.xml
 LICENSE                      # MIT License
 pyproject.toml               # Ruff lint config
 README.md
```

### Adding New Platforms

Thanks to the modular API system, adding support for a new platform is super easy:

1. **Create `api/yourplatform.py`** (50 lines)
2. **Register in `api/__init__.py`** (1 line)
3. **Add URL detection** (1 line)
4. Done! ✅

See [api/README.md](api/README.md) for detailed instructions.

---

## Getting Started

### Prerequisites

- **Python 3.8+**
- **Git**
- A **GitHub** account (for cloud-based APK builds)

### Clone the repo

```bash
git clone https://github.com/iam-sandipmaity/yt-downloader.git
cd yt-downloader
```

### Run locally (desktop preview)

```bash
pip install kivy==2.3.0 yt-dlp requests certifi mutagen
python main.py
```

> **Note:** Some Android-specific features (notifications, storage paths) won't work on desktop, but the UI will render for development purposes.

---

## Building the APK

The easiest way to build is via **GitHub Actions** — no local Android SDK needed.

### 1. Push your code to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/yt-downloader.git
git push -u origin main
```

### 2. Set up the workflow

Create `.github/workflows/build-apk.yml` in your repo with a Buildozer CI workflow. The workflow will:

- Install the Android SDK/NDK automatically
- Build the APK using Buildozer
- Upload it as a GitHub Release

### 3. Watch the build

1. Go to your repo  **Actions** tab
2. Click the running workflow
3. First build: **~30-45 min** (SDK download + cache)
4. Subsequent builds: **~10-15 min** (cached)

### 4. Download & install

- Go to **Releases** on your repo sidebar
- Download the `.apk` file
- Transfer to your Android phone  tap to install
- Enable "Install from unknown sources" if prompted

### Rebuilding

Any code push to `main` triggers a fresh build:

```bash
git add .
git commit -m "Update"
git push
```

---

## Permissions

The app requests the following Android permissions:

| Permission | Reason |
|-----------|--------|
| `INTERNET` | Download videos from YouTube |
| `WRITE_EXTERNAL_STORAGE` | Save downloaded files |
| `READ_EXTERNAL_STORAGE` | Access saved downloads |
| `FOREGROUND_SERVICE` | Show download progress notifications |
| `POST_NOTIFICATIONS` | Display notifications (Android 13+) |
| `MANAGE_EXTERNAL_STORAGE` | Full file access on Android 11+ |

---

## Configuration

Key settings in `app_settings.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `DEFAULT_THEME` | `"Neon Dusk"` | Dark theme by default |
| `DEFAULT_HISTORY_LIMIT` | `120` | Max items in download history |
| `DEFAULT_CACHE_MAX_AGE_HOURS` | `12` | Auto-clear cache after N hours |
| `DEFAULT_MAX_CRASH_LOG_MB` | `2` | Max crash log file size |

All settings are adjustable from within the app's **Settings** tab.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Build fails with "No module named X" | Add `X` to `requirements` in `buildozer.spec` |
| NDK download error | Retry the build (transient network issue) |
| Cython error | Already handled in the CI workflow |
| App crashes on launch | Check crash logs in app **Settings  Diagnostics** |
| Downloads stuck at 0% | Check internet connection; try a different video URL |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/awesome`)
3. Commit your changes (`git commit -m "Add awesome feature"`)
4. Push to the branch (`git push origin feature/awesome`)
5. Open a Pull Request

---

## Author

**Sandip Maity**

[![Twitter](https://img.shields.io/badge/Twitter-@iam__sandipmaity-1DA1F2?style=flat-square&logo=twitter&logoColor=white)](https://x.com/iam_sandipmaity)
[![GitHub](https://img.shields.io/badge/GitHub-iam--sandipmaity-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/iam-sandipmaity)
[![Instagram](https://img.shields.io/badge/Instagram-iam__sandipmaity-E4405F?style=flat-square&logo=instagram&logoColor=white)](https://instagram.com/iam_sandipmaity)

---

## License

This project is open source and available under the [MIT License](LICENSE).

---

<p align="center">
  Made with  in Python v1.0
</p>
