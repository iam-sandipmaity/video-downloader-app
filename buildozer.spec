[app]

title           = Video Downloader
package.name    = videodownloader
package.domain  = com.local

source.dir      = .
source.include_exts = py,png,jpg,kv,atlas

version         = 1.0
icon.filename   = assets/icon.png
presplash.filename = assets/presplash.png
android.presplash_color = #101119

# ── Requirements ──────────────────────────────────────────────────────────
# ffpyplayer compiles ffmpeg from source → yt-dlp uses it for A/V merging.
# Without ffpyplayer (and therefore ffmpeg), formats that need merging
# (1080p, 720p separate streams) would have no audio.
requirements = python3,kivy==2.3.0,yt-dlp,openssl,requests,certifi,mutagen,urllib3

# ── Permissions ───────────────────────────────────────────────────────────
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,CHANGE_NETWORK_STATE,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_VIDEO,READ_MEDIA_AUDIO,POST_NOTIFICATIONS,WAKE_LOCK

# ── Network security ──────────────────────────────────────────────────────
android.manifest.application_attributes = android:usesCleartextTraffic="true" android:networkSecurityConfig="@xml/network_security_config"

# ── Extra files ───────────────────────────────────────────────────────────
source.include_patterns = xml/*

# ── API levels ────────────────────────────────────────────────────────────
android.minapi   = 26
android.api      = 33
android.ndk      = 25b

android.sdk_path = ~/.buildozer/android/platform/android-sdk
android.ndk_path = ~/.buildozer/android/platform/android-ndk-r25b

# ── Architecture ──────────────────────────────────────────────────────────
android.archs = arm64-v8a

orientation       = portrait
fullscreen        = 0

android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
