"""
main.py — Video Downloader v8
UI: Fresh modern design — gradient header, pill format chips,
    animated download ring, glassmorphism cards, vibrant accent palette.
"""

import os, sys, threading, tempfile, traceback, webbrowser, urllib.parse, time
os.environ["KIVY_NO_ENV_CONFIG"] = "1"
os.environ["KIVY_LOG_MODE"]      = "PYTHON"

# Toggle to generate per-output "<file>.mux.log" files from downloader.py
ENABLE_MUX_DEBUG = False
if ENABLE_MUX_DEBUG:
    os.environ["YT_MUX_DEBUG"] = "1"

NOTIF_ACTION_PAUSE  = "com.local.videodownloader.action.PAUSE"
NOTIF_ACTION_RESUME = "com.local.videodownloader.action.RESUME"
NOTIF_ACTION_STOP   = "com.local.videodownloader.action.STOP"

def _get_data_dir():
    """Use app_settings.get_data_dir() when available, otherwise fall back."""
    cfg = globals().get("app_settings", None)
    if cfg and hasattr(cfg, "get_data_dir"):
        try:
            return cfg.get_data_dir()
        except Exception:
            pass
    try:
        from android.storage import primary_external_storage_path

        b = os.path.join(primary_external_storage_path(), "Download", "videodownloader")
    except ImportError:
        b = os.path.join(os.path.expanduser("~"), "Downloads", "videodownloader")
    return b


def _logpath():
    b = _get_data_dir()
    os.makedirs(b, exist_ok=True)
    return os.path.join(b, "crash.log")


def _max_log_bytes():
    cfg = globals().get("app_settings", None)
    if cfg and hasattr(cfg, "max_crash_log_bytes"):
        try:
            return int(cfg.max_crash_log_bytes())
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
            af.write(str(line) + "\n")
    except Exception:
        pass


def wlog(m):
    _append_line_capped(_logpath(), m, _max_log_bytes())

wlog("=== App starting ===")
try:
    from kivy.app import App
    from kivy.uix.boxlayout    import BoxLayout
    from kivy.uix.floatlayout  import FloatLayout
    from kivy.uix.scrollview   import ScrollView
    from kivy.uix.label        import Label
    from kivy.uix.textinput    import TextInput
    from kivy.uix.button       import Button
    from kivy.uix.image        import Image
    from kivy.uix.popup        import Popup
    from kivy.uix.filechooser  import FileChooserListView
    from kivy.uix.widget       import Widget
    from kivy.clock            import Clock
    from kivy.core.window      import Window
    from kivy.graphics         import (Color, RoundedRectangle, Rectangle,
                                       Ellipse, Line, Mesh, SmoothLine)
    from kivy.metrics          import dp, sp
    from kivy.properties       import (NumericProperty, ListProperty,
                                       StringProperty, BooleanProperty)
    from kivy.animation        import Animation
    from kivy.core.clipboard   import Clipboard
    import math
    wlog("kivy imports OK")
except Exception as e:
    wlog(f"kivy FAILED: {e}"); sys.exit(1)

try:
    import downloader_platforms as downloader
    wlog("downloader_platforms import OK")
except Exception as e:
    wlog(f"downloader_platforms FAILED: {e}")
    try:
        import downloader
        wlog("downloader import OK")
    except Exception as e2:
        wlog(f"downloader FAILED: {e2}")
        downloader = None

try:
    import app_settings
except Exception as e:
    wlog(f"app_settings FAILED: {e}")
    app_settings = None


# ═══════════════════════════════════════════════════════════
#  DESIGN TOKENS  — Premium "Aurora" palette
# ═══════════════════════════════════════════════════════════
BG      = (0.035, 0.035, 0.055, 1)   # #090910 — deep space
SURF    = (0.063, 0.067, 0.098, 1)   # #101119
CARD    = (0.086, 0.090, 0.125, 1)   # #161720
CARD2   = (0.110, 0.114, 0.157, 1)   # #1c1d28
BORDER  = (0.173, 0.180, 0.243, 1)   # #2c2e3e

# Accent: vivid violet-to-cyan gradient feel
ACCENT  = (0.400, 0.310, 1.000, 1)   # #664FFF — electric indigo
ACCENT2 = (0.000, 0.800, 0.950, 1)   # #00CCF2 — vivid cyan
ACCT_DK = (0.280, 0.200, 0.780, 1)   # #4733C7 — pressed

GREEN   = (0.176, 0.890, 0.565, 1)   # #2DE390
YELLOW  = (1.000, 0.800, 0.220, 1)   # #FFCC38
ORANGE  = (1.000, 0.510, 0.180, 1)   # #FF822E
ROSE    = (1.000, 0.286, 0.486, 1)   # #FF497C
BLUE    = (0.220, 0.580, 1.000, 1)   # #3894FF

MUTED   = (0.340, 0.350, 0.440, 1)
TEXT    = (0.940, 0.945, 0.965, 1)
TEXTSUB = (0.480, 0.490, 0.590, 1)
WHITE   = (1., 1., 1., 1)

PAD  = dp(18)
PAD2 = dp(12)
RAD  = dp(20)
RAD2 = dp(14)
RAD3 = dp(10)

# Tag colours per resolution badge
TAG_COLORS = {
    "4K":  list(YELLOW),
    "2K":  list(ORANGE),
    "FHD": list(ACCENT2),
    "HD":  list(GREEN),
    "SD":  list(MUTED),
    "":    list(MUTED),
}

THEMES = {
    "dark": {
        "BG":      BG, "SURF": SURF, "CARD": CARD, "CARD2": CARD2, "BORDER": BORDER,
        "ACCENT":  ACCENT, "ACCENT2": ACCENT2, "ACCT_DK": ACCT_DK,
        "GREEN":   GREEN, "YELLOW": YELLOW, "ORANGE": ORANGE, "ROSE": ROSE, "BLUE": BLUE,
        "MUTED":   MUTED, "TEXT": TEXT, "TEXTSUB": TEXTSUB,
    },
    "light": {
        "BG":      (0.953, 0.957, 0.976, 1),
        "SURF":    (1.000, 1.000, 1.000, 1),
        "CARD":    (0.965, 0.968, 0.985, 1),
        "CARD2":   (0.935, 0.940, 0.965, 1),
        "BORDER":  (0.824, 0.835, 0.882, 1),
        "ACCENT":  (0.345, 0.259, 0.906, 1),
        "ACCENT2": (0.000, 0.620, 0.800, 1),
        "ACCT_DK": (0.243, 0.180, 0.725, 1),
        "GREEN":   (0.082, 0.620, 0.349, 1),
        "YELLOW":  (0.800, 0.600, 0.000, 1),
        "ORANGE":  (0.860, 0.400, 0.060, 1),
        "ROSE":    (0.820, 0.180, 0.360, 1),
        "BLUE":    (0.180, 0.440, 0.860, 1),
        "MUTED":   (0.490, 0.510, 0.600, 1),
        "TEXT":    (0.082, 0.094, 0.161, 1),
        "TEXTSUB": (0.353, 0.376, 0.478, 1),
    },
}


def _apply_theme_globals(mode):
    global BG, SURF, CARD, CARD2, BORDER
    global ACCENT, ACCENT2, ACCT_DK
    global GREEN, YELLOW, ORANGE, ROSE, BLUE
    global MUTED, TEXT, TEXTSUB, TAG_COLORS
    m = str(mode or "dark").strip().lower()
    if m not in THEMES:
        m = "dark"
    t = THEMES[m]
    BG = t["BG"]
    SURF = t["SURF"]
    CARD = t["CARD"]
    CARD2 = t["CARD2"]
    BORDER = t["BORDER"]
    ACCENT = t["ACCENT"]
    ACCENT2 = t["ACCENT2"]
    ACCT_DK = t["ACCT_DK"]
    GREEN = t["GREEN"]
    YELLOW = t["YELLOW"]
    ORANGE = t["ORANGE"]
    ROSE = t["ROSE"]
    BLUE = t["BLUE"]
    MUTED = t["MUTED"]
    TEXT = t["TEXT"]
    TEXTSUB = t["TEXTSUB"]
    TAG_COLORS = {
        "4K":  list(YELLOW),
        "2K":  list(ORANGE),
        "FHD": list(ACCENT2),
        "HD":  list(GREEN),
        "SD":  list(MUTED),
        "":    list(MUTED),
    }


# ═══════════════════════════════════════════════════════════
#  BASE WIDGETS
# ═══════════════════════════════════════════════════════════

class Card(BoxLayout):
    bg     = ListProperty(list(CARD))
    radius = NumericProperty(RAD)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self._d, size=self._d, bg=self._d, radius=self._d)

    def _d(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            # Subtle drop shadow
            Color(0, 0, 0, 0.12)
            RoundedRectangle(
                pos=(self.x + dp(1), self.y - dp(2)),
                size=(self.width, self.height),
                radius=[self.radius + dp(1)] * 4)
            # Main card body
            Color(*self.bg)
            RoundedRectangle(pos=self.pos, size=self.size,
                             radius=[self.radius] * 4)


class GlassCard(Card):
    """Card with a subtle inner highlight border and frosted glass feel."""
    def _d(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            # Drop shadow
            Color(0, 0, 0, 0.15)
            RoundedRectangle(
                pos=(self.x + dp(1), self.y - dp(3)),
                size=(self.width, self.height),
                radius=[self.radius + dp(1)] * 4)
            # Main fill
            Color(*self.bg)
            RoundedRectangle(pos=self.pos, size=self.size,
                             radius=[self.radius] * 4)
            # Top-edge highlight (frosted glass effect)
            Color(1, 1, 1, 0.06)
            RoundedRectangle(
                pos=(self.x, self.y + self.height * 0.5),
                size=(self.width, self.height * 0.5),
                radius=[self.radius, self.radius, 0, 0])
            # Inner border
            Color(1, 1, 1, 0.04)
            Line(rounded_rectangle=(
                self.x + 1, self.y + 1,
                self.width - 2, self.height - 2,
                self.radius - 1), width=1.1)


class Btn(Button):
    """Gradient-look filled button with elevation."""
    bg     = ListProperty(list(ACCENT))
    bg_dn  = ListProperty(list(ACCT_DK))
    radius = NumericProperty(RAD2)
    _dn    = BooleanProperty(False)

    def __init__(self, **kw):
        kw.setdefault("background_normal", "")
        kw.setdefault("background_color",  (0, 0, 0, 0))
        kw.setdefault("color",             WHITE)
        kw.setdefault("bold",              True)
        kw.setdefault("font_size",         sp(14))
        super().__init__(**kw)
        self.bind(pos=self._d, size=self._d, bg=self._d, _dn=self._d)

    def _d(self, *_):
        self.canvas.before.clear()
        col = self.bg_dn if self._dn else self.bg
        with self.canvas.before:
            # Button shadow (lifts when not pressed)
            if not self._dn:
                Color(col[0] * 0.4, col[1] * 0.4, col[2] * 0.4, 0.25)
                RoundedRectangle(
                    pos=(self.x, self.y - dp(2)),
                    size=(self.width, self.height),
                    radius=[self.radius] * 4)
            # Main button body
            Color(*col)
            RoundedRectangle(pos=self.pos, size=self.size,
                             radius=[self.radius] * 4)
            # Top glass sheen
            Color(1, 1, 1, 0.10 if not self._dn else 0.04)
            RoundedRectangle(
                pos=(self.x, self.y + self.height * 0.5),
                size=(self.width, self.height * 0.5),
                radius=[self.radius, self.radius, 0, 0])

    def on_touch_down(self, t):
        if self.collide_point(*t.pos): self._dn = True
        return super().on_touch_down(t)

    def on_touch_up(self, t):
        self._dn = False
        return super().on_touch_up(t)


class OutlineBtn(Btn):
    """Ghost outline button with hover border."""
    def __init__(self, **kw):
        kw.setdefault("color", list(TEXT))
        super().__init__(**kw)
        self.bg    = list(CARD2)
        self.bg_dn = list(BORDER)

    def _d(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*(self.bg_dn if self._dn else self.bg))
            RoundedRectangle(pos=self.pos, size=self.size,
                             radius=[self.radius] * 4)
            Color(ACCENT[0], ACCENT[1], ACCENT[2],
                  0.6 if self._dn else 0.25)
            Line(rounded_rectangle=(
                self.x, self.y, self.width, self.height, self.radius),
                width=1.3)


class RingProgress(Widget):
    """Circular progress ring with glow effect and percentage."""
    value      = NumericProperty(0)   # 0–100
    ring_color = ListProperty(list(ACCENT))

    def __init__(self, **kw):
        self._pct_lbl = Label(
            text="0%", font_size=sp(28), bold=True,
            color=list(TEXT), halign="center", valign="middle",
        )
        super().__init__(**kw)
        self.add_widget(self._pct_lbl)
        self.bind(pos=self._d, size=self._d, value=self._d, ring_color=self._d)

    def _d(self, *_):
        if not hasattr(self, "_pct_lbl"):
            return
        self.canvas.clear()
        cx, cy = self.center
        r = max(dp(4), min(self.width, self.height) / 2 - dp(8))
        with self.canvas:
            # Background track
            Color(BORDER[0], BORDER[1], BORDER[2], 0.4)
            Line(circle=(cx, cy, r), width=dp(6), cap="round")
        if self.value > 0:
            deg = self.value / 100 * 360
            with self.canvas:
                # Glow layer (wider, semi-transparent)
                Color(self.ring_color[0], self.ring_color[1],
                      self.ring_color[2], 0.15)
                Line(ellipse=(cx - r, cy - r, r * 2, r * 2, 90, 90 - deg),
                     width=dp(14), cap="round")
                # Main progress arc
                Color(*self.ring_color)
                Line(ellipse=(cx - r, cy - r, r * 2, r * 2, 90, 90 - deg),
                     width=dp(6), cap="round")
        self._pct_lbl.center = (cx, cy)
        self._pct_lbl.size   = self.size
        self._pct_lbl.text   = f"{int(self.value)}%"


class PBar(Widget):
    """Thin horizontal progress bar with glow."""
    value     = NumericProperty(0)
    bar_color = ListProperty(list(ACCENT))

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self._d, size=self._d, value=self._d, bar_color=self._d)

    def _d(self, *_):
        self.canvas.clear()
        r = self.height / 2
        with self.canvas:
            # Track
            Color(BORDER[0], BORDER[1], BORDER[2], 0.35)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[r] * 4)
            if self.value > 0:
                w = max(self.height, self.width * self.value / 100)
                # Glow under bar
                Color(self.bar_color[0], self.bar_color[1],
                      self.bar_color[2], 0.18)
                RoundedRectangle(
                    pos=(self.x, self.y - dp(2)),
                    size=(w, self.height + dp(4)),
                    radius=[r + dp(2)] * 4)
                # Main bar
                Color(*self.bar_color)
                RoundedRectangle(pos=self.pos, size=(w, self.height),
                                 radius=[r] * 4)
                # Top shine
                Color(1, 1, 1, 0.15)
                RoundedRectangle(
                    pos=(self.x, self.y + self.height * 0.5),
                    size=(w, self.height * 0.5),
                    radius=[0, 0, r, r])

class LogoMark(Widget):
    """Premium app logo mark with play+download motif."""
    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self._d, size=self._d)

    def _d(self, *_):
        self.canvas.clear()
        x, y = self.pos
        w, h = self.size
        r = min(dp(11), w * 0.24)
        with self.canvas:
            # Background rounded square with gradient feel
            Color(*ACCENT)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[r] * 4)
            # Cyan overlay on bottom half
            Color(ACCENT2[0], ACCENT2[1], ACCENT2[2], 0.30)
            RoundedRectangle(pos=(x, y),
                             size=(w, h * 0.55), radius=[r, r, 0, 0])
            # Top sheen
            Color(1, 1, 1, 0.12)
            RoundedRectangle(pos=(x, y + h * 0.55),
                             size=(w, h * 0.45), radius=[0, 0, r, r])

            # Play triangle (centered)
            cx = x + w * 0.53
            cy = y + h * 0.54
            sz = w * 0.22
            Color(1, 1, 1, 0.95)
            tri = [cx - sz * 0.5, cy + sz * 0.6,
                   cx - sz * 0.5, cy - sz * 0.6,
                   cx + sz * 0.7, cy]
            Mesh(vertices=[
                tri[0], tri[1], 0, 0,
                tri[2], tri[3], 0, 0,
                tri[4], tri[5], 0, 0,
            ], indices=[0, 1, 2], mode="triangle_fan")

            # Small download arrow below
            arr_y = y + h * 0.22
            Color(1, 1, 1, 0.80)
            Line(points=[cx - dp(1), y + h * 0.38, cx - dp(1), arr_y + dp(4)],
                 width=dp(1.5), cap="round")
            Line(points=[cx - dp(1) - w * 0.08, arr_y + dp(7),
                         cx - dp(1), arr_y + dp(2),
                         cx - dp(1) + w * 0.08, arr_y + dp(7)],
                 width=dp(1.3), cap="round", joint="round")


def lbl(text="", size=13, color=None, bold=False,
        halign="left", h=None, markup=False):
    l = Label(
        text=text, font_size=sp(size),
        color=list(color or TEXT),
        bold=bold, halign=halign,
        valign="middle", markup=markup,
    )
    l.bind(size=l.setter("text_size"))
    if h:
        l.size_hint_y = None
        l.height = dp(h)
    return l


def spacer(h=8):
    return Widget(size_hint_y=None, height=dp(h))


def hr():
    d = Widget(size_hint_y=None, height=dp(1))
    with d.canvas:
        Color(*BORDER)
        Rectangle(pos=d.pos, size=d.size)
    d.bind(pos=lambda w, _: _draw_hr(w), size=lambda w, _: _draw_hr(w))
    return d


def _draw_hr(w):
    w.canvas.clear()
    with w.canvas:
        Color(*BORDER)
        Rectangle(pos=w.pos, size=w.size)


# ═══════════════════════════════════════════════════════════
#  FORMAT CHIP  (pill-shaped selectable button)
# ═══════════════════════════════════════════════════════════

class FmtChip(Button):
    selected = BooleanProperty(False)

    def __init__(self, fmt, **kw):
        self.fmt = fmt
        tag   = fmt.get("tag", "")
        label = self._clean_label(fmt)
        size  = fmt.get("size", "")
        needs_mux = fmt.get("needs_mux", False) or fmt.get("audio_id")

        tc = TAG_COLORS.get(tag, list(MUTED))
        tag_hex = "#{:02x}{:02x}{:02x}".format(
            int(tc[0] * 255), int(tc[1] * 255), int(tc[2] * 255))

        parts = []
        if tag:
            parts.append(f"[color={tag_hex[1:]}][b]{tag}[/b][/color]  ")
        parts.append(f"[b]{label}[/b]")
        if needs_mux:
            parts.append(f"  [color=ffcc38] MERGE[/color]")
        if size:
            parts.append(f"  [color=9ea0bd]{size}[/color]")

        txt = "".join(parts)

        super().__init__(
            text=txt,
            markup=True,
            halign="left",
            valign="middle",
            font_size=sp(13),
            color=list(TEXT),
            background_normal="",
            background_color=(0, 0, 0, 0),
            size_hint_y=None,
            height=dp(54),
            **kw,
        )
        self.bind(size=self.setter("text_size"))
        self.bind(pos=self._d, size=self._d, selected=self._d)

    def _clean_label(self, fmt):
        label = str(fmt.get("label", "?"))
        cat = str(fmt.get("category", ""))
        low = label.lower()
        if cat == "video_only" and low.endswith(" video only"):
            return label[: -len(" Video Only")]
        if cat == "audio_only" and low.startswith("audio "):
            return label[6:]
        return label

    def _d(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.selected:
                # Glow behind selected chip
                Color(ACCENT[0], ACCENT[1], ACCENT[2], 0.08)
                RoundedRectangle(
                    pos=(self.x - dp(1), self.y - dp(1)),
                    size=(self.width + dp(2), self.height + dp(2)),
                    radius=[RAD2 + dp(1)] * 4)
                # Filled accent background
                Color(ACCENT[0], ACCENT[1], ACCENT[2], 0.15)
                RoundedRectangle(pos=self.pos, size=self.size,
                                 radius=[RAD2] * 4)
                Color(*ACCENT)
                Line(rounded_rectangle=(
                    self.x, self.y, self.width, self.height, RAD2),
                    width=1.8)
                # Left accent bar
                Color(*ACCENT)
                RoundedRectangle(
                    pos=(self.x, self.y + dp(10)),
                    size=(dp(3), self.height - dp(20)),
                    radius=[dp(2)] * 4)
            else:
                Color(*CARD2)
                RoundedRectangle(pos=self.pos, size=self.size,
                                 radius=[RAD2] * 4)
                Color(BORDER[0], BORDER[1], BORDER[2], 0.5)
                Line(rounded_rectangle=(
                    self.x, self.y, self.width, self.height, RAD2),
                    width=0.8)

    def select(self):
        self.selected = True

    def deselect(self):
        self.selected = False

    def on_touch_down(self, t):
        return super().on_touch_down(t)


# ═══════════════════════════════════════════════════════════
#  HISTORY ITEM
# ═══════════════════════════════════════════════════════════

class HistoryItem(BoxLayout):
    def __init__(self, fname, ftype, **kw):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None, height=dp(66),
            padding=(dp(16), dp(12)),
            spacing=dp(14),
            **kw,
        )
        self.bind(pos=self._d, size=self._d)

        # Icon pill with gradient
        is_audio  = ftype == "audio"
        ic_char   = "AUD" if is_audio else "VID"
        ic_color  = list(ACCENT2) if is_audio else list(ACCENT)

        pill = FloatLayout(size_hint=(None, None),
                           size=(dp(42), dp(42)))
        with pill.canvas.before:
            Color(ic_color[0], ic_color[1], ic_color[2], 0.15)
            RoundedRectangle(pos=pill.pos, size=pill.size, radius=[dp(12)] * 4)
        pill.bind(pos=lambda w, _: self._pill_bg(w, ic_color),
                  size=lambda w, _: self._pill_bg(w, ic_color))
        ic_lbl = Label(text=ic_char, font_size=sp(10),
                       color=ic_color, bold=True,
                       pos_hint={"center_x": .5, "center_y": .5})
        pill.add_widget(ic_lbl)
        self.add_widget(pill)

        # Text column
        col = BoxLayout(orientation="vertical", spacing=dp(3))
        short = fname if len(fname) <= 48 else fname[:45] + "..."
        n = Label(text=short, font_size=sp(13), color=list(TEXT),
                  bold=True, halign="left", valign="bottom")
        n.bind(size=n.setter("text_size"))
        t = Label(text=ftype.upper(), font_size=sp(10),
                  color=list(TEXTSUB), halign="left", valign="top")
        t.bind(size=t.setter("text_size"))
        col.add_widget(n)
        col.add_widget(t)
        self.add_widget(col)

    def _d(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            # Subtle shadow
            Color(0, 0, 0, 0.08)
            RoundedRectangle(
                pos=(self.x + dp(1), self.y - dp(1)),
                size=(self.width, self.height),
                radius=[RAD2 + dp(1)] * 4)
            # Card body
            Color(*CARD)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[RAD2] * 4)

    def _pill_bg(self, w, c):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(c[0], c[1], c[2], 0.15)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(12)] * 4)


# ═══════════════════════════════════════════════════════════
#  MAIN APP
# ═══════════════════════════════════════════════════════════

class VideoDownloaderApp(App):

    def _init_state(self):
        if getattr(self, "_state_ready", False):
            return
        self.info      = None
        self.fmt_cards = []
        self.sel_fmt   = None
        self._all_fmts = []
        self._fmt_mode = "video_audio"
        self._fmt_mode_btns = {}
        self._perm_popup = None
        self._pending_storage_prompt = False
        self._notify_popup = None
        self._pending_notify_prompt = False
        self._notif_ready = False
        self._notif_last_pct = -1
        self._notif_last_step = ""
        self._settings = (
            app_settings.load_settings()
            if app_settings else {"download_dir": "", "notifications": True}
        )
        self._settings.setdefault("download_dir", "")
        self._settings.setdefault("notifications", True)
        self._settings.setdefault("resume_downloads", False)
        self._settings.setdefault("background_keep_awake", True)
        self._settings.setdefault("auto_cleanup_cache", True)
        self._settings.setdefault("cache_max_age_hours", 12)
        self._settings.setdefault("max_crash_log_mb", 2)
        self._settings.setdefault("history_limit", 120)
        self._settings.setdefault("diagnostics_live", True)
        self._settings.setdefault("theme", "Neon Dusk")
        self._settings.setdefault("theme_mode", "dark")
        self._logs     = []
        self._history  = []
        self._batch_urls = []  # remaining URLs for batch download
        self._cur_tab  = "download"
        self._settings_dir_input = None
        self._notif_btn = None
        self._cache_toggle_btn = None
        self._resume_cache_btn = None
        self._bg_awake_btn = None
        self._cache_age_input = None
        self._log_limit_input = None
        self.settings_status_lbl = None
        self._storage_lbl = None
        self._thumb_tmp_path = None
        self._history_limit_input = None
        self._diag_lbl = None
        self._diag_detail_lbl = None
        self._diag_live_btn = None
        self._diag_event = None
        self._diag_cache_hist = []
        self._history_status_lbl = None
        self._folder_picker_bound = False
        self._folder_picker_req = 7419
        self._theme_dark_btn = None
        self._theme_light_btn = None
        self._download_thread = None
        self._download_control = None
        self._download_active = False
        self._download_paused = False
        self._dns_retry_count = 0
        self._net_retry_count = 0
        self._net_retry_max = 0
        self._net_retry_scope = ""
        self._net_kind = "unknown"
        self._net_event = None
        self._net_status_lbl = None
        self._net_retry_lbl = None
        self.pause_btn = None
        self.stop_btn = None
        self._wake_lock = None
        self._wifi_lock = None
        self._intent_action_bound = False
        self._fetch_seq = 0
        self._fetch_inflight = False
        self._last_fetch_t = 0.0
        self._fetch_url = ""
        self._fetch_started_at = 0.0
        self._state_ready = True
        self._history = self._load_history_entries()

    def _compose_root(self, root):
        root.clear_widgets()

        # Full background
        bg = Widget()
        with bg.canvas:
            Color(*BG)
            Rectangle(pos=bg.pos, size=bg.size)
        bg.bind(pos=lambda w, _: self._rr(w, BG),
                size=lambda w, _: self._rr(w, BG))
        root.add_widget(bg)

        # Main layout
        main = BoxLayout(orientation="vertical",
                         pos_hint={"x": 0, "y": 0}, size_hint=(1, 1))
        root.add_widget(main)

        main.add_widget(self._mk_header())
        main.add_widget(self._mk_tabbar())

        self.content_scroll = ScrollView(do_scroll_x=False)
        self.content_col = BoxLayout(
            orientation="vertical",
            padding=(PAD, PAD2),
            spacing=dp(12),
            size_hint_y=None,
        )
        self.content_col.bind(
            minimum_height=self.content_col.setter("height"))
        self.content_scroll.add_widget(self.content_col)
        main.add_widget(self.content_scroll)

        if self._cur_tab == "history":
            self._build_history_tab()
        elif self._cur_tab == "settings":
            self._build_settings_tab()
        else:
            self._build_download_tab()

    def _rebuild_ui_for_theme(self):
        if not self.root:
            return
        cur_tab = self._cur_tab
        self._stop_diagnostics_updates()
        self._compose_root(self.root)
        self._cur_tab = cur_tab
        if hasattr(self, "tab_dl"):
            self._draw_tab_btn(self.tab_dl)
        if hasattr(self, "tab_his"):
            self._draw_tab_btn(self.tab_his)
        if hasattr(self, "tab_set"):
            self._draw_tab_btn(self.tab_set)

    def build(self):
        wlog("build() called")
        self._init_state()
        _apply_theme_globals(self._settings.get("theme_mode", "dark"))
        root = FloatLayout()
        self._compose_root(root)
        wlog("build() done")
        return root

    def _rr(self, w, col):
        w.canvas.clear()
        with w.canvas:
            Color(*col)
            Rectangle(pos=w.pos, size=w.size)

    # ── Storage Permission Flow (Android) ────────────────────────────────
    def _android_storage_perms(self):
        try:
            from android.permissions import Permission
        except Exception:
            return []
        out = []
        for name in (
            "READ_MEDIA_VIDEO",
            "READ_MEDIA_AUDIO",
            "READ_EXTERNAL_STORAGE",
            "WRITE_EXTERNAL_STORAGE",
        ):
            p = getattr(Permission, name, None)
            if p:
                out.append(p)
        return out

    def _has_storage_permission(self):
        try:
            from android.permissions import check_permission
        except Exception:
            return True
        perms = self._android_storage_perms()
        if not perms:
            return True
        try:
            return any(check_permission(p) for p in perms)
        except Exception as e:
            wlog(f"perm check failed: {e}")
            return True

    def _request_storage_permission(self):
        if self._has_storage_permission():
            return True
        try:
            from android.permissions import request_permissions, check_permission
            needed = [p for p in self._android_storage_perms() if not check_permission(p)]
            if needed:
                request_permissions(needed)
                self._pending_storage_prompt = True
                Clock.schedule_once(lambda dt: self._after_storage_prompt(), 1.0)
            return self._has_storage_permission()
        except Exception as e:
            wlog(f"perm request failed: {e}")
            return False

    def _after_storage_prompt(self):
        self._pending_storage_prompt = False
        if self._has_storage_permission():
            if self._perm_popup:
                self._perm_popup.dismiss()
                self._perm_popup = None
            self._log("[color=33ed9a]Storage permission granted[/color]")
        else:
            self._show_storage_permission_popup(
                "Storage permission is needed to save downloads.\n"
                "Allow permission or open Settings."
            )

    def _open_app_settings(self):
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Intent = autoclass("android.content.Intent")
            Settings = autoclass("android.provider.Settings")
            Uri = autoclass("android.net.Uri")

            activity = PythonActivity.mActivity
            intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
            intent.setData(Uri.fromParts("package", activity.getPackageName(), None))
            activity.startActivity(intent)
            return True
        except Exception as e:
            wlog(f"open settings failed: {e}")
            return False

    def _show_storage_permission_popup(self, message):
        if self._perm_popup:
            return
        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(14))
        m = Label(text=message, color=list(TEXT), halign="left", valign="middle")
        m.bind(size=m.setter("text_size"))
        box.add_widget(m)

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        allow_btn = Btn(text="ALLOW STORAGE", font_size=sp(12))
        settings_btn = OutlineBtn(text="OPEN SETTINGS", font_size=sp(12))
        close_btn = OutlineBtn(text="LATER", font_size=sp(12))

        def do_allow(*_):
            if self._request_storage_permission():
                if self._perm_popup:
                    self._perm_popup.dismiss()
                    self._perm_popup = None

        def do_settings(*_):
            self._open_app_settings()

        def do_close(*_):
            if self._perm_popup:
                self._perm_popup.dismiss()
                self._perm_popup = None

        allow_btn.bind(on_release=do_allow)
        settings_btn.bind(on_release=do_settings)
        close_btn.bind(on_release=do_close)
        row.add_widget(allow_btn)
        row.add_widget(settings_btn)
        row.add_widget(close_btn)
        box.add_widget(row)

        self._perm_popup = Popup(
            title="Storage Permission Required",
            content=box,
            size_hint=(0.94, None),
            height=dp(220),
            auto_dismiss=False,
        )
        self._perm_popup.bind(on_dismiss=lambda *_: setattr(self, "_perm_popup", None))
        self._perm_popup.open()

    def _ensure_storage_permission(self, show_ui=False):
        if self._has_storage_permission():
            return True
        if show_ui:
            granted = self._request_storage_permission()
            if not granted:
                self._show_storage_permission_popup(
                    "Storage permission is needed to save files in Downloads."
                )
            return granted
        return False

    # ── Notification Permission + Progress Notifications ─────────────────
    def _android_notification_perm(self):
        try:
            from android.permissions import Permission
            return getattr(Permission, "POST_NOTIFICATIONS", None)
        except Exception:
            return None

    def _has_notification_permission(self):
        p = self._android_notification_perm()
        if not p:
            return True
        try:
            from android.permissions import check_permission
            return bool(check_permission(p))
        except Exception as e:
            wlog(f"notif perm check failed: {e}")
            return True

    def _request_notification_permission(self):
        if self._has_notification_permission():
            return True
        p = self._android_notification_perm()
        if not p:
            return True
        try:
            from android.permissions import request_permissions
            request_permissions([p])
            self._pending_notify_prompt = True
            Clock.schedule_once(lambda dt: self._after_notify_prompt(), 1.0)
            return True
        except Exception as e:
            wlog(f"notif perm request failed: {e}")
            return False

    def _after_notify_prompt(self):
        self._pending_notify_prompt = False
        if self._has_notification_permission():
            if self._notify_popup:
                self._notify_popup.dismiss()
                self._notify_popup = None
            self._log("[color=33ed9a]Notification permission granted[/color]")
        else:
            self._show_notification_popup(
                "Notification permission helps show download progress in background."
            )

    def _show_notification_popup(self, message):
        if self._notify_popup:
            return
        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(14))
        m = Label(text=message, color=list(TEXT), halign="left", valign="middle")
        m.bind(size=m.setter("text_size"))
        box.add_widget(m)

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        allow_btn = Btn(text="ALLOW", font_size=sp(12))
        settings_btn = OutlineBtn(text="OPEN SETTINGS", font_size=sp(12))
        later_btn = OutlineBtn(text="LATER", font_size=sp(12))

        allow_btn.bind(on_release=lambda *_: self._request_notification_permission())
        settings_btn.bind(on_release=lambda *_: self._open_app_settings())
        later_btn.bind(on_release=lambda *_: self._notify_popup and self._notify_popup.dismiss())

        row.add_widget(allow_btn)
        row.add_widget(settings_btn)
        row.add_widget(later_btn)
        box.add_widget(row)

        self._notify_popup = Popup(
            title="Notification Permission",
            content=box,
            size_hint=(0.90, None),
            height=dp(200),
            auto_dismiss=True,
        )
        self._notify_popup.bind(on_dismiss=lambda *_: setattr(self, "_notify_popup", None))
        self._notify_popup.open()

    def _ensure_notification_permission(self, show_ui=False):
        if self._has_notification_permission():
            return True
        if show_ui:
            granted = self._request_notification_permission()
            if not granted:
                self._show_notification_popup(
                    "Allow notifications to see download progress outside the app."
                )
            return granted
        return False

    def _notify_init(self):
        if self._notif_ready:
            return True
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Context = autoclass("android.content.Context")
            NotificationManager = autoclass("android.app.NotificationManager")
            NotificationChannel = autoclass("android.app.NotificationChannel")
            BuildVersion = autoclass("android.os.Build$VERSION")

            act = PythonActivity.mActivity
            nm = act.getSystemService(Context.NOTIFICATION_SERVICE)
            if BuildVersion.SDK_INT >= 26:
                ch = NotificationChannel(
                    "videodl_downloads", "Downloads",
                    NotificationManager.IMPORTANCE_LOW
                )
                ch.setDescription("Video Downloader progress")
                nm.createNotificationChannel(ch)
            self._notif_ready = True
            return True
        except Exception as e:
            wlog(f"notify init failed: {e}")
            return False

    def _bind_notification_actions(self):
        if self._intent_action_bound:
            return True
        try:
            from android import activity as android_activity
            android_activity.bind(on_new_intent=self._on_android_new_intent)
            self._intent_action_bound = True
            return True
        except Exception as e:
            wlog(f"bind notify actions failed: {e}")
            return False

    def _build_action_pending_intent(self, action, request_code):
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Intent = autoclass("android.content.Intent")
            PendingIntent = autoclass("android.app.PendingIntent")

            act = PythonActivity.mActivity
            intent = Intent(act, act.getClass())
            intent.setAction(action)
            intent.addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP)
            flags = PendingIntent.FLAG_UPDATE_CURRENT
            if hasattr(PendingIntent, "FLAG_IMMUTABLE"):
                flags = flags | PendingIntent.FLAG_IMMUTABLE
            return PendingIntent.getActivity(act, int(request_code), intent, flags)
        except Exception as e:
            wlog(f"action intent failed ({action}): {e}")
            return None

    def _on_android_new_intent(self, intent):
        try:
            action = ""
            if intent is not None:
                action = str(intent.getAction() or "")
        except Exception:
            action = ""
        if action not in (NOTIF_ACTION_PAUSE, NOTIF_ACTION_RESUME, NOTIF_ACTION_STOP):
            return
        Clock.schedule_once(lambda dt, a=action: self._handle_notification_action(a), 0)

    def _handle_notification_action(self, action):
        if action == NOTIF_ACTION_PAUSE:
            self._pause_download(external=True)
        elif action == NOTIF_ACTION_RESUME:
            self._resume_download(external=True)
        elif action == NOTIF_ACTION_STOP:
            self._stop_download(external=True)

    def _notify_progress(self, pct, step):
        if not self._settings.get("notifications", True):
            return
        if not self._has_notification_permission():
            return
        if not self._notify_init():
            return
        self._bind_notification_actions()
        pct_i = int(max(0, min(100, pct or 0)))
        step = str(step or "")
        if pct_i == self._notif_last_pct and step == self._notif_last_step:
            return
        self._notif_last_pct = pct_i
        self._notif_last_step = step
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Context = autoclass("android.content.Context")
            BuildVersion = autoclass("android.os.Build$VERSION")
            NotificationBuilder = autoclass("android.app.Notification$Builder")

            act = PythonActivity.mActivity
            nm = act.getSystemService(Context.NOTIFICATION_SERVICE)
            icon = act.getApplicationInfo().icon
            if BuildVersion.SDK_INT >= 26:
                b = NotificationBuilder(act, "videodl_downloads")
            else:
                b = NotificationBuilder(act)
            b.setSmallIcon(icon)
            b.setContentTitle("Video Downloader")
            b.setContentText(f"{step} ({pct_i}%)")
            b.setOnlyAlertOnce(True)
            b.setOngoing(True)
            b.setProgress(100, pct_i, False)
            toggle_action = NOTIF_ACTION_RESUME if self._download_paused else NOTIF_ACTION_PAUSE
            toggle_label = "RESUME" if self._download_paused else "PAUSE"
            pi_toggle = self._build_action_pending_intent(toggle_action, 7002)
            pi_stop = self._build_action_pending_intent(NOTIF_ACTION_STOP, 7003)
            if pi_toggle is not None:
                b.addAction(icon, toggle_label, pi_toggle)
            if pi_stop is not None:
                b.addAction(icon, "STOP", pi_stop)
            nm.notify(7001, b.build())
        except Exception as e:
            wlog(f"notify progress failed: {e}")

    def _notify_done(self, name):
        if not self._has_notification_permission() or not self._notify_init():
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Context = autoclass("android.content.Context")
            BuildVersion = autoclass("android.os.Build$VERSION")
            NotificationBuilder = autoclass("android.app.Notification$Builder")

            act = PythonActivity.mActivity
            nm = act.getSystemService(Context.NOTIFICATION_SERVICE)
            icon = act.getApplicationInfo().icon
            if BuildVersion.SDK_INT >= 26:
                b = NotificationBuilder(act, "videodl_downloads")
            else:
                b = NotificationBuilder(act)
            b.setSmallIcon(icon)
            b.setContentTitle("Download complete")
            b.setContentText(name[:120])
            b.setAutoCancel(True)
            b.setOngoing(False)
            b.setProgress(0, 0, False)
            nm.notify(7001, b.build())
        except Exception as e:
            wlog(f"notify done failed: {e}")

    def _notify_error(self, msg):
        if not self._has_notification_permission() or not self._notify_init():
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Context = autoclass("android.content.Context")
            BuildVersion = autoclass("android.os.Build$VERSION")
            NotificationBuilder = autoclass("android.app.Notification$Builder")

            act = PythonActivity.mActivity
            nm = act.getSystemService(Context.NOTIFICATION_SERVICE)
            icon = act.getApplicationInfo().icon
            if BuildVersion.SDK_INT >= 26:
                b = NotificationBuilder(act, "videodl_downloads")
            else:
                b = NotificationBuilder(act)
            b.setSmallIcon(icon)
            b.setContentTitle("Download failed")
            b.setContentText(str(msg)[:120])
            b.setAutoCancel(True)
            b.setOngoing(False)
            b.setProgress(0, 0, False)
            nm.notify(7001, b.build())
        except Exception as e:
            wlog(f"notify error failed: {e}")

    def _acquire_wake_lock(self, force=False):
        if self._wake_lock is not None:
            return
        if (not force) and (not self._settings.get("background_keep_awake", True)):
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Context = autoclass("android.content.Context")
            PowerManager = autoclass("android.os.PowerManager")
            activity = PythonActivity.mActivity
            pm = activity.getSystemService(Context.POWER_SERVICE)
            lock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "videodownloader:download")
            lock.setReferenceCounted(False)
            lock.acquire()
            self._wake_lock = lock
            wlog("wake lock acquired")
        except Exception as e:
            wlog(f"wake lock acquire failed: {e}")

    def _acquire_wifi_lock(self, force=False):
        if self._wifi_lock is not None:
            return
        if (not force) and (not self._settings.get("background_keep_awake", True)):
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Context = autoclass("android.content.Context")
            WifiManager = autoclass("android.net.wifi.WifiManager")
            activity = PythonActivity.mActivity
            wm = activity.getApplicationContext().getSystemService(Context.WIFI_SERVICE)
            if wm is None:
                return
            mode = getattr(WifiManager, "WIFI_MODE_FULL_HIGH_PERF", None)
            if mode is None:
                mode = WifiManager.WIFI_MODE_FULL
            lock = wm.createWifiLock(int(mode), "videodownloader:wifi")
            lock.setReferenceCounted(False)
            lock.acquire()
            self._wifi_lock = lock
            wlog("wifi lock acquired")
        except Exception as e:
            wlog(f"wifi lock acquire failed: {e}")

    def _release_wake_lock(self):
        lock = self._wake_lock
        self._wake_lock = None
        if lock is None:
            return
        try:
            if lock.isHeld():
                lock.release()
            wlog("wake lock released")
        except Exception as e:
            wlog(f"wake lock release failed: {e}")

    def _release_wifi_lock(self):
        lock = self._wifi_lock
        self._wifi_lock = None
        if lock is None:
            return
        try:
            if lock.isHeld():
                lock.release()
            wlog("wifi lock released")
        except Exception as e:
            wlog(f"wifi lock release failed: {e}")

    def _acquire_active_locks(self, force=False):
        self._acquire_wake_lock(force=force)
        self._acquire_wifi_lock(force=force)

    def _release_active_locks(self):
        self._release_wifi_lock()
        self._release_wake_lock()

    def on_start(self):
        Window.clearcolor = BG
        if not downloader:
            self._show_prog()
            self._log("[color=ff4488]WARN: downloader module not loaded[/color]")
        Clock.schedule_once(lambda dt: self._ensure_storage_permission(show_ui=True), 0.25)
        if self._settings.get("notifications", True):
            Clock.schedule_once(lambda dt: self._ensure_notification_permission(show_ui=True), 0.75)
            self._bind_notification_actions()
        if (downloader and hasattr(downloader, "cleanup_temp_cache") and
                self._settings.get("auto_cleanup_cache", True)):
            def _bg_cleanup():
                try:
                    age_h = self._settings.get("cache_max_age_hours", 12)
                    out = downloader.cleanup_temp_cache(max_age_hours=age_h)
                    rd = int(out.get("removed_dirs", 0))
                    rb = int(out.get("removed_bytes", 0))
                    if rd > 0:
                        wlog(f"startup cleanup: {rd} dirs, {rb//1024}KB")
                except Exception as e:
                    wlog(f"startup cleanup failed: {e}")
            threading.Thread(target=_bg_cleanup, daemon=True).start()
        # Check clipboard for URL
        Clock.schedule_once(lambda dt: self._check_clipboard_on_startup(), 1.2)

    def on_pause(self):
        # Keep Python process alive while app is backgrounded if Android allows it.
        wlog("on_pause: allowing background execution")
        if self._download_active:
            wlog("background download: active")
        return True

    def on_resume(self):
        wlog("on_resume")
        if self._pending_storage_prompt:
            Clock.schedule_once(lambda dt: self._after_storage_prompt(), 0.2)
        if self._pending_notify_prompt:
            Clock.schedule_once(lambda dt: self._after_notify_prompt(), 0.2)

    def on_stop(self):
        self._stop_diagnostics_updates()
        self._stop_network_status_updates()
        self._save_history_entries()
        self._release_active_locks()
        if self._intent_action_bound:
            try:
                from android import activity as android_activity
                android_activity.unbind(on_new_intent=self._on_android_new_intent)
            except Exception:
                pass
            self._intent_action_bound = False
        if self._folder_picker_bound:
            try:
                from android import activity as android_activity
                android_activity.unbind(on_activity_result=self._on_android_activity_result)
            except Exception:
                pass
            self._folder_picker_bound = False
        self._cleanup_thumb_temp()

    # ── Header ────────────────────────────────────────────────────────────
    def _mk_header(self):
        bar = BoxLayout(
            size_hint_y=None, height=dp(74),
            padding=(PAD, 0, PAD, 0), spacing=dp(12),
        )
        with bar.canvas.before:
            # Clean single-surface header
            Color(*SURF)
            Rectangle(pos=bar.pos, size=bar.size)
        bar.bind(pos=lambda w, _: self._hdr_bg(w),
                 size=lambda w, _: self._hdr_bg(w))

        bar.add_widget(LogoMark(size_hint=(None, None), size=(dp(40), dp(40))))

        txt_col = BoxLayout(orientation="vertical", spacing=0)
        t1 = Label(text="Video Downloader", font_size=sp(17), bold=True,
                   color=list(TEXT), halign="left", valign="bottom")
        t1.bind(size=t1.setter("text_size"))
        t2 = Label(text="Videos + Audio  |  No Ads  |  Free",
                   font_size=sp(10), color=list(TEXTSUB),
                   halign="left", valign="top")
        t2.bind(size=t2.setter("text_size"))
        txt_col.add_widget(t1)
        txt_col.add_widget(t2)
        bar.add_widget(txt_col)

        return bar

    def _hdr_bg(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*SURF)
            Rectangle(pos=w.pos, size=w.size)

    # ── Tab bar ───────────────────────────────────────────────────────────
    def _mk_tabbar(self):
        wrap = BoxLayout(orientation="vertical",
                         size_hint_y=None, height=dp(54))
        bar = BoxLayout(
            size_hint_y=None, height=dp(52),
            padding=(PAD, dp(6)), spacing=dp(8),
        )
        with bar.canvas.before:
            Color(*SURF)
            Rectangle(pos=bar.pos, size=bar.size)
        bar.bind(pos=lambda w, _: self._surf_bg(w),
                 size=lambda w, _: self._surf_bg(w))

        self.tab_dl  = self._mk_tab("Download", "download")
        self.tab_his = self._mk_tab("History",  "history")
        self.tab_set = self._mk_tab("Settings", "settings")
        bar.add_widget(self.tab_dl)
        bar.add_widget(self.tab_his)
        bar.add_widget(self.tab_set)

        # Accent underline strip
        line = Widget(size_hint_y=None, height=dp(1))
        with line.canvas:
            Color(ACCENT[0], ACCENT[1], ACCENT[2], 0.50)
            Rectangle(pos=line.pos, size=line.size)
        line.bind(pos=lambda w, _: self._line_bg(w),
                  size=lambda w, _: self._line_bg(w))

        wrap.add_widget(bar)
        wrap.add_widget(line)
        return wrap

    def _surf_bg(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*SURF)
            Rectangle(pos=w.pos, size=w.size)

    def _line_bg(self, w):
        w.canvas.clear()
        with w.canvas:
            Color(ACCENT[0], ACCENT[1], ACCENT[2], 0.35)
            Rectangle(pos=w.pos, size=w.size)
            # Bright center glow
            Color(ACCENT2[0], ACCENT2[1], ACCENT2[2], 0.20)
            Rectangle(pos=(w.x + w.width * 0.25, w.y),
                      size=(w.width * 0.5, w.height))

    def _mk_tab(self, text, key):
        btn = Button(
            text=text,
            size_hint=(1, 1),
            background_normal="", background_color=(0, 0, 0, 0),
            color=list(TEXTSUB),
            bold=False,
            font_size=sp(13),
        )
        btn._tab_key = key
        btn.bind(pos=lambda b, _: self._draw_tab_btn(b),
                 size=lambda b, _: self._draw_tab_btn(b))
        btn.bind(on_release=lambda b, k=key: self._switch_tab(k))
        Clock.schedule_once(lambda dt, b=btn: self._draw_tab_btn(b), 0)
        return btn

    def _draw_tab_btn(self, btn):
        active = self._cur_tab == getattr(btn, "_tab_key", "")
        btn.color = list(TEXT if active else TEXTSUB)
        btn.bold = active
        btn.canvas.before.clear()
        with btn.canvas.before:
            if active:
                # Active pill background with accent glow
                Color(ACCENT[0], ACCENT[1], ACCENT[2], 0.06)
                RoundedRectangle(
                    pos=(btn.x - dp(1), btn.y - dp(1)),
                    size=(btn.width + dp(2), btn.height + dp(2)),
                    radius=[dp(16)] * 4)
                Color(ACCENT[0], ACCENT[1], ACCENT[2], 0.16)
                RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(15)] * 4)
                # Bottom indicator bar
                Color(*ACCENT)
                RoundedRectangle(
                    pos=(btn.x + btn.width * 0.2, btn.y),
                    size=(btn.width * 0.6, dp(3)),
                    radius=[dp(2)] * 4)
            else:
                Color(0, 0, 0, 0)
                RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(15)] * 4)

    def _switch_tab(self, key):
        if self._cur_tab == "settings" and key != "settings":
            self._stop_diagnostics_updates()
        self._cur_tab = key
        self.content_col.clear_widgets()
        if key == "download":
            self._build_download_tab()
        elif key == "history":
            self._build_history_tab()
        else:
            self._build_settings_tab()
        self._draw_tab_btn(self.tab_dl)
        self._draw_tab_btn(self.tab_his)
        self._draw_tab_btn(self.tab_set)

    # ── Format Mode Tabs ──────────────────────────────────────────────────
    def _mk_fmt_mode_btn(self, text, key):
        b = Button(
            text=text,
            background_normal="", background_color=(0, 0, 0, 0),
            color=list(TEXTSUB),
            font_size=sp(11),
            bold=False,
        )
        b._fmt_mode_key = key
        b.bind(on_release=lambda *_: self._set_fmt_mode(key))
        b.bind(pos=lambda w, _: self._draw_fmt_mode_btn(w),
               size=lambda w, _: self._draw_fmt_mode_btn(w))
        Clock.schedule_once(lambda dt, w=b: self._draw_fmt_mode_btn(w), 0)
        return b

    def _draw_fmt_mode_btn(self, btn):
        active = self._fmt_mode == getattr(btn, "_fmt_mode_key", "")
        btn.color = list(TEXT if active else TEXTSUB)
        btn.bold  = active
        btn.canvas.before.clear()
        with btn.canvas.before:
            if active:
                Color(ACCENT[0], ACCENT[1], ACCENT[2], 0.16)
                RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(12)] * 4)
                Color(*ACCENT)
                Line(rounded_rectangle=(
                    btn.x, btn.y, btn.width, btn.height, dp(12)), width=1.4)
            else:
                Color(CARD2[0], CARD2[1], CARD2[2], 0.3)
                RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(12)] * 4)
                Color(BORDER[0], BORDER[1], BORDER[2], 0.4)
                Line(rounded_rectangle=(
                    btn.x, btn.y, btn.width, btn.height, dp(12)), width=0.8)

    def _set_fmt_mode(self, key):
        self._fmt_mode = key
        self._refresh_fmt_mode_ui()
        self._refresh_fmt_list()

    def _refresh_fmt_mode_ui(self):
        for b in self._fmt_mode_btns.values():
            self._draw_fmt_mode_btn(b)

    def _fmt_category(self, fmt):
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

    def _filtered_formats(self):
        return [f for f in self._all_fmts if self._fmt_category(f) == self._fmt_mode]

    def _refresh_fmt_list(self):
        if not hasattr(self, "fmt_box"):
            return

        fmts = self._filtered_formats()
        old_id = self.sel_fmt.get("format_id") if self.sel_fmt else None

        self.fmt_box.clear_widgets()
        self.fmt_cards = []
        rows_h = 0
        for fmt in fmts:
            fc = FmtChip(fmt)
            fc.bind(on_release=lambda w, c=fc: self._sel(c))
            self.fmt_box.add_widget(fc)
            self.fmt_cards.append(fc)
            rows_h += fc.height + dp(6)
        self.fmt_box.height = rows_h

        base_h = PAD * 2 + dp(22) + dp(38) + dp(16)
        self.fmt_card.height  = base_h + rows_h
        self.fmt_card.opacity = 1 if fmts else 0

        selected = next((c for c in self.fmt_cards if c.fmt.get("format_id") == old_id), None)
        if selected:
            self._sel(selected)
        elif self.fmt_cards:
            self._sel(self.fmt_cards[0])
        else:
            self.sel_fmt = None
            self._hide_dl()

    # ── Download Tab ──────────────────────────────────────────────────────
    def _build_download_tab(self):
        c = self.content_col
        c.add_widget(spacer(6))

        # ── URL Input Card ────────────────────────────────────────────────
        url_card = GlassCard(
            orientation="vertical",
            padding=PAD, spacing=dp(12),
            size_hint_y=None, height=dp(172),
            bg=list(SURF), radius=RAD,
        )

        # Header row: icon + label + paste button
        hdr_row = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
        hdr_row.add_widget(lbl("URL", 11, ACCENT, bold=True, h=28))
        hdr_row.add_widget(lbl("Paste video URL", 11, TEXTSUB, bold=True, h=28))
        paste_btn = OutlineBtn(
            text="PASTE",
            size_hint=(None, None), size=(dp(72), dp(26)),
            font_size=sp(10), radius=dp(8),
        )
        paste_btn.bind(on_release=lambda *_: self._paste_url())
        hdr_row.add_widget(paste_btn)
        url_card.add_widget(hdr_row)

        self.url_in = TextInput(
            hint_text="https://youtube.com/watch?v=...",
            multiline=False,
            size_hint_y=None, height=dp(50),
            background_color=list(CARD),
            foreground_color=list(TEXT),
            hint_text_color=list(MUTED),
            cursor_color=list(ACCENT),
            font_size=sp(13),
            padding=[dp(16), dp(15)],
        )
        self.url_in.bind(on_text_validate=lambda *_: self.do_fetch())
        url_card.add_widget(self.url_in)

        self.fetch_btn = Btn(
            text="FETCH VIDEO INFO",
            size_hint_y=None, height=dp(50),
            font_size=sp(14),
        )
        self.fetch_btn.bind(on_press=lambda *_: self.do_fetch())
        url_card.add_widget(self.fetch_btn)
        c.add_widget(url_card)

        # ── Info Card (hidden until fetch) ────────────────────────────────
        self.info_card = GlassCard(
            orientation="vertical",
            padding=PAD, spacing=dp(10),
            size_hint_y=None, height=dp(0), opacity=0,
            bg=list(SURF), radius=RAD,
        )
        self.thumb_img = Image(
            size_hint_y=None, height=dp(0),
            allow_stretch=True, keep_ratio=True,
            opacity=0,
        )
        self.info_card.add_widget(self.thumb_img)

        self.lbl_title = Label(
            text="", font_size=sp(16), bold=True, color=list(TEXT),
            size_hint_y=None, height=dp(0),
            halign="left", valign="top",
        )
        self.lbl_title.bind(
            size=lambda w, v: setattr(w, "text_size", (v[0], None)),
            texture_size=lambda w, v: setattr(w, "height", min(v[1], dp(66))),
        )
        self.info_card.add_widget(self.lbl_title)

        self.lbl_meta = Label(
            text="", font_size=sp(11), color=list(TEXTSUB),
            size_hint_y=None, height=dp(22), markup=True,
            halign="left", valign="top",
        )
        self.lbl_meta.bind(size=lambda w, v: setattr(w, "text_size", (v[0], None)))
        self.info_card.add_widget(self.lbl_meta)
        c.add_widget(self.info_card)

        # ── Format Selector ───────────────────────────────────────────────
        self.fmt_card = GlassCard(
            orientation="vertical",
            padding=PAD, spacing=dp(10),
            size_hint_y=None, height=dp(0), opacity=0,
            bg=list(SURF), radius=RAD,
        )
        fmt_hdr = BoxLayout(size_hint_y=None, height=dp(24), spacing=dp(6))
        fmt_hdr.add_widget(lbl("FORMAT", 10, TEXTSUB, bold=True, h=24))
        self.fmt_card.add_widget(fmt_hdr)

        mode_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        self._fmt_mode_btns = {
            "video_audio": self._mk_fmt_mode_btn("VIDEO + AUDIO", "video_audio"),
            "video_only":  self._mk_fmt_mode_btn("VIDEO",  "video_only"),
            "audio_only":  self._mk_fmt_mode_btn("AUDIO",  "audio_only"),
        }
        mode_row.add_widget(self._fmt_mode_btns["video_audio"])
        mode_row.add_widget(self._fmt_mode_btns["video_only"])
        mode_row.add_widget(self._fmt_mode_btns["audio_only"])
        self.fmt_card.add_widget(mode_row)
        self.fmt_card.add_widget(spacer(2))

        self.fmt_box = BoxLayout(
            orientation="vertical", spacing=dp(6),
            size_hint_y=None, height=dp(0),
        )
        self.fmt_card.add_widget(self.fmt_box)
        c.add_widget(self.fmt_card)

        # ── Download Button ───────────────────────────────────────────────
        self.dl_btn = Btn(
            text="DOWNLOAD NOW",
            size_hint_y=None, height=dp(0), opacity=0,
            font_size=sp(16),
        )
        self.dl_btn.bg = list(GREEN)
        self.dl_btn.bg_dn = [max(0, c - 0.15) for c in GREEN[:3]] + [1]
        self.dl_btn.color = (0.02, 0.05, 0.03, 1)
        self.dl_btn.bind(on_release=lambda *_: self.do_download())
        c.add_widget(self.dl_btn)

        # ── Progress Card ─────────────────────────────────────────────────
        self.prog_card = GlassCard(
            orientation="vertical",
            padding=PAD, spacing=dp(10),
            size_hint_y=None, height=dp(0), opacity=0,
            bg=list(SURF), radius=RAD,
        )

        # Header row
        prog_hdr = BoxLayout(size_hint_y=None, height=dp(22), spacing=dp(8))
        prog_hdr.add_widget(lbl("DOWNLOADING", 10, TEXTSUB, bold=True, h=22))
        self.prog_status = lbl("", 10, ACCENT, h=22, halign="right")
        prog_hdr.add_widget(self.prog_status)
        self.prog_card.add_widget(prog_hdr)

        # Ring progress (larger)
        self.ring = RingProgress(
            size_hint=(None, None),
            size=(dp(130), dp(130)),
        )
        ring_wrap = BoxLayout(size_hint_y=None, height=dp(140))
        ring_wrap.add_widget(Widget())
        ring_wrap.add_widget(self.ring)
        ring_wrap.add_widget(Widget())
        self.prog_card.add_widget(ring_wrap)

        # Progress bar
        self.pbar = PBar(size_hint_y=None, height=dp(5))
        self.prog_card.add_widget(self.pbar)

        # Speed / ETA / size row
        stats = BoxLayout(size_hint_y=None, height=dp(22), spacing=dp(16))
        self.spd_lbl  = lbl("", 11, TEXTSUB, h=22)
        self.stp_lbl  = lbl("", 11, MUTED, h=22, halign="center")
        self.eta_lbl  = lbl("", 11, TEXTSUB, h=22, halign="right")
        stats.add_widget(self.spd_lbl)
        stats.add_widget(self.stp_lbl)
        stats.add_widget(self.eta_lbl)
        self.prog_card.add_widget(stats)

        self._net_status_lbl = Label(
            text="[color=606075]NET:[/color] unknown   [color=606075]DNS retries:[/color] 0",
            markup=True,
            font_size=sp(10),
            color=list(TEXTSUB),
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(20),
        )
        self._net_status_lbl.bind(size=self._net_status_lbl.setter("text_size"))
        self.prog_card.add_widget(self._net_status_lbl)
        self._net_retry_lbl = Label(
            text="[color=606075]NET retry:[/color] 0/0",
            markup=True,
            font_size=sp(9),
            color=list(TEXTSUB),
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(16),
        )
        self._net_retry_lbl.bind(size=self._net_retry_lbl.setter("text_size"))
        self.prog_card.add_widget(self._net_retry_lbl)

        ctl = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
        self.pause_btn = OutlineBtn(text="PAUSE", font_size=sp(11))
        self.pause_btn.bind(on_release=lambda *_: self._toggle_pause_download())
        self.stop_btn = OutlineBtn(text="STOP", font_size=sp(11))
        self.stop_btn.bind(on_release=lambda *_: self._stop_download())
        ctl.add_widget(self.pause_btn)
        ctl.add_widget(self.stop_btn)
        self.prog_card.add_widget(ctl)
        self._refresh_download_controls()

        # Log label
        self.log_lbl = Label(
            text="", font_size=sp(10), color=list(MUTED),
            size_hint_y=None, markup=True,
            halign="left", valign="top",
        )
        self.log_lbl.bind(
            texture_size=lambda w, v: setattr(w, "height", v[1]),
            width=lambda w, v: setattr(w, "text_size", (v, None)),
        )
        self.prog_card.add_widget(self.log_lbl)

        # Done banner
        self.done_card = GlassCard(
            orientation="horizontal",
            padding=(dp(16), dp(14)),
            spacing=dp(14),
            size_hint_y=None, height=dp(0), opacity=0,
            bg=(0.035, 0.165, 0.100, 1),
            radius=RAD2,
        )
        done_icon = Label(
            text="OK", font_size=sp(14), bold=True, color=list(GREEN),
            size_hint=(None, None), size=(dp(36), dp(36)),
        )
        self.done_text = Label(
            text="", font_size=sp(12), bold=True, color=list(GREEN),
            halign="left", valign="middle",
        )
        self.done_text.bind(size=self.done_text.setter("text_size"))
        self.done_card.add_widget(done_icon)
        self.done_card.add_widget(self.done_text)
        self.prog_card.add_widget(self.done_card)

        c.add_widget(self.prog_card)
        c.add_widget(spacer(40))

    # ── History Tab ───────────────────────────────────────────────────────
    def _build_history_tab(self):
        c = self.content_col
        c.add_widget(spacer(4))
        hdr = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(8))
        hdr.add_widget(lbl("RECENT DOWNLOADS", 9, TEXTSUB, bold=True, h=22))
        clear_all_btn = OutlineBtn(text="CLEAR ALL", size_hint=(None, None),
                                   size=(dp(100), dp(30)), font_size=sp(10), radius=dp(8))
        clear_all_btn.bind(on_release=lambda *_: self._clear_history_list())
        hdr.add_widget(clear_all_btn)
        c.add_widget(hdr)
        c.add_widget(spacer(6))

        if not self._history:
            empty = GlassCard(
                orientation="vertical",
                padding=PAD, spacing=dp(10),
                size_hint_y=None, height=dp(120),
                bg=list(SURF),
            )
            empty.add_widget(lbl("HISTORY", 18, MUTED, bold=True, halign="center", h=40))
            empty.add_widget(lbl("No downloads yet", 15, MUTED,
                                  halign="center", h=28))
            empty.add_widget(lbl("Files you download will appear here",
                                  11, TEXTSUB, halign="center", h=22))
            c.add_widget(empty)
        else:
            for item in reversed(self._history):
                if isinstance(item, tuple) and len(item) >= 2:
                    item = {
                        "id": f"h{int(time.time()*1000)}",
                        "name": str(item[0]),
                        "type": str(item[1]),
                        "path": "",
                        "added_at": int(time.time()),
                    }
                name = str(item.get("name", "unknown"))
                ftype = str(item.get("type", "video"))
                path = str(item.get("path", ""))

                row = BoxLayout(size_hint_y=None, height=dp(64), spacing=dp(8))
                hitem = HistoryItem(name, ftype)
                hitem.size_hint_x = 1
                row.add_widget(hitem)

                actions = BoxLayout(orientation="vertical",
                                    size_hint=(None, 1), width=dp(102), spacing=dp(4))
                rm_btn = OutlineBtn(text="REMOVE", font_size=sp(10), radius=dp(7))
                rm_btn.bind(on_release=lambda *_,
                            hid=item.get("id"): self._remove_history_entry(hid))
                del_btn = OutlineBtn(text="DEL FILE", font_size=sp(10), radius=dp(7))
                del_btn.bind(on_release=lambda *_,
                             it=dict(item): self._delete_history_file(it))
                if not path:
                    del_btn.disabled = True
                actions.add_widget(rm_btn)
                actions.add_widget(del_btn)
                row.add_widget(actions)

                c.add_widget(row)
                c.add_widget(spacer(6))

        self._history_status_lbl = Label(
            text="", markup=True, font_size=sp(10), color=list(TEXTSUB),
            halign="left", valign="middle", size_hint_y=None, height=dp(24),
        )
        self._history_status_lbl.bind(size=self._history_status_lbl.setter("text_size"))
        c.add_widget(self._history_status_lbl)
        c.add_widget(lbl(
            "REMOVE keeps file and clears entry. DEL FILE deletes file and clears entry.",
            10, TEXTSUB, h=20
        ))

        c.add_widget(spacer(40))

    # ── Fetch Logic ───────────────────────────────────────────────────────
    # Settings helpers
    def _default_download_dir(self):
        if app_settings:
            try:
                return app_settings.default_download_dir()
            except Exception as e:
                wlog(f"default dir fallback: {e}")
        return _get_data_dir()

    def _normalize_history_entry(self, item):
        if not isinstance(item, dict):
            return None
        name = str(item.get("name") or "").strip()
        if not name:
            return None
        ftype = str(item.get("type") or "video").strip() or "video"
        path = str(item.get("path") or "").strip()
        hid = str(item.get("id") or f"h{int(time.time()*1000)}")
        try:
            added_at = int(item.get("added_at") or time.time())
        except Exception:
            added_at = int(time.time())
        return {
            "id": hid,
            "name": name,
            "type": ftype,
            "path": path,
            "added_at": added_at,
        }

    def _load_history_entries(self):
        if app_settings and hasattr(app_settings, "load_history"):
            try:
                raw = app_settings.load_history()
                out = []
                for it in raw:
                    if isinstance(it, (list, tuple)) and len(it) >= 2:
                        it = {
                            "id": f"h{int(time.time()*1000)}",
                            "name": str(it[0]),
                            "type": str(it[1]),
                            "path": "",
                            "added_at": int(time.time()),
                        }
                    n = self._normalize_history_entry(it)
                    if n:
                        out.append(n)
                return out
            except Exception as e:
                wlog(f"load history failed: {e}")
        return []

    def _save_history_entries(self):
        if app_settings and hasattr(app_settings, "save_history"):
            try:
                app_settings.save_history(self._history)
            except Exception as e:
                wlog(f"save history failed: {e}")

    def _append_history_entry(self, path, ftype):
        name = os.path.basename(path or "").strip() or "unknown"
        item = {
            "id": f"h{int(time.time()*1000)}",
            "name": name,
            "type": str(ftype or "video"),
            "path": str(path or ""),
            "added_at": int(time.time()),
        }
        self._history.append(item)
        try:
            keep = int(self._settings.get("history_limit", 120))
        except Exception:
            keep = 120
        keep = max(10, min(500, keep))
        if len(self._history) > keep:
            self._history = self._history[-keep:]
        self._save_history_entries()

    def _remove_history_entry(self, item_id):
        sid = str(item_id or "")
        self._history = [x for x in self._history if str(x.get("id", "")) != sid]
        self._save_history_entries()
        if self._cur_tab == "history":
            self._switch_tab("history")
            self._set_history_status("History item removed", "33ed9a")

    def _remove_history_entry_by_path(self, path):
        sp = os.path.abspath(str(path or ""))
        self._history = [
            x for x in self._history
            if os.path.abspath(str(x.get("path", ""))) != sp
        ]
        self._save_history_entries()

    def _delete_history_file(self, item):
        p = str((item or {}).get("path") or "").strip()
        if not p:
            self._set_history_status("History item has no file path", "ffd533")
            self._remove_history_entry((item or {}).get("id"))
            return
        try:
            if os.path.exists(p):
                os.remove(p)
                self._set_history_status("File deleted", "33ed9a")
            else:
                self._set_history_status("File already missing, history cleared", "ffd533")
            self._remove_history_entry((item or {}).get("id"))
        except Exception as e:
            self._set_history_status(f"Delete failed: {e}", "ff4488")

    def _tree_uri_to_path(self, uri):
        try:
            from jnius import autoclass
            DocumentsContract = autoclass("android.provider.DocumentsContract")
            doc_id = str(DocumentsContract.getTreeDocumentId(uri) or "")
            if not doc_id:
                return None
            if ":" in doc_id:
                vol, rel = doc_id.split(":", 1)
            else:
                vol, rel = doc_id, ""
            rel = rel.replace("/", os.sep).strip(os.sep)
            vol_l = vol.lower()
            if vol_l == "primary":
                try:
                    from android.storage import primary_external_storage_path
                    base = primary_external_storage_path()
                except Exception:
                    base = "/storage/emulated/0"
                return os.path.join(base, rel) if rel else base
            if vol_l == "home":
                try:
                    from android.storage import primary_external_storage_path
                    base = os.path.join(primary_external_storage_path(), "Documents")
                except Exception:
                    base = "/storage/emulated/0/Documents"
                return os.path.join(base, rel) if rel else base
            if vol:
                base = os.path.join("/storage", vol)
                return os.path.join(base, rel) if rel else base
        except Exception as e:
            wlog(f"tree uri parse failed: {e}")
            try:
                raw = str(uri.toString())
                dec = urllib.parse.unquote(raw)
                mark = "primary:"
                if mark in dec:
                    rel = dec.split(mark, 1)[1]
                    from android.storage import primary_external_storage_path
                    return os.path.join(primary_external_storage_path(), rel.replace("/", os.sep))
            except Exception:
                pass
        return None

    def _bind_folder_picker(self):
        if self._folder_picker_bound:
            return True
        try:
            from android import activity as android_activity
            android_activity.bind(on_activity_result=self._on_android_activity_result)
            self._folder_picker_bound = True
            return True
        except Exception as e:
            wlog(f"folder picker bind failed: {e}")
            return False

    def _open_inapp_folder_browser(self):
        if "FileChooserListView" not in globals():
            self._set_settings_status("In-app folder browser not available", "ffd533")
            return
        start = self._settings.get("download_dir") or self._default_download_dir()
        if not os.path.isdir(start):
            start = "/storage/emulated/0" if os.path.isdir("/storage/emulated/0") else os.path.expanduser("~")

        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        chooser = FileChooserListView(path=start, dirselect=True, multiselect=False)
        chooser.size_hint_y = 1
        box.add_widget(chooser)

        status = Label(
            text=f"Current: {start}",
            color=list(TEXTSUB), halign="left", valign="middle", size_hint_y=None, height=dp(26)
        )
        status.bind(size=status.setter("text_size"))
        box.add_widget(status)

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        mk_btn = OutlineBtn(text="NEW FOLDER", font_size=sp(11))
        pick_btn = Btn(text="SELECT THIS", font_size=sp(11))
        cancel_btn = OutlineBtn(text="CANCEL", font_size=sp(11))
        row.add_widget(mk_btn)
        row.add_widget(pick_btn)
        row.add_widget(cancel_btn)
        box.add_widget(row)

        pop = Popup(
            title="Choose Download Folder",
            content=box,
            size_hint=(0.96, 0.90),
            auto_dismiss=False,
        )

        def _refresh_status(*_):
            cur = chooser.path
            sel = chooser.selection[0] if chooser.selection else ""
            if sel and os.path.isdir(sel):
                cur = sel
            status.text = f"Current: {cur}"

        chooser.bind(path=lambda *_: _refresh_status(), selection=lambda *_: _refresh_status())
        _refresh_status()

        def _create_folder(*_):
            inner = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
            name_in = TextInput(
                hint_text="Folder name", multiline=False,
                background_color=(0.102, 0.102, 0.137, 1),
                foreground_color=list(TEXT), hint_text_color=list(MUTED),
                cursor_color=list(ACCENT), font_size=sp(12),
                size_hint_y=None, height=dp(42), padding=[dp(10), dp(12)],
            )
            inner.add_widget(name_in)
            info = Label(text="", markup=True, color=list(TEXTSUB), size_hint_y=None, height=dp(22))
            info.bind(size=info.setter("text_size"))
            inner.add_widget(info)
            r2 = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
            ok = Btn(text="CREATE", font_size=sp(11))
            cc = OutlineBtn(text="CANCEL", font_size=sp(11))
            r2.add_widget(ok); r2.add_widget(cc)
            inner.add_widget(r2)
            p2 = Popup(title="Create Folder", content=inner, size_hint=(0.82, None),
                       height=dp(190), auto_dismiss=False)

            def _do_create(*__):
                nm = (name_in.text or "").strip()
                if not nm:
                    info.text = "[color=ff4488]Enter folder name[/color]"
                    return
                base = chooser.path
                target = os.path.join(base, nm)
                try:
                    os.makedirs(target, exist_ok=True)
                    chooser.path = target
                    chooser._update_files()
                    info.text = "[color=33ed9a]Created[/color]"
                    Clock.schedule_once(lambda dt: p2.dismiss(), 0.2)
                except Exception as e:
                    info.text = f"[color=ff4488]{e}[/color]"

            ok.bind(on_release=_do_create)
            cc.bind(on_release=lambda *_: p2.dismiss())
            p2.open()

        def _select_now(*_):
            picked = chooser.selection[0] if chooser.selection else chooser.path
            picked = str(picked or "").strip()
            if not picked:
                self._set_settings_status("No folder selected", "ffd533")
                return
            if not os.path.isdir(picked):
                picked = os.path.dirname(picked)
            if self._settings_dir_input is not None:
                self._settings_dir_input.text = picked
            self._save_download_location()
            pop.dismiss()

        mk_btn.bind(on_release=_create_folder)
        pick_btn.bind(on_release=_select_now)
        cancel_btn.bind(on_release=lambda *_: pop.dismiss())
        pop.open()

    def _pick_download_folder(self):
        if not self._bind_folder_picker():
            self._set_settings_status("Folder picker not available on this device", "ffd533")
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Intent = autoclass("android.content.Intent")
            activity = PythonActivity.mActivity
            intent = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE)
            flags = (
                Intent.FLAG_GRANT_READ_URI_PERMISSION
                | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION
                | Intent.FLAG_GRANT_PREFIX_URI_PERMISSION
            )
            intent.addFlags(flags)
            activity.startActivityForResult(intent, int(self._folder_picker_req))
            self._set_settings_status("Select a folder in file manager", "606075")
        except Exception as e:
            wlog(f"folder picker open failed: {e}")
            self._set_settings_status(f"Folder picker failed: {e}", "ff4488")

    def _on_android_activity_result(self, request_code, result_code, intent):
        if int(request_code) != int(self._folder_picker_req):
            return
        Clock.schedule_once(
            lambda dt, rc=request_code, rs=result_code, it=intent:
            self._handle_android_activity_result(rc, rs, it),
            0,
        )

    def _handle_android_activity_result(self, request_code, result_code, intent):
        try:
            from jnius import autoclass
            Activity = autoclass("android.app.Activity")
            Intent = autoclass("android.content.Intent")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            if int(result_code) != int(Activity.RESULT_OK) or intent is None:
                self._set_settings_status("Folder selection canceled", "ffd533")
                return
            uri = intent.getData()
            if uri is None:
                self._set_settings_status("No folder selected", "ffd533")
                return
            try:
                flags = intent.getFlags() & (
                    Intent.FLAG_GRANT_READ_URI_PERMISSION
                    | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                )
                PythonActivity.mActivity.getContentResolver().takePersistableUriPermission(uri, flags)
            except Exception as e:
                wlog(f"persist uri permission failed: {e}")
            path = self._tree_uri_to_path(uri)
            if not path:
                self._set_settings_status(
                    "Folder URI not mappable. Using in-app browser fallback.",
                    "ffd533",
                )
                Clock.schedule_once(lambda dt: self._open_inapp_folder_browser(), 0.2)
                return
            os.makedirs(path, exist_ok=True)
            if self._settings_dir_input is not None:
                self._settings_dir_input.text = path
            self._save_download_location()
        except Exception as e:
            wlog(f"activity result failed: {e}")
            self._set_settings_status(f"Folder selection failed: {e}", "ff4488")

    def _save_settings_state(self):
        try:
            if app_settings:
                self._settings = app_settings.save_settings(self._settings)
        except Exception as e:
            wlog(f"save settings state failed: {e}")

    def _set_settings_status(self, text, color="606075"):
        def _apply(*_):
            if self.settings_status_lbl:
                self.settings_status_lbl.text = f"[color={color}]{text}[/color]"
        if threading.current_thread() is threading.main_thread():
            _apply()
        else:
            Clock.schedule_once(_apply, 0)

    def _set_history_status(self, text, color="606075"):
        def _apply(*_):
            if self._history_status_lbl:
                self._history_status_lbl.text = f"[color={color}]{text}[/color]"
        if threading.current_thread() is threading.main_thread():
            _apply()
        else:
            Clock.schedule_once(_apply, 0)

    def _human_size(self, n):
        try:
            n = float(max(0, int(n or 0)))
        except Exception:
            return "0B"
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if n < 1024.0 or unit == "TB":
                if unit == "B":
                    return f"{int(n)}{unit}"
                return f"{n:.1f}{unit}"
            n /= 1024.0
        return "0B"

    def _safe_file_size(self, path):
        try:
            return os.path.getsize(path) if path and os.path.exists(path) else 0
        except Exception:
            return 0

    def _safe_dir_size(self, path):
        if not path or not os.path.isdir(path):
            return 0
        total = 0
        try:
            for root, _, files in os.walk(path):
                for name in files:
                    fp = os.path.join(root, name)
                    try:
                        total += os.path.getsize(fp)
                    except Exception:
                        pass
        except Exception:
            pass
        return total

    def _open_url(self, url):
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            activity = PythonActivity.mActivity
            intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
            activity.startActivity(intent)
            return True
        except Exception:
            try:
                return bool(webbrowser.open(url))
            except Exception as e:
                wlog(f"open url failed: {e}")
                return False

    def _save_download_location(self):
        if not self._settings_dir_input:
            return
        raw = (self._settings_dir_input.text or "").strip()
        target = raw or self._default_download_dir()
        target = os.path.abspath(os.path.expanduser(target))
        try:
            os.makedirs(target, exist_ok=True)
            if not os.path.isdir(target):
                raise OSError("Selected path is not a folder")
            if app_settings:
                saved = app_settings.set_download_dir(target)
                self._settings = app_settings.load_settings()
            else:
                saved = target
                self._settings["download_dir"] = saved
            self._settings["download_dir"] = saved
            self._settings_dir_input.text = saved
            self._set_settings_status(f"Saved download location: {saved}", "33ed9a")
            self._refresh_storage_stats()
        except Exception as e:
            wlog(f"save settings failed: {e}")
            self._set_settings_status(f"Save failed: {e}", "ff4488")

    def _reset_download_location(self):
        if not self._settings_dir_input:
            return
        self._settings_dir_input.text = self._default_download_dir()
        self._save_download_location()

    def _toggle_notifications_setting(self):
        enabled = not bool(self._settings.get("notifications", True))
        self._settings["notifications"] = enabled
        try:
            if app_settings and hasattr(app_settings, "set_notifications"):
                app_settings.set_notifications(enabled)
            elif app_settings:
                app_settings.save_settings(self._settings)
        except Exception as e:
            wlog(f"save notification setting failed: {e}")
        if enabled:
            self._ensure_notification_permission(show_ui=True)
        self._refresh_notifications_button()
        self._set_settings_status(
            f"Notifications {'enabled' if enabled else 'disabled'}",
            "33ed9a" if enabled else "ffd533",
        )

    def _refresh_notifications_button(self):
        if not self._notif_btn:
            return
        on = bool(self._settings.get("notifications", True))
        self._notif_btn.text = "Notifications: ON" if on else "Notifications: OFF"
        self._notif_btn.bg = list(ACCENT if on else CARD2)
        self._notif_btn.bg_dn = list(ACCT_DK if on else BORDER)

    def _toggle_auto_cleanup_setting(self):
        enabled = not bool(self._settings.get("auto_cleanup_cache", True))
        self._settings["auto_cleanup_cache"] = enabled
        if app_settings and hasattr(app_settings, "set_auto_cleanup_cache"):
            try:
                app_settings.set_auto_cleanup_cache(enabled)
            except Exception as e:
                wlog(f"set auto cleanup failed: {e}")
        else:
            self._save_settings_state()
        self._refresh_cache_toggle_button()
        self._set_settings_status(
            f"Auto cache cleanup {'enabled' if enabled else 'disabled'}",
            "33ed9a" if enabled else "ffd533",
        )

    def _refresh_cache_toggle_button(self):
        if not self._cache_toggle_btn:
            return
        on = bool(self._settings.get("auto_cleanup_cache", True))
        self._cache_toggle_btn.text = "Auto Cleanup: ON" if on else "Auto Cleanup: OFF"
        self._cache_toggle_btn.bg = list(ACCENT if on else CARD2)
        self._cache_toggle_btn.bg_dn = list(ACCT_DK if on else BORDER)

    def _toggle_resume_cache_setting(self):
        enabled = not bool(self._settings.get("resume_downloads", False))
        self._settings["resume_downloads"] = enabled
        if app_settings and hasattr(app_settings, "set_resume_downloads"):
            try:
                app_settings.set_resume_downloads(enabled)
            except Exception as e:
                wlog(f"set resume downloads failed: {e}")
        else:
            self._save_settings_state()
        self._refresh_resume_cache_button()
        self._set_settings_status(
            f"Resume cache {'enabled' if enabled else 'disabled'}",
            "33ed9a" if enabled else "ffd533",
        )

    def _refresh_resume_cache_button(self):
        if not self._resume_cache_btn:
            return
        on = bool(self._settings.get("resume_downloads", False))
        self._resume_cache_btn.text = "Resume Cache: ON" if on else "Resume Cache: OFF"
        self._resume_cache_btn.bg = list(ACCENT if on else CARD2)
        self._resume_cache_btn.bg_dn = list(ACCT_DK if on else BORDER)

    def _toggle_background_awake_setting(self):
        enabled = not bool(self._settings.get("background_keep_awake", True))
        self._settings["background_keep_awake"] = enabled
        if app_settings and hasattr(app_settings, "set_background_keep_awake"):
            try:
                app_settings.set_background_keep_awake(enabled)
            except Exception as e:
                wlog(f"set background keep awake failed: {e}")
        else:
            self._save_settings_state()
        self._refresh_background_awake_button()
        self._set_settings_status(
            f"Background keep-awake {'enabled' if enabled else 'disabled'}",
            "33ed9a" if enabled else "ffd533",
        )

    def _refresh_background_awake_button(self):
        if not self._bg_awake_btn:
            return
        on = bool(self._settings.get("background_keep_awake", True))
        self._bg_awake_btn.text = "Background Keep-Awake: ON" if on else "Background Keep-Awake: OFF"
        self._bg_awake_btn.bg = list(ACCENT if on else CARD2)
        self._bg_awake_btn.bg_dn = list(ACCT_DK if on else BORDER)

    def _save_performance_settings(self):
        try:
            age_h = int(float((self._cache_age_input.text or "").strip() or 12))
            age_h = max(1, min(168, age_h))
        except Exception:
            age_h = int(self._settings.get("cache_max_age_hours", 12))
        try:
            log_mb = int(float((self._log_limit_input.text or "").strip() or 2))
            log_mb = max(1, min(20, log_mb))
        except Exception:
            log_mb = int(self._settings.get("max_crash_log_mb", 2))
        try:
            hist_limit = int(float((self._history_limit_input.text or "").strip() or 120))
            hist_limit = max(10, min(500, hist_limit))
        except Exception:
            hist_limit = int(self._settings.get("history_limit", 120))

        self._settings["cache_max_age_hours"] = age_h
        self._settings["max_crash_log_mb"] = log_mb
        self._settings["history_limit"] = hist_limit
        if app_settings:
            try:
                if hasattr(app_settings, "set_cache_max_age_hours"):
                    app_settings.set_cache_max_age_hours(age_h)
                if hasattr(app_settings, "set_max_crash_log_mb"):
                    app_settings.set_max_crash_log_mb(log_mb)
                if hasattr(app_settings, "set_history_limit"):
                    app_settings.set_history_limit(hist_limit)
                self._settings = app_settings.load_settings()
            except Exception as e:
                wlog(f"save perf settings failed: {e}")
        else:
            self._save_settings_state()

        self._cache_age_input.text = str(age_h)
        self._log_limit_input.text = str(log_mb)
        self._history_limit_input.text = str(hist_limit)
        self._set_settings_status("Performance settings saved", "33ed9a")

    def _import_cookie_file(self):
        """Let the user pick a cookies.txt file from the filesystem."""
        try:
            from android.storage import primary_external_storage_path
            start = os.path.join(primary_external_storage_path(), "Download")
        except ImportError:
            start = os.path.expanduser("~")

        self._cookie_picker_shown = False
        popup = None

        chooser = FileChooserListView(
            path=start, filters=["*.txt"],
            dirselect=False, multiselect=False,
        )

        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(12))
        box.add_widget(lbl("Select cookies.txt", 12, TEXT, bold=True, h=26))
        box.add_widget(chooser)

        row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(10))

        def _cancel(*_):
            popup.dismiss()

        def _pick(*_):
            sel = chooser.selection
            if not sel:
                return
            path = sel[0]
            popup.dismiss()
            self._install_cookie_file(path)

        cancel_btn = OutlineBtn(text="Cancel", size_hint=(0.3, 1), font_size=sp(12))
        cancel_btn.bind(on_release=_cancel)
        pick_btn = Btn(text="Install", size_hint=(0.7, 1), font_size=sp(12))
        pick_btn.bind(on_release=_pick)
        row.add_widget(cancel_btn)
        row.add_widget(pick_btn)
        box.add_widget(row)

        popup = Popup(
            title="Cookie File", title_color=list(TEXT),
            title_size=sp(14),
            content=box,
            size_hint=(0.9, 0.7),
            background_color=list(CARD),
            separator_color=list(BORDER),
        )
        popup.open()

    def _install_cookie_file(self, src_path):
        """Copy a cookies.txt file into the app's data directory."""
        try:
            base = app_settings.get_data_dir()
            os.makedirs(base, exist_ok=True)
            fname = os.path.basename(src_path)
            dest = os.path.join(base, fname)
            import shutil
            shutil.copy2(src_path, dest)
            size = os.path.getsize(dest)
            wlog(f"Cookie installed: {fname} ({size} bytes)")
            lbl_ref = getattr(self, "_cookie_status_lbl", None)
            if lbl_ref:
                lbl_ref.text = f"[color=33ed9a]{fname} installed ({size // 1024} KB)[/color]"
        except Exception as e:
            wlog(f"Cookie install failed: {e}")
            lbl_ref = getattr(self, "_cookie_status_lbl", None)
            if lbl_ref:
                lbl_ref.text = f"[color=ff4488]Failed: {e}[/color]"

    def _show_cookie_help(self):
        """Show a popup explaining how to export browser cookies."""
        box = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(18))
        help_text = (
            "[b]How to export cookies:[/b]\n\n"
            "1. Install the [b]Get cookies.txt[/b] browser extension\n"
            "   (Chrome / Firefox / Edge)\n\n"
            "2. Log in to the platform (Instagram, Facebook, etc.)\n\n"
            "3. Click the extension icon → Export\n"
            "   This downloads a cookies.txt file\n\n"
            "4. Use IMPORT COOKIE FILE to install it\n\n"
            "Files are stored in:\n"
            "[color=00ccf2]Download/videodownloader/[/color]\n\n"
            "Or copy manually:\n"
            "[color=00ccf2]platform_cookies.txt[/color]"
        )
        box.add_widget(Label(
            text=help_text, markup=True, color=list(TEXT),
            font_size=sp(11), halign="left",
        ))
        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        ok_btn = Btn(text="Got it", font_size=sp(12))
        ok_btn.bind(on_release=lambda *_: popup.dismiss())
        row.add_widget(ok_btn)
        box.add_widget(row)

        popup = Popup(
            title="Cookie Setup", title_color=list(TEXT),
            title_size=sp(14),
            content=box,
            size_hint=(0.9, 0.6),
            background_color=list(CARD),
            separator_color=list(BORDER),
        )
        popup.open()

    def _clear_crash_log(self):
        try:
            p = _logpath()
            if os.path.exists(p):
                open(p, "w", encoding="utf-8").close()
            self._set_settings_status("Crash log cleared", "33ed9a")
        except Exception as e:
            self._set_settings_status(f"Crash log clear failed: {e}", "ff4488")
        self._refresh_storage_stats()

    def _clear_temp_cache_now(self):
        if getattr(self, "dl_btn", None) is not None and self.dl_btn.disabled:
            self._set_settings_status(
                "Download in progress. Try cache cleanup after it finishes.",
                "ffd533",
            )
            return
        if not downloader or not hasattr(downloader, "cleanup_temp_cache"):
            self._set_settings_status("Cache cleanup is not available", "ffd533")
            return
        try:
            out = downloader.cleanup_temp_cache(max_age_hours=0)
            rd = out.get("removed_dirs", 0)
            rb = out.get("removed_bytes", 0)
            self._set_settings_status(
                f"Removed {rd} temp dirs ({self._human_size(rb)})",
                "33ed9a",
            )
        except Exception as e:
            self._set_settings_status(f"Cache cleanup failed: {e}", "ff4488")
        self._refresh_storage_stats()

    def _refresh_storage_stats(self):
        if not self._storage_lbl:
            return
        self._storage_lbl.text = "[color=606075]Calculating storage...[/color]"

        def worker():
            dl_path = self._settings.get("download_dir") or self._default_download_dir()
            downloads_bytes = self._safe_dir_size(dl_path)
            log_bytes = self._safe_file_size(_logpath())
            settings_bytes = 0
            if app_settings and hasattr(app_settings, "settings_path"):
                settings_bytes = self._safe_file_size(app_settings.settings_path())
            temp_dirs = 0
            cache_bytes = 0
            if downloader and hasattr(downloader, "get_temp_cache_stats"):
                try:
                    st = downloader.get_temp_cache_stats()
                    temp_dirs = int(st.get("temp_dirs", 0))
                    cache_bytes = int(st.get("bytes", 0))
                except Exception:
                    pass
            txt = (
                f"[color=606075]Downloads:[/color] {self._human_size(downloads_bytes)}\n"
                f"[color=606075]Temp cache:[/color] {self._human_size(cache_bytes)} ({temp_dirs} dirs)\n"
                f"[color=606075]Crash log:[/color] {self._human_size(log_bytes)}\n"
                f"[color=606075]Settings file:[/color] {self._human_size(settings_bytes)}"
            )
            Clock.schedule_once(lambda dt: setattr(self._storage_lbl, "text", txt))

        threading.Thread(target=worker, daemon=True).start()

    def _read_proc_rss_mb(self):
        try:
            with open("/proc/self/status", "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        parts = line.split()
                        if len(parts) >= 2:
                            kb = int(parts[1])
                            return kb / 1024.0
        except Exception:
            pass
        return None

    def _android_dir_paths(self):
        out = {}
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity = PythonActivity.mActivity
            files_dir = activity.getFilesDir().getAbsolutePath()
            cache_dir = activity.getCacheDir().getAbsolutePath()
            out["files_dir"] = files_dir
            out["cache_dir"] = cache_dir
            out["app_data_dir"] = os.path.dirname(files_dir)
            try:
                out["code_cache_dir"] = activity.getCodeCacheDir().getAbsolutePath()
            except Exception:
                pass
        except Exception:
            pass
        return out

    def _run_full_diagnostics_scan(self):
        if not self._diag_detail_lbl:
            return
        self._diag_detail_lbl.text = "[color=606075]Scanning app storage...[/color]"

        def worker():
            dirs = self._android_dir_paths()
            lines = []
            if dirs:
                app_data = dirs.get("app_data_dir", "")
                files_dir = dirs.get("files_dir", "")
                cache_dir = dirs.get("cache_dir", "")
                code_cache = dirs.get("code_cache_dir", "")
                if app_data:
                    lines.append(
                        f"[color=606075]App data dir:[/color] {self._human_size(self._safe_dir_size(app_data))}"
                    )
                if files_dir:
                    lines.append(
                        f"[color=606075]Files dir:[/color] {self._human_size(self._safe_dir_size(files_dir))}"
                    )
                if cache_dir:
                    lines.append(
                        f"[color=606075]Cache dir:[/color] {self._human_size(self._safe_dir_size(cache_dir))}"
                    )
                if code_cache:
                    lines.append(
                        f"[color=606075]Code cache:[/color] {self._human_size(self._safe_dir_size(code_cache))}"
                    )
            else:
                lines.append("[color=ffd533]Internal Android dirs not available[/color]")

            dl_path = self._settings.get("download_dir") or self._default_download_dir()
            lines.append(
                f"[color=606075]Download folder:[/color] {self._human_size(self._safe_dir_size(dl_path))}"
            )

            Clock.schedule_once(
                lambda dt: setattr(self._diag_detail_lbl, "text", "\n".join(lines))
            )

        threading.Thread(target=worker, daemon=True).start()

    def _diag_tick(self, _dt=0):
        if not self._diag_lbl:
            return
        rss = self._read_proc_rss_mb()
        rss_txt = f"{rss:.1f} MB" if rss is not None else "N/A"
        th_count = threading.active_count()
        cache_bytes = 0
        temp_dirs = 0
        if downloader and hasattr(downloader, "get_temp_cache_stats"):
            try:
                st = downloader.get_temp_cache_stats()
                cache_bytes = int(st.get("bytes", 0))
                temp_dirs = int(st.get("temp_dirs", 0))
            except Exception:
                pass
        self._diag_cache_hist.append(cache_bytes)
        if len(self._diag_cache_hist) > 16:
            self._diag_cache_hist = self._diag_cache_hist[-16:]
        delta = 0
        if len(self._diag_cache_hist) >= 2:
            delta = self._diag_cache_hist[-1] - self._diag_cache_hist[-2]
        if delta > 0:
            trend = f"[color=ff8833]up +{self._human_size(delta)}[/color]"
        elif delta < 0:
            trend = f"[color=33ed9a]down -{self._human_size(abs(delta))}[/color]"
        else:
            trend = "[color=606075]stable[/color]"
        self._diag_lbl.text = (
            f"[color=606075]Threads:[/color] {th_count}   "
            f"[color=606075]RAM (RSS):[/color] {rss_txt}\n"
            f"[color=606075]Temp cache:[/color] {self._human_size(cache_bytes)} ({temp_dirs} dirs)   "
            f"[color=606075]Trend:[/color] {trend}"
        )

    def _start_diagnostics_updates(self):
        self._stop_diagnostics_updates()
        if not self._settings.get("diagnostics_live", True):
            return
        self._diag_cache_hist = []
        self._diag_tick(0)
        self._diag_event = Clock.schedule_interval(self._diag_tick, 3.0)

    def _stop_diagnostics_updates(self):
        if self._diag_event is not None:
            try:
                self._diag_event.cancel()
            except Exception:
                pass
            self._diag_event = None

    def _toggle_diagnostics_live(self):
        enabled = not bool(self._settings.get("diagnostics_live", True))
        self._settings["diagnostics_live"] = enabled
        try:
            if app_settings and hasattr(app_settings, "set_diagnostics_live"):
                app_settings.set_diagnostics_live(enabled)
            else:
                self._save_settings_state()
        except Exception as e:
            wlog(f"save diagnostics setting failed: {e}")
        self._refresh_diag_live_button()
        if enabled:
            self._start_diagnostics_updates()
        else:
            self._stop_diagnostics_updates()
        self._set_settings_status(
            f"Live diagnostics {'enabled' if enabled else 'disabled'}",
            "33ed9a" if enabled else "ffd533",
        )

    def _refresh_diag_live_button(self):
        if not self._diag_live_btn:
            return
        on = bool(self._settings.get("diagnostics_live", True))
        self._diag_live_btn.text = "Live Diagnostics: ON" if on else "Live Diagnostics: OFF"
        self._diag_live_btn.bg = list(ACCENT if on else CARD2)
        self._diag_live_btn.bg_dn = list(ACCT_DK if on else BORDER)

    def _refresh_theme_buttons(self):
        mode = str(self._settings.get("theme_mode", "dark")).lower()
        if self._theme_dark_btn:
            is_on = mode == "dark"
            self._theme_dark_btn.bg = list(ACCENT if is_on else CARD2)
            self._theme_dark_btn.bg_dn = list(ACCT_DK if is_on else BORDER)
        if self._theme_light_btn:
            is_on = mode == "light"
            self._theme_light_btn.bg = list(ACCENT if is_on else CARD2)
            self._theme_light_btn.bg_dn = list(ACCT_DK if is_on else BORDER)

    def _set_theme_mode(self, mode):
        m = str(mode or "").strip().lower()
        if m not in ("dark", "light"):
            return
        if getattr(self, "dl_btn", None) is not None and self.dl_btn.disabled:
            self._set_settings_status("Theme change is disabled while downloading", "ffd533")
            return
        if self._settings.get("theme_mode", "dark") == m:
            self._refresh_theme_buttons()
            return
        self._settings["theme_mode"] = m
        self._settings["theme"] = "Neon Dusk" if m == "dark" else "Light Breeze"
        try:
            if app_settings:
                self._settings = app_settings.save_settings(self._settings)
        except Exception as e:
            wlog(f"save theme failed: {e}")
        _apply_theme_globals(m)
        Window.clearcolor = BG
        self._rebuild_ui_for_theme()
        self._set_settings_status(f"Theme switched to {m}", "33ed9a")

    def _clear_history_list(self):
        self._history = []
        self._save_history_entries()
        self._set_settings_status("History cleared", "33ed9a")
        if self._cur_tab == "history":
            self._switch_tab("history")
            self._set_history_status("History cleared", "33ed9a")

    def _backup_settings_history(self):
        if not app_settings or not hasattr(app_settings, "create_backup"):
            self._set_settings_status("Backup is not available", "ffd533")
            return
        try:
            path = app_settings.create_backup(
                settings_data=self._settings,
                history_data=self._history,
            )
            self._set_settings_status(f"Backup created: {os.path.basename(path)}", "33ed9a")
        except Exception as e:
            self._set_settings_status(f"Backup failed: {e}", "ff4488")

    def _restore_latest_backup(self):
        if not app_settings or not hasattr(app_settings, "list_backups"):
            self._set_settings_status("Restore is not available", "ffd533")
            return
        try:
            lst = app_settings.list_backups(limit=1)
            if not lst:
                self._set_settings_status("No backup found", "ffd533")
                return
            p = lst[0].get("path")
            out = app_settings.restore_backup(p) if hasattr(app_settings, "restore_backup") else None
            if out and isinstance(out, dict):
                self._settings = out.get("settings", self._settings)
                self._history = out.get("history", self._history)
            else:
                self._settings = app_settings.load_settings()
                self._history = self._load_history_entries()
            new_mode = str(self._settings.get("theme_mode", "dark")).lower()
            _apply_theme_globals(new_mode)
            Window.clearcolor = BG
            if self._settings_dir_input:
                self._settings_dir_input.text = self._settings.get("download_dir", self._default_download_dir())
            if self._cache_age_input:
                self._cache_age_input.text = str(self._settings.get("cache_max_age_hours", 12))
            if self._log_limit_input:
                self._log_limit_input.text = str(self._settings.get("max_crash_log_mb", 2))
            if self._history_limit_input:
                self._history_limit_input.text = str(self._settings.get("history_limit", 120))
            self._refresh_notifications_button()
            self._refresh_cache_toggle_button()
            self._refresh_resume_cache_button()
            self._refresh_background_awake_button()
            self._refresh_diag_live_button()
            self._refresh_theme_buttons()
            self._refresh_storage_stats()
            self._run_full_diagnostics_scan()
            if self._settings.get("diagnostics_live", True):
                self._start_diagnostics_updates()
            else:
                self._stop_diagnostics_updates()
            self._rebuild_ui_for_theme()
            self._set_settings_status(f"Restored backup: {os.path.basename(p)}", "33ed9a")
        except Exception as e:
            self._set_settings_status(f"Restore failed: {e}", "ff4488")

    def _reset_all_settings(self):
        try:
            if app_settings:
                self._settings = app_settings.save_settings({})
            else:
                self._settings = {
                    "download_dir": self._default_download_dir(),
                    "notifications": True,
                    "resume_downloads": False,
                    "background_keep_awake": True,
                    "auto_cleanup_cache": True,
                    "cache_max_age_hours": 12,
                    "max_crash_log_mb": 2,
                    "history_limit": 120,
                    "diagnostics_live": True,
                    "theme_mode": "dark",
                    "theme": "Neon Dusk",
                }
            if self._settings_dir_input:
                self._settings_dir_input.text = self._settings.get("download_dir", "")
            if self._cache_age_input:
                self._cache_age_input.text = str(self._settings.get("cache_max_age_hours", 12))
            if self._log_limit_input:
                self._log_limit_input.text = str(self._settings.get("max_crash_log_mb", 2))
            if self._history_limit_input:
                self._history_limit_input.text = str(self._settings.get("history_limit", 120))
            _apply_theme_globals(self._settings.get("theme_mode", "dark"))
            Window.clearcolor = BG
            self._refresh_notifications_button()
            self._refresh_cache_toggle_button()
            self._refresh_resume_cache_button()
            self._refresh_background_awake_button()
            self._refresh_diag_live_button()
            self._refresh_theme_buttons()
            self._refresh_storage_stats()
            if self._settings.get("diagnostics_live", True):
                self._start_diagnostics_updates()
            else:
                self._stop_diagnostics_updates()
            self._rebuild_ui_for_theme()
            self._set_settings_status("Settings reset to defaults", "33ed9a")
        except Exception as e:
            self._set_settings_status(f"Reset failed: {e}", "ff4488")

    def _build_settings_tab(self):
        c = self.content_col
        c.add_widget(spacer(6))

        # Section header
        settings_hdr = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(8))
        settings_hdr.add_widget(lbl("SET", 11, ACCENT, bold=True, h=30))
        settings_hdr.add_widget(lbl("SETTINGS", 10, TEXTSUB, bold=True, h=30))
        c.add_widget(settings_hdr)
        c.add_widget(spacer(6))

        loc_card = GlassCard(
            orientation="vertical",
            padding=PAD, spacing=dp(10),
            size_hint_y=None, height=dp(306),
            bg=list(SURF), radius=RAD,
        )
        loc_card.add_widget(lbl("Download Location", 14, TEXT, bold=True, h=30))

        self._settings_dir_input = TextInput(
            text=self._settings.get("download_dir") or self._default_download_dir(),
            multiline=False,
            size_hint_y=None, height=dp(48),
            background_color=list(CARD),
            foreground_color=list(TEXT),
            hint_text_color=list(MUTED),
            cursor_color=list(ACCENT),
            font_size=sp(12),
            padding=[dp(14), dp(14)],
        )
        loc_card.add_widget(self._settings_dir_input)

        row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        save_btn = Btn(text="APPLY PATH", font_size=sp(12))
        save_btn.bind(on_release=lambda *_: self._save_download_location())
        reset_btn = OutlineBtn(text="RESET DEFAULT", font_size=sp(12))
        reset_btn.bind(on_release=lambda *_: self._reset_download_location())
        row.add_widget(save_btn)
        row.add_widget(reset_btn)
        loc_card.add_widget(row)

        row_pick = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        pick_btn = OutlineBtn(text="SELECT FOLDER", font_size=sp(11))
        pick_btn.bind(on_release=lambda *_: self._pick_download_folder())
        inapp_btn = OutlineBtn(text="BROWSE IN-APP", font_size=sp(11))
        inapp_btn.bind(on_release=lambda *_: self._open_inapp_folder_browser())
        mk_btn = OutlineBtn(text="CREATE / VALIDATE", font_size=sp(11))
        mk_btn.bind(on_release=lambda *_: self._save_download_location())
        row_pick.add_widget(pick_btn)
        row_pick.add_widget(inapp_btn)
        row_pick.add_widget(mk_btn)
        loc_card.add_widget(row_pick)

        loc_card.add_widget(
            lbl("Use SELECT FOLDER for reliable path from file manager", 10, TEXTSUB, h=22)
        )
        c.add_widget(loc_card)

        notif_card = GlassCard(
            orientation="vertical",
            padding=PAD, spacing=dp(10),
            size_hint_y=None, height=dp(170),
            bg=list(SURF), radius=RAD,
        )
        notif_card.add_widget(lbl("Background Notifications", 14, TEXT, bold=True, h=30))
        self._notif_btn = Btn(size_hint_y=None, height=dp(44), font_size=sp(12))
        self._notif_btn.bind(on_release=lambda *_: self._toggle_notifications_setting())
        notif_card.add_widget(self._notif_btn)

        ask_btn = OutlineBtn(text="REQUEST NOTIFICATION PERMISSION", font_size=sp(11))
        ask_btn.bind(on_release=lambda *_: self._ensure_notification_permission(show_ui=True))
        notif_card.add_widget(ask_btn)
        c.add_widget(notif_card)

        perf_card = GlassCard(
            orientation="vertical",
            padding=PAD, spacing=dp(10),
            size_hint_y=None, height=dp(500),
            bg=list(SURF), radius=RAD,
        )
        perf_card.add_widget(lbl("Storage & Performance", 14, TEXT, bold=True, h=30))

        self._cache_toggle_btn = Btn(size_hint_y=None, height=dp(42), font_size=sp(12))
        self._cache_toggle_btn.bind(on_release=lambda *_: self._toggle_auto_cleanup_setting())
        perf_card.add_widget(self._cache_toggle_btn)

        self._resume_cache_btn = Btn(size_hint_y=None, height=dp(42), font_size=sp(12))
        self._resume_cache_btn.bind(on_release=lambda *_: self._toggle_resume_cache_setting())
        perf_card.add_widget(self._resume_cache_btn)

        self._bg_awake_btn = Btn(size_hint_y=None, height=dp(42), font_size=sp(12))
        self._bg_awake_btn.bind(on_release=lambda *_: self._toggle_background_awake_setting())
        perf_card.add_widget(self._bg_awake_btn)

        inp_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        self._cache_age_input = TextInput(
            text=str(self._settings.get("cache_max_age_hours", 12)),
            multiline=False,
            input_filter="int",
            hint_text="Cache age (hours)",
            background_color=list(CARD),
            foreground_color=list(TEXT),
            hint_text_color=list(MUTED),
            cursor_color=list(ACCENT),
            font_size=sp(12),
            padding=[dp(12), dp(13)],
        )
        self._log_limit_input = TextInput(
            text=str(self._settings.get("max_crash_log_mb", 2)),
            multiline=False,
            input_filter="int",
            hint_text="Log limit (MB)",
            background_color=list(CARD),
            foreground_color=list(TEXT),
            hint_text_color=list(MUTED),
            cursor_color=list(ACCENT),
            font_size=sp(12),
            padding=[dp(12), dp(13)],
        )
        inp_row.add_widget(self._cache_age_input)
        inp_row.add_widget(self._log_limit_input)
        perf_card.add_widget(inp_row)

        hist_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        self._history_limit_input = TextInput(
            text=str(self._settings.get("history_limit", 120)),
            multiline=False,
            input_filter="int",
            hint_text="History limit (10-500)",
            background_color=list(CARD),
            foreground_color=list(TEXT),
            hint_text_color=list(MUTED),
            cursor_color=list(ACCENT),
            font_size=sp(12),
            padding=[dp(12), dp(13)],
        )
        save_perf_btn = Btn(text="SAVE PERF", font_size=sp(12))
        save_perf_btn.bind(on_release=lambda *_: self._save_performance_settings())
        hist_row.add_widget(self._history_limit_input)
        hist_row.add_widget(save_perf_btn)
        perf_card.add_widget(hist_row)

        perf_actions = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        clear_cache_btn = OutlineBtn(text="CLEAR TEMP CACHE", font_size=sp(12))
        clear_cache_btn.bind(on_release=lambda *_: self._clear_temp_cache_now())
        clear_log_btn = OutlineBtn(text="CLEAR CRASH LOG", font_size=sp(12))
        clear_log_btn.bind(on_release=lambda *_: self._clear_crash_log())
        perf_actions.add_widget(clear_cache_btn)
        perf_actions.add_widget(clear_log_btn)
        perf_card.add_widget(perf_actions)

        row2 = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        refresh_stats_btn = OutlineBtn(text="REFRESH STORAGE", font_size=sp(11))
        refresh_stats_btn.bind(on_release=lambda *_: self._refresh_storage_stats())
        app_info_btn = OutlineBtn(text="OPEN APP INFO", font_size=sp(11))
        app_info_btn.bind(on_release=lambda *_: self._open_app_settings())
        row2.add_widget(refresh_stats_btn)
        row2.add_widget(app_info_btn)
        perf_card.add_widget(row2)

        self._storage_lbl = Label(
            text="", markup=True,
            font_size=sp(10), color=list(TEXTSUB),
            halign="left", valign="top",
            size_hint_y=None, height=dp(102),
        )
        self._storage_lbl.bind(size=self._storage_lbl.setter("text_size"))
        perf_card.add_widget(self._storage_lbl)
        c.add_widget(perf_card)

        # ── Cookie Import Card ────────────────────────────────────────────
        cookie_card = GlassCard(
            orientation="vertical",
            padding=PAD, spacing=dp(10),
            size_hint_y=None, height=dp(110),
            bg=list(SURF), radius=RAD,
        )
        cookie_card.add_widget(lbl("Cookies (Instagram / Facebook / X)", 14, TEXT, bold=True, h=26))
        cookie_card.add_widget(lbl(
            "Some platforms require browser cookies for reliable downloads.",
            10, TEXTSUB, h=22,
        ))
        cookie_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        import_cookie_btn = OutlineBtn(text="IMPORT COOKIE FILE", font_size=sp(11))
        import_cookie_btn.bind(on_release=lambda *_: self._import_cookie_file())
        cookie_info_btn = OutlineBtn(text="HOW TO GET COOKIES", font_size=sp(11))
        cookie_info_btn.bind(on_release=lambda *_: self._show_cookie_help())
        cookie_row.add_widget(import_cookie_btn)
        cookie_row.add_widget(cookie_info_btn)
        cookie_card.add_widget(cookie_row)
        self._cookie_status_lbl = lbl("", 10, GREEN, h=20)
        cookie_card.add_widget(self._cookie_status_lbl)
        c.add_widget(cookie_card)

        diag_card = GlassCard(
            orientation="vertical",
            padding=PAD, spacing=dp(10),
            size_hint_y=None, height=dp(264),
            bg=list(SURF), radius=RAD,
        )
        diag_card.add_widget(lbl("Diagnostics", 14, TEXT, bold=True, h=30))
        self._diag_live_btn = Btn(size_hint_y=None, height=dp(42), font_size=sp(12))
        self._diag_live_btn.bind(on_release=lambda *_: self._toggle_diagnostics_live())
        diag_card.add_widget(self._diag_live_btn)
        self._diag_lbl = Label(
            text="", markup=True,
            font_size=sp(10), color=list(TEXTSUB),
            halign="left", valign="middle",
            size_hint_y=None, height=dp(58),
        )
        self._diag_lbl.bind(size=self._diag_lbl.setter("text_size"))
        diag_card.add_widget(self._diag_lbl)
        diag_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        scan_btn = OutlineBtn(text="FULL APP SCAN", font_size=sp(11))
        scan_btn.bind(on_release=lambda *_: self._run_full_diagnostics_scan())
        clear_hist_btn = OutlineBtn(text="CLEAR HISTORY", font_size=sp(11))
        clear_hist_btn.bind(on_release=lambda *_: self._clear_history_list())
        diag_row.add_widget(scan_btn)
        diag_row.add_widget(clear_hist_btn)
        diag_card.add_widget(diag_row)
        self._diag_detail_lbl = Label(
            text="", markup=True,
            font_size=sp(10), color=list(TEXTSUB),
            halign="left", valign="top",
            size_hint_y=None, height=dp(70),
        )
        self._diag_detail_lbl.bind(size=self._diag_detail_lbl.setter("text_size"))
        diag_card.add_widget(self._diag_detail_lbl)
        c.add_widget(diag_card)

        info_card = GlassCard(
            orientation="vertical",
            padding=PAD, spacing=dp(10),
            size_hint_y=None, height=dp(360),
            bg=list(SURF), radius=RAD,
        )
        version = getattr(app_settings, "APP_VERSION", "1.0")
        info_card.add_widget(lbl(f"Video Downloader v{version}", 14, TEXT, bold=True, h=28))
        info_card.add_widget(lbl("Theme", 11, TEXTSUB, bold=True, h=20))
        theme_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        self._theme_dark_btn = Btn(text="DARK", font_size=sp(11))
        self._theme_light_btn = Btn(text="LIGHT", font_size=sp(11))
        self._theme_dark_btn.bind(on_release=lambda *_: self._set_theme_mode("dark"))
        self._theme_light_btn.bind(on_release=lambda *_: self._set_theme_mode("light"))
        theme_row.add_widget(self._theme_dark_btn)
        theme_row.add_widget(self._theme_light_btn)
        info_card.add_widget(theme_row)

        info_card.add_widget(lbl("Backup / Restore", 11, TEXTSUB, bold=True, h=20))
        backup_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        backup_btn = OutlineBtn(text="BACKUP NOW", font_size=sp(11))
        restore_btn = OutlineBtn(text="RESTORE LAST", font_size=sp(11))
        backup_btn.bind(on_release=lambda *_: self._backup_settings_history())
        restore_btn.bind(on_release=lambda *_: self._restore_latest_backup())
        backup_row.add_widget(backup_btn)
        backup_row.add_widget(restore_btn)
        info_card.add_widget(backup_row)

        info_card.add_widget(lbl("Follow", 11, TEXTSUB, bold=True, h=20))
        social_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        tw_btn = OutlineBtn(text="Twitter", font_size=sp(11))
        gh_btn = OutlineBtn(text="GitHub", font_size=sp(11))
        ig_btn = OutlineBtn(text="Instagram", font_size=sp(11))
        tw_btn.bind(on_release=lambda *_: self._open_url("https://x.com/iam_sandipmaity"))
        gh_btn.bind(on_release=lambda *_: self._open_url("https://github.com/iam-sandipmaity"))
        ig_btn.bind(on_release=lambda *_: self._open_url("https://instagram.com/iam_sandipmaity"))
        social_row.add_widget(tw_btn)
        social_row.add_widget(gh_btn)
        social_row.add_widget(ig_btn)
        info_card.add_widget(social_row)
        actions_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        reset_all_btn = OutlineBtn(text="RESET SETTINGS", font_size=sp(11))
        reset_all_btn.bind(on_release=lambda *_: self._reset_all_settings())
        app_info2_btn = OutlineBtn(text="APP STORAGE PAGE", font_size=sp(11))
        app_info2_btn.bind(on_release=lambda *_: self._open_app_settings())
        actions_row.add_widget(reset_all_btn)
        actions_row.add_widget(app_info2_btn)
        info_card.add_widget(actions_row)
        self.settings_status_lbl = Label(
            text="", markup=True,
            font_size=sp(10), color=list(TEXTSUB),
            halign="left", valign="middle",
            size_hint_y=None, height=dp(42),
        )
        self.settings_status_lbl.bind(size=self.settings_status_lbl.setter("text_size"))
        info_card.add_widget(self.settings_status_lbl)
        c.add_widget(info_card)

        self._refresh_notifications_button()
        self._refresh_cache_toggle_button()
        self._refresh_resume_cache_button()
        self._refresh_background_awake_button()
        self._refresh_diag_live_button()
        self._refresh_theme_buttons()
        self._refresh_storage_stats()
        self._run_full_diagnostics_scan()
        if self._settings.get("diagnostics_live", True):
            self._start_diagnostics_updates()
        else:
            self._stop_diagnostics_updates()
        perm = "granted" if self._has_notification_permission() else "not granted"
        self._set_settings_status(f"Notification permission: {perm}", "606075")
        c.add_widget(spacer(40))

    def _paste_url(self):
        try:
            text = Clipboard.paste()
            if text and text.strip():
                text = text.strip()
                # Check for multiple URLs
                try:
                    from batch_download import classify_urls
                    info = classify_urls(text)
                    if len(info["urls"]) > 1:
                        self._show_batch_dialog(info)
                        return
                except Exception:
                    pass
                self.url_in.text = text
        except Exception as e:
            wlog(f"paste: {e}")

    def _check_clipboard_on_startup(self):
        """If clipboard contains a supported URL that isn't already in the
        URL input, offer a quick 'Paste & Download' prompt."""
        try:
            text = Clipboard.paste()
            if not text or not isinstance(text, str):
                return
            text = text.strip()
            if not text.startswith("http"):
                return
            # Don't prompt if already filled
            if self.url_in.text.strip() == text:
                return
            try:
                from batch_download import classify_urls, is_supported_platform
                info = classify_urls(text)
                if info["supported"] > 0:
                    self._show_clipboard_prompt(info)
            except Exception:
                pass
        except Exception as e:
            wlog(f"clip check: {e}")

    def _show_clipboard_prompt(self, info):
        """Offer a small popup suggesting the user paste the detected URL."""
        try:
            url = info["urls"][0]
            platform = urlparse(url).netloc.split(".")[-2] if len(urlparse(url).netloc.split(".")) >= 2 else "unknown"
            msg = f"[b]{platform.capitalize()}[/b] link detected in clipboard.\nPaste and fetch?"

            box = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(18))
            box.add_widget(Label(
                text=msg, markup=True, color=list(TEXT),
                font_size=sp(14), halign="center", valign="middle",
                size_hint_y=None, height=dp(40),
            ))
            row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(42))

            def _do_paste(*_):
                self.url_in.text = url
                try:
                    popup.dismiss()
                except Exception:
                    pass

            def _nope(*_):
                try:
                    popup.dismiss()
                except Exception:
                    pass

            dismiss_btn = OutlineBtn(
                text="No, thanks", size_hint=(0.4, 1),
                font_size=sp(12),
            )
            dismiss_btn.bind(on_release=_nope)
            paste_btn = Btn(
                text="Paste & Fetch", size_hint=(0.6, 1),
                font_size=sp(12),
            )
            paste_btn.bind(on_release=lambda *_: (_do_paste(), self.do_fetch()))
            row.add_widget(dismiss_btn)
            row.add_widget(paste_btn)
            box.add_widget(row)

            popup = Popup(
                title="Clipboard Link", title_color=list(TEXT),
                title_size=sp(14),
                content=box,
                size_hint=(0.85, None), height=dp(150),
                background_color=list(CARD),
                separator_color=list(BORDER),
            )
            Clock.schedule_once(lambda dt: popup.open(), 0.5)
        except Exception as e:
            wlog(f"clip prompt: {e}")

    def _show_batch_dialog(self, info):
        """Show detected URLs from clipboard and let user pick which to download."""
        urls = info["urls"]
        from batch_download import is_supported_platform

        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(14))
        box.add_widget(Label(
            text=f"[b]{len(urls)} links[/b] detected in clipboard",
            markup=True, color=list(TEXT),
            font_size=sp(13), halign="center", size_hint_y=None, height=dp(22),
        ))

        # Scrollable URL list with checkboxes
        from kivy.uix.gridlayout import GridLayout as Grid
        from kivy.uix.togglebutton import ToggleButton
        scroll = ScrollView(size_hint_y=1)
        inner = BoxLayout(orientation="vertical", spacing=dp(4), size_hint_y=None)
        inner.bind(minimum_height=inner.setter("height"))

        checked = {i: True for i in range(len(urls))}

        for i, url in enumerate(urls):
            row = BoxLayout(orientation="horizontal", size_hint=(None, 1), width=self.root.width * 0.8)
            tb = ToggleButton(
                text="✓", size_hint=(None, 1), width=dp(32),
                font_size=sp(14), state="down",
                color=list(GREEN),
            )
            tb.bind(state=lambda t, idx=i: checked.update({idx: t.state == "down"}))
            row.add_widget(tb)
            lbl = Label(
                text=url, font_size=sp(10), color=list(TEXTSUB),
                halign="left", size_hint_x=1,
            )
            lbl.bind(size=lambda w, v: setattr(w, "text_size", (v[0], None)))
            row.add_widget(lbl)
            status = lbl("ok" if is_supported_platform(url) else "?", 9,
                         GREEN if is_supported_platform(url) else YELLOW)
            row.add_widget(status)
            inner.add_widget(row)

        scroll.add_widget(inner)
        box.add_widget(scroll)

        # Bottom buttons
        row2 = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(42))

        def _cancel(*_):
            popup.dismiss()

        def _paste_selected(*_):
            selected = [urls[i] for i in range(len(urls)) if checked.get(i, False)]
            if selected:
                self.url_in.text = selected[0]
                self._batch_urls = selected[1:]  # remaining for batch
                if self._batch_urls:
                    self._log(f"[color=00ccf2]Batch ready: {len(self._batch_urls) + 1} URLs queued[/color]")
            popup.dismiss()

        cancel_btn = OutlineBtn(text="Cancel", size_hint=(0.3, 1), font_size=sp(12))
        cancel_btn.bind(on_release=_cancel)
        paste_btn = Btn(text="Use Selected", size_hint=(0.7, 1), font_size=sp(12))
        paste_btn.bind(on_release=_paste_selected)
        row2.add_widget(cancel_btn)
        row2.add_widget(paste_btn)
        box.add_widget(row2)

        popup = Popup(
            title="Detected URLs", title_color=list(TEXT),
            title_size=sp(14),
            content=box,
            size_hint=(0.9, 0.65),
            background_color=list(CARD),
            separator_color=list(BORDER),
        )
        popup.open()

    def do_fetch(self):
        if not downloader:
            self._show_prog()
            self._log("[color=ff4488]WARN: downloader not loaded[/color]")
            return
        url = self.url_in.text.strip()
        if not url:
            return
        now = time.time()
        if (now - float(self._last_fetch_t or 0.0)) < 0.25:
            return
        self._last_fetch_t = now

        if self._fetch_inflight:
            same_url = (url == (self._fetch_url or ""))
            age = now - float(self._fetch_started_at or 0.0)
            # Ignore rapid repeated taps for the same URL while active.
            if same_url and age < 8.0:
                if self.fetch_btn:
                    self.fetch_btn.text = "FETCHING..."
                    self.fetch_btn.disabled = True
                return

        self._fetch_seq += 1
        seq = int(self._fetch_seq)
        self._fetch_inflight = True
        self._fetch_url = url
        self._fetch_started_at = now
        self.fetch_btn.text = "FETCHING..."
        self.fetch_btn.disabled = True
        self._hide_info(); self._hide_fmt()
        self._hide_dl();   self._hide_prog()

        threading.Thread(target=lambda: self._ft(url, seq), daemon=True).start()
        Clock.schedule_once(lambda dt, s=seq: self._fetch_watchdog(s), 8.0)

    def _fetch_watchdog(self, seq):
        if int(seq) != int(self._fetch_seq):
            return
        if not self._fetch_inflight:
            return
        if self.fetch_btn:
            self.fetch_btn.text = "RETRY FETCH"
            self.fetch_btn.disabled = False

    def _ft(self, url, seq):
        try:
            info, err = downloader.get_info(url)
            Clock.schedule_once(lambda dt, i=info, e=err, s=seq: self._on_info(i, e, s))
        except Exception as e:
            wlog(f"_ft: {traceback.format_exc()}")
            Clock.schedule_once(lambda dt, s=seq, m=str(e): self._on_info(None, m, s))

    def _on_info(self, info, err, seq=None):
        if seq is not None and int(seq) != int(self._fetch_seq):
            return
        self._fetch_inflight = False
        self._fetch_url = ""
        self._fetch_started_at = 0.0
        self.fetch_btn.text = "FETCH VIDEO INFO"
        self.fetch_btn.disabled = False

        if err or not info:
            self._show_prog()
            self._log(f"[color=ff4488]Error: {err}[/color]")
            return

        self.info = info
        self._fill_info(info)

    def _fill_info(self, info):
        title   = info.get("title", "Unknown")
        channel = info.get("channel", "")
        dur     = downloader.fmt_dur(info.get("duration", 0))
        views   = downloader.fmt_views(info.get("views", 0))
        thumb   = info.get("thumbnail", "")
        fmts    = info.get("formats", [])

        self.lbl_title.text   = title
        self.lbl_title.height = dp(50)
        self.lbl_meta.text    = f"{channel}  |  {dur}  |  {views} views"
        self.lbl_meta.height  = dp(22)
        self.info_card.height  = dp(80)
        self.info_card.opacity = 1

        if thumb:
            threading.Thread(target=lambda: self._lt(thumb), daemon=True).start()

        # Format chips with category filter (video+audio / video-only / audio-only)
        self._all_fmts = list(fmts)
        available = {self._fmt_category(f) for f in self._all_fmts}
        if self._fmt_mode not in available:
            for fallback in ("video_audio", "video_only", "audio_only"):
                if fallback in available:
                    self._fmt_mode = fallback
                    break
        self._refresh_fmt_mode_ui()
        self._refresh_fmt_list()

        if self.sel_fmt:
            self.dl_btn.height  = dp(58)
            self.dl_btn.opacity = 1
        else:
            self._hide_dl()

    def _lt(self, url):
        try:
            fd, path = tempfile.mkstemp(prefix="ytdl_thumb_", suffix=".jpg")
            os.close(fd)
            ok  = downloader.fetch_thumbnail(url, path)
            if ok:
                Clock.schedule_once(lambda dt: self._st(path))
            else:
                try:
                    os.remove(path)
                except Exception:
                    pass
        except Exception as e:
            wlog(f"thumb: {e}")

    def _cleanup_thumb_temp(self, keep=None):
        p = self._thumb_tmp_path
        if not p:
            return
        if keep and os.path.abspath(str(p)) == os.path.abspath(str(keep)):
            return
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception as e:
            wlog(f"thumb cleanup failed: {e}")
        self._thumb_tmp_path = keep

    def _st(self, path):
        self._cleanup_thumb_temp(keep=path)
        self.thumb_img.source  = path
        self.thumb_img.height  = dp(190)
        self.thumb_img.opacity = 1
        self.info_card.height += dp(190)

    def _sel(self, card):
        for c in self.fmt_cards:
            c.deselect()
        card.select()
        self.sel_fmt = card.fmt

    def _refresh_download_controls(self):
        if self.pause_btn is None:
            return
        if not self._download_active or self._download_control is None:
            self.pause_btn.text = "PAUSE"
            self.pause_btn.disabled = True
            if self.stop_btn is not None:
                self.stop_btn.disabled = True
            return
        self.pause_btn.disabled = False
        self.pause_btn.text = "RESUME" if self._download_paused else "PAUSE"
        if self.stop_btn is not None:
            self.stop_btn.disabled = False

    def _toggle_pause_download(self):
        if self._download_paused:
            self._resume_download()
        else:
            self._pause_download()

    def _pause_download(self, external=False):
        if not self._download_active or self._download_control is None:
            return
        try:
            self._download_control.pause()
            self._download_paused = True
            if external:
                self._log("[color=ffd533]Paused from notification[/color]")
            else:
                self._log("[color=ffd533]Download paused[/color]")
            self._refresh_download_controls()
            self._notify_progress(getattr(self.ring, "value", 0), "Paused")
        except Exception as e:
            self._log(f"[color=ff4488]Pause failed: {e}[/color]")

    def _resume_download(self, external=False):
        if not self._download_active or self._download_control is None:
            return
        try:
            self._download_control.resume()
            self._download_paused = False
            if external:
                self._log("[color=33ed9a]Resumed from notification[/color]")
            else:
                self._log("[color=33ed9a]Download resumed[/color]")
            self._refresh_download_controls()
            self._notify_progress(getattr(self.ring, "value", 0), "Downloading...")
        except Exception as e:
            self._log(f"[color=ff4488]Resume failed: {e}[/color]")

    def _stop_download(self, external=False):
        if not self._download_active or self._download_control is None:
            return
        try:
            self._download_control.cancel()
            self._download_paused = False
            if external:
                self._log("[color=ffd533]Stop requested from notification[/color]")
            else:
                self._log("[color=ffd533]Stopping download...[/color]")
            self._refresh_download_controls()
            self._notify_progress(getattr(self.ring, "value", 0), "Stopping...")
        except Exception as e:
            self._log(f"[color=ff4488]Stop failed: {e}[/color]")

    def _on_download_state(self, state):
        s = str(state or "").strip().lower()
        def u(dt):
            if s == "paused":
                self._download_paused = True
                self.prog_status.text = "Paused"
            elif s == "resumed":
                self._download_paused = False
                self.prog_status.text = "Downloading..."
            self._refresh_download_controls()
        Clock.schedule_once(u, 0)

    def _get_connectivity_kind(self):
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Context = autoclass("android.content.Context")
            BuildVersion = autoclass("android.os.Build$VERSION")
            NetworkCapabilities = autoclass("android.net.NetworkCapabilities")
            activity = PythonActivity.mActivity
            cm = activity.getSystemService(Context.CONNECTIVITY_SERVICE)
            if cm is None:
                return "unknown"
            if int(BuildVersion.SDK_INT) >= 23:
                net = cm.getActiveNetwork()
                if net is None:
                    return "offline"
                caps = cm.getNetworkCapabilities(net)
                if caps is None:
                    return "offline"
                if caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI):
                    return "wifi"
                if caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR):
                    return "mobile"
                if caps.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET):
                    return "ethernet"
                return "online"
            ni = cm.getActiveNetworkInfo()
            if ni is None or not ni.isConnected():
                return "offline"
            return "online"
        except Exception:
            return "unknown"

    def _refresh_network_status_label(self):
        if self._net_status_lbl is None:
            return
        nk = str(self._net_kind or "unknown").lower()
        if nk in ("wifi", "online", "mobile", "ethernet"):
            c = "33ed9a"
        elif nk == "offline":
            c = "ff4488"
        else:
            c = "ffd533"
        dns_n = int(self._dns_retry_count or 0)
        if dns_n >= 3:
            dns_c = "ff4488"
        elif dns_n >= 1:
            dns_c = "ffd533"
        else:
            dns_c = "33ed9a"
        self._net_status_lbl.text = (
            f"[color=606075]NET:[/color] [color={c}]{nk.upper()}[/color]   "
            f"[color=606075]DNS retries:[/color] [color={dns_c}][b]{dns_n}[/b][/color]"
        )
        if self._net_retry_lbl is not None:
            nr = int(self._net_retry_count or 0)
            nm = int(self._net_retry_max or 0)
            if nm > 0 and nr >= nm:
                rc = "ff4488"
            elif nr > 0:
                rc = "ffd533"
            else:
                rc = "606075"
            scope = str(self._net_retry_scope or "").strip().upper()
            sfx = f" ({scope})" if scope else ""
            self._net_retry_lbl.text = (
                f"[color=606075]NET retry:[/color] "
                f"[color={rc}][b]{nr}/{nm}[/b][/color]{sfx}"
            )

    def _net_tick(self, _dt):
        self._net_kind = self._get_connectivity_kind()
        self._refresh_network_status_label()

    def _start_network_status_updates(self):
        if self._net_event is None:
            self._net_event = Clock.schedule_interval(self._net_tick, 2.0)
        self._net_tick(0)

    def _stop_network_status_updates(self):
        if self._net_event is not None:
            try:
                self._net_event.cancel()
            except Exception:
                pass
            self._net_event = None

    def _on_net_event(self, event):
        ev = event if isinstance(event, dict) else {}
        kind = str(ev.get("kind") or "").lower()

        def u(_dt):
            if kind == "reset":
                self._dns_retry_count = 0
                self._net_retry_count = 0
                self._net_retry_max = 0
                self._net_retry_scope = ""
            elif kind == "retry":
                try:
                    self._net_retry_count = max(int(self._net_retry_count), int(ev.get("net_retries") or 0))
                except Exception:
                    pass
                try:
                    self._net_retry_max = max(int(self._net_retry_max), int(ev.get("max_retries") or 0))
                except Exception:
                    pass
                scope = str(ev.get("scope") or "").strip().lower()
                if scope:
                    self._net_retry_scope = scope
                if bool(ev.get("dns_error")):
                    try:
                        dr = int(ev.get("dns_retries") or 0)
                    except Exception:
                        dr = 0
                    self._dns_retry_count = max(int(self._dns_retry_count), dr or (int(self._dns_retry_count) + 1))
            self._refresh_network_status_label()

        Clock.schedule_once(u, 0)

    # ── Download Logic ────────────────────────────────────────────────────
    def do_download(self):
        if not self.sel_fmt or not downloader:
            return
        if self._download_active:
            self._log("[color=ffd533]A download is already running[/color]")
            return
        if not self._ensure_storage_permission(show_ui=True):
            self._show_prog()
            self._log("[color=ff4488]Storage permission required to download[/color]")
            return
        if self._settings.get("notifications", True):
            self._ensure_notification_permission(show_ui=True)
        url = self.url_in.text.strip()
        wlog(f"Download: {self.sel_fmt.get('label')}")
        self.dl_btn.disabled = True
        self._show_prog()
        self._log(
            f"[color=7345ff]{self.sel_fmt.get('label', '?')}[/color]  selected")
        self._download_active = True
        self._download_paused = False
        self._dns_retry_count = 0
        self._net_retry_count = 0
        self._net_retry_max = 0
        self._net_retry_scope = ""
        self._net_kind = "unknown"
        self._download_control = (
            downloader.DownloadControl()
            if hasattr(downloader, "DownloadControl")
            else None
        )
        self._refresh_download_controls()
        self._start_network_status_updates()
        self._acquire_active_locks(force=True)

        # Inject video title so downloader never needs a second network call
        fmt = dict(self.sel_fmt)
        if self.info:
            fmt["title"] = self.info.get("title", "")

        self._download_thread = threading.Thread(
            target=lambda: downloader.download(
                url=url,
                fmt_info=fmt,
                on_progress=self._cp,
                on_done=self._cd,
                on_error=self._ce,
                control=self._download_control,
                on_state=self._on_download_state,
                on_net=self._on_net_event,
            ),
            daemon=False,
        )
        self._download_thread.start()

    def _cp(self, pct, spd, eta, step, total):
        self._notify_progress(pct, step)
        def u(dt):
            self.ring.value    = pct
            self.pbar.value    = pct
            self.prog_status.text = step[:28]
            self.spd_lbl.text  = f"SPD {spd}" if spd and spd != "-" else ""
            self.eta_lbl.text  = f"ETA {eta}" if eta and eta != "-" else ""
            self.stp_lbl.text  = total if total and total != "?" else ""
        Clock.schedule_once(u)

    def _cd(self, filepath):
        fname = os.path.basename(filepath)
        saved_dir = os.path.dirname(filepath)
        ftype = self.sel_fmt.get("type", "video") if self.sel_fmt else "video"
        self._append_history_entry(filepath, ftype)
        wlog(f"Done: {fname}")
        self._notify_done(fname)

        def u(dt):
            self._download_active = False
            self._download_paused = False
            self._download_control = None
            self._download_thread = None
            self.ring.value       = 100
            self.ring.ring_color  = list(GREEN)
            self.pbar.value       = 100
            self.pbar.bar_color   = list(GREEN)
            self.prog_status.text = "Done!"
            self.spd_lbl.text     = ""
            self.eta_lbl.text     = ""
            self.stp_lbl.text     = ""
            self._log(f"[color=33ed9a]OK Saved:[/color] {fname}")
            self.done_text.text   = f"Saved to:\n{saved_dir}"
            self.done_card.height  = dp(72)
            self.done_card.opacity = 1
            self.prog_card.height += dp(72)
            self.dl_btn.disabled   = False
            self._refresh_download_controls()
            self._stop_network_status_updates()
            self._release_active_locks()

            # Check for remaining batch URLs
            self._process_batch_queue()
        Clock.schedule_once(u)

    def _ce(self, msg):
        wlog(f"Error: {msg}")
        self._notify_error(msg)

        def u(dt):
            self._download_active = False
            self._download_paused = False
            self._download_control = None
            self._download_thread = None
            self.ring.ring_color  = list(ROSE)
            self.pbar.bar_color   = list(ROSE)
            is_cancel = "cancel" in str(msg).lower()
            self.prog_status.text = "Stopped" if is_cancel else "Failed"
            if is_cancel:
                self._log(f"[color=ffd533]Stopped: {msg}[/color]")
            else:
                self._log(f"[color=ff4488]ERROR: {msg}[/color]")
            self.dl_btn.disabled  = False
            self._refresh_download_controls()
            self._stop_network_status_updates()
            self._release_active_locks()

            # Check for remaining batch URLs
            self._process_batch_queue()
        Clock.schedule_once(u)

    def _process_batch_queue(self):
        """If there are remaining batch URLs, offer to download the next one."""
        remaining = getattr(self, "_batch_urls", [])
        if not remaining:
            return
        next_url = remaining[0]
        self._batch_urls = remaining[1:]
        cnt_left = len(self._batch_urls) + 1

        try:
            from batch_download import is_supported_platform
            platform_tag = urlparse(next_url).netloc
        except Exception:
            is_supported_platform = lambda u: True
            platform_tag = "unknown"

        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(14))
        box.add_widget(Label(
            text=f"[b]{len(remaining)}[/b] more URLs in queue\nDownload next?",
            markup=True, color=list(TEXT),
            font_size=sp(13), halign="center",
            size_hint_y=None, height=dp(40),
        ))
        url_preview = next_url if len(next_url) <= 55 else next_url[:52] + "..."
        box.add_widget(Label(
            text=url_preview, font_size=sp(10), color=list(ACCENT2),
            halign="left", size_hint_y=None, height=dp(20),
        ))
        box.add_widget(Label(
            text="", size_hint_y=None, height=dp(6),
        ))
        row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(42))

        def _skip(*_):
            popup.dismiss()
            # Skip and check further
            self._batch_urls = self._batch_urls  # already popped
            self._process_batch_queue()

        def _stop_batch(*_):
            self._batch_urls = []
            popup.dismiss()

        def _download_next(*_):
            popup.dismiss()
            self.url_in.text = next_url
            # Brief delay for UI to settle then auto-fetch
            Clock.schedule_once(lambda dt: self.do_fetch(), 0.3)

        skip_btn = OutlineBtn(text="Skip", size_hint=(0.25, 1), font_size=sp(12))
        skip_btn.bind(on_release=_skip)
        stop_btn = OutlineBtn(text="Stop", size_hint=(0.25, 1), font_size=sp(12), color=list(ROSE))
        stop_btn.bind(on_release=_stop_batch)
        next_btn = Btn(text="Next", size_hint=(0.5, 1), font_size=sp(12))
        next_btn.bind(on_release=_download_next)
        row.add_widget(skip_btn)
        row.add_widget(stop_btn)
        row.add_widget(next_btn)
        box.add_widget(row)

        popup = Popup(
            title="Batch Download", title_color=list(TEXT),
            title_size=sp(14),
            content=box,
            size_hint=(0.85, None), height=dp(180),
            background_color=list(CARD),
            separator_color=list(BORDER),
        )
        popup.open()

    # ── Visibility Helpers ────────────────────────────────────────────────
    def _show_prog(self):
        self._notif_last_pct = -1
        self._notif_last_step = ""
        self._dns_retry_count = 0
        self._net_retry_count = 0
        self._net_retry_max = 0
        self._net_retry_scope = ""
        self._net_kind = "unknown"
        self.ring.value       = 0
        self.ring.ring_color  = list(ACCENT)
        self.pbar.value       = 0
        self.pbar.bar_color   = list(ACCENT)
        self.prog_status.text = ""
        self.spd_lbl.text     = ""
        self.eta_lbl.text     = ""
        self.stp_lbl.text     = ""
        self.log_lbl.text     = ""
        self._logs            = []
        self.done_card.height  = dp(0)
        self.done_card.opacity = 0
        self.prog_card.height  = dp(346)
        self.prog_card.opacity = 1
        self._refresh_network_status_label()
        self._refresh_download_controls()

    def _hide_info(self):
        self._cleanup_thumb_temp()
        self.thumb_img.source = ""
        self.info_card.height  = dp(0)
        self.info_card.opacity = 0
        self.thumb_img.height  = dp(0)
        self.thumb_img.opacity = 0

    def _hide_fmt(self):
        self.fmt_card.height  = dp(0)
        self.fmt_card.opacity = 0

    def _hide_dl(self):
        self.dl_btn.height  = dp(0)
        self.dl_btn.opacity = 0

    def _hide_prog(self):
        self._stop_network_status_updates()
        self.prog_card.height  = dp(0)
        self.prog_card.opacity = 0

    def _log(self, text):
        self._logs.append(text)
        if len(self._logs) > 30:
            self._logs = self._logs[-30:]
        Clock.schedule_once(
            lambda dt: setattr(self.log_lbl, "text", "\n".join(self._logs)))


if __name__ == "__main__":
    try:
        wlog("Calling VideoDownloaderApp().run()")
        VideoDownloaderApp().run()
    except Exception:
        wlog(f"FATAL:\n{traceback.format_exc()}")
        raise
