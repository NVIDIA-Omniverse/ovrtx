#!/usr/bin/env python3
"""Radar figures, group B, of the nonvisual sensor documentation.

Four diagrams for the Radar generic wpmDmat model pages: the moving-targets
example scene from above, the scan cycle against the stepping cadence, the
order of the seven validation checks and the anatomy of one radar point-cloud
output. ``generate_diagrams.py`` in this directory imports this module and
calls :func:`generate`; running the module directly regenerates only this
group::

    python3 -B _gen_radar_b.py            # in place
    python3 -B _gen_radar_b.py /tmp/check # elsewhere, to diff against the committed files
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import _diagram_lib as dl
import math


# ------------------------------------------------------------------------ local helpers ---
def _rect(c, x, y, w, h, fill, stroke="none", stroke_width=1, rx=0, dashed=False, opacity=None):
    attrs = f'x="{dl.fmt(x)}" y="{dl.fmt(y)}" width="{dl.fmt(w)}" height="{dl.fmt(h)}"'
    if rx:
        attrs += f' rx="{dl.fmt(rx)}"'
    attrs += f' fill="{fill}"'
    if opacity is not None:
        attrs += f' fill-opacity="{dl.fmt(opacity)}"'
    if stroke != "none":
        attrs += f' stroke="{stroke}" stroke-width="{dl.fmt(stroke_width)}"'
        if dashed:
            attrs += f' stroke-dasharray="{dl.fmt(3 * stroke_width)} {dl.fmt(2 * stroke_width)}"'
    c.add(f"<rect {attrs}/>")


def _poly(c, points, fill, opacity=None, stroke="none", stroke_width=1):
    pts = " ".join(f"{dl.fmt(px)},{dl.fmt(py)}" for px, py in points)
    attrs = f'points="{pts}" fill="{fill}"'
    if opacity is not None:
        attrs += f' fill-opacity="{dl.fmt(opacity)}"'
    if stroke != "none":
        attrs += f' stroke="{stroke}" stroke-width="{dl.fmt(stroke_width)}"'
    c.add(f"<polygon {attrs}/>")


def _circle(c, cx, cy, r, fill):
    c.add(f'<circle cx="{dl.fmt(cx)}" cy="{dl.fmt(cy)}" r="{dl.fmt(r)}" fill="{fill}"/>')


def _line(c, x1, y1, x2, y2, stroke, width=1, dashed=False):
    dl.arrow(c, x1, y1, x2, y2, stroke=stroke, width=width, head=False, dashed=dashed)


def _bracket(c, x1, x2, y, tick=6, stroke=dl.DK, width=1.5):
    """A horizontal bracket from x1 to x2 at y, its end ticks pointing down toward the content."""
    _line(c, x1, y, x2, y, stroke, width)
    _line(c, x1, y, x1, y + tick, stroke, width)
    _line(c, x2, y, x2, y + tick, stroke, width)


def _mixed(c, x, y, parts, size=12, anchor="start", fill=dl.DK, weight="normal", gap=5.0):
    """One baseline, several font families: ``parts`` is a list of (string, family).

    Prose segments use ``dl.F``, attribute names and values ``dl.M``. Returns (x0, x1).
    """
    widths = [dl.text_width(s, size, weight, fam) for s, fam in parts]
    total = sum(widths) + gap * (len(parts) - 1)
    x0 = float(x) - (total / 2 if anchor == "middle" else total if anchor == "end" else 0.0)
    cur = x0
    for (s, fam), w in zip(parts, widths):
        dl.text(c, cur, y, s, size, weight, "start", fill, fam)
        cur += w + gap
    return x0, x0 + total


# ============================================================ radar_moving_targets_scene ===
def radar_moving_targets_scene(out_dir):
    """The example scene from above: radar at the origin, steel cube closing in, concrete cube fixed."""
    S = 22.0                                              # px per meter
    X_MIN, X_MAX, Y_MIN, Y_MAX = -4.0, 37.0, -9.0, 9.0    # world extent of the sketch, m
    PLOT_X, PLOT_Y = 64.0, 80.0                           # top-left corner of the plot
    PLOT_W, PLOT_H = (X_MAX - X_MIN) * S, (Y_MAX - Y_MIN) * S
    W, H = PLOT_X + PLOT_W + 28, PLOT_Y + PLOT_H + 60
    LEGEND_Y = 22.0
    STEEL_X, STEEL_END_X, STEEL_Y = 30.0, 20.0, 4.0       # the time-sampled path, m
    CONCRETE_X, CONCRETE_Y = 30.0, -4.0
    EDGE = 1.5                                            # cube edge, m
    FOV_HALF_DEG = 66.0                                   # the schema default: the example authors no limit
    BORESIGHT_M = 5.0                                     # length of the boresight arrow, m
    GLYPH = 16.0                                          # radar glyph, px
    ARROW_FROM_X, ARROW_TO_X = STEEL_X - EDGE / 2 - 0.1, STEEL_END_X - EDGE / 2 - 0.4
    PATH_LABEL_X = (STEEL_X + STEEL_END_X) / 2 - 0.5      # m, the labels over the path
    PATH_LABEL_Y1, PATH_LABEL_Y2 = 6.5, 5.5               # baselines, m
    STEEL_LABEL_Y1, STEEL_LABEL_Y2 = 2.55, 1.55           # under the steel cube, m
    CONCRETE_LABEL_Y1, CONCRETE_LABEL_Y2 = -5.65, -6.65   # under the concrete cube, m
    LOS_LABEL_X, LOS_LABEL_Y = 14.0, 0.9                  # "line of sight", m
    FOV_LABEL_X, FOV_LABEL_Y = 3.6, 6.2                   # "field of view", just inside the upper edge, m
    OUTSIDE_LABEL_X, OUTSIDE_LABEL_Y = -3.6, 7.9          # "outside the field of view", in the notch, m
    BORESIGHT_LABEL_X, BORESIGHT_LABEL_Y = 2.4, -0.7      # m
    RADAR_LABEL_X, RADAR_LABEL_Y = 1.4, -1.7              # m, inside the wedge
    X_TICKS = (0, 5, 10, 15, 20, 25, 30, 35)
    Y_TICKS = (8, 4, 0, -4, -8)
    half = EDGE / 2

    def px(x):
        return PLOT_X + (x - X_MIN) * S

    def py(y):
        return PLOT_Y + (Y_MAX - y) * S

    c = dl.Canvas(
        W, H, "The radar example scene from above",
        "Top-down sketch, X to the right and Y up, in meters. The radar sits at the origin and looks "
        "along +X over an asphalt ground plane. A steel cube travels along the line y = 4 from "
        "x = 30 to x = 20, one meter per 0.1 s step, toward the radar; its detections report a "
        "negative RadialVelocityMs near -10 m/s. A concrete cube stays at (30, -4) and reports a "
        "radial velocity near zero. A dashed line of sight joins the radar to the steel cube. The shaded "
        "wedge is the field of view at the schema defaults; both cubes lie well inside it.")

    # ground plane, field of view, grid
    _rect(c, PLOT_X, PLOT_Y, PLOT_W, PLOT_H, dl.PANEL, stroke=dl.FAINT)
    # the field of view is wide: its edges leave the sketch through the top and bottom, so the wedge
    # is the part of the plot to the right of them, clipped to the plot rectangle
    x_top = Y_MAX / math.tan(math.radians(FOV_HALF_DEG))
    x_bottom = -Y_MIN / math.tan(math.radians(FOV_HALF_DEG))
    _poly(c, [(px(0), py(0)), (px(x_top), py(Y_MAX)), (px(X_MAX), py(Y_MAX)), (px(X_MAX), py(Y_MIN)),
              (px(x_bottom), py(Y_MIN))], dl.FAINT, opacity=0.45)
    for yv in (4.0, 0.0, -4.0):
        _line(c, PLOT_X, py(yv), PLOT_X + PLOT_W, py(yv), dl.FAINT, 1, dashed=True)
    for xv in (10.0, 20.0, 30.0):
        _line(c, px(xv), PLOT_Y, px(xv), PLOT_Y + PLOT_H, dl.FAINT, 1, dashed=True)
    dl.text(c, px(FOV_LABEL_X), py(FOV_LABEL_Y), "field of view at the schema defaults", 11, "normal", "start",
            dl.GREY)
    dl.text(c, px(OUTSIDE_LABEL_X), py(OUTSIDE_LABEL_Y), "outside the field of view", 11, "normal", "start", dl.GREY)
    dl.text(c, PLOT_X + 10, PLOT_Y + PLOT_H - 10,
            "asphalt ground plane: -200 m to 200 m in X and in Y (the sketch shows the part near the radar)",
            11, fill=dl.GREY)

    # line of sight to the steel cube, ending at its near face
    t = (STEEL_X - half) / STEEL_X
    _line(c, px(0), py(0), px(STEEL_X - half), py(STEEL_Y * t), dl.GREY, 1.5, dashed=True)
    dl.text(c, px(LOS_LABEL_X), py(LOS_LABEL_Y), "line of sight", 11, "normal", "middle", dl.GREY)

    # the radar: glyph at the origin, boresight along +X
    dl.arrow(c, px(0) + GLYPH / 2 + 2, py(0), px(BORESIGHT_M), py(0), stroke=dl.DK, width=2.5)
    _rect(c, px(0) - GLYPH / 2, py(0) - GLYPH / 2, GLYPH, GLYPH, dl.DK, rx=3)
    _circle(c, px(0) + 3, py(0), 2.5, dl.WHITE)
    dl.text(c, px(BORESIGHT_LABEL_X), py(BORESIGHT_LABEL_Y), "boresight, +X", 11, "normal", "middle", dl.GREY)
    dl.text(c, px(RADAR_LABEL_X), py(RADAR_LABEL_Y), "radar at (0, 0), 1 m above the plane", 12)

    # the steel cube: its later positions, the cube itself, the motion arrow and its labels
    for xv in range(int(STEEL_X) - 1, int(STEEL_END_X) - 1, -1):
        _rect(c, px(xv - half), py(STEEL_Y + half), EDGE * S, EDGE * S, dl.WHITE, stroke=dl.FAINT,
              stroke_width=1.2, dashed=True)
    _rect(c, px(STEEL_X - half), py(STEEL_Y + half), EDGE * S, EDGE * S, dl.BLUE)
    dl.arrow(c, px(ARROW_FROM_X), py(STEEL_Y), px(ARROW_TO_X), py(STEEL_Y), stroke=dl.BLUE, width=3)
    dl.text(c, px(PATH_LABEL_X), py(PATH_LABEL_Y1), "1 m per step (0.1 s): about 10 m/s", 12, "bold", "middle")
    _mixed(c, px(PATH_LABEL_X), py(PATH_LABEL_Y2),
           [("RadialVelocityMs < 0", dl.M), ("(approaching, near -10 m/s)", dl.F)], 12, anchor="middle")
    dl.text(c, px(STEEL_X), py(STEEL_LABEL_Y1), "steel cube", 12, "bold", "middle")
    dl.text(c, px(STEEL_X), py(STEEL_LABEL_Y2), "from (30, 4) to (20, 4), 1.5 m edge", 11, "normal",
            "middle", dl.GREY)

    # the concrete cube
    _rect(c, px(CONCRETE_X - half), py(CONCRETE_Y + half), EDGE * S, EDGE * S, dl.GREEN)
    dl.text(c, px(CONCRETE_X), py(CONCRETE_LABEL_Y1), "concrete cube, fixed at (30, -4)", 12, "bold", "middle")
    _mixed(c, px(CONCRETE_X), py(CONCRETE_LABEL_Y2),
           [("RadialVelocityMs ~ 0", dl.M), ("(static)", dl.F)], 12, anchor="middle")

    # axes and legend
    dl.tick_marks(c, PLOT_X, PLOT_Y + PLOT_H, PLOT_W, [px(v) - PLOT_X for v in X_TICKS],
                  [str(v) for v in X_TICKS])
    dl.text(c, PLOT_X + PLOT_W, PLOT_Y + PLOT_H + 40, "X (m)", 12, "normal", "end", dl.GREY)
    dl.tick_marks(c, PLOT_X, PLOT_Y, PLOT_H, [py(v) - PLOT_Y for v in Y_TICKS],
                  [str(v) for v in Y_TICKS], horizontal=False)
    dl.text(c, PLOT_X, PLOT_Y - 12, "Y (m)", 12, "normal", "middle", dl.GREY)
    dl.legend(c, PLOT_X, LEGEND_Y, [
        ("steel cube, closing on the radar", dl.BLUE),
        ("concrete cube, fixed", dl.GREEN),
        ("later positions of the steel cube, one per step", dl.FAINT, "outline"),
        ("line of sight", dl.GREY, "dashed"),
    ])

    dl.validate(c)
    dl.write_svg(out_dir / "radar_moving_targets_scene.svg", c.render())


# ========================================================= radar_scan_cycle_vs_stepping ===
def _frame_card(c, x, y, w, h, color, lines):
    """A delivered frame: a card with a point-cloud glyph and one or two mono label lines."""
    DOT_Y, DOT_R, DOT_PITCH = 12.0, 2.4, 16.0
    _rect(c, x, y, w, h, dl.PANEL, stroke=color, stroke_width=2, rx=5)
    n = max(5, int(w // DOT_PITCH) - 1)                  # a wider card carries more points
    for i in range(n):
        _circle(c, x + w * (i + 1) / (n + 1), y + DOT_Y + (3 if i % 2 else 0), DOT_R, color)
    if len(lines) == 1:
        dl.text(c, x + w / 2, y + h / 2 + 10, lines[0], 12, "normal", "middle", dl.DK, dl.M)
    else:
        dl.text(c, x + w / 2, y + h / 2 + 1, lines[0], 12, "bold", "middle", dl.DK, dl.M)
        dl.text(c, x + w / 2, y + h / 2 + 18, lines[1], 11, "normal", "middle", dl.DK, dl.M)


def _no_frame_card(c, x, y, w, h):
    """A step with no published radar frame: a dashed card with no glyph."""
    _rect(c, x, y, w, h, dl.WHITE, stroke=dl.MUTED, stroke_width=1.5, rx=5, dashed=True)
    dl.text(c, x + w / 2, y + h / 2 + 1, "no", 11, "normal", "middle", dl.MUTED)
    dl.text(c, x + w / 2, y + h / 2 + 18, "frame", 11, "normal", "middle", dl.MUTED)


def _scan_marker(c, x, y, size=5.0):
    """The scan-time marker: a small filled triangle standing on the axis."""
    _poly(c, [(x, y - 1), (x - size, y - 2 * size), (x + size, y - 2 * size)], dl.DK)


def _legend_card(c, x, y, color=None):
    """A miniature card for the legend: a delivered frame, or no published frame."""
    w, h = 20.0, 14.0
    if color is None:
        _rect(c, x, y, w, h, dl.WHITE, stroke=dl.MUTED, stroke_width=1.2, rx=3, dashed=True)
    else:
        _rect(c, x, y, w, h, dl.PANEL, stroke=color, stroke_width=1.5, rx=3)
        for f in (0.25, 0.5, 0.75):
            _circle(c, x + f * w, y + h / 2, 1.6, color)
    return w


def radar_scan_cycle_vs_stepping(out_dir):
    """Two timelines: steps at the scan period, and steps at twice that rate."""
    X0 = 124.0                                   # t = 0 on the shared axis
    P = 160.0                                    # px per scan period T
    N = 6                                        # periods shown
    AXIS_W = N * P
    W = X0 + AXIS_W + 30
    LEGEND_X, LEGEND_Y = 30.0, 20.0
    CARD_H, BOX_H, CARD_INSET = 60.0, 28.0, 6.0
    R1_HEAD_Y, R1_CARD_Y = 76.0, 86.0
    R1_BOX_Y = R1_CARD_Y + CARD_H + 6
    R1_CURSOR_Y = R1_BOX_Y + BOX_H + 19
    R1_NOTE_Y = R1_CURSOR_Y + 23
    R2_HEAD_Y, R2_CARD_Y = 266.0, 276.0
    R2_BOX_Y = R2_CARD_Y + CARD_H + 6
    R2_CURSOR_Y = R2_BOX_Y + BOX_H + 19
    R2_NOTE_Y = R2_CURSOR_Y + 23
    AXIS_Y = 446.0
    AXIS_TITLE_Y = AXIS_Y + 46
    H = AXIS_TITLE_Y + 24
    CAPTION_X = X0 - 12                          # right edge of the small row captions
    COLOR = {"s001": dl.BLUE, "s002": dl.PURPLE}
    TICK_LABELS = ("0", "T", "2T", "3T", "4T", "5T", "6T")

    c = dl.Canvas(
        W, H, "The scan cycle against the stepping cadence",
        "Two timelines for scans s001 and s002 with zero start and scan offsets, on one time "
        "axis ticked in scan periods. At the scan period, every step starts on a scan time and delivers "
        "a frame, and the scan index alternates 0, 1, 0, 1. At twice the rate, only every other step "
        "starts on a scan time; the steps in between fire no scan, publish no radar frame "
        "and leave the pending scan unchanged, so the published frames still alternate "
        "s001 and s002.")

    # scan-time guides behind everything, in segments that leave the headings and notes alone
    GUIDES = ((R1_CARD_Y - 4, R1_CURSOR_Y + 5), (R2_CARD_Y - 4, R2_CURSOR_Y + 5), (R2_NOTE_Y + 6, AXIS_Y))
    for k in range(N + 1):
        for y1, y2 in GUIDES:
            _line(c, X0 + k * P, y1, X0 + k * P, y2, dl.FAINT, 1, dashed=True)

    # legend
    lx = LEGEND_X
    for label, color in (("frame from s001 (scanIdx 0)", dl.BLUE), ("frame from s002 (scanIdx 1)", dl.PURPLE),
                         ("no radar frame", None)):
        cw = _legend_card(c, lx, LEGEND_Y, color)
        tb = dl.text(c, lx + cw + 8, LEGEND_Y + 11.5, label, 12)
        lx = tb.x1 + 24
    _scan_marker(c, lx + 6, LEGEND_Y + 15)
    dl.text(c, lx + 20, LEGEND_Y + 11.5, "scan time (every multiple of T)", 12)

    # row 1: one step per period
    head = dl.text(c, X0, R1_HEAD_Y, "Steps at the scan period", 14, "bold")
    dl.text(c, head.x1 + 12, R1_HEAD_Y, "one step per T", 12, fill=dl.GREY)
    for i in range(N):
        x = X0 + i * P
        scan, idx = ("s001", 0) if i % 2 == 0 else ("s002", 1)
        _frame_card(c, x + CARD_INSET, R1_CARD_Y, P - 2 * CARD_INSET, CARD_H, COLOR[scan],
                    [f"{scan} / scanIdx {idx}"])
        dl.box(c, x, R1_BOX_Y, P, BOX_H, f"step {i + 1}", fill=dl.PANEL, stroke=dl.MUTED, stroke_width=1,
               rx=3, label_size=12, label_weight="normal")
        dl.text(c, x + P / 2, R1_CURSOR_Y, scan, 12, "normal", "middle", COLOR[scan], dl.M)
    dl.text(c, X0, R1_NOTE_Y, "every step starts on a scan time and delivers a frame", 12, fill=dl.GREY)

    # row 2: two steps per period
    head = dl.text(c, X0, R2_HEAD_Y, "Steps at twice the rate", 14, "bold")
    dl.text(c, head.x1 + 12, R2_HEAD_Y, "one step per T/2", 12, fill=dl.GREY)
    pending = 0                                  # the scan whose turn it is; moves on firings only
    for i in range(2 * N):
        x = X0 + i * P / 2
        scan = "s001" if pending == 0 else "s002"
        if i % 2 == 0:                           # this step starts on a scan time: the pending scan fires
            _frame_card(c, x + CARD_INSET, R2_CARD_Y, P / 2 - 2 * CARD_INSET, CARD_H, COLOR[scan],
                        [scan, f"scanIdx {pending}"])
        else:                                    # no scan time in this step: nothing fires, nothing moves
            _no_frame_card(c, x + CARD_INSET, R2_CARD_Y, P / 2 - 2 * CARD_INSET, CARD_H)
        dl.box(c, x, R2_BOX_Y, P / 2, BOX_H, f"step {i + 1}", fill=dl.PANEL, stroke=dl.MUTED, stroke_width=1,
               rx=3, label_size=12, label_weight="normal")
        dl.text(c, x + P / 4, R2_CURSOR_Y, scan, 12, "normal", "middle", COLOR[scan], dl.M)
        if i % 2 == 0:
            pending = 1 - pending
    dl.text(c, X0, R2_NOTE_Y,
            "only firings advance the scan; the steps between scan times leave it unchanged, so the "
            "published frames still alternate s001 and s002", 12, fill=dl.GREY)

    # row captions
    for card_y, box_y, cursor_y in ((R1_CARD_Y, R1_BOX_Y, R1_CURSOR_Y), (R2_CARD_Y, R2_BOX_Y, R2_CURSOR_Y)):
        dl.text(c, CAPTION_X, card_y + CARD_H / 2 + 4, "output", 11, "normal", "end", dl.GREY)
        dl.text(c, CAPTION_X, box_y + BOX_H / 2 + 4, "step", 11, "normal", "end", dl.GREY)
        dl.text(c, CAPTION_X, cursor_y, "active scan", 11, "normal", "end", dl.GREY)

    # the shared time axis
    dl.tick_marks(c, X0, AXIS_Y, AXIS_W, [k * P for k in range(N + 1)], TICK_LABELS)
    for k in range(N + 1):
        _scan_marker(c, X0 + k * P, AXIS_Y)
    dl.text(c, X0 + AXIS_W / 2, AXIS_TITLE_Y,
            "time in scan periods T, the reciprocal of the frame rate; a scan is scheduled at every multiple of T",
            12, "normal", "middle", dl.GREY)

    dl.validate(c)
    dl.write_svg(out_dir / "radar_scan_cycle_vs_stepping.svg", c.render())


# ========================================================= radar_validation_check_order ===
def radar_validation_check_order(out_dir):
    """The seven validation checks as a left-to-right chain in dependency order."""
    MARGIN = 30.0
    BOX_W, BOX_H, GAP = 138.0, 104.0, 26.0
    LEGEND_Y = 20.0
    BAND_Y, BAND_H = 60.0, 32.0
    BOXES_Y = 124.0
    NUM_Y, TITLE_Y, TITLE_LH = 30.0, 54.0, 17.0        # baselines inside a box, and the line height
    ANNOT_Y, ANNOT_LH = BOXES_Y + BOX_H + 20, 16.0     # the notes under the boxes
    W = 2 * MARGIN + 7 * BOX_W + 6 * GAP
    H = ANNOT_Y + ANNOT_LH + 24
    CHECKS = ("Coordinates and coverage", "Resolution and accuracy", "Doppler and ambiguity",
              "Materials and antenna response", "Multipath", "Detection filtering", "Timing and scans")
    NOTES = (("range, angle, frame of", "reference, rejection"), ("separation, then", "measurement error"),
             ("velocity sign,", "resolution, folding"), ("RCS and detection", "probability"),
             ("ghost detections", "plausible for the scene"), ("false alarms and", "missed detections"),
             ("frame rate, scan order,", "motion BVH"))
    FILLS = (dl.BLUE,) * 5 + (dl.ORANGE, dl.GREY)
    BAND_LABEL = "tune CFAR and noise only after these five are stable"

    c = dl.Canvas(
        W, H, "The seven radar validation checks in dependency order",
        "Seven boxes joined left to right by arrows: 1 coordinates and coverage, 2 resolution and "
        "accuracy, 3 Doppler and ambiguity, 4 materials and antenna response, 5 multipath, 6 detection "
        "filtering, 7 timing and scans. A band above the first five says to tune CFAR and noise only "
        "after they are stable and points at box 6. Under box 7: frame rate, scan order, motion BVH.")

    boxes = []
    for i, (title, fill) in enumerate(zip(CHECKS, FILLS)):
        x = MARGIN + i * (BOX_W + GAP)
        r = dl.box(c, x, BOXES_Y, BOX_W, BOX_H, fill=fill, rx=8)
        boxes.append(r)
        dl.text(c, r.cx, BOXES_Y + NUM_Y, str(i + 1), 20, "bold", "middle", dl.WHITE)
        for j, line in enumerate(dl.wrap_text(title, BOX_W - 16, 12, "bold")):
            dl.text(c, r.cx, BOXES_Y + TITLE_Y + j * TITLE_LH, line, 12, "bold", "middle", dl.WHITE)
        for j, line in enumerate(NOTES[i]):
            dl.text(c, r.cx, ANNOT_Y + j * ANNOT_LH, line, 11, "normal", "middle", dl.GREY)
    for a, b in zip(boxes, boxes[1:]):
        dl.arrow(c, a.right, a.cy, b.left, b.cy, stroke=dl.GREY, width=2)

    # the band over checks 1 to 5, pointing at check 6
    band_x, band_w = boxes[0].left, boxes[4].right - boxes[0].left
    _rect(c, band_x, BAND_Y, band_w, BAND_H, dl.PANEL, stroke=dl.ORANGE, stroke_width=1.5, rx=6)
    dl.text(c, band_x + band_w / 2, BAND_Y + BAND_H / 2 + 4.5, BAND_LABEL, 12, "bold", "middle")
    dl.curve(c, [(boxes[4].right, BAND_Y + BAND_H / 2), (boxes[5].cx - 24, BAND_Y + BAND_H / 2),
                 (boxes[5].cx, BOXES_Y - 2)], stroke=dl.ORANGE, width=2, smooth=0.6)

    dl.legend(c, MARGIN, LEGEND_Y, [
        ("shapes the signal: check first, in this order", dl.BLUE),
        ("filters the signal: tune only after 1 to 5 are stable", dl.ORANGE),
        ("cadence and motion: check last", dl.GREY),
    ])

    dl.validate(c)
    dl.write_svg(out_dir / "radar_validation_check_order.svg", c.render())


# ================================================================ radar_output_anatomy ===
# geometry of a param box: padding, title baseline, gap to the first subtitle line, subtitle line
# height, gap from the last subtitle to the first row, row line height and row font size
_PBOX_PAD, _PBOX_TITLE_Y, _PBOX_SUB_GAP, _PBOX_SUB_LH = 12.0, 22.0, 18.0, 16.0
_PBOX_ROW_GAP, _PBOX_ROW_LH, _PBOX_ROW_SIZE, _PBOX_BOTTOM = 14.0, 17.0, 11.5, 12.0


def _pbox_rows_base(subtitle_lines):
    """Baseline of the first name / type row, relative to the box top."""
    return (_PBOX_TITLE_Y + _PBOX_SUB_GAP + _PBOX_SUB_LH * (len(subtitle_lines) - 1)
            + _PBOX_ROW_GAP + _PBOX_ROW_SIZE)


def _param_box_height(subtitle_lines, rows):
    return _pbox_rows_base(subtitle_lines) + _PBOX_ROW_LH * (len(rows) - 1) + _PBOX_BOTTOM


def _param_box(c, x, y, w, title, subtitle_lines, rows):
    """A tinted box listing params: a bold title, grey subtitle lines, then name / type rows."""
    h = _param_box_height(subtitle_lines, rows)
    dl.box(c, x, y, w, h, fill=dl.PANEL, rx=8)
    dl.text(c, x + _PBOX_PAD, y + _PBOX_TITLE_Y, title, 13, "bold")
    for i, s in enumerate(subtitle_lines):
        dl.text(c, x + _PBOX_PAD, y + _PBOX_TITLE_Y + _PBOX_SUB_GAP + _PBOX_SUB_LH * i, s, 11, fill=dl.GREY)
    base = y + _pbox_rows_base(subtitle_lines)
    for i, (name, typ) in enumerate(rows):
        dl.text(c, x + _PBOX_PAD, base + i * _PBOX_ROW_LH, name, _PBOX_ROW_SIZE, family=dl.M)
        dl.text(c, x + w - _PBOX_PAD, base + i * _PBOX_ROW_LH, typ, _PBOX_ROW_SIZE, anchor="end",
                fill=dl.GREY, family=dl.M)
    return h


def radar_output_anatomy(out_dir):
    """Capacity against count for every per-detection tensor, beside the two groups of params."""
    MARGIN = 24.0
    NAME_X = 180.0                   # right edge of the tensor-name column
    TAG_X = NAME_X + 66              # right edge of the component-tag column
    BAR_X = TAG_X + 10
    BAR_W, FILL_W = 500.0, 100.0     # the bar is Nmax slots; the first fifth is delivered
    ROW_H, ROW_GAP = 26.0, 2.0       # the three Coordinates rows
    BAR_H, BAR_GAP = 34.0, 12.0      # the other tensors
    NMAX_LABEL_Y, NMAX_Y = 70.0, 80.0
    COUNT_LABEL_Y, COUNT_Y = 108.0, 116.0
    BARS_Y = 130.0
    NOTE_GAP = 20.0                  # room for the component-first note under Coordinates
    COUNTS_BOX_W, COUNTS_BOX_H, COUNTS_GAP = 72.0, 26.0, 28.0
    LEGEND_GAP = 36.0
    PANEL_X = BAR_X + BAR_W + 40
    PANEL_W = 280.0
    PANEL_Y, PANEL_GAP = 40.0, 16.0
    W = PANEL_X + PANEL_W + MARGIN
    TENSORS = (("RCS", "float32 [Nmax] dBsm", None), ("RadialVelocityMs", "float32 [Nmax] m/s", None),
               ("TimeOffsetNs", "int32 [Nmax] ns", "all 0"), ("Flags", "uint8 [Nmax]", "VALID 0x40"))
    COORD_TAGS = ("x (az)", "y (el)", "z (range)")
    SHARED = (("frameId", "uint64 [1]"), ("timestampNs", "uint64 [1]"), ("modality", "uint32 [1]"),
              ("frameOfReference", "uint16 [1]"), ("coordsType", "uint32 [1]"),
              ("modelToAppTransform", "float32 [4, 4]"), ("frameStartTimeStampNs", "uint64 [1]"),
              ("frameStartPosM", "float32 [3]"), ("frameStartOrientation", "float32 [4]"),
              ("frameEndTimeStampNs", "uint64 [1]"), ("frameEndPosM", "float32 [3]"),
              ("frameEndOrientation", "float32 [4]"), ("maxPoints", "uint32 [1]"))
    SCAN = (("sensorID", "uint8 [1]"), ("scanIdx", "uint8 [1]"), ("cycleCnt", "uint64 [1]"),
            ("maxRangeM", "float32 [1]"), ("minVelMps", "float32 [1]"), ("maxVelMps", "float32 [1]"),
            ("minAzRad", "float32 [1]"), ("maxAzRad", "float32 [1]"), ("minElRad", "float32 [1]"),
            ("maxElRad", "float32 [1]"))

    SHARED_SUB = ("CPU-resident", "shared with the Lidar generic core model")
    SCAN_SUB = ("CPU-resident", "describe the scan that produced the frame")
    # the taller column decides the height: the two param boxes, or the bars plus their legend
    coords_h = 3 * ROW_H + 2 * ROW_GAP
    bars_bottom = BARS_Y + coords_h + NOTE_GAP + BAR_GAP + 4 * (BAR_H + BAR_GAP) - BAR_GAP
    legend_y = bars_bottom + COUNTS_GAP + COUNTS_BOX_H + LEGEND_GAP
    scan_y = PANEL_Y + _param_box_height(SHARED_SUB, SHARED) + PANEL_GAP
    H = max(legend_y + 2 * 20 + MARGIN, scan_y + _param_box_height(SCAN_SUB, SCAN) + MARGIN)
    c = dl.Canvas(
        W, H, "Anatomy of one radar PointCloud output",
        "Left: one horizontal bar per per-detection tensor, each 2500 slots wide; Coordinates as three "
        "component-first rows x, y, z (or azimuth, elevation, range) and RCS, RadialVelocityMs, "
        "TimeOffsetNs and Flags as one row each. In every bar the first Counts[0] slots are filled and "
        "the rest are gray. A bracket over the full width reads Nmax = maxPoints = 2500 and one over the "
        "filled part reads Counts[0]; a small Counts box points at the boundary. Right: two boxes list "
        "the CPU-resident params, the thirteen shared with the Lidar generic core model from frameId to "
        "maxPoints and the ten scan params from sensorID to maxElRad.")

    # brackets
    _bracket(c, BAR_X, BAR_X + BAR_W, NMAX_Y)
    _mixed(c, BAR_X + BAR_W / 2, NMAX_LABEL_Y,
           [("Nmax = maxPoints = 2500", dl.M), ("slots allocated in every bar", dl.F)], 12, anchor="middle")
    _bracket(c, BAR_X, BAR_X + FILL_W, COUNT_Y)
    _mixed(c, BAR_X + FILL_W / 2, COUNT_LABEL_Y, [("Counts[0]", dl.M), ("delivered", dl.F)], 12,
           anchor="middle")

    # Coordinates: three component-first rows
    y = BARS_Y
    for i, tag in enumerate(COORD_TAGS):
        ry = y + i * (ROW_H + ROW_GAP)
        _rect(c, BAR_X, ry, BAR_W, ROW_H, dl.FAINT)
        _rect(c, BAR_X, ry, FILL_W, ROW_H, dl.GREEN)
        dl.text(c, TAG_X, ry + ROW_H / 2 + 4, tag, 11, "normal", "end", dl.GREY, dl.M)
    mid = y + coords_h / 2
    dl.text(c, NAME_X, mid - 4, "Coordinates", 12, "bold", "end", dl.DK, dl.M)
    dl.text(c, NAME_X, mid + 12, "float32 [3, Nmax]", 11, "normal", "end", dl.GREY, dl.M)
    dl.text(c, BAR_X + FILL_W / 2, y + ROW_H / 2 + 4, "delivered", 11, "normal", "middle", dl.DK)
    dl.text(c, BAR_X + FILL_W + (BAR_W - FILL_W) / 2, y + ROW_H / 2 + 4,
            "past Counts[0]: not detections, do not read", 11, "normal", "middle", dl.DK)
    y += coords_h
    dl.text(c, BAR_X, y + 15, "component-first: all x, then all y, then all z; strides [Nmax, 1]", 11,
            fill=dl.GREY)
    y += NOTE_GAP + BAR_GAP

    # the four single-row tensors
    for name, typ, note in TENSORS:
        _rect(c, BAR_X, y, BAR_W, BAR_H, dl.FAINT)
        _rect(c, BAR_X, y, FILL_W, BAR_H, dl.GREEN)
        dl.text(c, NAME_X, y + BAR_H / 2 - 4, name, 12, "bold", "end", dl.DK, dl.M)
        dl.text(c, NAME_X, y + BAR_H / 2 + 12, typ, 11, "normal", "end", dl.GREY, dl.M)
        if note:
            dl.text(c, BAR_X + FILL_W / 2, y + BAR_H / 2 + 4, note, 11, "normal", "middle", dl.DK, dl.M)
        y += BAR_H + BAR_GAP

    # the Counts box, pointing at the boundary between delivered and allocated
    bx, by = BAR_X + FILL_W - COUNTS_BOX_W / 2, bars_bottom + COUNTS_GAP
    _rect(c, bx, by, COUNTS_BOX_W, COUNTS_BOX_H, dl.WHITE, stroke=dl.DK, stroke_width=1.5, rx=4)
    dl.text(c, bx + COUNTS_BOX_W / 2, by + COUNTS_BOX_H / 2 + 4, "Counts", 11, "bold", "middle", dl.DK, dl.M)
    dl.arrow(c, BAR_X + FILL_W, by, BAR_X + FILL_W, bars_bottom + 1, stroke=dl.DK, width=2)
    _mixed(c, bx + COUNTS_BOX_W + 10, by + 11, [("Counts int32 [1]:", dl.M), ("the delivered count;", dl.F)], 12)
    dl.text(c, bx + COUNTS_BOX_W + 10, by + 28, "read every bar up to it, never to its length", 12)
    dl.legend(c, BAR_X, legend_y, [
        ("delivered entries, indices [0, Counts[0])", dl.GREEN),
        ("allocated but past Counts[0]: not detections", dl.FAINT),
    ], horizontal=False)

    # the params
    _param_box(c, PANEL_X, PANEL_Y, PANEL_W, "Shared params (13)", SHARED_SUB, SHARED)
    _param_box(c, PANEL_X, scan_y, PANEL_W, "Scan params (10)", SCAN_SUB, SCAN)

    dl.validate(c)
    dl.write_svg(out_dir / "radar_output_anatomy.svg", c.render())


def generate(out_dir: pathlib.Path) -> None:
    radar_moving_targets_scene(out_dir)
    radar_scan_cycle_vs_stepping(out_dir)
    radar_validation_check_order(out_dir)
    radar_output_anatomy(out_dir)


if __name__ == "__main__":
    generate(dl.output_dir(__file__))
