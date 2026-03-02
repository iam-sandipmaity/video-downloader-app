"""
downloader.py v9
================
Strategy: No ffmpeg binary required. Works 100% on Android.

For formats that need merging (720p+):
  1. Download video-only stream via yt-dlp  (0–55%)
  2. Download audio-only stream via yt-dlp  (55–90%)
  3. Mux them in pure Python                (90–100%)

MP4 mux:  Rewrites moov atoms, fixes stco/co64 chunk offsets.
WebM mux: Combines EBML Tracks + interleaves Clusters by timecode.

For combined streams (360p, audio-only): direct single download.
Key: ffmpeg_location set to /dev/null so yt-dlp NEVER tries to invoke
     the missing ffmpeg binary — we handle all merging ourselves.
"""

import os, ssl, struct, traceback, tempfile, shutil, time, threading
from pathlib import Path

try:
    import app_settings
except Exception:
    app_settings = None

try:
    import yt_dlp
    _YT_DLP_AVAILABLE = True
except ImportError:
    yt_dlp = None
    _YT_DLP_AVAILABLE = False

# ── Storage / Logging ─────────────────────────────────────────────────────
def _base():
    try:
        from android.storage import primary_external_storage_path
        b = os.path.join(primary_external_storage_path(), "Download", "videodownloader")
    except ImportError:
        b = os.path.join(os.path.expanduser("~"), "Downloads", "videodownloader")
    os.makedirs(b, exist_ok=True)
    return b


def _logpath():
    return os.path.join(_base(), "crash.log")


def _max_log_bytes():
    if app_settings and hasattr(app_settings, "max_crash_log_bytes"):
        try:
            return int(app_settings.max_crash_log_bytes())
        except Exception:
            pass
    return 2 * 1024 * 1024


def _append_line_capped(path, line, max_bytes):
    try:
        if os.path.exists(path):
            sz = os.path.getsize(path)
            if sz > max_bytes:
                keep = max_bytes // 2
                with open(path, "rb") as rf:
                    rf.seek(max(0, sz - keep))
                    tail = rf.read()
                with open(path, "wb") as wf:
                    wf.write(b"...log truncated...\n")
                    wf.write(tail)
        with open(path, "a", encoding="utf-8", errors="ignore") as af:
            af.write(line + "\n")
    except Exception:
        pass


def log(msg):
    _append_line_capped(_logpath(), str(msg), _max_log_bytes())

def _bool_env(name):
    v = str(os.environ.get(name, "")).strip().lower()
    return v in ("1", "true", "yes", "on")

MUX_DEBUG = _bool_env("YT_MUX_DEBUG")
# Enable with environment variable: YT_MUX_DEBUG=1
_SSL_READY = False


class DownloadCancelled(Exception):
    pass


class DownloadControl:
    """Thread-safe pause/resume/cancel control for active downloads."""
    def __init__(self):
        self._pause_evt = threading.Event()
        self._cancel_evt = threading.Event()

    def pause(self):
        self._pause_evt.set()

    def resume(self):
        self._pause_evt.clear()

    def cancel(self):
        self._cancel_evt.set()
        self._pause_evt.clear()

    def is_paused(self):
        return self._pause_evt.is_set()

    def is_cancelled(self):
        return self._cancel_evt.is_set()

def _mux_debug_log(out_path, msg):
    if not MUX_DEBUG:
        return
    try:
        p = f"{out_path}.mux.log"
        with open(p, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception as e:
        log(f"mux_debug write failed: {e}")

def fix_ssl():
    global _SSL_READY
    if _SSL_READY:
        return
    try:
        import certifi
        ca = certifi.where()
        os.environ["SSL_CERT_FILE"]      = ca
        os.environ["REQUESTS_CA_BUNDLE"] = ca
        ssl._create_default_https_context = \
            lambda: ssl.create_default_context(cafile=ca)
        _SSL_READY = True
    except Exception as e:
        log(f"SSL: {e}")

def request_perms():
    """
    Permission check only.
    Runtime request is handled by main.py UI flow.
    """
    try:
        from android.permissions import check_permission, Permission
        probes = []
        for name in (
            "READ_MEDIA_VIDEO",
            "READ_MEDIA_AUDIO",
            "READ_EXTERNAL_STORAGE",
            "WRITE_EXTERNAL_STORAGE",
        ):
            p = getattr(Permission, name, None)
            if p:
                probes.append(p)
        if not probes:
            return True
        return any(check_permission(p) for p in probes)
    except ImportError:
        return True
    except Exception as e:
        log(f"Perms check note: {e}")
        return True

def get_dl_dir():
    if app_settings:
        try:
            return app_settings.get_download_dir()
        except Exception as e:
            log(f"settings dir fallback: {e}")
    return _base()


def _cache_candidates():
    return [
        "/data/user/0/com.local.videodownloader/cache",
        "/data/data/com.local.videodownloader/cache",
    ]


def get_temp_cache_stats():
    dirs = []
    total = 0
    count = 0
    for c in _cache_candidates():
        if not os.path.isdir(c):
            continue
        dirs.append(c)
        try:
            for name in os.listdir(c):
                if not name.startswith("ytdl_"):
                    continue
                p = os.path.join(c, name)
                if os.path.isdir(p):
                    count += 1
                    for root, _, files in os.walk(p):
                        for fn in files:
                            fp = os.path.join(root, fn)
                            try:
                                total += os.path.getsize(fp)
                            except Exception:
                                pass
        except Exception:
            pass
    return {
        "dirs": dirs,
        "temp_dirs": count,
        "bytes": total,
    }


def cleanup_temp_cache(max_age_hours=12):
    try:
        max_age_hours = float(max_age_hours)
    except Exception:
        max_age_hours = 12.0
    now = time.time()
    max_age_sec = max(0.0, max_age_hours) * 3600.0
    removed_dirs = 0
    removed_bytes = 0

    for c in _cache_candidates():
        if not os.path.isdir(c):
            continue
        try:
            names = os.listdir(c)
        except Exception:
            continue
        for name in names:
            if not name.startswith("ytdl_"):
                continue
            p = os.path.join(c, name)
            if not os.path.isdir(p):
                continue
            try:
                mtime = os.path.getmtime(p)
                age = now - mtime
                if max_age_sec > 0 and age < max_age_sec:
                    continue
                size = 0
                for root, _, files in os.walk(p):
                    for fn in files:
                        fp = os.path.join(root, fn)
                        try:
                            size += os.path.getsize(fp)
                        except Exception:
                            pass
                shutil.rmtree(p, ignore_errors=True)
                removed_dirs += 1
                removed_bytes += size
            except Exception:
                pass
    return {
        "removed_dirs": removed_dirs,
        "removed_bytes": removed_bytes,
    }

UA = ("Mozilla/5.0 (Linux; Android 13; Pixel 7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/116.0.0.0 Mobile Safari/537.36")

def fetch_thumbnail(url, dest):
    try:
        import certifi, urllib.request
        ctx = ssl.create_default_context(cafile=certifi.where())
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            with open(dest, "wb") as f:
                f.write(r.read())
        return True
    except Exception as e:
        log(f"Thumb: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════
#  PURE-PYTHON MP4 MUXER
#  Combines one video-only .mp4 + one audio-only .m4a into a playable .mp4
#  Output layout: [ftyp][moov(video+audio traks, offsets patched)][mdat-v][mdat-a]
# ══════════════════════════════════════════════════════════════════════════

def _u32(data, pos):
    return struct.unpack_from(">I", data, pos)[0]

def _u64(data, pos):
    return struct.unpack_from(">Q", data, pos)[0]

def _find_box(data, fourcc, start=0):
    """Return (offset, size) of first box or None."""
    fc = fourcc if isinstance(fourcc, bytes) else fourcc.encode()
    i, end = start, len(data)
    while i + 8 <= end:
        raw_sz = _u32(data, i)
        if raw_sz == 1:
            if i + 16 > end: break
            sz = _u64(data, i + 8)
        elif raw_sz == 0:
            sz = end - i
        else:
            sz = raw_sz
        if sz < 8: break
        if data[i+4:i+8] == fc:
            return i, sz
        i += sz
    return None

def _get_box(data, fourcc, start=0):
    r = _find_box(data, fourcc, start)
    return None if r is None else data[r[0]:r[0]+r[1]]

def _iter_top_boxes(data):
    i, end = 0, len(data)
    while i + 8 <= end:
        raw_sz = _u32(data, i)
        if raw_sz == 1:
            if i + 16 > end: break
            sz = _u64(data, i + 8)
        elif raw_sz == 0:
            sz = end - i
        else:
            sz = raw_sz
        if sz < 8: break
        yield i, sz, data[i+4:i+8]
        i += sz

# ── Box builders ─────────────────────────────────────────────────────────

def _box(fc, pl=b""):
    fc = fc if isinstance(fc, bytes) else fc.encode()
    return struct.pack(">I", 8 + len(pl)) + fc + pl

def _fullbox(fc, version, flags, pl=b""):
    fc = fc if isinstance(fc, bytes) else fc.encode()
    return struct.pack(">I", 12 + len(pl)) + fc + \
           struct.pack(">I", (version << 24) | (flags & 0xFFFFFF)) + pl

# ── trak helpers ──────────────────────────────────────────────────────────

def _handler(trak):
    mdia = _get_box(trak, b"mdia", 8)
    if not mdia: return ""
    hdlr = _get_box(mdia, b"hdlr", 8)
    if not hdlr or len(hdlr) < 20: return ""
    return hdlr[16:20].decode("latin1", errors="replace").strip("\x00")

def _tkhd_track_id(trak):
    """Read track_ID from tkhd (version 0 or 1)."""
    tkhd = _get_box(trak, b"tkhd", 8)
    if not tkhd: return 0
    ver = tkhd[8]
    pos = 28 if ver == 1 else 20
    return _u32(tkhd, pos) if len(tkhd) >= pos + 4 else 0

def _patch_tkhd_track_id(trak, new_id):
    """Return trak with track_ID in tkhd replaced."""
    r = _find_box(trak, b"tkhd", 8)
    if not r: return trak
    o, s = r
    tkhd = bytearray(trak[o:o+s])
    ver  = tkhd[8]
    pos  = 28 if ver == 1 else 20
    if len(tkhd) < pos + 4: return trak
    struct.pack_into(">I", tkhd, pos, new_id)
    return trak[:o] + bytes(tkhd) + trak[o+s:]

def _patch_tkhd_flags(trak, flags=3):
    """Set tkhd flags (default 3 = enabled + in_movie)."""
    r = _find_box(trak, b"tkhd", 8)
    if not r: return trak
    o, s = r
    tkhd = bytearray(trak[o:o+s])
    if len(tkhd) < 12: return trak
    # flags occupy bytes 9-11 of the box
    tkhd[9]  = (flags >> 16) & 0xFF
    tkhd[10] = (flags >>  8) & 0xFF
    tkhd[11] =  flags        & 0xFF
    return trak[:o] + bytes(tkhd) + trak[o+s:]

def _is_fragmented(moov):
    """True if moov contains mvex (fragmented MP4)."""
    return _find_box(moov[8:], b"mvex") is not None

# ── fMP4 fragment helpers ─────────────────────────────────────────────────

def _moof_track_id(moof):
    """track_ID from moof → traf → tfhd."""
    inner = moof[8:]
    r = _find_box(inner, b"traf")
    if not r: return 1
    traf = inner[r[0]+8:r[0]+r[1]]
    r2   = _find_box(traf, b"tfhd")
    if not r2 or len(traf) < r2[0]+16: return 1
    return _u32(traf, r2[0]+12)

def _moof_decode_time(moof):
    """Base decode time from moof → traf → tfdt."""
    inner = moof[8:]
    r = _find_box(inner, b"traf")
    if not r: return 0
    traf = inner[r[0]+8:r[0]+r[1]]
    r2   = _find_box(traf, b"tfdt")
    if not r2: return 0
    tfdt = traf[r2[0]:r2[0]+r2[1]]
    if len(tfdt) < 12: return 0
    return (_u64(tfdt, 12) if tfdt[8] == 1 and len(tfdt) >= 20
            else _u32(tfdt, 12) if len(tfdt) >= 16 else 0)

def _patch_moof_track_id(moof, old_id, new_id):
    """Patch track_ID in every traf→tfhd within a moof blob."""
    if old_id == new_id: return moof
    buf  = bytearray(moof)
    end  = len(buf)
    i    = 8  # skip moof header
    while i + 8 <= end:
        raw = _u32(buf, i)
        sz  = _u64(buf, i+8) if raw == 1 else (end - i if raw == 0 else raw)
        if sz < 8 or i + sz > end: break
        if bytes(buf[i+4:i+8]) == b"traf":
            j      = i + 8
            t_end  = i + sz
            while j + 8 <= t_end:
                raw2 = _u32(buf, j)
                sz2  = _u64(buf, j+8) if raw2 == 1 else (t_end - j if raw2 == 0 else raw2)
                if sz2 < 8 or j + sz2 > t_end: break
                if bytes(buf[j+4:j+8]) == b"tfhd" and j + 16 <= t_end:
                    if _u32(buf, j+12) == old_id:
                        struct.pack_into(">I", buf, j+12, new_id)
                j += sz2
        i += sz
    return bytes(buf)

def _patch_mfhd_seq(moof, seq):
    """Set sequence_number in moof → mfhd."""
    buf = bytearray(moof)
    i   = 8
    end = len(buf)
    while i + 8 <= end:
        raw = _u32(buf, i)
        sz  = raw if raw > 1 else (end - i if raw == 0 else _u64(buf, i+8))
        if sz < 8 or i + sz > end: break
        if bytes(buf[i+4:i+8]) == b"mfhd" and i + 16 <= end:
            struct.pack_into(">I", buf, i+12, seq)
            break
        i += sz
    return bytes(buf)

def _moof_trun_duration(moof):
    """Sum all sample durations declared in trun boxes of this moof."""
    inner = moof[8:]
    r = _find_box(inner, b"traf")
    if not r: return 0
    traf = inner[r[0]+8:r[0]+r[1]]
    default_dur = 0
    r2 = _find_box(traf, b"tfhd")
    if r2:
        tfhd  = traf[r2[0]:r2[0]+r2[1]]
        tf_fl = _u32(tfhd, 8) & 0xFFFFFF
        p = 16
        if tf_fl & 0x01: p += 8
        if tf_fl & 0x02: p += 4
        if tf_fl & 0x08 and len(tfhd) >= p+4:
            default_dur = _u32(tfhd, p)
    total = 0
    i2, end2 = 0, len(traf)
    while i2 + 8 <= end2:
        raw = _u32(traf, i2)
        sz  = _u64(traf, i2+8) if raw == 1 else (end2-i2 if raw == 0 else raw)
        if sz < 8 or i2+sz > end2: break
        if traf[i2+4:i2+8] == b"trun":
            box   = traf[i2:i2+sz]
            tr_fl = _u32(box, 8) & 0xFFFFFF
            cnt   = _u32(box, 12)
            pos   = 16
            if tr_fl & 0x001: pos += 4
            if tr_fl & 0x004: pos += 4
            for _ in range(cnt):
                dur = default_dur
                if tr_fl & 0x100:
                    dur = _u32(box, pos) if pos+4 <= len(box) else dur
                    pos += 4
                if tr_fl & 0x200: pos += 4
                if tr_fl & 0x400: pos += 4
                if tr_fl & 0x800: pos += 4
                total += dur
        i2 += sz
    return total

def _parse_fragments(data):
    """Return list of (decode_time, track_id, moof_bytes, mdat_bytes)."""
    frags = []
    dlen  = len(data)
    i     = 0
    while i + 8 <= dlen:
        raw = _u32(data, i)
        sz  = _u64(data, i+8) if raw == 1 else (dlen-i if raw == 0 else raw)
        if sz < 8 or i+sz > dlen: break
        if data[i+4:i+8] == b"moof":
            moof = data[i:i+sz]
            j    = i + sz
            mdat = b""
            if j + 8 <= dlen:
                mr  = _u32(data, j)
                msz = _u64(data, j+8) if mr == 1 else (dlen-j if mr == 0 else mr)
                if data[j+4:j+8] == b"mdat" and msz >= 8 and j+msz <= dlen:
                    mdat = data[j:j+msz]
                    frags.append((_moof_decode_time(moof), _moof_track_id(moof),
                                  moof, mdat))
                    i = j + msz
                    continue
        i += sz
    return frags

# ── mvex / trex builders ──────────────────────────────────────────────────

def _build_trex(track_id):
    return _fullbox(b"trex", 0, 0,
                    struct.pack(">IIIII", track_id, 1, 0, 0, 0))

def _build_mvex(track_ids):
    return _box(b"mvex", b"".join(_build_trex(t) for t in track_ids))

def _strip_children(container, *fourccs):
    fcs = {(f if isinstance(f, bytes) else f.encode()) for f in fourccs}
    out = bytearray()
    for o, s, fc in _iter_top_boxes(container):
        if fc not in fcs:
            out += container[o:o+s]
    return bytes(out)

def _get_mdhd_timescale(moov_inner, handler_type="vide"):
    """Return mdhd timescale for the first trak of given handler type."""
    for o, s, fc in _iter_top_boxes(moov_inner):
        if fc != b"trak": continue
        trak = moov_inner[o:o+s]
        if _handler(trak) != handler_type: continue
        mdia = _get_box(trak, b"mdia", 8)
        if not mdia: continue
        mdhd = _get_box(mdia, b"mdhd", 8)
        if not mdhd or len(mdhd) < 20: continue
        ver = mdhd[8]
        ts  = _u32(mdhd, 20) if ver == 0 else _u32(mdhd, 28)
        if ts: return ts
    return 90000

def _patch_box_dur(buf, abs_start, f_v0, f_v1, value):
    """Patch a version-dependent 32/64-bit duration field in a bytearray."""
    if abs_start + 9 > len(buf): return
    ver = buf[abs_start + 8]
    off = abs_start + (f_v1 if ver == 1 else f_v0)
    if ver == 1 and off + 8 <= len(buf):
        struct.pack_into(">Q", buf, off, value)
    elif off + 4 <= len(buf):
        struct.pack_into(">I", buf, off, min(value, 0xFFFFFFFF))

def _patch_moov_durations(moov_bytes, mvhd_dur, mvhd_ts,
                          v_media_dur, v_ts, a_media_dur, a_ts):
    """
    Patch mvhd.duration, and per-trak tkhd.duration + mdhd.duration
    so Android shows correct total time.
    """
    buf = bytearray(moov_bytes)

    # mvhd: v0→offset 20, v1→offset 28
    r = _find_box(bytes(buf), b"mvhd", 8)
    if r: _patch_box_dur(buf, r[0], 20, 28, mvhd_dur)

    # Walk trak boxes at the moov level
    i = 8
    while i + 8 <= len(buf):
        raw = _u32(buf, i)
        sz  = _u64(buf, i+8) if raw == 1 else (len(buf)-i if raw == 0 else raw)
        if sz < 8: break
        if bytes(buf[i+4:i+8]) == b"trak":
            trak = bytes(buf[i:i+sz])
            h    = _handler(trak)
            if h == "vide":
                mdhd_dur = v_media_dur
                track_ts = v_ts
            elif h == "soun":
                mdhd_dur = a_media_dur
                track_ts = a_ts
            else:
                mdhd_dur = None
                track_ts = 0

            if mdhd_dur is not None:
                # tkhd duration is in movie timescale (mvhd timescale).
                tkhd_dur = (int(mdhd_dur * mvhd_ts / track_ts)
                            if mvhd_ts and track_ts else mdhd_dur)
                # tkhd: v0→offset 20, v1→offset 28
                r2 = _find_box(trak, b"tkhd")
                if r2: _patch_box_dur(buf, i+r2[0], 20, 28, tkhd_dur)
                # mdia → mdhd: v0→offset 16, v1→offset 24
                j2 = 8
                while j2 + 8 <= len(trak):
                    rr = _u32(trak, j2)
                    ss = _u64(trak, j2+8) if rr==1 else (len(trak)-j2 if rr==0 else rr)
                    if ss < 8: break
                    if trak[j2+4:j2+8] == b"mdia":
                        mdia = trak[j2:j2+ss]
                        r3   = _find_box(mdia, b"mdhd")
                        if r3: _patch_box_dur(buf, i+j2+r3[0], 16, 24, mdhd_dur)
                        break
                    j2 += ss
        i += sz
    return bytes(buf)

def _time_to_us(decode_time, timescale):
    if not timescale:
        return 0
    return (decode_time * 1_000_000) // timescale

def _build_sidx(reference_id, timescale, frags):
    """
    Build sidx (version 1, 64-bit) so Android MediaPlayer can seek.
    frags = [(decode_time, moof_bytes, mdat_bytes)] for ONE track, sorted.
    subsegment_duration = next_dt - this_dt (real delta from tfdt values).
    """
    if not frags: return b""
    refs = []
    for k, (dt, moof, mdat) in enumerate(frags):
        rsz = len(moof) + len(mdat)
        sub_dur = (frags[k+1][0] - dt) if k+1 < len(frags) else _moof_trun_duration(moof)
        refs.append((rsz, max(0, sub_dur)))

    payload  = struct.pack(">II", reference_id, timescale)
    payload += struct.pack(">Q", frags[0][0])   # earliest_presentation_time
    payload += struct.pack(">Q", 0)              # first_offset
    payload += struct.pack(">HH", 0, len(refs))
    for rsz, sub_dur in refs:
        payload += struct.pack(">I", rsz & 0x7FFFFFFF)
        payload += struct.pack(">I", sub_dur & 0xFFFFFFFF)
        payload += struct.pack(">I", 0x90000000)  # SAP=1 type=1
    return _fullbox(b"sidx", 1, 0, payload)

def _build_interleaved_video_sidx(reference_id, timescale, merged_frags, debug_refs=None):
    """
    Build a video sidx that matches the final interleaved byte layout.
    merged_frags = [(norm_us, kind, decode_time, moof, mdat)] sorted for output.
    """
    v_pos = [i for i, (_, kind, _, _, _) in enumerate(merged_frags) if kind == "v"]
    if not v_pos:
        return b""

    # If audio appears before first video, account for it in first_offset.
    first_offset = 0
    for _, _, _, moof, mdat in merged_frags[:v_pos[0]]:
        first_offset += len(moof) + len(mdat)

    refs = []
    earliest = merged_frags[v_pos[0]][2]
    for idx, pos in enumerate(v_pos):
        next_pos = v_pos[idx+1] if idx + 1 < len(v_pos) else len(merged_frags)
        cur_dt   = merged_frags[pos][2]
        cur_moof = merged_frags[pos][3]

        byte_len = 0
        for _, _, _, moof, mdat in merged_frags[pos:next_pos]:
            byte_len += len(moof) + len(mdat)

        if idx + 1 < len(v_pos):
            next_dt = merged_frags[v_pos[idx+1]][2]
            sub_dur = max(0, next_dt - cur_dt)
        else:
            next_dt = None
            sub_dur = _moof_trun_duration(cur_moof)
        if sub_dur <= 0:
            sub_dur = _moof_trun_duration(cur_moof)
        refs.append((byte_len, sub_dur))
        if debug_refs is not None:
            debug_refs.append((idx + 1, cur_dt, next_dt, byte_len, sub_dur))

    payload  = struct.pack(">II", reference_id, timescale)
    payload += struct.pack(">Q", earliest)
    payload += struct.pack(">Q", first_offset)
    payload += struct.pack(">HH", 0, len(refs))
    for rsz, sub_dur in refs:
        payload += struct.pack(">I", rsz & 0x7FFFFFFF)
        payload += struct.pack(">I", sub_dur & 0xFFFFFFFF)
        payload += struct.pack(">I", 0x90000000)
    return _fullbox(b"sidx", 1, 0, payload)

def _dump_fmp4_debug(out_path, v_ts, a_ts, all_frags, sidx_refs):
    if not MUX_DEBUG:
        return

    lines = []
    lines.append("=" * 72)
    lines.append(f"mux_file: {Path(out_path).name}")
    lines.append(f"timescale: video={v_ts} audio={a_ts}")
    lines.append(f"fragments_total: {len(all_frags)}")
    lines.append("fragment_order:")

    byte_off = 0
    for idx, (norm_us, kind, dt, moof, mdat) in enumerate(all_frags, 1):
        frag_sz = len(moof) + len(mdat)
        lines.append(
            f"  #{idx:04d} kind={kind} dt={dt} t_us={norm_us} "
            f"bytes={frag_sz} byte_off={byte_off}"
        )
        byte_off += frag_sz

    lines.append("sidx_video_map:")
    for ref_idx, cur_dt, next_dt, byte_len, sub_dur in sidx_refs:
        nxt = str(next_dt) if next_dt is not None else "end"
        lines.append(
            f"  ref#{ref_idx:04d} dt={cur_dt}->{nxt} "
            f"sub_dur={sub_dur} bytes={byte_len}"
        )

    for line in lines:
        _mux_debug_log(out_path, line)

# ── plain MP4 offset patching ─────────────────────────────────────────────

def _patch_stco_co64(trak, delta):
    """Recursively patch stco / co64 chunk offsets inside a trak blob."""
    if delta == 0: return trak
    buf = bytearray(trak)

    def walk(s, e):
        i = s
        while i + 8 <= e:
            raw = _u32(buf, i)
            # Guard: only read 8-byte size if we actually have 16 bytes available
            if raw == 1:
                if i + 16 > e: break
                sz  = _u64(buf, i+8)
                hdr = 16
            elif raw == 0:
                sz  = e - i
                hdr = 8
            else:
                sz  = raw
                hdr = 8
            if sz < 8 or i + sz > e: break
            fc = bytes(buf[i+4:i+8])
            if fc == b"stco":
                cnt = _u32(buf, i+12)
                for k in range(cnt):
                    p = i + 16 + k*4
                    if p + 4 > i+sz: break
                    struct.pack_into(">I", buf, p,
                                     min(_u32(buf, p) + delta, 0xFFFFFFFF))
                log(f"  stco patched: {cnt} entries Δ={delta:+d}")
            elif fc == b"co64":
                cnt = _u32(buf, i+12)
                for k in range(cnt):
                    p = i + 16 + k*8
                    if p + 8 > i+sz: break
                    struct.pack_into(">Q", buf, p, _u64(buf, p) + delta)
                log(f"  co64 patched: {cnt} entries Δ={delta:+d}")
            else:
                walk(i + hdr, i + sz)
            i += sz

    walk(0, len(buf))
    return bytes(buf)

# ══════════════════════════════════════════════════════════════════════════
#  mux_mp4 — handles both fragmented (fMP4/DASH) and plain MP4
#  fMP4: merges V+A fragments, patches real durations, adds sidx for seeking
#  plain: patches stco/co64 absolute offsets
# ══════════════════════════════════════════════════════════════════════════

def mux_mp4(video_path, audio_path, out_path):
    log(f"mux_mp4: {Path(video_path).name} + {Path(audio_path).name}")
    try:
        vd = open(video_path, "rb").read()
        ad = open(audio_path, "rb").read()

        v_moov = _get_box(vd, b"moov")
        a_moov = _get_box(ad, b"moov")
        if not v_moov: raise ValueError("No moov in video")
        if not a_moov: raise ValueError("No moov in audio")

        fragmented = _is_fragmented(v_moov)
        log(f"  fragmented={fragmented}")

        # ── ftyp ──────────────────────────────────────────────────────────
        raw_ftyp = _get_box(vd, b"ftyp")
        if raw_ftyp and len(raw_ftyp) >= 16:
            compat = set()
            for k in range(0, len(raw_ftyp)-16, 4):
                compat.add(raw_ftyp[16+k:16+k+4])
            compat |= {b"isom", b"iso6", b"avc1", b"mp41"}
            compat.discard(b"\x00\x00\x00\x00")
            ftyp = (struct.pack(">I", 16+len(compat)*4) + b"ftyp"
                    + b"isom\x00\x00\x02\x00" + b"".join(sorted(compat)))
        else:
            ftyp = _box(b"ftyp", b"isom\x00\x00\x02\x00isomavc1mp41iso6")

        # ── Extract traks ─────────────────────────────────────────────────
        vi = v_moov[8:]
        ai = a_moov[8:]
        v_traks = [vi[o:o+s] for o,s,fc in _iter_top_boxes(vi) if fc == b"trak"]
        a_traks = [ai[o:o+s] for o,s,fc in _iter_top_boxes(ai) if fc == b"trak"]

        vtrak = next((t for t in v_traks if _handler(t) == "vide"),
                     v_traks[0] if v_traks else None)
        atrak = next((t for t in a_traks if _handler(t) == "soun"),
                     a_traks[0] if a_traks else None)
        if not vtrak: raise ValueError("No video trak found")
        if not atrak: raise ValueError("No audio trak found")

        V_ID, A_ID = 1, 2
        vtrak = _patch_tkhd_track_id(_patch_tkhd_flags(vtrak, 3), V_ID)
        atrak = _patch_tkhd_track_id(_patch_tkhd_flags(atrak, 3), A_ID)

        # ── mvhd ─────────────────────────────────────────────────────────
        mvhd = bytearray(_get_box(vi, b"mvhd") or b"")
        if mvhd:
            nti = 116 if mvhd[8] == 1 else 104
            if len(mvhd) >= nti+4: struct.pack_into(">I", mvhd, nti, 3)
        mvhd = bytes(mvhd)

        if fragmented:
            # ── Fragmented MP4: merge V+A, patch durations, add sidx ──────
            v_frags = _parse_fragments(vd)
            a_frags = _parse_fragments(ad)
            log(f"  fragments: {len(v_frags)}v {len(a_frags)}a")
            if not v_frags: raise ValueError("No video fragments")
            if not a_frags: raise ValueError("No audio fragments")

            # Patch track IDs
            v_tid_raw = _moof_track_id(v_frags[0][2])
            a_tid_raw = _moof_track_id(a_frags[0][2])
            v_frags2 = [(dt, _patch_moof_track_id(mf, v_tid_raw, V_ID), md)
                        for dt, _, mf, md in v_frags]
            a_frags2 = [(dt, _patch_moof_track_id(mf, a_tid_raw, A_ID), md)
                        for dt, _, mf, md in a_frags]

            # Compute real total durations from tfdt decode times + trun sample durations
            v_ts = _get_mdhd_timescale(vi, "vide")
            a_ts = _get_mdhd_timescale(ai, "soun")

            if len(v_frags2) > 1:
                v_total = v_frags2[-1][0] - v_frags2[0][0] + _moof_trun_duration(v_frags2[-1][1])
            else:
                v_total = _moof_trun_duration(v_frags2[0][1])

            if len(a_frags2) > 1:
                a_total = a_frags2[-1][0] - a_frags2[0][0] + _moof_trun_duration(a_frags2[-1][1])
            else:
                a_total = _moof_trun_duration(a_frags2[0][1])

            # mvhd duration: video duration in mvhd timescale
            mvhd_ts = (_u32(mvhd, 28) if len(mvhd) > 28 and mvhd[8] == 1
                       else _u32(mvhd, 20) if len(mvhd) > 20 else 1000)
            if not mvhd_ts:
                mvhd_ts = 1000
            mvhd_dur = int(v_total * mvhd_ts / v_ts) if v_ts else v_total
            log(f"  dur: {v_total}/{v_ts}v  {a_total}/{a_ts}a  mvhd={mvhd_dur}/{mvhd_ts}")

            # Build moov with mvex and correct durations
            mvex       = _build_mvex([V_ID, A_ID])
            vi_clean   = _strip_children(vi, b"mvex")
            moov_inner = mvhd + vtrak + atrak + mvex
            for o, s, fc in _iter_top_boxes(vi_clean):
                if fc in (b"udta", b"meta"):
                    moov_inner += vi_clean[o:o+s]
            moov = _box(b"moov", moov_inner)
            moov = _patch_moov_durations(
                moov, mvhd_dur, mvhd_ts,
                v_total, v_ts, a_total, a_ts
            )

            # Interleave V+A fragments by normalized decode time (microseconds).
            all_frags = (
                [(_time_to_us(dt, v_ts), "v", dt, mf, md) for dt, mf, md in v_frags2] +
                [(_time_to_us(dt, a_ts), "a", dt, mf, md) for dt, mf, md in a_frags2]
            )
            all_frags.sort(key=lambda x: (x[0], 0 if x[1] == "v" else 1))

            # sidx must match final interleaved byte layout for reliable seeking.
            sidx_refs = [] if MUX_DEBUG else None
            sidx = _build_interleaved_video_sidx(V_ID, v_ts, all_frags, sidx_refs)

            frag_bytes = bytearray()
            for seq, (_, _, _, moof, mdat) in enumerate(all_frags, 1):
                frag_bytes += _patch_mfhd_seq(moof, seq) + mdat

            with open(out_path, "wb") as f:
                f.write(ftyp)
                f.write(moov)
                f.write(sidx)
                f.write(bytes(frag_bytes))

            if MUX_DEBUG:
                _dump_fmp4_debug(out_path, v_ts, a_ts, all_frags, sidx_refs or [])

        else:
            # ── Plain MP4: patch stco absolute offsets ────────────────────
            v_pay = b"".join(
                vd[o+(16 if _u32(vd,o)==1 else 8):o+s]
                for o,s,fc in _iter_top_boxes(vd) if fc == b"mdat")
            a_pay = b"".join(
                ad[o+(16 if _u32(ad,o)==1 else 8):o+s]
                for o,s,fc in _iter_top_boxes(ad) if fc == b"mdat")
            if not v_pay: raise ValueError("No mdat in video")
            if not a_pay: raise ValueError("No mdat in audio")

            v_old = next((o+(16 if _u32(vd,o)==1 else 8)
                          for o,s,fc in _iter_top_boxes(vd) if fc==b"mdat"), len(vd))
            a_old = next((o+(16 if _u32(ad,o)==1 else 8)
                          for o,s,fc in _iter_top_boxes(ad) if fc==b"mdat"), len(ad))

            ftyp_sz    = len(ftyp)
            moov_inner = mvhd + vtrak + atrak
            msz        = 8 + len(moov_inner)
            v_new = ftyp_sz + msz + 8
            a_new = ftyp_sz + msz + 8 + len(v_pay) + 8

            vtp  = _patch_stco_co64(vtrak, v_new - v_old)
            atp  = _patch_stco_co64(atrak, a_new - a_old)
            moov = _box(b"moov", mvhd + vtp + atp)

            if len(moov) != msz:
                msz   = len(moov)
                v_new = ftyp_sz + msz + 8
                a_new = ftyp_sz + msz + 8 + len(v_pay) + 8
                vtp   = _patch_stco_co64(vtrak, v_new - v_old)
                atp   = _patch_stco_co64(atrak, a_new - a_old)
                moov  = _box(b"moov", mvhd + vtp + atp)

            with open(out_path, "wb") as f:
                f.write(ftyp)
                f.write(moov)
                f.write(struct.pack(">I", 8+len(v_pay)) + b"mdat" + v_pay)
                f.write(struct.pack(">I", 8+len(a_pay)) + b"mdat" + a_pay)

        sz_mb = os.path.getsize(out_path) // 1_048_576
        log(f"mux_mp4 OK: {sz_mb}MB  {'seekable-fMP4' if fragmented else 'flat'}")
        return True

    except Exception:
        log(f"mux_mp4 FAILED:\n{traceback.format_exc()}")
        try: shutil.copy2(video_path, out_path)
        except Exception: pass
        return False




# ══════════════════════════════════════════════════════════════════════════
#  PURE-PYTHON WEBM MUXER
# ══════════════════════════════════════════════════════════════════════════

_EBML_ID    = b"\x1A\x45\xDF\xA3"
_SEG_ID     = b"\x18\x53\x80\x67"
_INFO_ID    = b"\x15\x49\xA9\x66"
_TRACKS_ID  = b"\x16\x54\xAE\x6B"
_TENTRY_ID  = b"\xAE"
_TNUM_ID    = b"\xD7"
_TTYPE_ID   = b"\x83"
_CLUSTER_ID = b"\x1F\x43\xB6\x75"
_TC_ID      = b"\xE7"
_CUES_ID    = b"\x1C\x53\xBB\x6B"
_CUEP_ID    = b"\xBB"
_CUETIME_ID = b"\xB3"
_CUETP_ID   = b"\xB7"
_CUETRK_ID  = b"\xF7"
_CUECP_ID   = b"\xF1"

def _vr(data, pos):
    if pos >= len(data): return 0, 1
    b = data[pos]
    if   b & 0x80: n, m = 1, 0x7F
    elif b & 0x40: n, m = 2, 0x3F
    elif b & 0x20: n, m = 3, 0x1F
    elif b & 0x10: n, m = 4, 0x0F
    elif b & 0x08: n, m = 5, 0x07
    elif b & 0x04: n, m = 6, 0x03
    elif b & 0x02: n, m = 7, 0x01
    else:           n, m = 8, 0x00
    if pos + n > len(data): return 0, n
    val = int.from_bytes(data[pos:pos+n], "big")
    val ^= (data[pos] & ~m) << (8*(n-1))
    return val, n

def _ve(val):
    if   val < 0x7F:       return bytes([0x80|val])
    elif val < 0x3FFF:     return bytes([0x40|(val>>8), val&0xFF])
    elif val < 0x1FFFFF:   return bytes([0x20|(val>>16),(val>>8)&0xFF,val&0xFF])
    elif val < 0x0FFFFFFF: return bytes([0x10|(val>>24),(val>>16)&0xFF,(val>>8)&0xFF,val&0xFF])
    else:                  return b"\x01" + val.to_bytes(7,"big")

def _ebml_el(eid, payload): return eid + _ve(len(payload)) + payload
def _ebml_uint(eid, v):
    n = max(1,(v.bit_length()+7)//8)
    return _ebml_el(eid, v.to_bytes(n,"big"))

def _fe(data, eid, start=0):
    el = len(eid)
    for i in range(start, len(data)-el+1):
        if data[i:i+el] == eid:
            val, n = _vr(data, i+el)
            unknown = (val == 0x00FFFFFFFFFFFFFF)
            ps = i+el+n
            pl = (len(data)-ps) if unknown else val
            return i, ps, pl
    return None

def _ge(data, eid, start=0):
    r = _fe(data, eid, start)
    return None if r is None else data[r[1]:r[1]+r[2]]

def _ger(data, eid, start=0):
    r = _fe(data, eid, start)
    return None if r is None else data[r[0]:r[1]+r[2]]

def _track_entries(tp):
    entries, i = [], 0
    while i < len(tp):
        if tp[i:i+1] == _TENTRY_ID:
            val, n = _vr(tp, i+1)
            entries.append(tp[i:i+1+n+val])
            i += 1+n+val
        else:
            i += 1
    return entries

def _tnum(e):
    b = _ge(e, _TNUM_ID)
    return int.from_bytes(b,"big") if b else 1

def _ttype(e):
    b = _ge(e, _TTYPE_ID)
    return b[0] if b else 0

def _clusters(seg):
    out, i = [], 0
    while i < len(seg)-4:
        if seg[i:i+4] == _CLUSTER_ID:
            val, n = _vr(seg, i+4)
            unknown = (val == 0x00FFFFFFFFFFFFFF)
            end = len(seg) if unknown else i+4+n+val
            raw = seg[i:end]
            payload = seg[i+4+n:end]
            tcb = _ge(payload, _TC_ID)
            tc  = int.from_bytes(tcb,"big") if tcb else 0
            out.append((tc, raw))
            i = end
        else:
            i += 1
    return out

def _patch_cluster(raw, old, new):
    if old == new: return raw
    val, n = _vr(raw, 4)
    hdr = raw[:4+n]
    pl  = bytearray(raw[4+n:])
    i = 0
    while i < len(pl):
        if pl[i] in (0xA3, 0xA1):   # SimpleBlock or Block
            sz, sn = _vr(pl, i+1)
            if sz <= 0 or i + 1 + sn + sz > len(pl):
                i += 1
                continue
            bs = i+1+sn
            tn, tn_n = _vr(pl, bs)
            if tn == old:
                nv = _ve(new)
                # Track numbers 1..127 encode in one byte; if width changes, skip patch.
                if len(nv) == tn_n:
                    pl[bs:bs+tn_n] = nv
            i = i + 1 + sn + sz
        else:
            i += 1
    return hdr + bytes(pl)

def _build_webm_cues(video_track_num, cue_points):
    """
    Build Cues for video clusters to improve seek reliability.
    cue_points = [(timecode, cluster_pos_relative_to_segment)].
    """
    if not cue_points:
        return b""
    cps = bytearray()
    for tc, pos in cue_points:
        ctp = (_ebml_uint(_CUETRK_ID, video_track_num) +
               _ebml_uint(_CUECP_ID, pos))
        cp  = (_ebml_uint(_CUETIME_ID, tc) +
               _ebml_el(_CUETP_ID, ctp))
        cps += _ebml_el(_CUEP_ID, cp)
    return _ebml_el(_CUES_ID, bytes(cps))

def _dump_webm_debug(out_path, v_tn, a_tn_old, a_tn_new, merged, cue_points):
    if not MUX_DEBUG:
        return
    lines = []
    lines.append("=" * 72)
    lines.append(f"mux_file: {Path(out_path).name}")
    lines.append(f"type: webm")
    lines.append(f"tracks: video={v_tn} audio_old={a_tn_old} audio_new={a_tn_new}")
    lines.append(f"clusters_total: {len(merged)}")
    lines.append("cluster_order:")
    byte_off = 0
    for idx, (tc, kind, raw) in enumerate(merged, 1):
        lines.append(
            f"  #{idx:04d} kind={kind} tc={tc} bytes={len(raw)} byte_off={byte_off}"
        )
        byte_off += len(raw)
    lines.append(f"cues_total: {len(cue_points)}")
    lines.append("cue_map:")
    for idx, (tc, pos) in enumerate(cue_points, 1):
        lines.append(f"  cue#{idx:04d} tc={tc} cluster_pos={pos}")
    for line in lines:
        _mux_debug_log(out_path, line)

def mux_webm(video_path, audio_path, out_path):
    log(f"mux_webm: {Path(video_path).name} + {Path(audio_path).name}")
    try:
        vd = open(video_path,"rb").read()
        ad = open(audio_path,"rb").read()

        ebml_hdr = _ger(vd, _EBML_ID)
        if not ebml_hdr: raise ValueError("No EBML in video")

        rv = _fe(vd, _SEG_ID)
        if not rv: raise ValueError("No Segment in video")
        vseg = vd[rv[1]:]

        ra = _fe(ad, _SEG_ID)
        if not ra: raise ValueError("No Segment in audio")
        aseg = ad[ra[1]:]

        info_raw = _ger(vseg, _INFO_ID)
        if not info_raw: raise ValueError("No Info in video")

        vtp = _ge(vseg, _TRACKS_ID)
        atp = _ge(aseg, _TRACKS_ID)
        if not vtp: raise ValueError("No Tracks in video")
        if not atp: raise ValueError("No Tracks in audio")

        ve = _track_entries(vtp)
        ae = _track_entries(atp)
        v_entry = next((e for e in ve if _ttype(e)==1), ve[0] if ve else None)
        a_entry = next((e for e in ae if _ttype(e)==2), ae[0] if ae else None)
        if not v_entry: raise ValueError("No video track entry")
        if not a_entry: raise ValueError("No audio track entry")

        v_tn = _tnum(v_entry)
        a_tn_old = _tnum(a_entry)
        a_tn_new = 2 if v_tn != 2 else 3

        tn_raw = _ger(a_entry, _TNUM_ID)
        if tn_raw:
            a_entry = a_entry.replace(tn_raw, _ebml_uint(_TNUM_ID, a_tn_new), 1)

        tracks = _ebml_el(_TRACKS_ID, v_entry + a_entry)

        vc = _clusters(vseg)
        ac = _clusters(aseg)
        log(f"WebM clusters: {len(vc)}v {len(ac)}a")

        pac = [(tc, _patch_cluster(raw, a_tn_old, a_tn_new)) for tc, raw in ac]
        merged = sorted(
            [(tc,"v",r) for tc,r in vc] + [(tc,"a",r) for tc,r in pac],
            key=lambda x: x[0]
        )

        clusters_blob = b"".join(r for _,_,r in merged)
        cluster_base  = len(info_raw) + len(tracks)
        cue_points    = []
        off           = cluster_base
        last_tc       = None
        for tc, kind, raw in merged:
            if kind == "v" and tc != last_tc:
                cue_points.append((tc, off))
                last_tc = tc
            off += len(raw)
        cues = _build_webm_cues(v_tn, cue_points)

        seg_payload = info_raw + tracks + clusters_blob + cues
        with open(out_path,"wb") as f:
            f.write(ebml_hdr)
            f.write(_SEG_ID + b"\x01\xFF\xFF\xFF\xFF\xFF\xFF\xFF" + seg_payload)

        if MUX_DEBUG:
            _dump_webm_debug(out_path, v_tn, a_tn_old, a_tn_new, merged, cue_points)

        log(f"mux_webm OK: {os.path.getsize(out_path)//1048576}MB")
        return True

    except Exception:
        log(f"mux_webm FAILED:\n{traceback.format_exc()}")
        try: shutil.copy2(video_path, out_path)
        except Exception: pass
        return False


# ══════════════════════════════════════════════════════════════════════════
#  FORMAT HELPERS
# ══════════════════════════════════════════════════════════════════════════

def fmt_size(b):
    b = int(b or 0)
    if not b: return ""
    if b >= 1_073_741_824: return f"{b/1073741824:.1f}GB"
    if b >= 1_048_576:     return f"{b/1048576:.0f}MB"
    return f"{b/1024:.0f}KB"

def fmt_dur(s):
    s = int(s or 0)
    h, m, sec = s//3600, (s%3600)//60, s%60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"

def fmt_views(n):
    n = int(n or 0)
    if n >= 1_000_000_000: return f"{n/1e9:.1f}B"
    if n >= 1_000_000:     return f"{n/1e6:.1f}M"
    if n >= 1_000:         return f"{n/1e3:.0f}K"
    return str(n)

def _height_tag(h):
    if h >= 2160: return "4K"
    if h >= 1440: return "2K"
    if h >= 1080: return "FHD"
    if h >= 720:  return "HD"
    if h >= 480:  return "SD"
    return ""


# ══════════════════════════════════════════════════════════════════════════
#  GET INFO
# ══════════════════════════════════════════════════════════════════════════

def get_info(url):
    log(f"get_info: {url}")
    fix_ssl()
    if not _YT_DLP_AVAILABLE:
        return None, "yt-dlp not installed"

    try:
        with yt_dlp.YoutubeDL({
            "quiet": True, "no_warnings": True,
            "http_headers": {"User-Agent": UA},
            "socket_timeout": 15,
            "retries": 2,
            "extractor_retries": 2,
        }) as ydl:
            raw = ydl.extract_info(url, download=False)
        log(f"Title: {raw.get('title','?')}")

        combined={};  mp4_video={};  webm_video={}
        m4a_audio=None;  webm_audio=None
        audio_opts=[]

        for fmt in raw.get("formats",[]):
            h   = fmt.get("height") or 0
            vc  = (fmt.get("vcodec") or "none").lower()
            ac  = (fmt.get("acodec") or "none").lower()
            ext = (fmt.get("ext") or "").lower()
            vbr = fmt.get("vbr") or fmt.get("tbr") or 0
            abr = fmt.get("abr") or 0
            hv  = vc not in ("none","")
            ha  = ac not in ("none","")

            if hv and ha and h>0:
                if h not in combined or vbr>combined[h].get("vbr",0):
                    combined[h]={**fmt,"vbr":vbr}
            elif hv and not ha and h>0:
                if ext in ("mp4","m4v"):
                    if h not in mp4_video or vbr>mp4_video[h].get("vbr",0):
                        mp4_video[h]={**fmt,"vbr":vbr}
                elif ext=="webm":
                    if h not in webm_video or vbr>webm_video[h].get("vbr",0):
                        webm_video[h]={**fmt,"vbr":vbr}
            elif ha and not hv:
                if ext in ("m4a","mp4","webm","opus"):
                    audio_opts.append({**fmt, "abr": abr})
                if ext in ("m4a","mp4"):
                    if m4a_audio is None or abr>(m4a_audio.get("abr") or 0):
                        m4a_audio={**fmt,"abr":abr}
                elif ext in ("webm","opus"):
                    if webm_audio is None or abr>(webm_audio.get("abr") or 0):
                        webm_audio={**fmt,"abr":abr}

        formats=[]
        # Video + audio (direct or muxed)
        for h in sorted(set(list(combined)+list(mp4_video)+list(webm_video)),reverse=True):
            if h in combined:
                f=combined[h]
                formats.append({"format_id":f["format_id"],"audio_id":None,
                    "label":f"{h}p","tag":_height_tag(h),
                    "size":fmt_size(f.get("filesize") or f.get("filesize_approx") or 0),
                    "type":"video","ext":f.get("ext","mp4"),"height":h,
                    "needs_mux":False,"mux_type":None,
                    "category":"video_audio"})
            elif h in mp4_video and m4a_audio:
                f=mp4_video[h]
                formats.append({"format_id":f["format_id"],"audio_id":m4a_audio["format_id"],
                    "label":f"{h}p","tag":_height_tag(h),
                    "size":fmt_size((f.get("filesize") or f.get("filesize_approx") or 0)+
                                    (m4a_audio.get("filesize") or m4a_audio.get("filesize_approx") or 0)),
                    "type":"video","ext":"mp4","height":h,
                    "needs_mux":True,"mux_type":"mp4",
                    "category":"video_audio"})
            elif h in webm_video:
                audio=webm_audio or m4a_audio
                if not audio: continue
                f=webm_video[h]
                formats.append({"format_id":f["format_id"],"audio_id":audio["format_id"],
                    "label":f"{h}p","tag":_height_tag(h),
                    "size":fmt_size((f.get("filesize") or f.get("filesize_approx") or 0)+
                                    (audio.get("filesize") or audio.get("filesize_approx") or 0)),
                    "type":"video","ext":"webm","height":h,
                    "needs_mux":True,"mux_type":"webm",
                    "category":"video_audio"})

        # Video only (mute): one entry per height, prefer MP4 over WEBM.
        video_only_best = {}
        for h, f in mp4_video.items():
            video_only_best[h] = (2, f.get("vbr") or 0, "mp4", f)
        for h, f in webm_video.items():
            cand = (1, f.get("vbr") or 0, "webm", f)
            cur  = video_only_best.get(h)
            if cur is None or cand > cur:
                video_only_best[h] = cand

        for h in sorted(video_only_best.keys(), reverse=True):
            _, _, ext, f = video_only_best[h]
            formats.append({"format_id":f["format_id"],"audio_id":None,
                "label":f"{h}p Video Only","tag":_height_tag(h),
                "size":fmt_size(f.get("filesize") or f.get("filesize_approx") or 0),
                "type":"video","ext":ext,"height":h,
                "needs_mux":False,"mux_type":None,
                "category":"video_only"})

        # Audio only (multiple options per ext)
        seen_audio_ids = set()
        seen_audio_keys = set()
        per_ext_counts = {}
        for f in sorted(audio_opts, key=lambda x: x.get("abr") or x.get("tbr") or 0, reverse=True):
            fid = f.get("format_id")
            if not fid or fid in seen_audio_ids:
                continue
            ext = (f.get("ext") or "").lower()
            if ext == "opus":
                ext = "webm"
            if ext == "mp4":
                ext = "m4a"
            if ext not in ("m4a", "webm"):
                continue
            if per_ext_counts.get(ext, 0) >= 5:
                continue

            abr = f.get("abr") or f.get("tbr") or 0
            abr_i = int(abr) if abr else 0
            uniq = (ext, abr_i)
            if uniq in seen_audio_keys:
                continue

            seen_audio_ids.add(fid)
            seen_audio_keys.add(uniq)
            per_ext_counts[ext] = per_ext_counts.get(ext, 0) + 1

            formats.append({"format_id":fid,"audio_id":None,
                "label":f"Audio {ext.upper()} {abr_i}kbps" if abr_i else f"Audio {ext.upper()}",
                "tag":"",
                "size":fmt_size(f.get("filesize") or f.get("filesize_approx") or 0),
                "type":"audio","ext":ext,"height":0,
                "needs_mux":False,"mux_type":None,
                "category":"audio_only"})

        before = len(formats)
        seen = set()
        deduped = []
        for f in formats:
            key = (
                str(f.get("category") or ""),
                str(f.get("label") or "").strip().lower(),
                str(f.get("ext") or "").strip().lower(),
                int(f.get("height") or 0),
                bool(f.get("needs_mux")),
                str(f.get("mux_type") or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(f)
        formats = deduped
        if len(formats) != before:
            log(f"Formats deduped: {before} -> {len(formats)}")
        log(f"Formats: {[f['label'] for f in formats]}")
        return {"title":raw.get("title","Unknown"),
                "channel":raw.get("channel") or raw.get("uploader",""),
                "duration":raw.get("duration",0) or 0,
                "views":raw.get("view_count",0) or 0,
                "thumbnail":raw.get("thumbnail",""),
                "formats":formats,"url":url}, None

    except Exception as e:
        log(f"get_info error:\n{traceback.format_exc()}")
        return None, str(e)

def _fmt_category(fmt):
    c = fmt.get("category")
    if c:
        return c
    if fmt.get("type") == "audio":
        return "audio_only"
    if fmt.get("type") == "video":
        if fmt.get("needs_mux") or fmt.get("audio_id"):
            return "video_audio"
        if "video only" in str(fmt.get("label", "")).lower():
            return "video_only"
        return "video_audio"
    return "video_audio"

def _is_format_unavailable_error(err):
    s = str(err).lower()
    return ("requested format is not available" in s or
            "format is not available" in s)


def _is_transient_network_error(err):
    s = str(err).lower()
    needles = (
        "failed to resolve",
        "temporary failure in name resolution",
        "no address associated with hostname",
        "name or service not known",
        "network is unreachable",
        "connection reset",
        "connection aborted",
        "connection timed out",
        "timed out",
        "read timed out",
        "unable to download webpage",
    )
    return any(n in s for n in needles)


def _is_dns_resolution_error(err):
    s = str(err).lower()
    needles = (
        "failed to resolve",
        "no address associated with hostname",
        "temporary failure in name resolution",
        "name or service not known",
    )
    return any(n in s for n in needles)

def _pick_best_format_match(wanted, formats):
    if not formats:
        return None
    wcat  = _fmt_category(wanted)
    whei  = int(wanted.get("height") or 0)
    wext  = (wanted.get("ext") or "").lower()
    wmux  = wanted.get("mux_type")
    wneed = bool(wanted.get("needs_mux", False))
    wtag  = str(wanted.get("tag") or "")

    pool = [f for f in formats if _fmt_category(f) == wcat]
    if not pool:
        pool = list(formats)

    def score(f):
        s = 0
        fh = int(f.get("height") or 0)
        if whei and fh:
            s -= abs(fh - whei) * 20
            if fh == whei:
                s += 500
        if wext and (f.get("ext") or "").lower() == wext:
            s += 120
        if wmux and f.get("mux_type") == wmux:
            s += 80
        if bool(f.get("needs_mux", False)) == wneed:
            s += 40
        if wtag and str(f.get("tag") or "") == wtag:
            s += 20
        return s

    return max(pool, key=score)

def _refresh_format_choice(url, wanted):
    info, err = get_info(url)
    if err or not info:
        log(f"refresh fmt failed: {err}")
        return None
    cand = _pick_best_format_match(wanted, info.get("formats", []))
    if not cand:
        return None
    out = dict(cand)
    if wanted.get("title"):
        out["title"] = wanted["title"]
    log(f"format refresh: {wanted.get('label')} -> {out.get('label')}")
    return out


# ══════════════════════════════════════════════════════════════════════════
#  DOWNLOAD
# ══════════════════════════════════════════════════════════════════════════

def _tmp_dir():
    for candidate in _cache_candidates():
        try:
            os.makedirs(candidate, exist_ok=True)
            return tempfile.mkdtemp(prefix="ytdl_", dir=candidate)
        except Exception:
            pass
    return tempfile.mkdtemp(prefix="ytdl_")


def _respect_control(control, on_state=None, on_progress=None, pct=0, total="?"):
    if not control:
        return
    if control.is_cancelled():
        raise DownloadCancelled("Download cancelled")

    paused_notified = False
    while control.is_paused():
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
        if control.is_cancelled():
            raise DownloadCancelled("Download cancelled")

    if paused_notified and on_state:
        try:
            on_state("resumed")
        except Exception:
            pass


def _sleep_with_control(seconds, control=None, on_state=None, on_progress=None, pct=0, total="?"):
    end_t = time.time() + max(0.0, float(seconds or 0))
    while time.time() < end_t:
        _respect_control(control, on_state=on_state, on_progress=on_progress, pct=pct, total=total)
        time.sleep(0.25)

def _dl_one(url, format_id, outtmpl, common, hook):
    if not _YT_DLP_AVAILABLE:
        raise ImportError("yt-dlp not installed")
    with yt_dlp.YoutubeDL({**common, "format": format_id,
                            "outtmpl": outtmpl, "progress_hooks": [hook]}) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)
    if not Path(path).exists():
        d = Path(path).parent
        files = sorted(d.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
        if files: path = str(files[0])
    log(f"_dl_one → {path} ({os.path.getsize(path)//1024}KB)")
    return path, info

def download(url, fmt_info=None, on_progress=None, on_done=None, on_error=None,
             control=None, on_state=None, on_net=None):
    if not fmt_info:
        if on_error: on_error("No format selected")
        return

    log(f"download: {fmt_info.get('label')} needs_mux={fmt_info.get('needs_mux')}")
    request_perms(); fix_ssl()
    if on_net:
        try:
            on_net({"kind": "reset", "dns_retries": 0, "net_retries": 0})
        except Exception:
            pass

    if not _YT_DLP_AVAILABLE:
        if on_error: on_error("yt-dlp not installed"); return

    dl_dir     = get_dl_dir()
    active_fmt = dict(fmt_info)
    s = {}
    try:
        s = app_settings.load_settings() if app_settings else {}
        if s.get("auto_cleanup_cache", True):
            age_h = s.get("cache_max_age_hours", 12)
            out = cleanup_temp_cache(max_age_hours=age_h)
            if out.get("removed_dirs"):
                log(f"cache cleanup: {out.get('removed_dirs')} dirs, {out.get('removed_bytes', 0)//1024}KB")
    except Exception as e:
        log(f"cache cleanup failed: {e}")

    resume_enabled = bool(s.get("resume_downloads", False))
    ytdlp_cache_dir = os.path.join(_base(), ".ytdlp_cache")
    if resume_enabled:
        try:
            os.makedirs(ytdlp_cache_dir, exist_ok=True)
        except Exception:
            pass
    else:
        ytdlp_cache_dir = False

    # Point ffmpeg_location at a non-existent path so yt-dlp
    # never tries to spawn the missing binary on its own.
    common = {
        "quiet": True, "no_warnings": True,
        "http_headers": {"User-Agent": UA},
        "postprocessors": [],
        "retries": 8, "fragment_retries": 8,
        "socket_timeout": 30,
        "continuedl": resume_enabled,
        "nopart": (not resume_enabled),
        "cachedir": ytdlp_cache_dir,
        "ffmpeg_location": "/dev/null",
    }

    def make_hook(label, p0, p1):
        def hook(d):
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done  = d.get("downloaded_bytes", 0)
            frac  = done/total if total else 0
            pct   = round(p0 + frac*(p1-p0), 1)
            total_txt = f"{total/1048576:.0f} MB" if total else "?"
            _respect_control(control, on_state=on_state, on_progress=on_progress,
                             pct=pct, total=total_txt)
            if d["status"] == "downloading" and on_progress:
                spd   = d.get("speed") or 0
                eta   = d.get("eta") or 0
                on_progress(pct,
                    f"{spd/1048576:.1f} MB/s" if spd else "-",
                    f"{eta}s" if eta else "-",
                    label,
                    total_txt)
        return hook

    try:
        if not active_fmt.get("needs_mux", False):
            fmt_retries = 0
            net_retries = 0
            max_fmt_retries = 2
            max_net_retries = 4
            while True:
                _respect_control(control, on_state=on_state, on_progress=on_progress, pct=0, total="?")
                if on_progress: on_progress(0,"-","-","Starting...","")
                try:
                    final, _ = _dl_one(url, active_fmt["format_id"],
                                       os.path.join(dl_dir,"%(title)s.%(ext)s"),
                                       common, make_hook("Downloading",0,100))
                    break
                except Exception as e:
                    if _is_format_unavailable_error(e):
                        if fmt_retries >= max_fmt_retries:
                            raise
                        fmt_retries += 1
                        refreshed = _refresh_format_choice(url, active_fmt)
                        if not refreshed:
                            raise
                        log(f"retry single after refresh: {active_fmt.get('format_id')} -> {refreshed.get('format_id')}")
                        active_fmt = refreshed
                        if on_progress: on_progress(2,"-","-","Refreshing format...","")
                        continue
                    if _is_transient_network_error(e):
                        if net_retries >= max_net_retries:
                            raise
                        net_retries += 1
                        wait_s = min(20, 2 * net_retries)
                        is_dns = _is_dns_resolution_error(e)
                        if on_net:
                            try:
                                on_net({
                                    "kind": "retry",
                                    "scope": "single",
                                    "dns_error": bool(is_dns),
                                    "dns_retries": net_retries if is_dns else 0,
                                    "net_retries": net_retries,
                                    "max_retries": max_net_retries,
                                    "error": str(e),
                                })
                            except Exception:
                                pass
                        log(f"network retry single {net_retries}/{max_net_retries}: {e}")
                        if on_progress:
                            on_progress(min(95, 5 + net_retries * 2), "-", "-",
                                        f"Network retry {net_retries}/{max_net_retries}", "")
                        refreshed = _refresh_format_choice(url, active_fmt)
                        if refreshed:
                            active_fmt = refreshed
                        _sleep_with_control(wait_s, control=control, on_state=on_state,
                                            on_progress=on_progress,
                                            pct=min(95, 5 + net_retries * 2), total="?")
                        continue
                    raise

            if on_progress: on_progress(100,"-","-","Done!","")
            log(f"Done: {final}")
            if on_done: on_done(final)
            return

        # ── Two-phase download + pure-Python mux ─────────────────────
        tmp = _tmp_dir()
        try:
            fmt_retries = 0
            net_retries = 0
            max_fmt_retries = 2
            max_net_retries = 4
            while True:
                _respect_control(control, on_state=on_state, on_progress=on_progress, pct=0, total="?")
                try:
                    if on_progress: on_progress(0,"-","-","Downloading video...","")
                    v_file, v_info = _dl_one(url, active_fmt["format_id"],
                                             os.path.join(tmp,"video.%(ext)s"),
                                             common, make_hook("Video",0,55))

                    if on_progress: on_progress(55,"-","-","Downloading audio...","")
                    a_id = active_fmt.get("audio_id")
                    if not a_id:
                        raise ValueError("No compatible audio stream for selected format")
                    a_file, _ = _dl_one(url, a_id,
                                        os.path.join(tmp,"audio.%(ext)s"),
                                        common, make_hook("Audio",55,90))
                    break
                except Exception as e:
                    if _is_format_unavailable_error(e):
                        if fmt_retries >= max_fmt_retries:
                            raise
                        fmt_retries += 1
                        refreshed = _refresh_format_choice(url, active_fmt)
                        if not refreshed:
                            raise
                        log("retry mux after refresh: "
                            f"{active_fmt.get('format_id')}+{active_fmt.get('audio_id')} -> "
                            f"{refreshed.get('format_id')}+{refreshed.get('audio_id')}")
                        active_fmt = refreshed
                        if on_progress: on_progress(3,"-","-","Refreshing format...","")
                        continue
                    if _is_transient_network_error(e):
                        if net_retries >= max_net_retries:
                            raise
                        net_retries += 1
                        wait_s = min(20, 2 * net_retries)
                        is_dns = _is_dns_resolution_error(e)
                        if on_net:
                            try:
                                on_net({
                                    "kind": "retry",
                                    "scope": "mux",
                                    "dns_error": bool(is_dns),
                                    "dns_retries": net_retries if is_dns else 0,
                                    "net_retries": net_retries,
                                    "max_retries": max_net_retries,
                                    "error": str(e),
                                })
                            except Exception:
                                pass
                        log(f"network retry mux {net_retries}/{max_net_retries}: {e}")
                        if on_progress:
                            on_progress(min(89, 6 + net_retries * 2), "-", "-",
                                        f"Network retry {net_retries}/{max_net_retries}", "")
                        refreshed = _refresh_format_choice(url, active_fmt)
                        if refreshed:
                            active_fmt = refreshed
                        _sleep_with_control(wait_s, control=control, on_state=on_state,
                                            on_progress=on_progress,
                                            pct=min(89, 6 + net_retries * 2), total="?")
                        continue
                    raise

            _respect_control(control, on_state=on_state, on_progress=on_progress, pct=90, total="?")
            if on_progress: on_progress(90,"-","-","Merging...","")

            # Use title from already-downloaded info — no extra network call
            raw_title = active_fmt.get("title") or v_info.get("title") or active_fmt.get("label", "video")

            safe  = "".join(c if c.isalnum() or c in " ._-" else "_"
                            for c in raw_title)[:80].strip("_").strip()
            ext   = active_fmt.get("ext","mp4")
            final = os.path.join(dl_dir, f"{safe}.{ext}")
            # Avoid overwriting
            if os.path.exists(final):
                base, e = os.path.splitext(final)
                n = 1
                while os.path.exists(f"{base}_{n}{e}"): n += 1
                final = f"{base}_{n}{e}"

            if active_fmt.get("mux_type") == "webm":
                mux_webm(v_file, a_file, final)
            else:
                mux_mp4(v_file, a_file, final)

        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        if on_progress: on_progress(100,"-","-","Done!","")
        log(f"Done: {final}")
        if on_done: on_done(final)

    except DownloadCancelled as e:
        log(str(e))
        if on_error: on_error(str(e))
    except Exception as e:
        log(f"download error:\n{traceback.format_exc()}")
        if on_error: on_error(str(e))
