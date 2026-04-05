"""
Multi-platform downloader wrapper.

YouTube URLs are delegated to downloader.py so the custom YouTube mux logic
stays unchanged. Other platforms use yt-dlp direct download flow.

Now uses modular API system from /api folder for easy platform management.
"""

import os
import time
import traceback
from urllib.parse import urlparse

import downloader as yt_downloader
import api  # New modular API system

try:
    import yt_dlp
    _YT_DLP_AVAILABLE = True
except ImportError:
    yt_dlp = None
    _YT_DLP_AVAILABLE = False

# Re-export shared helpers so main.py can use this module as drop-in downloader.
fmt_dur = yt_downloader.fmt_dur
fmt_views = yt_downloader.fmt_views
fmt_size = yt_downloader.fmt_size
fetch_thumbnail = yt_downloader.fetch_thumbnail
cleanup_temp_cache = yt_downloader.cleanup_temp_cache
get_temp_cache_stats = yt_downloader.get_temp_cache_stats
DownloadControl = yt_downloader.DownloadControl
log = yt_downloader.log


def detect_platform(url):
    """Detect which platform a URL belongs to."""
    try:
        host = (urlparse(str(url or "")).netloc or "").lower()
    except Exception:
        host = ""
    
    # Exact matches first
    if "youtu.be" in host or "youtube.com" in host:
        return "youtube"
    if "x.com" in host or "twitter.com" in host:
        return "x"
    if "instagram.com" in host or "instagr.am" in host:
        return "instagram"
    if "facebook.com" in host or "fb.watch" in host or "fb.me" in host:
        return "facebook"
    if "tiktok.com" in host:
        return "tiktok"
    if "reddit.com" in host or "redd.it" in host:
        return "reddit"
    if "vimeo.com" in host:
        return "vimeo"
    if "dailymotion.com" in host or "dai.ly" in host:
        return "dailymotion"
    if "twitch.tv" in host:
        return "twitch"
    if "streamable.com" in host:
        return "streamable"
    if "pinterest.com" in host or "pin.it" in host:
        return "pinterest"
    if "linkedin.com" in host:
        return "linkedin"
    
    # Generic fallback
    if host:
        parts = [p for p in host.split(".") if p]
        if len(parts) >= 2:
            return parts[-2]
        return parts[0] if parts else "unknown"
    return "unknown"


def _is_youtube(url):
    return detect_platform(url) == "youtube"


def _build_generic_formats(raw_formats, platform="unknown"):
    """
    Build format list from raw yt-dlp formats.
    For most platforms (Instagram, Facebook, etc.), combined video+audio is common.
    """
    video_audio = []
    video_only = []
    audio_only = []
    seen = set()
    
    for f in raw_formats or []:
        fid = str(f.get("format_id") or "").strip()
        if not fid:
            continue
        ext = str(f.get("ext") or "mp4").lower()
        h = int(f.get("height") or 0)
        vc = str(f.get("vcodec") or "none").lower()
        ac = str(f.get("acodec") or "none").lower()
        hv = vc not in ("none", "")
        ha = ac not in ("none", "")
        size = yt_downloader.fmt_size(f.get("filesize") or f.get("filesize_approx") or 0)

        if hv and ha:
            # Combined video+audio format (most common for Instagram, Facebook, etc.)
            label = f"{h}p" if h else f"Video {ext.upper()}"
            category = "video_audio"
            ftype = "video"
        elif hv and not ha:
            label = f"{h}p Video Only" if h else f"Video Only {ext.upper()}"
            category = "video_only"
            ftype = "video"
        elif ha and not hv:
            abr = int(f.get("abr") or f.get("tbr") or 0)
            label = f"Audio {ext.upper()} {abr}kbps" if abr else f"Audio {ext.upper()}"
            category = "audio_only"
            ftype = "audio"
        else:
            continue

        key = (category, label.lower(), ext, h)
        if key in seen:
            continue
        seen.add(key)
        item = {
            "format_id": fid,
            "audio_id": None,
            "label": label,
            "tag": yt_downloader._height_tag(h) if h else "",
            "size": size,
            "type": ftype,
            "ext": ext,
            "height": h,
            "needs_mux": False,
            "mux_type": None,
            "category": category,
        }
        if category == "video_audio":
            video_audio.append(item)
        elif category == "video_only":
            video_only.append(item)
        else:
            audio_only.append(item)

    video_audio.sort(key=lambda x: int(x.get("height") or 0), reverse=True)
    video_only.sort(key=lambda x: int(x.get("height") or 0), reverse=True)

    # Always provide fallback "best" options
    if not video_audio:
        video_audio.append({
            "format_id": "best",
            "audio_id": None,
            "label": "Best Quality (Video+Audio)",
            "tag": "",
            "size": "",
            "type": "video",
            "ext": "mp4",
            "height": 0,
            "needs_mux": False,
            "mux_type": None,
            "category": "video_audio",
        })
    if not video_only:
        video_only.append({
            "format_id": "bestvideo",
            "audio_id": None,
            "label": "Best Video Only",
            "tag": "",
            "size": "",
            "type": "video",
            "ext": "mp4",
            "height": 0,
            "needs_mux": False,
            "mux_type": None,
            "category": "video_only",
        })
    if not audio_only:
        audio_only.append({
            "format_id": "bestaudio",
            "audio_id": None,
            "label": "Best Audio",
            "tag": "",
            "size": "",
            "type": "audio",
            "ext": "m4a",
            "height": 0,
            "needs_mux": False,
            "mux_type": None,
            "category": "audio_only",
        })

    out = video_audio + video_only + audio_only
    yt_downloader.log(f"[{platform}] Built {len(video_audio)} video+audio, {len(video_only)} video-only, {len(audio_only)} audio-only formats")
    return out


def get_info(url):
    if _is_youtube(url):
        info, err = yt_downloader.get_info(url)
        if info:
            info["platform"] = "youtube"
        return info, err

    yt_downloader.fix_ssl()
    platform = detect_platform(url)
    if not _YT_DLP_AVAILABLE:
        return None, "yt-dlp not installed"

    # Get platform-specific configuration using new API system
    platform_config = api.get_platform_config(platform)
    cookie_file = api.get_cookie_file_path(platform)
    
    # Get yt-dlp config from platform API
    base_config = platform_config.get_yt_dlp_config(yt_downloader.UA)
    base_config.update({
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
    })
    
    # Add cookies if available
    if cookie_file:
        base_config["cookiefile"] = cookie_file
        yt_downloader.log(f"[{platform}] Using cookies from: {cookie_file}")
    elif platform_config.requires_cookies:
        yt_downloader.log(f"[{platform}] WARNING: Cookies recommended but not found")

    try:
        with yt_dlp.YoutubeDL(base_config) as ydl:
            raw = ydl.extract_info(url, download=False)

        # Log raw format info for debugging
        raw_formats = raw.get("formats", [])
        yt_downloader.log(f"[{platform}] Extracted {len(raw_formats)} raw formats for: {raw.get('title', '?')}")
        
        formats = _build_generic_formats(raw_formats, platform)
        
        return {
            "title": raw.get("title", "Unknown"),
            "channel": raw.get("channel") or raw.get("uploader", ""),
            "duration": raw.get("duration", 0) or 0,
            "views": raw.get("view_count", 0) or 0,
            "thumbnail": raw.get("thumbnail", ""),
            "formats": formats,
            "url": url,
            "platform": platform,
        }, None
    except Exception as e:
        err_msg = str(e)
        yt_downloader.log(f"[{platform}] get_info error: {err_msg}\n{traceback.format_exc()}")
        
        # Use platform-specific error parsing
        friendly_error = platform_config.parse_error(err_msg)
        return None, friendly_error


def _respect_control_local(control, on_state=None, on_progress=None, pct=0, total="?"):
    if not control:
        return
    if hasattr(control, "is_cancelled") and control.is_cancelled():
        raise yt_downloader.DownloadCancelled("Download cancelled")

    paused_notified = False
    while hasattr(control, "is_paused") and control.is_paused():
        if on_state and not paused_notified:
            try:
                on_state("paused")
            except Exception:
                pass
            paused_notified = True
        if on_progress:
            try:
                on_progress(float(pct), "-", "-", "Paused", total or "?")
            except Exception:
                pass
        time.sleep(0.25)
        if hasattr(control, "is_cancelled") and control.is_cancelled():
            raise yt_downloader.DownloadCancelled("Download cancelled")

    if paused_notified and on_state:
        try:
            on_state("resumed")
        except Exception:
            pass


def download(url, fmt_info=None, on_progress=None, on_done=None, on_error=None,
             control=None, on_state=None, on_net=None):
    if _is_youtube(url):
        return yt_downloader.download(
            url=url,
            fmt_info=fmt_info,
            on_progress=on_progress,
            on_done=on_done,
            on_error=on_error,
            control=control,
            on_state=on_state,
            on_net=on_net,
        )

    yt_downloader.fix_ssl()
    platform = detect_platform(url)
    if not _YT_DLP_AVAILABLE:
        if on_error:
            on_error("yt-dlp not installed")
        return

    s = {}
    if yt_downloader.app_settings:
        try:
            s = yt_downloader.app_settings.load_settings()
        except Exception:
            s = {}
    resume_enabled = bool(s.get("resume_downloads", False))
    ytdlp_cache_dir = os.path.join(yt_downloader._base(), ".ytdlp_cache")
    if resume_enabled:
        try:
            os.makedirs(ytdlp_cache_dir, exist_ok=True)
        except Exception:
            pass
    else:
        ytdlp_cache_dir = False

    dl_dir = yt_downloader.get_dl_dir()
    format_id = (fmt_info or {}).get("format_id") or "best"

    # Get platform-specific configuration using new API system
    platform_config = api.get_platform_config(platform)
    cookie_file = api.get_cookie_file_path(platform)
    
    # Get download config from platform API
    common = platform_config.get_download_config(yt_downloader.UA)
    common.update({
        "quiet": True,
        "no_warnings": True,
        "continuedl": resume_enabled,
        "nopart": (not resume_enabled),
        "cachedir": ytdlp_cache_dir,
        "outtmpl": os.path.join(dl_dir, "%(title)s.%(ext)s"),
        "format": format_id,
    })
    
    # Add cookies if available
    if cookie_file:
        common["cookiefile"] = cookie_file
        yt_downloader.log(f"[{platform}] Using cookies for download: {cookie_file}")
    elif platform_config.requires_cookies:
        yt_downloader.log(f"[{platform}] WARNING: Cookies recommended but not found")

    def hook(d):
        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
        done = d.get("downloaded_bytes", 0)
        frac = done / total if total else 0
        pct = round(frac * 100.0, 1)
        total_txt = f"{total/1048576:.0f} MB" if total else "?"
        _respect_control_local(control, on_state=on_state, on_progress=on_progress, pct=pct, total=total_txt)
        if d.get("status") == "downloading" and on_progress:
            spd = d.get("speed") or 0
            eta = d.get("eta") or 0
            on_progress(
                pct,
                f"{spd/1048576:.1f} MB/s" if spd else "-",
                f"{eta}s" if eta else "-",
                "Downloading",
                total_txt,
            )

    try:
        if on_net:
            try:
                on_net({"kind": "reset", "dns_retries": 0, "net_retries": 0})
            except Exception:
                pass
        with yt_dlp.YoutubeDL({**common, "progress_hooks": [hook]}) as ydl:
            info = ydl.extract_info(url, download=True)
            final = ydl.prepare_filename(info)
        if on_progress:
            on_progress(100, "-", "-", "Done!", "")
        if on_done:
            on_done(final)
    except yt_downloader.DownloadCancelled as e:
        yt_downloader.log(f"[{platform}] Download cancelled: {e}")
        if on_error:
            on_error(str(e))
    except Exception as e:
        err_msg = str(e)
        yt_downloader.log(f"[{platform}] download error: {err_msg}\n{traceback.format_exc()}")
        
        # Use platform-specific error parsing
        friendly_error = platform_config.parse_error(err_msg)
        if on_error:
            on_error(friendly_error)


def download_batch(url_list, fmt_info=None, on_progress=None, on_done=None,
                   on_error=None, on_batch_done=None, control=None,
                   on_state=None, on_net=None):
    """Download a list of URLs sequentially.

    on_batch_done(completed, failed, total) is called once at the end, where
    *completed* and *failed* are lists of result dicts with keys:
    {"url", "path"/"error"}.
    """
    completed = []
    failed = []
    total = len(url_list)

    for idx, url in enumerate(url_list, 1):
        if hasattr(control, "is_cancelled") and control.is_cancelled():
            break

        done = {"url": url}
        error_holder = {"error": None}

        def _on_done(path):
            done["path"] = path

        def _on_err(msg):
            error_holder["error"] = msg

        def _on_prog(pct, spd, eta, state, total_txt):
            if on_progress:
                label = f"[{idx}/{total}] {pct:.0f}% — {urlparse(url).netloc}"
                on_progress(pct, spd, eta, label, total_txt)

        download(
            url=url,
            fmt_info=fmt_info,
            on_progress=_on_prog,
            on_done=_on_done,
            on_error=_on_err,
            control=control,
            on_state=on_state,
            on_net=on_net,
        )

        if error_holder["error"]:
            done["error"] = error_holder["error"]
            failed.append(done)
        elif "path" in done:
            completed.append(done)
        else:
            done["error"] = "Unknown failure"
            failed.append(done)

    if on_batch_done:
        on_batch_done(completed, failed, total)
