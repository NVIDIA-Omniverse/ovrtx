#!/usr/bin/env python3
"""Shared helpers for the generated SVG diagrams of the ovrtx sensor docs.

Every ``<area>/generate_diagrams.py`` beside this file imports this module so
that all sensor figures share one palette, one font stack and one set of
shapes::

    import pathlib, sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
    import _diagram_lib as dl

    c = dl.Canvas(760, 220, "Sensor data path", "Scene, sensor model and output in a row.")
    a = dl.box(c, 40, 70, 200, 72, "scene", fill=dl.GREEN)
    b = dl.box(c, 300, 70, 200, 72, "sensor model", sublabel="one per modality")
    dl.arrow(c, a.right + 6, a.cy, b.left - 6, b.cy)
    dl.validate(c)                                   # overlap and canvas-edge backstop
    dl.write_svg(dl.output_dir(__file__) / "data-path.svg", c.render())

What the helpers enforce or assume (see ``../README.md``):

* stdlib only -- no plotting library, no build dependency;
* byte-for-byte reproducible output -- no timestamps, no randomness, every
  number is written through :func:`fmt`;
* the canvas is sized from the content plus padding and text never touches
  the canvas edge (:func:`check_bounds`), text never overlaps other text
  (:func:`check_overlaps`);
* arrowheads scale with the line weight, every SVG carries a ``<title>`` and
  a ``<desc>``.

Palette, font stack and helper shapes follow
``rendering/docs/plc/rtx/sensor-versioning/images/generate_diagrams.py``.
"""

from __future__ import annotations

import math
import os
import pathlib
import re
import shutil
import subprocess
import sys
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple, Union

__all__ = [
    "GREEN", "ORANGE", "RED", "BLUE", "PURPLE", "GREY", "DK", "MUTED", "FAINT", "PANEL", "WHITE",
    "F", "M", "Rect", "TextBox", "Canvas",
    "fmt", "esc", "text_width", "fit_label", "wrap_text", "contrast_text",
    "text", "text_block", "box", "arrow", "curve", "connector", "lane", "tick_marks", "legend",
    "check_overlaps", "check_bounds", "validate",
    "write_svg", "output_dir", "find_sharp_node_modules", "rasterize_hint", "SHARP_NODE_MODULES",
]

# --------------------------------------------------------------------------- palette and fonts ---
GREEN, ORANGE, RED = "#76B900", "#EF9100", "#C8102E"          # brand accents: ok / caution / stop
BLUE, PURPLE = "#0074DF", "#952FC6"                            # two neutral "flow" colours
GREY, DK, MUTED, FAINT, PANEL = "#757575", "#313131", "#9A9A9A", "#C0C0C0", "#F2F2F2"
WHITE = "#fff"
F = "Inter,'DejaVu Sans',Helvetica,Arial,sans-serif"           # proportional stack
M = "'Roboto Mono','DejaVu Sans Mono',Menlo,monospace"         # monospace stack (code, versions)

Number = Union[int, float]
Point = Tuple[Number, Number]

# The ``node_modules`` directory that holds the ``sharp`` rasterizer, for a caller that wants to
# pin it in code. ``None`` (the default) lets :func:`find_sharp_node_modules` look it up: the
# ``DIAGRAM_SHARP_NODE_MODULES`` environment variable, then ``./node_modules``, then ``npm root -g``.
SHARP_NODE_MODULES: Optional[str] = None


# ------------------------------------------------------------------------------ number/text utils ---
def fmt(x: Number) -> str:
    """Format a coordinate deterministically: at most 2 decimals, no trailing zeros, never ``-0``."""
    s = f"{float(x):.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def esc(s: str) -> str:
    """Escape text for SVG content. Runs of spaces become NBSPs so ``1.0   1.1`` keeps its gap."""
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r" {2,}", lambda m: " " + "&#160;" * (len(m.group()) - 1), s)


# Advance widths in em, DejaVu Sans -- the widest member of the stack, so the estimate is
# conservative for Inter/Helvetica/Arial: labels may come out a little smaller than strictly
# necessary, but they never clip. Unknown characters count as 0.7 em.
_WIDTHS: Dict[str, float] = {}
for _chars, _w in (
    ("ijl'", 0.278), (" .,·", 0.318), ("/:;|\\", 0.337), ("f", 0.352), ("-", 0.361),
    ("()[]", 0.39), ("t", 0.392), ("!", 0.401), ("r", 0.411), ('"', 0.46), ("*_`–°", 0.5),
    ("s", 0.521), ("z", 0.525), ("?", 0.531), ("c", 0.55), ("k", 0.579), ("vxy", 0.592),
    ("o", 0.612), ("a", 0.613), ("e", 0.615), ("hnuµ", 0.634), ("bdgpq", 0.635),
    ("0123456789${}", 0.636), ("&", 0.78), ("w", 0.818), ("m", 0.974),
    ("IJ", 0.295), ("L", 0.557), ("F", 0.575), ("P", 0.603), ("TY", 0.611), ("E", 0.632),
    ("S", 0.635), ("K", 0.656), ("AV", 0.684), ("XZ", 0.685), ("B", 0.686), ("R", 0.695),
    ("C", 0.698), ("U", 0.732), ("N", 0.748), ("H", 0.752), ("D", 0.77), ("G", 0.775),
    ("OQ", 0.787), ("#+<=>^~×→", 0.838), ("M", 0.863), ("%", 0.95), ("W", 0.989),
    ("@—", 1.0),
):
    for _ch in _chars:
        _WIDTHS[_ch] = _w
_DEFAULT_WIDTH = 0.7
_MONO_WIDTH = 0.602
_BOLD_FACTOR = 1.13                  # DejaVu Sans Bold vs Book, measured
_ASCENT, _DESCENT = 0.78, 0.24      # glyph box above/below the baseline, in em
_CAP = 0.72                          # cap height in em, used to centre a label vertically


def _is_mono(family: str) -> bool:
    return "mono" in family.lower()


def _is_bold(weight: Union[str, int]) -> bool:
    w = str(weight).lower()
    return w in ("bold", "bolder", "semibold") or (w.isdigit() and int(w) >= 600)


def text_width(s: str, size: Number, weight: Union[str, int] = "normal", family: str = F) -> float:
    """Estimate the rendered width of ``s`` in px (about 0.5-0.6 em per character, 0.6 for mono)."""
    if _is_mono(family):
        em = _MONO_WIDTH * len(s)
    else:
        em = sum(_WIDTHS.get(ch, _DEFAULT_WIDTH) for ch in s)
    if _is_bold(weight):
        em *= _BOLD_FACTOR
    return round(em * float(size), 2)


MIN_TEXT_PX = 11.0
"""The smallest font size a figure may use; :func:`validate` rejects anything below it."""


def fit_label(s: str, w: Number, size: Number, min_size: Number = MIN_TEXT_PX,
              weight: Union[str, int] = "bold", family: str = F) -> float:
    """Shrink ``size`` in 0.5 px steps until ``s`` fits into ``w`` px; never below ``min_size``.

    ``min_size`` defaults to the 11 px floor; a label that still does not fit at the floor needs a
    wider box or a shorter string, not smaller text.
    """
    size = float(size)
    while size - 0.5 >= float(min_size) and text_width(s, size, weight, family) > float(w):
        size -= 0.5
    return size


def wrap_text(s: str, max_width: Number, size: Number, weight: Union[str, int] = "normal",
              family: str = F) -> List[str]:
    """Greedy word wrap of ``s`` to ``max_width`` px; explicit newlines start a new line."""
    lines: List[str] = []
    for para in s.split("\n"):
        cur = ""
        for word in para.split():
            cand = f"{cur} {word}" if cur else word
            if cur and text_width(cand, size, weight, family) > float(max_width):
                lines.append(cur)
                cur = word
            else:
                cur = cand
        lines.append(cur)
    return lines


def _luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    rgb = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast_text(fill: str) -> str:
    """Pick the label colour for a fill: DK on light and mid fills, white on dark fills.

    The threshold sits below the brand green (luminance 0.385) and orange (0.386), so labels on
    them are dark: white on either is about 2.4:1, below the 4.5:1 that body text needs.
    """
    f = fill.lower()
    if f in ("none", "white", "#fff", "#ffffff", PANEL.lower(), FAINT.lower()) or not f.startswith("#"):
        return DK
    return DK if _luminance(f) > 0.30 else WHITE


def sublabel_text(fill: str, label_color: str) -> str:
    """Pick the sublabel colour for a box: the label colour on dark fills, DK on mid fills (the
    brand green and orange), GREY only on light fills, where grey still reads."""
    if label_color != DK:
        return label_color
    f = fill.lower()
    if f in ("none", "white", "#fff", "#ffffff", PANEL.lower(), FAINT.lower()) or not f.startswith("#"):
        return GREY
    return GREY if _luminance(f) > 0.6 else DK


def _dash(width: Number) -> str:
    return f"{fmt(3 * float(width))} {fmt(2 * float(width))}"


def _head(width: Number) -> Tuple[float, float]:
    """Arrowhead length and width for a line weight -- the head grows with the stroke."""
    return 5.5 * float(width), 4.5 * float(width)


# -------------------------------------------------------------------------------------- canvas ---
class Rect(NamedTuple):
    """A placed rectangle; returned by :func:`box`, :func:`lane`, :func:`legend`, :func:`text_block`."""

    x: float
    y: float
    w: float
    h: float

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


class TextBox(NamedTuple):
    """Estimated extent of one drawn string, kept for :func:`check_overlaps` / :func:`check_bounds`."""

    x0: float
    y0: float
    x1: float
    y1: float
    label: str


class Canvas:
    """Collects SVG elements and renders a standalone SVG document.

    ``title`` and ``desc`` are mandatory: they become the ``<title>``/``<desc>`` of the SVG and
    are the only thing a screen reader gets. ``background`` is white by default; pass ``PANEL``
    for a tinted figure or ``"none"`` for a transparent one.
    """

    def __init__(self, width: Number, height: Number, title: str, desc: str,
                 background: str = WHITE) -> None:
        if not title.strip() or not desc.strip():
            raise ValueError("every diagram needs a non-empty title and desc")
        self.width, self.height = float(width), float(height)
        self.title, self.desc, self.background = title, desc, background
        self.elements: List[str] = []
        self.texts: List[TextBox] = []
        self._markers: Dict[str, str] = {}

    def add(self, element: str) -> None:
        """Append one raw SVG element (one line of the output)."""
        self.elements.append(element)

    def note_text(self, tb: TextBox) -> None:
        """Register the extent of a text-bearing shape for the overlap/bounds checks."""
        self.texts.append(tb)

    def marker(self, color: str, width: Number) -> str:
        """Return the id of an arrowhead marker for ``color``/``width``, defining it on first use."""
        key = re.sub(r"[^a-z0-9]", "", color.lower()) or "none"
        mid = f"arrow-{key}-{fmt(width).replace('.', 'p')}"
        if mid not in self._markers:
            hl, hw = _head(width)
            self._markers[mid] = (
                f'<marker id="{mid}" markerUnits="userSpaceOnUse" markerWidth="{fmt(hl)}" '
                f'markerHeight="{fmt(hw)}" refX="0" refY="{fmt(hw / 2)}" orient="auto" '
                f'overflow="visible"><path d="M0,0 L{fmt(hl)},{fmt(hw / 2)} L0,{fmt(hw)} z" '
                f'fill="{color}"/></marker>')
        return mid

    def render(self) -> str:
        """Render the complete SVG document, one element per line, ``<title>``/``<desc>`` first."""
        w, h = fmt(self.width), fmt(self.height)
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
               f'viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc">',
               f'<title id="title">{esc(self.title)}</title>',
               f'<desc id="desc">{esc(self.desc)}</desc>']
        if self._markers:
            out.append("<defs>" + "".join(self._markers[k] for k in sorted(self._markers)) + "</defs>")
        if self.background not in ("none", "", None):
            out.append(f'<rect width="{w}" height="{h}" fill="{self.background}"/>')
        out.extend(self.elements)
        out.append("</svg>")
        return "\n".join(out) + "\n"


# ------------------------------------------------------------------------------------- shapes ---
def text(c: Canvas, x: Number, y: Number, s: str, size: Number = 14, weight: Union[str, int] = "normal",
         anchor: str = "start", fill: str = DK, family: str = F) -> TextBox:
    """Draw one line of text with its baseline at ``y``; ``anchor`` is start/middle/end."""
    s = str(s)
    attrs = (f'x="{fmt(x)}" y="{fmt(y)}" font-family="{family}" font-size="{fmt(size)}" '
             f'fill="{fill}"')
    if anchor != "start":
        attrs += f' text-anchor="{anchor}"'
    if str(weight) != "normal":
        attrs += f' font-weight="{weight}"'
    c.add(f"<text {attrs}>{esc(s)}</text>")
    w = text_width(s, size, weight, family)
    x0 = float(x) - (w / 2 if anchor == "middle" else w if anchor == "end" else 0.0)
    tb = TextBox(round(x0, 2), round(float(y) - _ASCENT * float(size), 2),
                 round(x0 + w, 2), round(float(y) + _DESCENT * float(size), 2), s)
    c.note_text(tb)
    return tb


def text_block(c: Canvas, x: Number, y: Number, s: str, max_width: Number, size: Number = 13,
               fill: str = GREY, anchor: str = "start", weight: Union[str, int] = "normal",
               family: str = F, line_height: float = 1.45) -> Rect:
    """Word-wrap ``s`` into ``max_width`` px and draw it; ``y`` is the first baseline.

    Returns the rectangle the lines occupy (for the anchor, ``x`` is the left edge, centre or
    right edge of that rectangle).
    """
    lines = wrap_text(s, max_width, size, weight, family)
    lh = float(size) * line_height
    boxes = [text(c, x, float(y) + i * lh, ln, size, weight, anchor, fill, family)
             for i, ln in enumerate(lines)]
    x0 = min(b.x0 for b in boxes)
    x1 = max(b.x1 for b in boxes)
    return Rect(x0, boxes[0].y0, x1 - x0, boxes[-1].y1 - boxes[0].y0)


def box(c: Canvas, x: Number, y: Number, w: Number, h: Number, label: Optional[str] = None,
        fill: str = PANEL, stroke: str = "none", rx: Number = 6, label_size: Number = 14,
        sublabel: Optional[str] = None, label_fill: Optional[str] = None,
        sublabel_size: Optional[Number] = None, stroke_width: Number = 2, dashed: bool = False,
        label_weight: Union[str, int] = "bold", label_family: str = F) -> Rect:
    """A rounded rectangle with an optional centred label and a smaller sublabel beneath it.

    The label shrinks (:func:`fit_label`) until it fits the box minus 8 px of padding on each
    side. The label colour defaults to :func:`contrast_text` of the fill.
    """
    attrs = (f'x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" rx="{fmt(rx)}" '
             f'fill="{fill}"')
    if stroke != "none":
        attrs += f' stroke="{stroke}" stroke-width="{fmt(stroke_width)}"'
        if dashed:
            attrs += f' stroke-dasharray="{_dash(stroke_width)}"'
    c.add(f"<rect {attrs}/>")
    if label is not None:
        fg = label_fill or contrast_text(fill)
        inner = float(w) - 16
        ls = fit_label(label, inner, label_size, weight=label_weight, family=label_family)
        cx, cy = float(x) + float(w) / 2, float(y) + float(h) / 2
        if sublabel is None:
            text(c, cx, cy + 0.5 * _CAP * ls, label, ls, label_weight, "middle", fg, label_family)
        else:
            ss = fit_label(sublabel, inner, sublabel_size or max(ls - 2, MIN_TEXT_PX), min_size=MIN_TEXT_PX,
                           weight="normal", family=label_family)
            gap = 6.0
            block = _CAP * ls + _DESCENT * ls + gap + _CAP * ss + _DESCENT * ss
            yb1 = cy - block / 2 + _CAP * ls
            yb2 = yb1 + _DESCENT * ls + gap + _CAP * ss
            text(c, cx, yb1, label, ls, label_weight, "middle", fg, label_family)
            text(c, cx, yb2, sublabel, ss, "normal", "middle", sublabel_text(fill, fg), label_family)
    return Rect(float(x), float(y), float(w), float(h))


def arrow(c: Canvas, x1: Number, y1: Number, x2: Number, y2: Number, stroke: str = GREY,
          width: Number = 2, head: bool = True, dashed: bool = False) -> None:
    """A straight connector from (x1, y1) to (x2, y2); the arrowhead tip lands exactly on (x2, y2)."""
    x1, y1, x2, y2 = float(x1), float(y1), float(x2), float(y2)
    ex, ey = x2, y2
    if head:
        hl = _head(width)[0]
        d = math.hypot(x2 - x1, y2 - y1)
        if d > hl:                       # end the line at the base of the head
            ex, ey = x2 - (x2 - x1) / d * hl, y2 - (y2 - y1) / d * hl
    attrs = (f'x1="{fmt(x1)}" y1="{fmt(y1)}" x2="{fmt(ex)}" y2="{fmt(ey)}" stroke="{stroke}" '
             f'stroke-width="{fmt(width)}"')
    if dashed:
        attrs += f' stroke-dasharray="{_dash(width)}"'
    if head:
        attrs += f' marker-end="url(#{c.marker(stroke, width)})"'
    c.add(f"<line {attrs}/>")


def _stroke_path(c: Canvas, d: str, stroke: str, width: Number, head: bool, dashed: bool) -> None:
    attrs = f'd="{d}" fill="none" stroke="{stroke}" stroke-width="{fmt(width)}"'
    if dashed:
        attrs += f' stroke-dasharray="{_dash(width)}"'
    if head:
        attrs += f' marker-end="url(#{c.marker(stroke, width)})"'
    c.add(f"<path {attrs}/>")


def curve(c: Canvas, points: Sequence[Point], stroke: str = GREY, width: Number = 2,
          head: bool = True, dashed: bool = False, smooth: float = 1.0) -> None:
    """A smooth polyline (Catmull-Rom spline) through ``points``; two points give a straight line.

    ``smooth`` scales the tangents: 1.0 is the classic spline, 0 degenerates to straight segments.
    """
    pts = [(float(px), float(py)) for px, py in points]
    if len(pts) < 2:
        raise ValueError("curve needs at least two points")
    if head:
        hl = _head(width)[0]
        (ax, ay), (bx, by) = pts[-2], pts[-1]
        d = math.hypot(bx - ax, by - ay)
        if d > hl:
            pts[-1] = (bx - (bx - ax) / d * hl, by - (by - ay) / d * hl)
    seg = [f"M{fmt(pts[0][0])},{fmt(pts[0][1])}"]
    if len(pts) == 2:
        seg.append(f"L{fmt(pts[1][0])},{fmt(pts[1][1])}")
    else:
        k = smooth / 6.0
        ext = [pts[0]] + pts + [pts[-1]]
        for i in range(1, len(ext) - 2):
            p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
            c1 = (p1[0] + k * (p2[0] - p0[0]), p1[1] + k * (p2[1] - p0[1]))
            c2 = (p2[0] - k * (p3[0] - p1[0]), p2[1] - k * (p3[1] - p1[1]))
            seg.append(f"C{fmt(c1[0])},{fmt(c1[1])} {fmt(c2[0])},{fmt(c2[1])} "
                       f"{fmt(p2[0])},{fmt(p2[1])}")
    _stroke_path(c, " ".join(seg), stroke, width, head, dashed)


def connector(c: Canvas, x1: Number, y1: Number, x2: Number, y2: Number, stroke: str = GREY,
              width: Number = 2, head: bool = True, dashed: bool = False, bow: float = 0.42,
              vertical: bool = False) -> None:
    """An S-curve between two ports that leaves and arrives horizontally (or vertically).

    This is the connector of the sensor-versioning diagrams: use it between boxes in different
    rows/columns where a straight :func:`arrow` would cut across the layout.
    """
    x1, y1, x2, y2 = float(x1), float(y1), float(x2), float(y2)
    if head:
        hl = _head(width)[0]
        if vertical and abs(y2 - y1) > hl:
            y2 -= math.copysign(hl, y2 - y1)
        elif not vertical and abs(x2 - x1) > hl:
            x2 -= math.copysign(hl, x2 - x1)
    if vertical:
        dy = (y2 - y1) * bow
        d = f"M{fmt(x1)},{fmt(y1)} C{fmt(x1)},{fmt(y1 + dy)} {fmt(x2)},{fmt(y2 - dy)} {fmt(x2)},{fmt(y2)}"
    else:
        dx = (x2 - x1) * bow
        d = f"M{fmt(x1)},{fmt(y1)} C{fmt(x1 + dx)},{fmt(y1)} {fmt(x2 - dx)},{fmt(y2)} {fmt(x2)},{fmt(y2)}"
    _stroke_path(c, d, stroke, width, head, dashed)


def lane(c: Canvas, x: Number, y: Number, w: Number, h: Number, label: str, fill: str = PANEL,
         label_width: Optional[Number] = None, label_size: Number = 13, label_fill: str = DK,
         rx: Number = 4) -> Rect:
    """A timeline lane: a tinted band with its name in a label column on the left.

    Returns the content area to the right of the label column, where the author places the
    events. Pass the same ``label_width`` to every lane of a timeline so the columns align.
    """
    x, y, w, h = float(x), float(y), float(w), float(h)
    c.add(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" rx="{fmt(rx)}" '
          f'fill="{fill}"/>')
    lw = float(label_width) if label_width is not None else text_width(label, label_size, "bold") + 24
    ls = fit_label(label, lw - 20, label_size)
    text(c, x + 12, y + h / 2 + 0.5 * _CAP * ls, label, ls, "bold", "start", label_fill)
    c.add(f'<line x1="{fmt(x + lw)}" y1="{fmt(y + 6)}" x2="{fmt(x + lw)}" y2="{fmt(y + h - 6)}" '
          f'stroke="{FAINT}" stroke-width="1"/>')
    return Rect(x + lw, y, w - lw, h)


def tick_marks(c: Canvas, x: Number, y: Number, length: Number, positions: Sequence[Number],
               labels: Optional[Sequence[str]] = None, horizontal: bool = True, tick: Number = 6,
               stroke: str = GREY, width: Number = 1.5, size: Number = 12, fill: str = GREY,
               axis: bool = True) -> None:
    """An axis from (x, y) with ticks at ``positions`` (px offsets along it) and optional labels.

    Horizontal axes run to the right with ticks and labels below; vertical axes run downward
    (SVG y grows down) with ticks and right-aligned labels to the left.
    """
    x, y, length = float(x), float(y), float(length)
    sw = f'stroke="{stroke}" stroke-width="{fmt(width)}"'
    if axis:
        ex, ey = (x + length, y) if horizontal else (x, y + length)
        c.add(f'<line x1="{fmt(x)}" y1="{fmt(y)}" x2="{fmt(ex)}" y2="{fmt(ey)}" {sw}/>')
    for i, p in enumerate(positions):
        p = float(p)
        lbl = labels[i] if labels is not None and i < len(labels) else None
        if horizontal:
            c.add(f'<line x1="{fmt(x + p)}" y1="{fmt(y)}" x2="{fmt(x + p)}" y2="{fmt(y + float(tick))}" {sw}/>')
            if lbl is not None:
                text(c, x + p, y + float(tick) + float(size), lbl, size, "normal", "middle", fill)
        else:
            c.add(f'<line x1="{fmt(x)}" y1="{fmt(y + p)}" x2="{fmt(x - float(tick))}" y2="{fmt(y + p)}" {sw}/>')
            if lbl is not None:
                text(c, x - float(tick) - 6, y + p + 0.5 * _CAP * float(size), lbl, size, "normal", "end", fill)


def _swatch(c: Canvas, x: float, y: float, s: float, color: str, style: str) -> None:
    mid = y + s / 2
    if style == "line" or style == "dashed":
        dash = f' stroke-dasharray="{_dash(2)}"' if style == "dashed" else ""
        c.add(f'<line x1="{fmt(x)}" y1="{fmt(mid)}" x2="{fmt(x + s + 4)}" y2="{fmt(mid)}" '
              f'stroke="{color}" stroke-width="2"{dash}/>')
    elif style == "outline":
        c.add(f'<rect x="{fmt(x + 1)}" y="{fmt(y + 1)}" width="{fmt(s - 2)}" height="{fmt(s - 2)}" '
              f'rx="2" fill="none" stroke="{color}" stroke-width="1.5" stroke-dasharray="{_dash(1.5)}"/>')
    else:
        c.add(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(s)}" height="{fmt(s)}" rx="2" fill="{color}"/>')


def legend(c: Canvas, x: Number, y: Number, entries: Sequence[Sequence[str]], size: Number = 12,
           swatch: Number = 12, gap: Number = 22, horizontal: bool = True, fill: str = DK) -> Rect:
    """A legend of ``(label, color)`` or ``(label, color, style)`` entries starting at (x, y).

    ``style`` is ``box`` (default), ``outline`` (dashed hollow box), ``line`` or ``dashed``.
    Entries run left to right, or top to bottom with ``horizontal=False``. Returns the extent.
    """
    x, y, s, gap = float(x), float(y), float(swatch), float(gap)
    cx, cy = x, y
    row = max(s, float(size)) + 8
    sw_len = s + 4 if any(len(e) > 2 and e[2] in ("line", "dashed") for e in entries) else s
    widest = 0.0
    for e in entries:
        label, color = e[0], e[1]
        style = e[2] if len(e) > 2 else "box"
        _swatch(c, cx, cy, s, color, style)
        tb = text(c, cx + sw_len + 7, cy + s / 2 + 0.5 * _CAP * float(size), label, size, "normal",
                  "start", fill)
        ew = tb.x1 - cx
        widest = max(widest, ew)
        if horizontal:
            cx += ew + gap
        else:
            cy += row
    if horizontal:
        return Rect(x, y, cx - gap - x, max(s, float(size)))
    return Rect(x, y, widest, cy - y)


# ------------------------------------------------------------------------------------- checks ---
def _overlap_area(a: TextBox, b: TextBox, pad: float) -> float:
    w = min(a.x1, b.x1) - max(a.x0, b.x0) + 2 * pad
    h = min(a.y1, b.y1) - max(a.y0, b.y0) + 2 * pad
    return w * h if w > 0 and h > 0 else 0.0


def check_overlaps(canvas: Canvas, min_area: float = 4.0, pad: float = 2.0) -> List[Tuple[TextBox, TextBox]]:
    """Return every pair of text-bearing shapes whose estimated boxes intersect by > ``min_area`` px^2.

    Each box is first grown by ``pad`` px on every side, so two labels that merely touch (less
    than ``2 * pad`` px of air between them) are reported as well.
    """
    hits = []
    ts = canvas.texts
    for i in range(len(ts)):
        for j in range(i + 1, len(ts)):
            if _overlap_area(ts[i], ts[j], pad) > min_area:
                hits.append((ts[i], ts[j]))
    return hits


def check_bounds(canvas: Canvas, margin: float = 8.0) -> List[TextBox]:
    """Return every text that comes closer than ``margin`` px to the canvas edge (or leaves it)."""
    return [tb for tb in canvas.texts
            if tb.x0 < margin or tb.y0 < margin
            or tb.x1 > canvas.width - margin or tb.y1 > canvas.height - margin]


def check_text_sizes(canvas: Canvas, min_px: float = MIN_TEXT_PX) -> List[float]:
    """Font sizes used on the canvas that lie below ``min_px``, smallest first."""
    sizes = {float(m) for m in re.findall(r'font-size="([0-9.]+)"', "".join(canvas.elements))}
    return sorted(s for s in sizes if s < float(min_px))


def validate(canvas: Canvas, min_area: float = 4.0, margin: float = 8.0, pad: float = 2.0) -> None:
    """Raise ``ValueError`` naming every overlap, edge-hugging text and too-small text; call before writing."""
    problems = [f"overlap: {a.label!r} / {b.label!r}" for a, b in check_overlaps(canvas, min_area, pad)]
    problems += [f"touches canvas edge: {tb.label!r} at ({fmt(tb.x0)},{fmt(tb.y0)})-({fmt(tb.x1)},{fmt(tb.y1)})"
                 for tb in check_bounds(canvas, margin)]
    problems += [f"text below {fmt(MIN_TEXT_PX)} px: {fmt(s)} px" for s in check_text_sizes(canvas)]
    if problems:
        raise ValueError(f"{canvas.title!r}: " + "; ".join(problems))


# ---------------------------------------------------------------------------------------- I/O ---
def write_svg(path: Union[str, "os.PathLike[str]"], svg: str) -> pathlib.Path:
    """Write ``svg`` with LF line endings, no trailing whitespace and exactly one final newline."""
    lines = [ln.rstrip() for ln in svg.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    return p


def output_dir(script_file: str, argv: Optional[Sequence[str]] = None) -> pathlib.Path:
    """The directory a generator writes to: its first argument, else the generator's own directory.

    ``python3 generate_diagrams.py`` regenerates in place; ``python3 generate_diagrams.py /tmp/check``
    writes elsewhere so the result can be diffed against the committed SVGs.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    out = pathlib.Path(args[0]) if args else pathlib.Path(script_file).resolve().parent
    out.mkdir(parents=True, exist_ok=True)
    return out


def find_sharp_node_modules(node_modules: Optional[str] = None) -> Optional[str]:
    """The ``node_modules`` directory ``require('sharp')`` resolves from, or ``None`` if there is none.

    Checked in order: the argument, ``$DIAGRAM_SHARP_NODE_MODULES`` and :data:`SHARP_NODE_MODULES`
    (these three are taken as given), then a ``node_modules`` in the current directory and the
    global ``npm root -g``, which count only if they actually contain ``sharp``.
    """
    pinned = node_modules or os.environ.get("DIAGRAM_SHARP_NODE_MODULES") or SHARP_NODE_MODULES
    if pinned:
        return str(pinned)
    candidates = [pathlib.Path.cwd() / "node_modules"]
    npm = shutil.which("npm")
    if npm:
        try:
            root = subprocess.run([npm, "root", "-g"], capture_output=True, text=True, timeout=20,
                                  check=False).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            root = ""
        if root:
            candidates.append(pathlib.Path(root))
    for nm in candidates:
        if (nm / "sharp").is_dir():
            return str(nm)
    return None


def rasterize_hint(svg: str = "x.svg", png: str = "x.png", density: int = 150,
                   node_modules: Optional[str] = None) -> str:
    """The shell command that rasterizes ``svg`` to ``png`` with the ``sharp`` package.

    The ``node_modules`` directory comes from :func:`find_sharp_node_modules`. When no install is
    found, the returned text says how to get one instead: ``npm install sharp`` in a directory of
    your choice, then point ``DIAGRAM_SHARP_NODE_MODULES`` (or the ``node_modules`` argument) at it.
    """

    def js(s: str) -> str:
        return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"

    def sh(s: str) -> str:
        return "'" + s.replace("'", "'\\''") + "'"

    program = f"require('sharp')({js(svg)},{{density:{int(density)}}}).png().toFile({js(png)})"
    nm = find_sharp_node_modules(node_modules)
    if nm is None:
        return ("# sharp is not installed: run `npm install sharp` in a directory of your choice, then\n"
                "# export DIAGRAM_SHARP_NODE_MODULES=/path/to/node_modules and call this again, or run\n"
                f"NODE_PATH=/path/to/node_modules node -e \"{program}\"")
    return f"NODE_PATH={sh(nm)} node -e \"{program}\""
