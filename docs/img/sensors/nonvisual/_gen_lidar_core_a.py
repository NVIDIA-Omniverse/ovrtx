#!/usr/bin/env python3
"""Lidar generic core model figures, group A.

The anatomy of a firing pattern, the two azimuth conventions, the three field-of-view
windows and how a solid-state scan plays out over simulation steps.
``python3 -B _gen_lidar_core_a.py`` inside this directory regenerates only these SVGs in
place; ``generate_diagrams.py`` runs every ``_gen_*.py`` module of the directory.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import _diagram_lib as dl  # noqa: E402

_ASCENT, _DESCENT = 0.78, 0.24      # glyph box above/below the baseline, in em (as in _diagram_lib)
_F = dl.fmt


# ------------------------------------------------------------------------------- local helpers ---
def code(s: str):
    """Mark a run of a :func:`rich` line as an attribute name or value (monospace)."""
    return (s, dl.M)


def rich(c, x, y, runs, size=12, anchor="start", fill=dl.DK, weight="normal"):
    """One text line of mixed runs: plain strings are prose (dl.F), :func:`code` runs are mono.

    Rendered as one ``<text>`` with ``<tspan>`` children so the overlap check sees one box;
    ``xml:space="preserve"`` keeps the spaces at the run boundaries.
    """
    width, spans, label = 0.0, [], []
    for run in runs:
        s, fam = (run, dl.F) if isinstance(run, str) else run
        width += dl.text_width(s, size, weight, fam)
        label.append(s)
        spans.append(f'<tspan font-family="{fam}">{dl.esc(s)}</tspan>')
    attrs = (f'x="{_F(x)}" y="{_F(y)}" font-family="{dl.F}" font-size="{_F(size)}" fill="{fill}" '
             f'xml:space="preserve"')
    if anchor != "start":
        attrs += f' text-anchor="{anchor}"'
    if str(weight) != "normal":
        attrs += f' font-weight="{weight}"'
    c.add(f"<text {attrs}>{''.join(spans)}</text>")
    x0 = float(x) - (width / 2 if anchor == "middle" else width if anchor == "end" else 0.0)
    tb = dl.TextBox(round(x0, 2), round(float(y) - _ASCENT * size, 2),
                    round(x0 + width, 2), round(float(y) + _DESCENT * size, 2), "".join(label))
    c.note_text(tb)
    return tb


def polar(cx, cy, r, deg):
    """Point at radius ``r`` and ``deg`` degrees clockwise from straight up (+X forward)."""
    a = math.radians(deg)
    return cx + r * math.sin(a), cy - r * math.cos(a)


def arc_d(cx, cy, r, a0, a1):
    """Arc path data from ``a0`` to ``a1`` (clockwise degrees from up; a1 < a0 runs counter-clockwise)."""
    x0, y0 = polar(cx, cy, r, a0)
    x1, y1 = polar(cx, cy, r, a1)
    span = a1 - a0
    large = 1 if abs(span) > 180 else 0
    sweep = 1 if span >= 0 else 0
    return f"M{_F(x0)},{_F(y0)} A{_F(r)},{_F(r)} 0 {large} {sweep} {_F(x1)},{_F(y1)}"


def arc(c, cx, cy, r, a0, a1, stroke, width=2, dashed=False, head=False):
    """A stroked arc; with ``head`` the arrowhead tip lands exactly at ``a1``."""
    a_end = a1
    if head:
        trim = math.degrees(5.5 * width / r)
        a_end = a1 - trim if a1 >= a0 else a1 + trim
    attrs = f'd="{arc_d(cx, cy, r, a0, a_end)}" fill="none" stroke="{stroke}" stroke-width="{_F(width)}"'
    if dashed:
        attrs += f' stroke-dasharray="{_F(3 * width)} {_F(2 * width)}"'
    if head:
        attrs += f' marker-end="url(#{c.marker(stroke, width)})"'
    c.add(f"<path {attrs}/>")


def sector(c, cx, cy, r_in, r_out, a0, a1, fill, opacity=1.0):
    """A filled (annular) sector from ``a0`` to ``a1`` degrees clockwise from up."""
    span = a1 - a0
    large = 1 if abs(span) > 180 else 0
    sweep = 1 if span >= 0 else 0
    ox0, oy0 = polar(cx, cy, r_out, a0)
    ox1, oy1 = polar(cx, cy, r_out, a1)
    d = f"M{_F(ox0)},{_F(oy0)} A{_F(r_out)},{_F(r_out)} 0 {large} {sweep} {_F(ox1)},{_F(oy1)} "
    if r_in > 0:
        ix0, iy0 = polar(cx, cy, r_in, a0)
        ix1, iy1 = polar(cx, cy, r_in, a1)
        d += f"L{_F(ix1)},{_F(iy1)} A{_F(r_in)},{_F(r_in)} 0 {large} {1 - sweep} {_F(ix0)},{_F(iy0)} Z"
    else:
        d += f"L{_F(cx)},{_F(cy)} Z"
    op = "" if opacity >= 1.0 else f' fill-opacity="{_F(opacity)}"'
    c.add(f'<path d="{d}" fill="{fill}"{op}/>')


def circle(c, cx, cy, r, fill="none", stroke=dl.FAINT, width=1.5, dashed=False):
    attrs = f'cx="{_F(cx)}" cy="{_F(cy)}" r="{_F(r)}" fill="{fill}"'
    if stroke != "none":
        attrs += f' stroke="{stroke}" stroke-width="{_F(width)}"'
        if dashed:
            attrs += f' stroke-dasharray="{_F(3 * width)} {_F(2 * width)}"'
    c.add(f"<circle {attrs}/>")


def dot(c, x, y, r, color, hollow=False):
    """A filled dot, or a hollow one (white fill, colored ring)."""
    if hollow:
        circle(c, x, y, r, fill=dl.WHITE, stroke=color, width=2)
    else:
        circle(c, x, y, r, fill=color, stroke="none")


def line(c, x1, y1, x2, y2, stroke=dl.GREY, width=1.5, dashed=False):
    attrs = (f'x1="{_F(x1)}" y1="{_F(y1)}" x2="{_F(x2)}" y2="{_F(y2)}" stroke="{stroke}" '
             f'stroke-width="{_F(width)}"')
    if dashed:
        attrs += f' stroke-dasharray="{_F(3 * width)} {_F(2 * width)}"'
    c.add(f"<line {attrs}/>")


def dim(c, x1, y1, x2, y2, stroke=dl.DK, width=1.2, tick=5):
    """A dimension line with perpendicular end ticks."""
    line(c, x1, y1, x2, y2, stroke, width)
    d = math.hypot(x2 - x1, y2 - y1)
    nx, ny = -(y2 - y1) / d * tick, (x2 - x1) / d * tick
    for px, py in ((x1, y1), (x2, y2)):
        line(c, px - nx, py - ny, px + nx, py + ny, stroke, width)


def panel(c, x, y, w, h):
    """A dashed, unfilled rounded frame grouping one part of a figure."""
    return dl.box(c, x, y, w, h, fill="none", stroke=dl.FAINT, rx=8, dashed=True, stroke_width=1.5)


def dot_stack(c, x, base_y, n, color, r=4.5, step=11):
    """``n`` dots stacked upward from ``base_y`` (a fire-time group)."""
    for i in range(n):
        dot(c, x, base_y - i * step, r, color)


# ------------------------------------------------------------------------------------ figures ---
def lidar_core_firing_pattern_anatomy(out_dir: pathlib.Path) -> None:
    W, H = 1140, 700
    PX, PY, PW, PH = 20, 20, 440, 490            # outer-layer panel
    QX, QY, QW, QH = 480, 20, 640, 490           # inner-layer panel
    IX, IY, IW, IH = 20, 530, 1100, 150          # solid-state band across the bottom
    CX, CY, R = 240, 300, 110                    # rotary head seen from above
    TICK_STEP, HILITE = 15, 30                   # tick spacing drawn, highlighted tick (deg CW from +X)
    STEP_MARK_A0 = 180                           # where the angular step is marked (deg CW from +X)
    SWEEP_A0, SWEEP_A1 = 95, 150                 # CW sweep arrow (deg CW from +X)
    SWEEP_LABEL = (CX + 146, CY + 72)
    PULL_MID = (440, 210)                        # waypoint of the pull-out curve
    OX, OY = 590, 340                            # origin of the expanded tick
    PCX, PCY, HW, VH = 805, 240, 108, 62         # reference frame the emitter rays reach
    # (horizontal, vertical) on the frame; chosen so that, seen from the origin, no two rays and
    # no ray and the dashed tick direction run within about 5 degrees of each other
    EMITTERS = ((-75, -45), (-60, 47), (60, 51), (30, -47), (85, 20))
    LABEL_OFF = ((8, 4), (8, -6), (8, -6), (8, 4), (8, -6))              # emitter number offsets
    AX, AY, ALEN = 560, 430, 500                 # fire-time axis
    FIRE_POS = (60, 170, 170, 290, 380)          # axis offset of emitters 1..5 (2 and 3 share one)
    FX, FY, FW, FH = 36, 572, 130, 92            # solid-state flat frame
    GRID_ROWS, GRID_COLS, GRID_DX, GRID_DY = 4, 7, 17, 21
    SMALL, BODY, TITLE, LINE = 11.5, 12, 15, 17

    c = dl.Canvas(W, H, "Anatomy of a firing pattern",
                  "A rotary sensor seen from above with ticks spaced by rotPatternFiringResDeg around "
                  "the rotation; one tick is expanded into its emitters fanned out by azimuthDeg and "
                  "elevationDeg, with their fireTimeNs offsets on a time axis beneath. Panels show scan "
                  "scheduling and an emitter-state API instance; a band beneath shows a solid-state sensor "
                  "with one tick per scan.")

    # scan scheduling -------------------------------------------------------------------------------
    panel(c, PX, PY, PW, PH)
    dl.text(c, PX + 16, PY + 26, "Scan scheduling", TITLE, "bold")
    dl.text(c, PX + 16, PY + 48, "frameRate  rotPatternFiringResDeg  numberOfEmitters", SMALL, fill=dl.GREY,
            family=dl.M)
    dl.text(c, PX + 16, PY + 66, "numberOfChannels  stateResolutionStep", SMALL, fill=dl.GREY, family=dl.M)

    circle(c, CX, CY, R)
    for k in range(360 // TICK_STEP):
        a = k * TICK_STEP
        if a == HILITE:
            continue
        x0, y0 = polar(CX, CY, R - 7, a)
        x1, y1 = polar(CX, CY, R + 7, a)
        line(c, x0, y0, x1, y1, dl.GREY, 1.5)
    x0, y0 = polar(CX, CY, R - 10, HILITE)
    x1, y1 = polar(CX, CY, R + 16, HILITE)
    line(c, x0, y0, x1, y1, dl.GREEN, 3)
    dot(c, CX, CY, 4, dl.DK)
    dl.text(c, CX, CY + 22, "sensor", 11, anchor="middle", fill=dl.GREY)
    dl.arrow(c, CX, CY, CX, CY - R - 34, dl.DK, 1.5)
    dl.text(c, CX, CY - R - 44, "+X forward (firing angle 0°)", BODY, anchor="middle")
    # the angular step between two neighboring ticks, marked at the bottom of the rim
    arc(c, CX, CY, R + 20, STEP_MARK_A0, STEP_MARK_A0 + TICK_STEP, dl.GREY, 1.5)
    for a in (STEP_MARK_A0, STEP_MARK_A0 + TICK_STEP):
        x0, y0 = polar(CX, CY, R + 15, a)
        x1, y1 = polar(CX, CY, R + 25, a)
        line(c, x0, y0, x1, y1, dl.GREY, 1.5)
    rich(c, CX, CY + R + 42, [code("rotPatternFiringResDeg"), " between neighboring ticks"], SMALL,
         anchor="middle")
    rich(c, CX, CY + R + 62, [code("360 / rotPatternFiringResDeg"), " ticks per rotation (floor or ceil)"],
         SMALL, anchor="middle")
    rich(c, CX, CY + R + 82, ["one rotation is one scan; ", code("frameRate"), " sets scans per second"],
         SMALL, anchor="middle")
    arc(c, CX, CY, R + 26, SWEEP_A0, SWEEP_A1, dl.BLUE, 2, head=True)
    dl.text(c, SWEEP_LABEL[0], SWEEP_LABEL[1], "CW sweep", SMALL, fill=dl.BLUE)

    # the pull-out ------------------------------------------------------------------------------
    sx, sy = polar(CX, CY, R + 16, HILITE)
    dl.curve(c, [(sx, sy), PULL_MID, (OX - 8, OY - 6)], dl.GREEN, 2, head=True, dashed=True)

    # emitter-state API instance -------------------------------------------------------------------------------
    panel(c, QX, QY, QW, QH)
    dl.text(c, QX + 16, QY + 26, "Emitter-state API instance (s001)", TITLE, "bold")
    dl.text(c, QX + 16, QY + 48, "emitterState:s001:  azimuthDeg  elevationDeg  fireTimeNs  channelId", SMALL,
            fill=dl.GREY, family=dl.M)
    rich(c, QX + 16, QY + 66, ["per-emitter arrays, ", code("numberOfEmitters"), " elements in each"], SMALL,
         fill=dl.GREY)

    dl.box(c, PCX - HW, PCY - VH, 2 * HW, 2 * VH, fill="none", stroke=dl.FAINT, rx=2, dashed=True,
           stroke_width=1.5)
    line(c, OX, OY, PCX, PCY, dl.GREY, 1.5, dashed=True)
    line(c, PCX - 6, PCY, PCX + 6, PCY, dl.GREY, 1.5)
    line(c, PCX, PCY - 6, PCX, PCY + 6, dl.GREY, 1.5)
    rich(c, PCX, PCY - VH - 12, ["tick position — ", code("azimuthDeg"), " is measured from here"], SMALL,
         anchor="middle", fill=dl.GREY)
    for h, v in EMITTERS:
        line(c, OX, OY, PCX + h, PCY + v, dl.BLUE, 1.5)
    for i, (h, v) in enumerate(EMITTERS):
        ex, ey = PCX + h, PCY + v
        dot(c, ex, ey, 4.5, dl.BLUE)
        dl.text(c, ex + LABEL_OFF[i][0], ey + LABEL_OFF[i][1], str(i + 1), 11, fill=dl.BLUE, family=dl.M)
    dot(c, OX, OY, 5.5, dl.GREEN)
    dl.text(c, OX, OY + 24, "one tick, expanded", SMALL, anchor="middle", fill=dl.GREEN)
    dim(c, PCX - HW, PCY + VH + 18, PCX + HW, PCY + VH + 18)
    rich(c, PCX, PCY + VH + 38, [code("azimuthDeg"), ": relative to the tick position"], SMALL, anchor="middle")
    dim(c, PCX + HW + 16, PCY - VH, PCX + HW + 16, PCY + VH)
    dl.text(c, PCX + HW + 26, PCY - 4, "elevationDeg", SMALL, family=dl.M)
    dl.text(c, PCX + HW + 26, PCY + 12, "absolute", SMALL)

    rich(c, AX, AY - 36, [code("fireTimeNs"), ": each emitter's delay from the tick start, in nanoseconds"],
         SMALL)
    dl.tick_marks(c, AX, AY, ALEN, (0,) + tuple(sorted(set(FIRE_POS))) + (ALEN,),
                  ("tick start", "1", "2, 3", "4", "5", "tick period"))
    seen = {}
    for p in FIRE_POS:
        n = seen.get(p, 0)
        dot(c, AX + p, AY - 8 - n * 11, 4.5, dl.BLUE)
        seen[p] = n + 1
    dl.text(c, AX + FIRE_POS[1], AY + 38, "one group: equal fire times fire together", SMALL, anchor="middle",
            fill=dl.GREY)
    dl.legend(c, QX + 16, QY + QH - 24, (("the tick that is expanded", dl.GREEN),
                                         ("other ticks of the rotation", dl.GREY),
                                         ("emitters of that tick", dl.BLUE)))

    # solid-state band --------------------------------------------------------------------------
    panel(c, IX, IY, IW, IH)
    dl.text(c, IX + 16, IY + 26, "Solid-state sensor — one tick per scan", 14, "bold")
    dl.box(c, FX, FY, FW, FH, fill=dl.PANEL, stroke=dl.FAINT, rx=4, stroke_width=1.5)
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            dot(c, FX + 14 + col * GRID_DX, FY + 14 + row * GRID_DY, 3, dl.BLUE)
    tx, ty = FX + FW + 18, FY + 34
    rich(c, tx, ty, ["The whole pattern is one tick, applied once per scan, with its emitters laid out in "
                     "lines (", code("numLines"), ", ", code("numRaysPerLine"), ")."], SMALL)
    rich(c, tx, ty + LINE, [code("rotPatternFiringResDeg"), " is not read; the angular extent comes from the "
                            "emitter ", code("azimuthDeg"), " and ", code("elevationDeg"), " arrays."], SMALL)
    rich(c, tx, ty + 2 * LINE, ["Every point of a solid-state scan carries ", code("TickId"), " 0."], SMALL)

    dl.validate(c)
    dl.write_svg(out_dir / "lidar_core_firing_pattern_anatomy.svg", c.render())


def lidar_core_azimuth_conventions(out_dir: pathlib.Path) -> None:
    W, H = 1180, 600
    LCX, LCY = 300, 330                          # firing-angle panel
    RCX, RCY = 880, 330                          # delivered-azimuth panel
    R = 150
    TITLE_Y, SUBTITLE_Y = 46, 68
    LBL = R + 36                                 # radius of the top and bottom cardinal labels
    SIDE = R + 14                                # the left/right cardinal labels start this far out
    WIN0, WIN1 = 0, 90                           # example window, firing angle
    ROI0, ROI1 = 110, 160                        # ROI interval, drawn without values
    WRAP0, WRAP1 = 320, 385                      # a window with start > end, crossing 0/360
    CW_A0, CW_A1 = 4, 26                         # sweep arrows just inside the rim
    CCW_A0, CCW_A1 = 356, 334
    POS_A0, POS_A1 = 356, 326                    # positive delivered azimuth
    OFF_A0, OFF_A1 = 282, 322                    # start offset rotation (deg CW from +X)
    NOTE_Y, LINE = 186, 16                       # first baseline of the notes beside the rims
    NOTE_DX = 128                                # notes right of a rim start here
    WRAP_DX = 124                                # the wrap note ends here, left of the rim
    DIR_DX, DIR_DY = 14, 62                      # direction labels beside the +X axis
    LEGEND = (40, 560)
    SMALL, BODY, TITLE = 11.5, 12, 15

    c = dl.Canvas(W, H, "Angle conventions of a rotary sensor",
                  "Two top-down views of a rotary sensor. Left: the firing angle measured clockwise from "
                  "the forward axis, before startAzimuthOffsetDeg, with the validStartAzimuthDeg to "
                  "validEndAzimuthDeg window and the ROI interval drawn as arcs, and arrows showing the "
                  "CW and CCW sweep directions. Right: the delivered azimuth measured counter-clockwise "
                  "from the forward axis in the range (-180, 180], including startAzimuthOffsetDeg.")

    def head(cx, cy, title, subtitle):
        dl.text(c, cx, TITLE_Y, title, TITLE, "bold", anchor="middle")
        rich(c, cx, SUBTITLE_Y, subtitle, SMALL, anchor="middle", fill=dl.GREY)
        circle(c, cx, cy, R)
        dot(c, cx, cy, 5, dl.DK)
        dl.arrow(c, cx, cy, cx, cy - R - 12, dl.DK, 1.5)

    def cardinals(cx, cy, top, right, bottom, left):
        dl.text(c, cx, cy - LBL + 4, top, BODY, anchor="middle")
        dl.text(c, cx + SIDE, cy + 4, right, BODY)
        dl.text(c, cx, cy + LBL + 9, bottom, BODY, anchor="middle")
        dl.text(c, cx - SIDE, cy + 4, left, BODY, anchor="end")

    # left: firing angle --------------------------------------------------------------------------
    sector(c, LCX, LCY, 0, R, WIN0, WIN1, dl.GREEN, 0.18)
    head(LCX, LCY, "Firing angle — where the window is measured",
         ["clockwise from +X, before ", code("startAzimuthOffsetDeg"), " is added"])
    cardinals(LCX, LCY, "0° (+X forward)", "90° (-Y, right)", "180° (behind)",
              "270° (+Y, left)")
    arc(c, LCX, LCY, R + 5, WIN0, WIN1, dl.GREEN, 4)
    wx = LCX + NOTE_DX
    dl.text(c, wx, NOTE_Y, "validStartAzimuthDeg ..", SMALL, family=dl.M)
    dl.text(c, wx, NOTE_Y + LINE, "validEndAzimuthDeg", SMALL, family=dl.M)
    dl.text(c, wx, NOTE_Y + 2 * LINE, "(example: 0° to 90°)", SMALL, fill=dl.GREY)
    arc(c, LCX, LCY, R + 16, ROI0, ROI1, dl.ORANGE, 3)
    rx, ry = polar(LCX, LCY, R + 32, (ROI0 + ROI1) / 2)
    dl.text(c, rx + 6, ry + 10, "minAzimuthROI ..", SMALL, family=dl.M)
    dl.text(c, rx + 6, ry + 10 + LINE, "maxAzimuthROI", SMALL, family=dl.M)
    dl.text(c, rx + 6, ry + 10 + 2 * LINE, "ROI interval, not the field of view", SMALL, fill=dl.GREY)
    arc(c, LCX, LCY, R + 22, WRAP0, WRAP1, dl.GREY, 2, dashed=True)
    dl.text(c, LCX - WRAP_DX, NOTE_Y, "a window with start > end", SMALL, anchor="end")
    dl.text(c, LCX - WRAP_DX, NOTE_Y + LINE, "wraps through 360°", SMALL, anchor="end")
    arc(c, LCX, LCY, R - 16, CW_A0, CW_A1, dl.BLUE, 2, head=True)
    dl.text(c, LCX + DIR_DX, LCY - R + DIR_DY, "CW climbs", SMALL, fill=dl.BLUE)
    dl.text(c, LCX + DIR_DX, LCY - R + DIR_DY + LINE, "from 0°", SMALL, fill=dl.BLUE)
    arc(c, LCX, LCY, R - 16, CCW_A0, CCW_A1, dl.BLUE, 2, head=True)
    dl.text(c, LCX - DIR_DX, LCY - R + DIR_DY, "CCW descends", SMALL, anchor="end", fill=dl.BLUE)
    dl.text(c, LCX - DIR_DX, LCY - R + DIR_DY + LINE, "from 360°", SMALL, anchor="end", fill=dl.BLUE)

    # right: delivered azimuth --------------------------------------------------------------------
    sector(c, RCX, RCY, 0, R, WIN0, WIN1, dl.GREEN, 0.18)
    head(RCX, RCY, "Delivered azimuth — what the output reports",
         ["counter-clockwise from +X in (-180, 180], including ", code("startAzimuthOffsetDeg")])
    cardinals(RCX, RCY, "0° (+X forward)", "-90° (-Y, right)", "±180° (behind)",
              "+90° (+Y, left)")
    arc(c, RCX, RCY, R + 5, WIN0, WIN1, dl.GREEN, 4)
    wx = RCX + NOTE_DX
    dl.text(c, wx, NOTE_Y, "window 0°..90°", SMALL)
    dl.text(c, wx, NOTE_Y + LINE, "delivers -90°..0°", SMALL)
    dl.text(c, wx, NOTE_Y + 2 * LINE, "(no offset)", SMALL, fill=dl.GREY)
    arc(c, RCX, RCY, R - 16, POS_A0, POS_A1, dl.BLUE, 2, head=True)
    dl.text(c, RCX - DIR_DX, RCY - R + DIR_DY, "azimuth increases", SMALL, anchor="end", fill=dl.BLUE)
    dl.text(c, RCX - DIR_DX, RCY - R + DIR_DY + LINE, "counter-clockwise", SMALL, anchor="end", fill=dl.BLUE)
    arc(c, RCX, RCY, R + 22, OFF_A0, OFF_A1, dl.PURPLE, 2, head=True)
    ox, oy = polar(RCX, RCY, R + 22, OFF_A0)
    rich(c, ox - 12, oy + 6, ["+ ", code("startAzimuthOffsetDeg")], SMALL, anchor="end", fill=dl.PURPLE)
    dl.text(c, ox - 12, oy + 6 + LINE, "rotates the whole pattern", SMALL, anchor="end", fill=dl.GREY)

    dl.legend(c, LEGEND[0], LEGEND[1], (("azimuth window, example 0° to 90°", dl.GREEN),
                                        ("ROI interval", dl.ORANGE, "line"),
                                        ("window with start > end", dl.GREY, "dashed"),
                                        ("angle or sweep direction", dl.BLUE, "line"),
                                        ("start offset rotation", dl.PURPLE, "line")))

    dl.validate(c)
    dl.write_svg(out_dir / "lidar_core_azimuth_conventions.svg", c.render())


def lidar_core_field_of_view(out_dir: pathlib.Path) -> None:
    W, H = 1180, 690
    CX, CY = 390, 390                            # the sensor
    RN, RF = 75, 215                             # nearRangeM, farRangeM (not to scale)
    WIN0, WIN1 = 0, 90                           # example window, firing angle (clockwise)
    ROI0, ROI1 = 130, 170                        # ROI interval, drawn without values
    DIM_ANGLE = 250                              # direction of the range dimension line
    RETURN_IN = (185, 45)                        # (radius, deg CW from +X) of the drawn returns
    RETURN_FAR = (248, 36)
    RETURN_NEAR = (54, 35)                       # inside the window's angle, so only the near limit drops it
    RETURN_OUT = (150, 125)
    BAND_LABEL = (CX - 110, CY + 114)
    FIRING_R, FIRING_A0, FIRING_A1 = 150, 6, 60  # firing-angle arrow inside the window
    FIRING_LABEL = (548, 222)
    ROI_LABEL = (585, 556)
    ICX, ICY, IR = 960, 256, 90                  # inset: a wrapping window
    IWIN0, IWIN1 = 300, 420                      # 300 .. 60 through 360
    INSET_TITLE_Y = 82
    NOTE = (40, 44)
    LEGEND = (40, 660)
    SMALL, LINE = 11.5, 16

    c = dl.Canvas(W, H, "The three windows of a rotary sensor",
                  "Top-down view of a rotary sensor with +X forward. An annulus between nearRangeM and "
                  "farRangeM marks the range band. An arc measured clockwise from +X on the firing angle "
                  "runs from validStartAzimuthDeg to validEndAzimuthDeg, next to a second, wrapping "
                  "example that passes through 360 degrees. A separate arc marks the region of interest "
                  "between minAzimuthROI and maxAzimuthROI.")
    dl.text(c, NOTE[0], NOTE[1], "not to scale", 11, fill=dl.GREY)

    # range band ---------------------------------------------------------------------------------
    circle(c, CX, CY, RF, fill=dl.PANEL)
    circle(c, CX, CY, RN, fill=dl.WHITE)
    sector(c, CX, CY, RN, RF, WIN0, WIN1, dl.GREEN, 0.22)
    for a in (WIN0, WIN1):
        x1, y1 = polar(CX, CY, RF + 6, a)
        line(c, CX, CY, x1, y1, dl.GREEN, 2)
    dot(c, CX, CY, 5, dl.DK)
    x1, y1 = polar(CX, CY, RF, DIM_ANGLE)
    line(c, CX, CY, x1, y1, dl.DK, 1, dashed=True)
    for r in (RN, RF):
        px, py = polar(CX, CY, r, DIM_ANGLE)
        dot(c, px, py, 3, dl.DK)
    nx, ny = polar(CX, CY, RN, DIM_ANGLE)
    dl.text(c, nx - 6, ny - 10, "nearRangeM", SMALL, anchor="end", family=dl.M)
    fx, fy = polar(CX, CY, RF, DIM_ANGLE)
    dl.text(c, fx - 6, fy + 20, "farRangeM", SMALL, anchor="end", family=dl.M)
    dl.text(c, BAND_LABEL[0], BAND_LABEL[1], "range band", SMALL, anchor="middle", fill=dl.GREY)

    # returns ------------------------------------------------------------------------------------
    px, py = polar(CX, CY, *RETURN_IN)
    dot(c, px, py, 5, dl.DK)
    dl.text(c, px + 10, py + 4, "delivered return", SMALL)
    px, py = polar(CX, CY, *RETURN_FAR)
    dot(c, px, py, 5, dl.GREY, hollow=True)
    rich(c, px + 12, py + 4, ["beyond ", code("farRangeM"), ", not delivered"], SMALL)
    px, py = polar(CX, CY, *RETURN_NEAR)
    dot(c, px, py, 5, dl.GREY, hollow=True)
    rich(c, px + 12, py - 4, ["inside ", code("nearRangeM"), ","], SMALL)
    dl.text(c, px + 12, py - 4 + LINE, "not delivered", SMALL)
    px, py = polar(CX, CY, *RETURN_OUT)
    dot(c, px, py, 5, dl.GREY, hollow=True)
    dl.text(c, px + 11, py + 4, "outside the azimuth window", SMALL)

    # azimuth window -----------------------------------------------------------------------------
    arc(c, CX, CY, FIRING_R, FIRING_A0, FIRING_A1, dl.BLUE, 2, head=True)
    dl.text(c, CX + 12, CY - RF - 9, "validStartAzimuthDeg = 0°", SMALL, family=dl.M)
    dl.text(c, CX + RF - 9, CY - 10, "validEndAzimuthDeg = 90°", SMALL, anchor="end", family=dl.M)
    dl.text(c, FIRING_LABEL[0], FIRING_LABEL[1], "firing angle: clockwise from +X,", SMALL, fill=dl.BLUE)
    rich(c, FIRING_LABEL[0], FIRING_LABEL[1] + LINE, ["before ", code("startAzimuthOffsetDeg"), " is added"],
         SMALL, fill=dl.BLUE)

    # ROI ----------------------------------------------------------------------------------------
    arc(c, CX, CY, RF + 14, ROI0, ROI1, dl.ORANGE, 3)
    dl.text(c, ROI_LABEL[0], ROI_LABEL[1], "minAzimuthROI .. maxAzimuthROI", SMALL, family=dl.M,
            fill=dl.ORANGE)
    dl.text(c, ROI_LABEL[0], ROI_LABEL[1] + LINE, "ROI interval: where ROI-tagged states fire,", SMALL,
            fill=dl.GREY)
    dl.text(c, ROI_LABEL[0], ROI_LABEL[1] + 2 * LINE, "not the field of view", SMALL, fill=dl.GREY)

    # forward axis -------------------------------------------------------------------------------
    dl.arrow(c, CX, CY - RF - 10, CX, CY - RF - 36, dl.DK, 1.5)
    dl.text(c, CX, CY - RF - 44, "+X forward", SMALL, anchor="middle")

    # inset: a wrapping window -------------------------------------------------------------------
    dl.text(c, ICX, INSET_TITLE_Y, "A wrapping window", 13, "bold", anchor="middle")
    dl.text(c, ICX, INSET_TITLE_Y + 18, "start > end wraps through 360°", SMALL, anchor="middle",
            fill=dl.GREY)
    dl.text(c, ICX, INSET_TITLE_Y + 36, "validStartAzimuthDeg = 300, validEndAzimuthDeg = 60", 11,
            anchor="middle", family=dl.M)
    circle(c, ICX, ICY, IR)
    sector(c, ICX, ICY, 0, IR, IWIN0, IWIN1, dl.GREEN, 0.22)
    arc(c, ICX, ICY, IR + 5, IWIN0, IWIN1, dl.GREEN, 4)
    dot(c, ICX, ICY, 4, dl.DK)
    dl.arrow(c, ICX, ICY, ICX, ICY - IR + 10, dl.DK, 1.5)
    dl.text(c, ICX, ICY - IR - 14, "0° / 360°", 11, anchor="middle")
    px, py = polar(ICX, ICY, IR + 22, IWIN0)
    dl.text(c, px, py, "300°", 11, anchor="end")
    px, py = polar(ICX, ICY, IR + 22, IWIN1)
    dl.text(c, px, py, "60°", 11)
    arc(c, ICX, ICY, IR - 18, IWIN0 + 6, IWIN1 - 6, dl.BLUE, 2, head=True)

    dl.legend(c, LEGEND[0], LEGEND[1], (("azimuth window", dl.GREEN), ("range band", dl.FAINT),
                                        ("ROI interval", dl.ORANGE, "line"),
                                        ("firing angle, clockwise", dl.BLUE, "line")))

    dl.validate(c)
    dl.write_svg(out_dir / "lidar_core_field_of_view.svg", c.render())


def lidar_core_solid_state_windows(out_dir: pathlib.Path) -> None:
    W, H = 1180, 650
    LX, LW, LABEL_W = 24, 1132, 130              # lanes
    S, B, E = 210, 480, 830                      # scan start, step boundary, scan end (x)
    AX1 = 1140                                   # end of the time axis
    PERIOD_Y, PERIOD_LABEL_Y = 78, 70            # scan-period bracket
    BOUND_LABEL_Y, BOUND_EXPR_Y = 100, 116       # scan boundary labels
    DASH_Y0, DASH_Y1 = 124, 600                  # scan boundary lines
    FY, FH = 128, 92                             # flash lane
    GY, GH = 232, 130                            # groups lane
    AY = 392                                     # time axis
    S1Y, S2Y = 430, 468                          # step rows
    SPX0, SPX1, SPYA, SPYB = 650, 1000, 556, 572  # a step crossing the scan end, split in two
    FLASH_X, FLASH_N = 400, 8
    GROUPS = ((270, 2, dl.BLUE), (350, 3, dl.BLUE), (B, 2, dl.PURPLE), (590, 1, dl.PURPLE),
              (700, 2, dl.PURPLE), (E, 1, dl.PURPLE))
    LEGEND_Y, NOTE_Y = 618, 628
    SMALL, LINE = 11.5, 16

    c = dl.Canvas(W, H, "A solid-state scan over two simulation steps",
                  "A solid-state scan on a time axis with scan period boundaries, fire-time groups and, "
                  "in a second lane, a flash group; two simulation steps with half-open windows, the group "
                  "on the step boundary firing in the later step, and the step that reaches the period end "
                  "completing the scan and advancing the emitter state.")

    # scan period and boundaries -----------------------------------------------------------------
    dim(c, S, PERIOD_Y, E, PERIOD_Y)
    rich(c, (S + E) / 2, PERIOD_LABEL_Y, ["scan period = ", code("1 / frameRate")], SMALL, anchor="middle")
    dl.text(c, S, BOUND_LABEL_Y, "scan start", SMALL, "bold", anchor="middle")
    dl.text(c, S, BOUND_EXPR_Y, "startTime + k * (1 / frameRate)", 11, anchor="middle", family=dl.M,
            fill=dl.GREY)
    dl.text(c, E, BOUND_LABEL_Y, "scan end, next scan start", SMALL, "bold", anchor="middle")
    dl.text(c, E, BOUND_EXPR_Y, "startTime + (k + 1) * (1 / frameRate)", 11, anchor="middle", family=dl.M,
            fill=dl.GREY)

    # lanes --------------------------------------------------------------------------------------
    dl.lane(c, LX, FY, LW, FH, "flash pattern", label_width=LABEL_W)
    dl.text(c, LX + 12, FY + FH / 2 + 22, "every emitter shares", 11, fill=dl.GREY)
    dl.text(c, LX + 12, FY + FH / 2 + 22 + LINE, "one fireTimeNs", 11, fill=dl.GREY, family=dl.M)
    dl.lane(c, LX, GY, LW, GH, "several groups", label_width=LABEL_W)
    dl.text(c, LX + 12, GY + GH / 2 + 22, "emitters with equal", 11, fill=dl.GREY)
    dl.text(c, LX + 12, GY + GH / 2 + 22 + LINE, "fire times form a group", 11, fill=dl.GREY)
    for x in (S, E):
        line(c, x, DASH_Y0, x, DASH_Y1, dl.GREY, 1.5, dashed=True)

    # flash lane ---------------------------------------------------------------------------------
    dot_stack(c, FLASH_X, FY + FH - 16, FLASH_N, dl.BLUE, step=9)
    rich(c, FLASH_X + 16, FY + 32, ["flash group: every emitter shares one ", code("fireTimeNs"), ","], SMALL)
    dl.text(c, FLASH_X + 16, FY + 32 + LINE, "so the whole pattern is one group that fires once per scan,",
            SMALL)
    dl.text(c, FLASH_X + 16, FY + 32 + 2 * LINE, "in whichever step holds that time (step 1 here)", SMALL)

    # groups lane --------------------------------------------------------------------------------
    base = GY + GH - 6
    for x, n, color in GROUPS:
        dot_stack(c, x, base, n, color)
    dl.arrow(c, S, GY + 30, GROUPS[1][0], GY + 30, dl.DK, 1.2)
    rich(c, S + 8, GY + 22, [code("fireTimeNs"), " counted from the scan start"], SMALL, fill=dl.GREY)
    dl.text(c, B, GY + 78, "on the step boundary", 11, anchor="middle", fill=dl.GREY)
    dl.text(c, E - 10, GY + 98, "timed exactly at the scan end", 11, anchor="end", fill=dl.GREY)

    # time axis ----------------------------------------------------------------------------------
    dl.arrow(c, LX + LABEL_W, AY, AX1, AY, dl.GREY, 1.5)
    dl.text(c, AX1, AY - 10, "time", SMALL, anchor="end", fill=dl.GREY)

    # steps --------------------------------------------------------------------------------------
    for x, n, color in GROUPS:
        if x == B:
            dl.arrow(c, x + 4, base + 6, x + 46, S2Y - 7, color, 1.5)
        elif color == dl.BLUE:
            dl.arrow(c, x, base + 6, x, S1Y - 7, color, 1.5)
        else:
            dl.arrow(c, x, base + 6, x, S2Y - 7, color, 1.5)
    line(c, S, S1Y, B, S1Y, dl.BLUE, 2.5)
    dot(c, S, S1Y, 5.5, dl.BLUE)
    dot(c, B, S1Y, 5.5, dl.BLUE, hollow=True)
    rich(c, (S + B) / 2, S1Y + 20, ["step 1: ", code("[scan start, boundary)")], SMALL, anchor="middle")
    line(c, B, S2Y, E, S2Y, dl.PURPLE, 2.5)
    dot(c, B, S2Y, 5.5, dl.PURPLE)
    dot(c, E, S2Y, 5.5, dl.PURPLE)
    rich(c, (B + E) / 2, S2Y + 18, ["step 2: ", code("[boundary, scan end]")], SMALL, anchor="middle")
    dl.text(c, B - 14, S1Y + 42, "boundary group fires in the later step", SMALL, anchor="end", fill=dl.PURPLE)
    circle(c, E, S2Y, 9, fill="none", stroke=dl.GREEN, width=2.5)
    dl.text(c, E + 16, S2Y - 4, "scan completes here;", SMALL, fill=dl.GREEN)
    rich(c, E + 16, S2Y - 4 + LINE, ["emitter state advances (", code("s001 → s002"), ")"], SMALL,
         fill=dl.GREEN)
    dl.text(c, E + 16, S2Y - 4 + 2 * LINE, "the closing step also fires the group at the scan end", SMALL,
            fill=dl.GREY)

    # a step that crosses a scan boundary --------------------------------------------------------
    dl.text(c, E - 10, SPYA - 34, "a step that crosses a scan boundary", SMALL, anchor="end", fill=dl.GREY)
    dl.text(c, E - 10, SPYA - 18, "is split into one window per scan", SMALL, anchor="end", fill=dl.GREY)
    line(c, SPX0, SPYA, E, SPYA, dl.GREY, 2.5)
    dot(c, SPX0, SPYA, 5.5, dl.GREY)
    dot(c, E, SPYA, 5.5, dl.GREY)
    line(c, E, SPYB, SPX1, SPYB, dl.GREY, 2.5)
    dot(c, E, SPYB, 5.5, dl.GREY)
    dot(c, SPX1, SPYB, 5.5, dl.GREY, hollow=True)
    dl.text(c, (SPX0 + E) / 2, SPYB + 22, "window in scan k", 11, anchor="middle", fill=dl.GREY)
    dl.text(c, (E + SPX1) / 2, SPYB + 22, "window in scan k + 1", 11, anchor="middle", fill=dl.GREY)

    dl.legend(c, LX + LABEL_W, LEGEND_Y, (("fires in step 1", dl.BLUE), ("fires in step 2", dl.PURPLE),
                                          ("scan boundary", dl.GREY, "dashed"),
                                          ("scan completes, emitter state advances", dl.GREEN)))
    dl.text(c, LX + LW, NOTE_Y, "filled end: instant included · open end: excluded", SMALL, anchor="end",
            fill=dl.GREY)

    dl.validate(c)
    dl.write_svg(out_dir / "lidar_core_solid_state_windows.svg", c.render())


def generate(out_dir: pathlib.Path) -> None:
    lidar_core_firing_pattern_anatomy(out_dir)
    lidar_core_azimuth_conventions(out_dir)
    lidar_core_field_of_view(out_dir)
    lidar_core_solid_state_windows(out_dir)


if __name__ == "__main__":
    generate(dl.output_dir(__file__))
