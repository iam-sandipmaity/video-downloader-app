"""
Persistent app settings for Video Downloader.
"""

import json
import os
import time

APP_VERSION = "1.0"
DEFAULT_THEME = "Neon Dusk"
DEFAULT_MAX_CRASH_LOG_MB = 2
DEFAULT_CACHE_MAX_AGE_HOURS = 12
DEFAULT_HISTORY_LIMIT = 120
DEFAULT_DIAGNOSTICS_LIVE = True


def _external_base():
    try:
        from android.storage import primary_external_storage_path
        root = primary_external_storage_path()
    except Exception:
        root = os.path.expanduser("~")
    return os.path.join(root, "Download", "videodownloader")


def default_download_dir():
    return _external_base()


def settings_path():
    return os.path.join(_external_base(), "settings.json")


def crash_log_path():
    return os.path.join(_external_base(), "crash.log")


def history_path():
    return os.path.join(_external_base(), "history.json")


def backups_dir():
    p = os.path.join(_external_base(), "backups")
    os.makedirs(p, exist_ok=True)
    return p


def _defaults():
    return {
        "download_dir": default_download_dir(),
        "theme": DEFAULT_THEME,
        "theme_mode": "dark",
        "notifications": True,
        "resume_downloads": False,
        "background_keep_awake": True,
        "auto_cleanup_cache": True,
        "cache_max_age_hours": DEFAULT_CACHE_MAX_AGE_HOURS,
        "max_crash_log_mb": DEFAULT_MAX_CRASH_LOG_MB,
        "history_limit": DEFAULT_HISTORY_LIMIT,
        "diagnostics_live": DEFAULT_DIAGNOSTICS_LIVE,
    }


def load_settings():
    data = _defaults()
    p = settings_path()
    try:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                raw = json.load(f)
                if isinstance(raw, dict):
                    data.update(raw)
    except Exception:
        pass
    return data


def save_settings(data):
    merged = _defaults()
    if isinstance(data, dict):
        merged.update(data)
    p = settings_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    return merged


def load_history():
    p = history_path()
    try:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                raw = json.load(f)
                if isinstance(raw, list):
                    out = []
                    for it in raw:
                        if isinstance(it, dict):
                            out.append(it)
                    return out
    except Exception:
        pass
    return []


def save_history(items):
    p = history_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    payload = items if isinstance(items, list) else []
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


def _mk_hist_id():
    return f"h{int(time.time() * 1000)}"


def append_history(entry, limit=DEFAULT_HISTORY_LIMIT):
    arr = load_history()
    if not isinstance(entry, dict):
        return arr
    item = dict(entry)
    item.setdefault("id", _mk_hist_id())
    item.setdefault("name", "")
    item.setdefault("type", "video")
    item.setdefault("path", "")
    item.setdefault("added_at", int(time.time()))
    arr.append(item)
    try:
        lim = max(10, min(500, int(float(limit))))
    except Exception:
        lim = DEFAULT_HISTORY_LIMIT
    if len(arr) > lim:
        arr = arr[-lim:]
    return save_history(arr)


def delete_history_item(item_id):
    arr = load_history()
    sid = str(item_id or "")
    out = [x for x in arr if str(x.get("id", "")) != sid]
    save_history(out)
    return out


def clear_history():
    return save_history([])


def create_backup(settings_data=None, history_data=None):
    now = time.strftime("%Y%m%d_%H%M%S")
    p = os.path.join(backups_dir(), f"backup_{now}.json")
    payload = {
        "created_at": int(time.time()),
        "settings": settings_data if isinstance(settings_data, dict) else load_settings(),
        "history": history_data if isinstance(history_data, list) else load_history(),
    }
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return p


def list_backups(limit=20):
    out = []
    bdir = backups_dir()
    try:
        names = [x for x in os.listdir(bdir) if x.lower().endswith(".json")]
        names.sort(reverse=True)
        for name in names[:max(1, int(limit))]:
            p = os.path.join(bdir, name)
            try:
                st = os.stat(p)
                out.append({
                    "name": name,
                    "path": p,
                    "size": st.st_size,
                    "mtime": int(st.st_mtime),
                })
            except Exception:
                pass
    except Exception:
        pass
    return out


def restore_backup(path):
    p = str(path or "").strip()
    if not p or not os.path.exists(p):
        raise FileNotFoundError("Backup file not found")
    with open(p, "r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        raise ValueError("Invalid backup format")
    s = raw.get("settings")
    h = raw.get("history")
    if isinstance(s, dict):
        save_settings(s)
    if isinstance(h, list):
        save_history(h)
    return {
        "settings": load_settings(),
        "history": load_history(),
    }


def get_download_dir():
    s = load_settings()
    path = str(s.get("download_dir") or "").strip()
    if not path:
        path = default_download_dir()
    os.makedirs(path, exist_ok=True)
    return path


def set_download_dir(path):
    p = str(path or "").strip()
    if not p:
        p = default_download_dir()
    os.makedirs(p, exist_ok=True)
    s = load_settings()
    s["download_dir"] = p
    save_settings(s)
    return p


def set_notifications(enabled):
    s = load_settings()
    s["notifications"] = bool(enabled)
    save_settings(s)
    return bool(s.get("notifications", True))


def set_auto_cleanup_cache(enabled):
    s = load_settings()
    s["auto_cleanup_cache"] = bool(enabled)
    save_settings(s)
    return bool(s.get("auto_cleanup_cache", True))


def set_resume_downloads(enabled):
    s = load_settings()
    s["resume_downloads"] = bool(enabled)
    save_settings(s)
    return bool(s.get("resume_downloads", False))


def set_background_keep_awake(enabled):
    s = load_settings()
    s["background_keep_awake"] = bool(enabled)
    save_settings(s)
    return bool(s.get("background_keep_awake", True))


def set_cache_max_age_hours(hours):
    s = load_settings()
    try:
        val = max(1, int(float(hours)))
    except Exception:
        val = DEFAULT_CACHE_MAX_AGE_HOURS
    s["cache_max_age_hours"] = val
    save_settings(s)
    return int(s.get("cache_max_age_hours", DEFAULT_CACHE_MAX_AGE_HOURS))


def set_max_crash_log_mb(mb):
    s = load_settings()
    try:
        val = max(1, int(float(mb)))
    except Exception:
        val = DEFAULT_MAX_CRASH_LOG_MB
    s["max_crash_log_mb"] = val
    save_settings(s)
    return int(s.get("max_crash_log_mb", DEFAULT_MAX_CRASH_LOG_MB))


def max_crash_log_bytes():
    s = load_settings()
    mb = s.get("max_crash_log_mb", DEFAULT_MAX_CRASH_LOG_MB)
    try:
        mb = max(1, int(float(mb)))
    except Exception:
        mb = DEFAULT_MAX_CRASH_LOG_MB
    return mb * 1024 * 1024


def set_history_limit(limit):
    s = load_settings()
    try:
        val = max(10, min(500, int(float(limit))))
    except Exception:
        val = DEFAULT_HISTORY_LIMIT
    s["history_limit"] = val
    save_settings(s)
    return int(s.get("history_limit", DEFAULT_HISTORY_LIMIT))


def set_diagnostics_live(enabled):
    s = load_settings()
    s["diagnostics_live"] = bool(enabled)
    save_settings(s)
    return bool(s.get("diagnostics_live", DEFAULT_DIAGNOSTICS_LIVE))


def set_theme_mode(mode):
    s = load_settings()
    m = str(mode or "").strip().lower()
    if m not in ("dark", "light"):
        m = "dark"
    s["theme_mode"] = m
    s["theme"] = DEFAULT_THEME if m == "dark" else "Light Breeze"
    save_settings(s)
    return str(s.get("theme_mode", "dark"))
