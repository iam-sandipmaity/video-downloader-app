"""
UI widgets used across the app.

All colour tokens are resolved through a theme getter so the module is
Kivy-standalone and works with any palette.  Call :func:`set_theme_getter`
once before any widget is instantiated.
"""

from __future__ import annotations

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle, Line, Mesh
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty, ListProperty, BooleanProperty


# ---------------------------------------------------------------------------
# Theme access
# ---------------------------------------------------------------------------

_theme_getter = None


def set_theme_getter(getter) -> None:
    """Pass a callable that returns the current theme dict."""
    global _theme_getter
    _theme_getter = getter


def _t() -> dict:
    """Return the current theme dict, or safe fallback."""
    if _theme_getter:
        return _theme_getter()
    return {
        "CARD": (0.086, 0.090, 0.125, 1),
        "CARD2": (0.110, 0.114, 0.157, 1),
        "BORDER": (0.173, 0.180, 0.243, 1),
        "ACCENT": (0.400, 0.310, 1.000, 1),
        "ACCENT2": (0.000, 0.800, 0.950, 1),
        "ACCT_DK": (0.280, 0.200, 0.780, 1),
        "GREEN": (0.176, 0.890, 0.565, 1),
        "YELLOW": (1.000, 0.800, 0.220, 1),
        "ORANGE": (1.000, 0.510, 0.180, 1),
        "ROSE": (1.000, 0.286, 0.486, 1),
        "BLUE": (0.220, 0.580, 1.000, 1),
        "MUTED": (0.340, 0.350, 0.440, 1),
        "TEXT": (0.940, 0.945, 0.965, 1),
        "TEXTSUB": (0.480, 0.490, 0.590, 1),
        "BG": (0.035, 0.035, 0.055, 1),
    }


PAD = dp(18)
PAD2 = dp(12)
RAD = dp(20)
RAD2 = dp(14)
RAD3 = dp(10)


# ---------------------------------------------------------------------------
# Quick label factory
# ---------------------------------------------------------------------------

def lbl(text: str = "", size: int = 13, color=None, bold: bool = False,
        halign: str = "left", h=None, markup: bool = False) -> Label:
    t = _t()
    l = Label(
        text=text, font_size=sp(size),
        color=list(color or t["TEXT"]),
        bold=bold, halign=halign,
        valign="middle", markup=markup,
    )
    if h is not None:
        l.size_hint_y = None
        l.height = h
    return l


# ---------------------------------------------------------------------------
# Cards
# ---------------------------------------------------------------------------

class Card(BoxLayout):
    bg = ListProperty([])
    radius = NumericProperty(RAD)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self._draw, size=self._draw, bg=self._draw, radius=self._draw)
        if not self.bg:
            self.bg = list(_t()["CARD"])

    def _draw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0, 0, 0, 0.12)
            RoundedRectangle(
                pos=(self.x + dp(1), self.y - dp(2)),
                size=(self.width, self.height),
                radius=[self.radius + dp(1)] * 4)
            Color(*self.bg)
            RoundedRectangle(pos=self.pos, size=self.size,
                             radius=[self.radius] * 4)


class GlassCard(Card):
    def _draw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0, 0, 0, 0.15)
            RoundedRectangle(
                pos=(self.x + dp(1), self.y - dp(3)),
                size=(self.width, self.height),
                radius=[self.radius + dp(1)] * 4)
            Color(*self.bg)
            RoundedRectangle(pos=self.pos, size=self.size,
                             radius=[self.radius] * 4)
            Color(1, 1, 1, 0.06)
            RoundedRectangle(
                pos=(self.x, self.y + self.height * 0.5),
                size=(self.width, self.height * 0.5),
                radius=[self.radius, self.radius, 0, 0])
            Color(1, 1, 1, 0.04)
            Line(rounded_rectangle=(
                self.x + 1, self.y + 1,
                self.width - 2, self.height - 2,
                self.radius - 1), width=dp(1.1))


# ---------------------------------------------------------------------------
# Buttons
# ---------------------------------------------------------------------------

class Btn(Button):
    bg = ListProperty([])
    bg_dn = ListProperty([])
    radius = NumericProperty(RAD2)
    _dn = BooleanProperty(False)

    def __init__(self, **kw):
        t = _t()
        kw.setdefault("background_normal", "")
        kw.setdefault("background_color", (0, 0, 0, 0))
        kw.setdefault("color", t["TEXT"])
        kw.setdefault("bold", True)
        kw.setdefault("font_size", sp(14))
        super().__init__(**kw)
        if not self.bg:
            self.bg = list(t["ACCENT"])
        if not self.bg_dn:
            self.bg_dn = list(t["ACCT_DK"])
        self.bind(pos=self._draw, size=self._draw, bg=self._draw, _dn=self._draw)

    def _draw(self, *_):
        self.canvas.before.clear()
        col = self.bg_dn if self._dn else self.bg
        with self.canvas.before:
            if not self._dn:
                Color(col[0] * 0.4, col[1] * 0.4, col[2] * 0.4, 0.25)
                RoundedRectangle(
                    pos=(self.x, self.y - dp(2)),
                    size=(self.width, self.height),
                    radius=[self.radius] * 4)
            Color(*col)
            RoundedRectangle(pos=self.pos, size=self.size,
                             radius=[self.radius] * 4)
            Color(1, 1, 1, 0.10 if not self._dn else 0.04)
            RoundedRectangle(
                pos=(self.x, self.y + self.height * 0.5),
                size=(self.width, self.height * 0.5),
                radius=[self.radius, self.radius, 0, 0])

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._dn = True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        self._dn = False
        return super().on_touch_up(touch)


class OutlineBtn(Btn):
    def __init__(self, **kw):
        kw.setdefault("color", list(_t()["TEXT"]))
        super().__init__(**kw)
        self.bg = list(_t()["CARD2"])
        self.bg_dn = list(_t()["BORDER"])

    def _draw(self, *_):
        self.canvas.before.clear()
        t = _t()
        with self.canvas.before:
            Color(*(self.bg_dn if self._dn else self.bg))
            RoundedRectangle(pos=self.pos, size=self.size,
                             radius=[self.radius] * 4)
            Color(t["ACCENT"][0], t["ACCENT"][1], t["ACCENT"][2],
                  0.6 if self._dn else 0.25)
            Line(rounded_rectangle=(
                self.x, self.y, self.width, self.height, self.radius),
                width=dp(1.3))


# ---------------------------------------------------------------------------
# Progress indicators
# ---------------------------------------------------------------------------

class RingProgress(Widget):
    value = NumericProperty(0)
    ring_color = ListProperty([])

    def __init__(self, **kw):
        t = _t()
        self._pct_lbl = Label(
            text="0%", font_size=sp(28), bold=True,
            color=list(t["TEXT"]), halign="center", valign="middle",
        )
        super().__init__(**kw)
        self.add_widget(self._pct_lbl)
        if not self.ring_color:
            self.ring_color = list(t["ACCENT"])
        self.bind(pos=self._draw, size=self._draw, value=self._draw, ring_color=self._draw)

    def _draw(self, *_):
        if not hasattr(self, "_pct_lbl"):
            return
        self.canvas.clear()
        cx, cy = self.center
        r = max(dp(4), min(self.width, self.height) / 2 - dp(8))
        t = _t()
        with self.canvas:
            Color(t["BORDER"][0], t["BORDER"][1], t["BORDER"][2], 0.4)
            Line(circle=(cx, cy, r), width=dp(6), cap="round")
        if self.value > 0:
            deg = self.value / 100 * 360
            with self.canvas:
                Color(self.ring_color[0], self.ring_color[1],
                      self.ring_color[2], 0.15)
                Line(ellipse=(cx - r, cy - r, r * 2, r * 2, 90, 90 - deg),
                     width=dp(14), cap="round")
                Color(*self.ring_color)
                Line(ellipse=(cx - r, cy - r, r * 2, r * 2, 90, 90 - deg),
                     width=dp(6), cap="round")
        self._pct_lbl.center = (cx, cy)
        self._pct_lbl.size = self.size
        self._pct_lbl.text = f"{int(self.value)}%"


class PBar(Widget):
    value = NumericProperty(0)
    bar_color = ListProperty([])

    def __init__(self, **kw):
        super().__init__(**kw)
        if not self.bar_color:
            self.bar_color = list(_t()["ACCENT"])
        self.bind(pos=self._draw, size=self._draw, value=self._draw, bar_color=self._draw)

    def _draw(self, *_):
        self.canvas.clear()
        r = self.height / 2
        t = _t()
        with self.canvas:
            Color(t["BORDER"][0], t["BORDER"][1], t["BORDER"][2], 0.35)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[r] * 4)
            if self.value > 0:
                w = max(self.height, self.width * self.value / 100)
                Color(self.bar_color[0], self.bar_color[1],
                      self.bar_color[2], 0.18)
                RoundedRectangle(
                    pos=(self.x, self.y - dp(2)),
                    size=(w, self.height + dp(4)),
                    radius=[r + dp(2)] * 4)
                Color(*self.bar_color)
                RoundedRectangle(pos=self.pos, size=(w, self.height),
                                 radius=[r] * 4)
                Color(1, 1, 1, 0.15)
                RoundedRectangle(
                    pos=(self.x, self.y + self.height * 0.5),
                    size=(w, self.height * 0.5),
                    radius=[0, 0, r, r])


# ---------------------------------------------------------------------------
# Logo mark
# ---------------------------------------------------------------------------

class LogoMark(Widget):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        self.canvas.clear()
        x, y = self.pos
        w, h = self.size
        t = _t()
        r = min(dp(11), w * 0.24)
        with self.canvas:
            Color(*t["ACCENT"])
            RoundedRectangle(pos=self.pos, size=self.size, radius=[r] * 4)
            Color(t["ACCENT2"][0], t["ACCENT2"][1], t["ACCENT2"][2], 0.30)
            RoundedRectangle(pos=(x, y),
                             size=(w, h * 0.55), radius=[r, r, 0, 0])
            Color(1, 1, 1, 0.12)
            RoundedRectangle(pos=(x, y + h * 0.55),
                             size=(w, h * 0.45), radius=[0, 0, r, r])

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

            arr_y = y + h * 0.22
            Color(1, 1, 1, 0.80)
            Line(points=[cx - dp(1), y + h * 0.38, cx - dp(1), arr_y + dp(4)],
                 width=dp(1.5), cap="round")
            Line(points=[cx - dp(1) - w * 0.08, arr_y + dp(7),
                         cx - dp(1), arr_y + dp(2),
                         cx - dp(1) + w * 0.08, arr_y + dp(7)],
                 width=dp(1.3), cap="round", joint="round")


# ---------------------------------------------------------------------------
# Format selection chip
# ---------------------------------------------------------------------------

_TAG_COLORS = {
    "4K":  "YELLOW",
    "2K":  "ORANGE",
    "FHD": "ACCENT2",
    "HD":  "GREEN",
    "SD":  "MUTED",
    "":    "MUTED",
}


class FmtChip(Button):
    selected = BooleanProperty(False)

    def __init__(self, fmt, **kw):
        self.fmt = fmt
        tag = fmt.get("tag", "")
        label = self._clean_label(fmt)
        size = fmt.get("size", "")
        needs_mux = fmt.get("needs_mux", False) or fmt.get("audio_id")

        t = _t()
        tc_key = _TAG_COLORS.get(tag, "MUTED")
        tc = t[tc_key]
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
            color=list(t["TEXT"]),
            background_normal="",
            background_color=(0, 0, 0, 0),
            size_hint_y=None,
            height=dp(54),
            **kw,
        )
        self.bind(size=self.setter("text_size"))
        self.bind(pos=self._draw, size=self._draw, selected=self._draw)

    @staticmethod
    def _clean_label(fmt):
        label = str(fmt.get("label", "?"))
        cat = str(fmt.get("category", ""))
        low = label.lower()
        if cat == "video_only" and low.endswith(" video only"):
            return label[: -len(" Video Only")]
        if cat == "audio_only" and low.startswith("audio "):
            return label[6:]
        return label

    def _draw(self, *_):
        self.canvas.before.clear()
        t = _t()
        rad = RAD2
        if self.selected:
            Color(t["ACCENT"][0], t["ACCENT"][1], t["ACCENT"][2], 0.08)
            RoundedRectangle(
                pos=(self.x - dp(1), self.y - dp(1)),
                size=(self.width + dp(2), self.height + dp(2)),
                radius=[rad + dp(1)] * 4)
            Color(t["ACCENT"][0], t["ACCENT"][1], t["ACCENT"][2], 0.15)
            RoundedRectangle(pos=self.pos, size=self.size,
                             radius=[rad] * 4)
            Color(*t["ACCENT"])
            Line(rounded_rectangle=(
                self.x, self.y, self.width, self.height, rad),
                width=dp(1.8))
            Color(*t["ACCENT"])
            RoundedRectangle(
                pos=(self.x, self.y + dp(10)),
                size=(dp(3), self.height - dp(20)),
                radius=[dp(2)] * 4)
        else:
            Color(*t["CARD2"])
            RoundedRectangle(pos=self.pos, size=self.size,
                             radius=[rad] * 4)
            Color(t["BORDER"][0], t["BORDER"][1], t["BORDER"][2], 0.5)
            Line(rounded_rectangle=(
                self.x, self.y, self.width, self.height, rad),
                width=dp(0.8))

    def select(self):
        self.selected = True

    def deselect(self):
        self.selected = False

    def on_touch_down(self, touch):
        return super().on_touch_down(touch)


# ---------------------------------------------------------------------------
# History list item
# ---------------------------------------------------------------------------

class HistoryItem(BoxLayout):
    def __init__(self, fname, ftype, **kw):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None, height=dp(66),
            padding=(dp(16), dp(12)),
            spacing=dp(14),
            **kw,
        )
        self._ftype = ftype
        self._pill_col = None
        self.bind(pos=self._draw, size=self._draw)

        is_audio = ftype == "audio"
        ic_char = "AUD" if is_audio else "VID"
        t = _t()
        ic_color = list(t["ACCENT2"]) if is_audio else list(t["ACCENT"])
        self._pill_col = ic_color

        pill = FloatLayout(size_hint=(None, None),
                           size=(dp(42), dp(42)))
        pill.bind(pos=lambda w, _: self._pill_bg(w),
                  size=lambda w, _: self._pill_bg(w))
        ic_lbl = Label(text=ic_char, font_size=sp(10),
                       color=ic_color, bold=True,
                       pos_hint={"center_x": .5, "center_y": .5})
        pill.add_widget(ic_lbl)
        self.add_widget(pill)

        col = BoxLayout(orientation="vertical", spacing=dp(3))
        short = fname if len(fname) <= 48 else fname[:45] + "..."
        n = Label(text=short, font_size=sp(13), color=list(t["TEXT"]),
                  bold=True, halign="left", valign="bottom")
        n.bind(size=n.setter("text_size"))
        tt = Label(text=ftype.upper(), font_size=sp(10),
                   color=list(t["TEXTSUB"]), halign="left", valign="top")
        tt.bind(size=tt.setter("text_size"))
        col.add_widget(n)
        col.add_widget(tt)
        self.add_widget(col)

    def _draw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0, 0, 0, 0.08)
            RoundedRectangle(
                pos=(self.x + dp(1), self.y - dp(1)),
                size=(self.width, self.height),
                radius=[RAD2 + dp(1)] * 4)
            Color(*_t()["CARD"])
            RoundedRectangle(pos=self.pos, size=self.size, radius=[RAD2] * 4)

    def _pill_bg(self, w):
        w.canvas.before.clear()
        c = self._pill_col or _t()["ACCENT"]
        with w.canvas.before:
            Color(c[0], c[1], c[2], 0.15)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(12)] * 4)
