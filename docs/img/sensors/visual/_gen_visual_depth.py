#!/usr/bin/env python3
"""Figures of the Camera single-view stereo depth model pages.

One function per SVG, named after the file it writes. ``python3 -B _gen_visual_depth.py``
run in this directory regenerates only this group in place; ``generate_diagrams.py`` runs
every ``_gen_*.py`` module of the directory. Shared palette, fonts and shapes come from
``../_diagram_lib.py``.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import _diagram_lib as dl  # noqa: E402

# The two shades the near-limit plot's shaded spans actually show, for their legend swatches:
# PURPLE at 0.10 opacity over white, and BLUE at 0.12 opacity over that (where both spans overlap).
PURPLE_TINT, BOTH_TINT = "#F4EAF9", "#D7DCF6"


# ------------------------------------------------------------------------------------ helpers ---
def _fits(s: str, w: float, size: float, weight="normal", family: str = dl.F) -> float:
    """Assert that ``s`` fits into ``w`` px at ``size`` so that nothing is shrunk silently."""
    tw = dl.text_width(s, size, weight, family)
    assert tw <= w, (s, tw, w)
    return size


def _vtext(c: dl.Canvas, x: float, y: float, s: str, size: float = 12, fill: str = dl.GREY,
           weight="normal", family: str = dl.F) -> None:
    """Text rotated by -90 degrees (reads bottom to top), centred on (x, y); registered for the checks."""
    attrs = (f'x="{dl.fmt(x)}" y="{dl.fmt(y)}" font-family="{family}" font-size="{dl.fmt(size)}" '
             f'fill="{fill}" text-anchor="middle" transform="rotate(-90 {dl.fmt(x)} {dl.fmt(y)})"')
    if str(weight) != "normal":
        attrs += f' font-weight="{weight}"'
    c.add(f"<text {attrs}>{dl.esc(s)}</text>")
    w = dl.text_width(s, size, weight, family)
    c.note_text(dl.TextBox(round(x - 0.78 * size, 2), round(y - w / 2, 2),
                           round(x + 0.24 * size, 2), round(y + w / 2, 2), s))


def _line(c: dl.Canvas, x1, y1, x2, y2, stroke: str = dl.FAINT, width: float = 1,
          dashed: bool = False) -> None:
    attrs = (f'x1="{dl.fmt(x1)}" y1="{dl.fmt(y1)}" x2="{dl.fmt(x2)}" y2="{dl.fmt(y2)}" '
             f'stroke="{stroke}" stroke-width="{dl.fmt(width)}"')
    if dashed:
        attrs += f' stroke-dasharray="{dl.fmt(3 * width)} {dl.fmt(2 * width)}"'
    c.add(f"<line {attrs}/>")


def _path(c: dl.Canvas, pts, stroke: str, width: float, dashed: bool = False) -> None:
    """A polyline through ``pts`` with round joins; no smoothing, no arrowhead."""
    d = " ".join(("M" if i == 0 else "L") + f"{dl.fmt(x)},{dl.fmt(y)}" for i, (x, y) in enumerate(pts))
    attrs = (f'd="{d}" fill="none" stroke="{stroke}" stroke-width="{dl.fmt(width)}" '
             f'stroke-linejoin="round" stroke-linecap="round"')
    if dashed:
        attrs += f' stroke-dasharray="{dl.fmt(3 * width)} {dl.fmt(2 * width)}"'
    c.add(f"<path {attrs}/>")


def _rect(c: dl.Canvas, x, y, w, h, fill: str, opacity: float = 1.0, stroke: str = "none",
          stroke_width: float = 1) -> None:
    attrs = f'x="{dl.fmt(x)}" y="{dl.fmt(y)}" width="{dl.fmt(w)}" height="{dl.fmt(h)}" fill="{fill}"'
    if opacity < 1.0:
        attrs += f' fill-opacity="{dl.fmt(opacity)}"'
    if stroke != "none":
        attrs += f' stroke="{stroke}" stroke-width="{dl.fmt(stroke_width)}"'
    c.add(f"<rect {attrs}/>")


def _dot(c: dl.Canvas, x, y, r: float, fill: str, stroke: str = "none", stroke_width: float = 0) -> None:
    attrs = f'cx="{dl.fmt(x)}" cy="{dl.fmt(y)}" r="{dl.fmt(r)}" fill="{fill}"'
    if stroke != "none":
        attrs += f' stroke="{stroke}" stroke-width="{dl.fmt(stroke_width)}"'
    c.add(f"<circle {attrs}/>")


def _dim_h(c: dl.Canvas, x1, x2, y, stroke: str = dl.GREY, width: float = 1.2) -> None:
    """A double-headed horizontal dimension line from ``x1`` to ``x2`` at ``y``."""
    mid = (float(x1) + float(x2)) / 2
    dl.arrow(c, mid, y, x1, y, stroke, width)
    dl.arrow(c, mid, y, x2, y, stroke, width)


def _dim_v(c: dl.Canvas, x, y1, y2, stroke: str = dl.GREY, width: float = 1.2) -> None:
    """A double-headed vertical dimension line from ``y1`` to ``y2`` at ``x``."""
    mid = (float(y1) + float(y2)) / 2
    dl.arrow(c, x, mid, x, y1, stroke, width)
    dl.arrow(c, x, mid, x, y2, stroke, width)


def _bracket_h(c: dl.Canvas, x0, x1, y, tick: float, color: str, width: float = 1.5) -> None:
    """A horizontal bracket from ``x0`` to ``x1`` at ``y`` whose end ticks point up."""
    d = (f"M{dl.fmt(x0)},{dl.fmt(y - tick)} L{dl.fmt(x0)},{dl.fmt(y)} "
         f"L{dl.fmt(x1)},{dl.fmt(y)} L{dl.fmt(x1)},{dl.fmt(y - tick)}")
    c.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{dl.fmt(width)}"/>')


def _legend_rows(c: dl.Canvas, x: float, y: float, rows, size: float = 12, row_h: float = 20) -> float:
    """A vertical legend of ``(style, color, label, family)`` rows; returns the y below the last row.

    ``style`` is ``box``, ``line``, ``thick``, ``dashed`` or ``ring``. Unlike :func:`dl.legend`
    each row chooses its font family, so attribute names can be set in mono.
    """
    for i, (style, color, label, family) in enumerate(rows):
        cy = y + i * row_h
        if style == "box":
            c.add(f'<rect x="{dl.fmt(x)}" y="{dl.fmt(cy - 6)}" width="14" height="12" rx="2" fill="{color}" '
                  f'stroke="{dl.FAINT}" stroke-width="1"/>')
        elif style == "ring":
            _dot(c, x + 7, cy, 4.5, dl.WHITE, color, 2)
        else:
            w = 4 if style == "thick" else 2
            _line(c, x, cy, x + 16, cy, color, w, dashed=(style == "dashed"))
        dl.text(c, x + 24, cy + 0.36 * size, label, size, "normal", "start", dl.DK, family)
    return y + len(rows) * row_h


def depth_disparity_geometry(out_dir: pathlib.Path) -> None:
    """Top view of two pinhole imagers observing one point, with a confidence-threshold inset."""
    W, H = 1040, 680
    HEADING, LABEL, SMALL = 14, 12, 11
    # geometry: the scene point P at the top, the optical centres below it, the image planes
    # behind the centres (a pinhole imager), so the rays pass through the centres and continue
    PX, PY = 390, 72                       # scene point P
    LX, RX, CY = 300, 480, 372             # optical centres; the baseline is RX - LX
    FL = 80                                # optical centre to image plane
    PLY = CY + FL                          # image plane row
    HW = 80                                # half the drawn width of each image plane
    D = CY - PY                            # distance from the centres to P
    L_HIT = LX - (PX - LX) * FL / D        # where P lands on the left plane
    R_HIT = RX + (RX - PX) * FL / D        # where P lands on the right plane
    GHOST = RX + (L_HIT - LX)              # the left imager's column, carried to the right plane
    TICK_STEP, TICK_LEN = 16, 5            # sensor pixel ticks along the planes
    # dimension lines
    BASE_Y = CY - 34                       # baselineMM dimension above the centres
    DIST_X = 684                           # distance_m dimension at the right
    FOC_X = 580                            # focalLengthPixel dimension at the right imager
    SENS_Y = PLY + 50                      # sensorSizePixel dimensions below the planes
    BRACKET_Y = PLY + 14                   # disparity bracket under the right plane
    GRID_Y, GRID_ROW, CELL = PLY + 86, 12, 8   # output pixel grid under the right imager
    FORMULA_X, FORMULA_Y, FORMULA_LH = 40, 614, 20
    # inset
    IN_X, IN_Y, IN_W, IN_H = 620, 430, 400, 230
    PLOT_X0, PLOT_X1, PLOT_Y0, PLOT_Y1 = 700, 1004, 486, 616
    LEGEND_X, LEGEND_Y = 700, 110

    c = dl.Canvas(W, H, "Disparity geometry",
                  "Two imagers separated by a baseline observe one point at distance d; the point projects to "
                  "different pixel columns on the two imagers, and the column difference is the "
                  "disparity. An inset plots the applied confidence threshold against the authored "
                  "threshold.")
    dl.text(c, 24, 30, "Top view: one scene point P seen by two imagers", HEADING, "bold")

    # --- optical axes, image planes with sensor-pixel ticks, the disparity highlight
    for cx in (LX, RX):
        _line(c, cx, CY, cx, PLY, dl.FAINT, 1, dashed=True)
        _line(c, cx - HW, PLY, cx + HW, PLY, dl.DK, 3)
        for i in range(2 * HW // TICK_STEP + 1):
            tx = cx - HW + i * TICK_STEP
            _line(c, tx, PLY + 2, tx, PLY + 2 + TICK_LEN, dl.GREY, 1)
    _line(c, GHOST, PLY, R_HIT, PLY, dl.GREEN, 6)

    # --- rays from P through the centres to the planes, then the points on top
    _line(c, PX, PY, L_HIT, PLY, dl.BLUE, 2)
    _line(c, PX, PY, R_HIT, PLY, dl.PURPLE, 2)
    _dot(c, PX, PY, 5, dl.DK)
    dl.text(c, PX, PY - 12, "P", HEADING, "bold", "middle")
    for cx in (LX, RX):
        _dot(c, cx, CY, 4, dl.DK, dl.WHITE, 1.5)
    _dot(c, L_HIT, PLY, 4.5, dl.BLUE, dl.WHITE, 1.5)
    _dot(c, GHOST, PLY, 4.5, dl.WHITE, dl.BLUE, 2)
    _dot(c, R_HIT, PLY, 4.5, dl.PURPLE, dl.WHITE, 1.5)

    # --- imager names, above the centres and clear of the rays
    dl.text(c, LX - 8, CY - 10, "rendered camera", LABEL, "normal", "end", dl.GREY)
    dl.text(c, RX + 8, CY - 10, "simulated second imager", LABEL, "normal", "start", dl.GREY)

    # --- baselineMM between the optical centres
    _line(c, LX, CY - 8, LX, BASE_Y - 6)
    _line(c, RX, CY - 8, RX, BASE_Y - 6)
    _dim_h(c, LX, RX, BASE_Y)
    dl.text(c, (LX + RX) / 2, BASE_Y - 10, "baselineMM (mm)", LABEL, "normal", "middle", dl.DK, dl.M)

    # --- distance_m from the centres' row to P, and focalLengthPixel from a centre to its plane
    _line(c, PX + 8, PY, DIST_X + 6, PY)
    _line(c, RX + 8, CY, DIST_X + 6, CY)
    _dim_v(c, DIST_X, PY, CY)
    dl.text(c, DIST_X + 8, (PY + CY) / 2 + 4, "distance_m (m)", LABEL, "normal", "start", dl.DK, dl.M)
    _line(c, RX + HW + 4, PLY, FOC_X + 6, PLY)
    _dim_v(c, FOC_X, CY, PLY)
    dl.text(c, FOC_X + 10, (CY + PLY) / 2 + 4, "focalLengthPixel (px)", LABEL, "normal", "start",
            dl.DK, dl.M)

    # --- the disparity on the right plane, measured in output pixels beneath it
    _bracket_h(c, GHOST, R_HIT, BRACKET_Y, 5, dl.GREEN, 1.5)
    dl.text(c, RX, BRACKET_Y + 18, "disparity_px", LABEL, "normal", "middle", dl.DK, dl.M)

    # --- sensorSizePixel: the width of each image plane
    for cx in (LX, RX):
        _line(c, cx - HW, PLY + 4, cx - HW, SENS_Y + 4)
        _line(c, cx + HW, PLY + 4, cx + HW, SENS_Y + 4)
        _dim_h(c, cx - HW, cx + HW, SENS_Y)
        dl.text(c, cx, SENS_Y + 18, "sensorSizePixel (px)", LABEL, "normal", "middle", dl.DK, dl.M)

    # --- the output pixel grid: the product's resolution laid over the right imager's width
    n_cells = 2 * HW // CELL
    _rect(c, RX - HW, GRID_Y, 2 * HW, 2 * GRID_ROW, dl.WHITE, 1.0, dl.GREY, 1)
    first = int((GHOST - (RX - HW)) // CELL)
    last = int((R_HIT - (RX - HW)) // CELL)
    _rect(c, RX - HW + first * CELL, GRID_Y, (last - first) * CELL, 2 * GRID_ROW, dl.GREEN, 0.3)
    for i in range(1, n_cells):
        _line(c, RX - HW + i * CELL, GRID_Y, RX - HW + i * CELL, GRID_Y + 2 * GRID_ROW, dl.FAINT, 1)
    _line(c, RX - HW, GRID_Y + GRID_ROW, RX + HW, GRID_Y + GRID_ROW, dl.FAINT, 1)
    dl.text(c, RX, GRID_Y + 2 * GRID_ROW + 20, "width_px = product resolution", LABEL, "normal", "middle",
            dl.DK, dl.M)

    # --- the relation, as the page prints it
    dl.text(c, FORMULA_X, FORMULA_Y, "disparity_px = width_px * baselineMM * focalLengthPixel", 13,
            "normal", "start", dl.DK, dl.M)
    # the continuation line is placed explicitly (leading spaces do not survive every renderer)
    dl.text(c, FORMULA_X + dl.text_width("disparity_px = ", 13, family=dl.M), FORMULA_Y + FORMULA_LH,
            "/ sensorSizePixel / (distance_m * 1000)", 13, "normal", "start", dl.DK, dl.M)

    # --- legend
    _legend_rows(c, LEGEND_X, LEGEND_Y, [
        ("line", dl.BLUE, "ray to the rendered camera (left imager)", dl.F),
        ("line", dl.PURPLE, "ray to the simulated second imager", dl.F),
        ("thick", dl.GREEN, "disparity: the column shift between the two", dl.F),
        ("ring", dl.BLUE, "the left imager's column on the right imager", dl.F),
    ])

    # --- inset: the applied confidence threshold against the authored value
    dl.box(c, IN_X, IN_Y, IN_W, IN_H, fill=dl.PANEL, rx=8)
    dl.text(c, IN_X + 16, IN_Y + 22, "Applied confidence threshold", 13, "bold")
    dl.text(c, IN_X + 16, IN_Y + 39, "1 - confidenceThreshold^0.05", SMALL, "normal", "start",
            dl.GREY, dl.M)
    px_w, py_h = PLOT_X1 - PLOT_X0, PLOT_Y1 - PLOT_Y0

    def tx(t: float) -> float:
        return PLOT_X0 + t * px_w

    def ty(threshold: float) -> float:
        return PLOT_Y1 - threshold * py_h

    marks = (0.0, 0.1, 0.5, 0.9, 1.0)
    dl.tick_marks(c, PLOT_X0, PLOT_Y1, px_w, [tx(t) - PLOT_X0 for t in marks],
                  ["0", "0.1", "0.5", "0.9", "1"], size=SMALL)
    dl.tick_marks(c, PLOT_X0, PLOT_Y0, py_h, [0, py_h / 2, py_h], ["1", "0.5", "0"], horizontal=False,
                  size=SMALL)
    dl.text(c, (PLOT_X0 + PLOT_X1) / 2, PLOT_Y1 + 36, "authored confidenceThreshold", SMALL, "normal",
            "middle", dl.GREY, dl.M)
    _vtext(c, IN_X + 36, (PLOT_Y0 + PLOT_Y1) / 2, "applied threshold", SMALL)
    # the curve plunges from 1 at t = 0, so sample densely near zero
    ts = [0.0, 1e-6, 1e-5, 1e-4, 1e-3, 0.002, 0.005, 0.01, 0.02, 0.03, 0.05, 0.075]
    ts += [i / 40 for i in range(4, 41)]
    _path(c, [(tx(t), ty(1 - t ** 0.05)) for t in ts], dl.BLUE, 2)
    # the three points of the page's remap table, labelled with the applied threshold
    for t in (0.1, 0.5):
        _dot(c, tx(t), ty(1 - t ** 0.05), 3, dl.BLUE)
    _dot(c, tx(0.9), ty(1 - 0.9 ** 0.05), 4.5, dl.GREEN, dl.WHITE, 1.5)
    dl.text(c, tx(0.1) + 8, ty(1 - 0.1 ** 0.05) - 7, "about 0.11", SMALL, "normal", "start", dl.DK)
    dl.text(c, tx(0.5), ty(1 - 0.5 ** 0.05) - 9, "about 0.034", SMALL, "normal", "middle", dl.DK)
    dl.text(c, PLOT_X1, ty(1 - 0.9 ** 0.05) - 13, "about 0.005", SMALL, "normal", "end", dl.DK)

    dl.validate(c)
    dl.write_svg(out_dir / "depth_disparity_geometry.svg", c.render())


def depth_camera_near_limit(out_dir: pathlib.Path) -> None:
    """Disparity against distance at two product widths, with disparity and distance limits."""
    W, H = 1000, 600
    X0, X1, Y0, Y1 = 72, 960, 70, 490            # plot area
    D_MIN, D_MAX, V_MAX = 0.2, 3.0, 260           # axis ranges: metres, disparity pixels
    K_A, K_B = 49.335, 98.67                      # disparity = K / distance_m for 1280 and 2560 px
    CAP, GATE = 110, 0.5                          # maxDisparityPixel, minDistance
    D_A, D_B = 0.4485, 0.897                      # where each curve reaches the cap
    STEP = 0.01
    LABEL_D = 2.6                                 # where the curve names sit
    LEGEND_X, LEGEND_Y = 600, 100
    BODY, SMALL = 11.5, 11

    def xs(d: float) -> float:
        return X0 + (d - D_MIN) / (D_MAX - D_MIN) * (X1 - X0)

    def ys(v: float) -> float:
        return Y1 - v / V_MAX * (Y1 - Y0)

    c = dl.Canvas(W, H, "Near limit from maximum disparity, schema defaults",
                  "The effective near limit is the greater of minDistance and the disparity-derived distance. "
                  "Disparity in pixels against distance in meters at the schema defaults: a 1280-pixel-"
                  "wide product reaches maxDisparityPixel = 110 at about 0.45 m, below "
                  "minDistance = 0.5 m, so minDistance determines the near limit. A 2560-pixel-wide product "
                  "reaches the maximum disparity at about 0.9 m, which determines its near limit.")
    dl.text(c, 24, 34, "Near limit from maximum disparity, schema defaults", 15, "bold")

    # --- shaded spans where nothing is measured: left of the gate for A, left of the cap for B
    _rect(c, xs(D_MIN), Y0, xs(D_B) - xs(D_MIN), Y1 - Y0, dl.PURPLE, 0.10)
    _rect(c, xs(D_MIN), Y0, xs(GATE) - xs(D_MIN), Y1 - Y0, dl.BLUE, 0.12)
    # the two spans overlap nearer than the gate, so that part is where neither product measures
    for i, ln in enumerate(("nothing", "measured by", "either product")):
        _fits(ln, xs(GATE) - xs(D_MIN) - 12, SMALL)
        dl.text(c, (xs(D_MIN) + xs(GATE)) / 2, Y1 - 52 + i * 17, ln, SMALL, "normal", "middle", dl.DK)
    for i, ln in enumerate(("nothing measured", "by the 2560 px", "product only")):
        _fits(ln, xs(D_B) - xs(GATE) - 12, SMALL)
        dl.text(c, (xs(GATE) + xs(D_B)) / 2, Y1 - 52 + i * 17, ln, SMALL, "normal", "middle", dl.DK)

    # --- axes
    d_ticks = [0.2, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    dl.tick_marks(c, X0, Y1, X1 - X0, [xs(d) - X0 for d in d_ticks], [f"{d:.1f}" for d in d_ticks])
    v_ticks = [250, 200, 150, 100, 50, 0]
    dl.tick_marks(c, X0, Y0, Y1 - Y0, [ys(v) - Y0 for v in v_ticks], [str(v) for v in v_ticks],
                  horizontal=False)
    dl.text(c, (X0 + X1) / 2, Y1 + 50, "distance (m)", 13, "normal", "middle", dl.GREY)
    _vtext(c, 26, (Y0 + Y1) / 2, "disparity (px)", 13)

    # --- cap and gate
    _line(c, X0, ys(CAP), X1, ys(CAP), dl.RED, 1.5, dashed=True)
    dl.text(c, X1 - 4, ys(CAP) - 8, "maxDisparityPixel = 110", BODY, "normal", "end", dl.DK, dl.M)
    _line(c, xs(GATE), Y0, xs(GATE), Y1, dl.ORANGE, 1.5, dashed=True)
    dl.text(c, xs(GATE) + 8, Y0 + 20, "minDistance = 0.5 m", BODY, "normal", "start", dl.DK, dl.M)

    # --- the two curves
    n = int(round((D_MAX - D_MIN) / STEP))
    pts_a = [(xs(D_MIN + i * STEP), ys(K_A / (D_MIN + i * STEP))) for i in range(n + 1)]
    d_b0 = K_B / V_MAX                                   # where curve B enters the plot from above
    pts_b = [(xs(d_b0), Y0)]
    pts_b += [(xs(D_MIN + i * STEP), ys(K_B / (D_MIN + i * STEP))) for i in range(n + 1)
              if D_MIN + i * STEP > d_b0]
    _path(c, pts_a, dl.BLUE, 2.2)
    _path(c, pts_b, dl.PURPLE, 2.2)
    dl.text(c, xs(LABEL_D), ys(K_A / LABEL_D) + 20, "1280 px product", BODY, "bold", "middle", dl.BLUE)
    dl.text(c, xs(LABEL_D), ys(K_B / LABEL_D) - 14, "2560 px product", BODY, "bold", "middle", dl.PURPLE)

    # --- where each curve reaches the cap
    _dot(c, xs(D_A), ys(CAP), 5, dl.WHITE, dl.BLUE, 2.5)
    _dot(c, xs(D_B), ys(CAP), 5, dl.WHITE, dl.PURPLE, 2.5)
    dl.text(c, xs(D_B) + 12, ys(CAP) - 10, "about 0.9 m: near limit at 2560 px", BODY, "normal",
            "start", dl.DK)
    dl.text_block(c, xs(D_MIN) + 6, ys(CAP) + 24,
                  "about 0.45 m: already excluded by minDistance = 0.5 m",
                  xs(GATE) - xs(D_MIN) - 12, BODY, dl.DK)

    # --- legend
    _legend_rows(c, LEGEND_X, LEGEND_Y, [
        ("line", dl.BLUE, "1280 px product", dl.F),
        ("line", dl.PURPLE, "2560 px product", dl.F),
        ("dashed", dl.RED, "maxDisparityPixel = 110", dl.M),
        ("dashed", dl.ORANGE, "minDistance = 0.5 m", dl.M),
        ("box", BOTH_TINT, "nothing measured by either product", dl.F),
        ("box", PURPLE_TINT, "nothing measured by the 2560 px product only", dl.F),
    ])

    dl.validate(c)
    dl.write_svg(out_dir / "depth_camera_near_limit.svg", c.render())


def depth_camera_stage_chain(out_dir: pathlib.Path) -> None:
    """Six post-processing stages: 1-3 down the left, 4-6 down the right, renderer inputs
    at the left edge, the stage-1 branch at the top right and the four stage-6 outputs in a grid
    below the columns. Body text is 16 px on a 1000 px canvas."""
    W = 1000
    LANE_X = 24                                   # the LdrColor route down to stage 5
    IN_X, IN_W = 36, 224                          # input chips at the left edge
    COL_W, L_X = 300, 296                         # stage columns: left column starts here
    STRIP_LANES = 4                               # vertical routes between the columns
    LANE_DX = 13
    R_X = L_X + COL_W + LANE_DX * (STRIP_LANES + 1)
    OUT_W = 305                                   # output chips at the right edge
    OUT_X = W - 16 - OUT_W
    COL1_X, LEFT_W = 330, 266                     # the output grid's left column: clear of the legend,
                                                  # just wide enough for DepthSensorPointCloudColor
    GRID_GAP = OUT_X - COL1_X - LEFT_W            # between the two columns of the output grid (83)
    GAP = 34                                      # gap between stacked stages
    TITLE, BODY, LH = 16, 16, 21                  # font sizes (px) and line height
    PAD, TEXT_DX, DOT_R = 14, 38, 11
    CHIP_PAD = 10

    stages = [
        ("Luminance",
         "Rec. 709 luminance of the color image, scaled to 0–1. This image is DepthSensorImager and "
         "the input of stage 2.",
         "discards nothing: every pixel gets a value", None),
        ("Confidence from texture",
         "A luminance edge measure compared with the threshold derived from confidenceThreshold. "
         "When effectiveDistance > 0 the simulated IR projector adds a term that lets near surfaces "
         "pass whatever their texture.",
         "discards smooth, untextured pixels; the result is kept per source pixel and applied in stage 6",
         "confidenceThreshold, effectiveDistance"),
        ("Reprojection",
         "Each pixel's distance becomes a disparity and is written where the second imager, "
         "baselineMM away, would have seen it.",
         "discards distances outside minDistance..maxDistance, disparities above maxDisparityPixel, "
         "the farther of two samples projected to one pixel, and samples outside their tile; "
         "pixels with no projected sample have no measurement",
         "baselineMM, minDistance, maxDistance, maxDisparityPixel"),
        ("Outlier cleanup",
         "When outlierRemovalEnabled is enabled, an invalid pixel between two valid row neighbors "
         "is assigned the farther distance. A valid pixel between two invalid neighbors is removed.",
         "discards isolated valid pixels; excludes the leftmost and rightmost columns",
         "outlierRemovalEnabled"),
        ("Noise and quantization",
         "Disparity jitter and quantization change a sample's pixel position along its row "
         "while preserving its distance value. The point position and color are written "
         "here from the source pixel.",
         "discards nothing directly; a moved sample can empty one pixel and fill another",
         "noiseMean, noiseSigma, noiseDownscaleFactorPixel"),
        ("Final filtering and output",
         "Writes DepthSensorDistance, the point cloud (zero for invalid measurements) and the "
         "visualization image.",
         "zeroes a distance at or outside the range limits, a sample occluded by a nearer reprojected surface, "
         "and a sample whose source pixel failed the confidence test",
         "minDistance, maxDistance"),
    ]
    # (name, type line, role line) of the three renderer outputs the model reads
    inputs = [
        ("LdrColor", "uint8 RGBA, 0–255", "luminance · point color"),
        ("DistanceToImagePlaneSD", "float32, meters", "rendered distance"),
        ("Camera3dPositionSD", "float32 xyzw, scene units", "point positions"),
    ]
    # (name, lines...) of the five depth outputs; the first branches off stage 1, the rest are
    # written by stage 6
    outputs = [
        ("DepthSensorImager", "float32 (H, W, 1)"),
        ("DepthSensorDistance", "float32 (H, W, 1), meters"),
        ("DepthSensorPointCloudPosition", "float32 (H, W, 4), w = 1"),
        ("DepthSensorPointCloudColor", "uint8 (H, W, 4)"),
        ("DepthSensorOutputVisualization", "uint8 (H, W, 4)", "selected by rgbDepthOutputMode"),
    ]

    tw = COL_W - TEXT_DX - 14                     # text width inside a stage box

    def stage_lines(desc: str, disc: str, attrs):
        d = dl.wrap_text(desc, tw, BODY)
        x = dl.wrap_text(disc, tw - 14, BODY)
        a = dl.wrap_text(attrs, tw, BODY, "normal", dl.M) if attrs else []
        return d, x, a

    def stage_height(desc: str, disc: str, attrs) -> float:
        d, x, a = stage_lines(desc, disc, attrs)
        h = PAD + 13 + 26 + (len(d) - 1) * LH + 29 + (len(x) - 1) * LH
        if a:
            h += 29 + (len(a) - 1) * LH
        return h + 5 + PAD

    def draw_stage(c: dl.Canvas, i: int, r: dl.Rect, title: str, desc: str, disc: str, attrs) -> None:
        dl.box(c, r.x, r.y, r.w, r.h, fill=dl.PANEL, rx=8)
        yb = r.y + PAD + 13
        _dot(c, r.x + 20, yb - 5.8, DOT_R, dl.DK)
        dl.text(c, r.x + 20, yb, str(i + 1), 16, "bold", "middle", dl.WHITE)
        tx = r.x + TEXT_DX
        _fits(title, tw, TITLE, "bold")
        dl.text(c, tx, yb, title, TITLE, "bold")
        d, x, a = stage_lines(desc, disc, attrs)
        yb += 26
        for ln in d:
            dl.text(c, tx, yb, ln, BODY, "normal", "start", dl.GREY)
            yb += LH
        yb += 8
        _rect(c, tx, yb - 9, 9, 9, dl.RED)
        for ln in x:
            dl.text(c, tx + 14, yb, ln, BODY, "normal", "start", dl.DK)
            yb += LH
        if a:
            yb += 8
            for ln in a:
                dl.text(c, tx, yb, ln, BODY, "normal", "start", dl.GREY, dl.M)
                yb += LH

    def chip(c: dl.Canvas, x: float, y: float, w: float, lines, fill: str) -> dl.Rect:
        """A rounded chip: the name in mono on the first line, the other lines in the body font."""
        h = 2 * CHIP_PAD + LH * len(lines)
        dl.box(c, x, y, w, h, fill=fill, rx=6)
        fg = dl.contrast_text(fill)
        sub = dl.sublabel_text(fill, fg)
        for k, ln in enumerate(lines):
            fam = dl.M if k == 0 else dl.F
            _fits(ln, w - 12, 16, "normal", fam)
            dl.text(c, x + w / 2, y + CHIP_PAD + 15 + k * LH, ln, 16, "normal", "middle",
                    fg if k == 0 else sub, fam)
        return dl.Rect(x, y, w, h)

    def elbow(c: dl.Canvas, pts, stroke: str, width: float = 2, dashed: bool = False) -> None:
        """A routed connector of horizontal and vertical segments; the arrowhead lands on the last point."""
        dl.curve(c, pts, stroke, width, dashed=dashed, smooth=0)

    # --- layout: stages 1-3 down the left column, 4-6 down the right, the right column starting
    # below the DepthSensorImager chip and the verdict's route across the top
    heights = [stage_height(d, x, a) for _, d, x, a in stages]
    L_TOP, R_TOP = 24, 136
    tops = []
    for col, y in ((heights[:3], L_TOP), (heights[3:], R_TOP)):
        for h in col:
            tops.append(y)
            y += h + GAP
    rects = [dl.Rect(L_X if i < 3 else R_X, t, COL_W, h) for i, (t, h) in enumerate(zip(tops, heights))]
    s1, s2, s3, s4, s5, s6 = rects
    x_v, x_a, x_A, x_B = [L_X + COL_W + LANE_DX * (k + 1) for k in range(STRIP_LANES)]
    x_r = R_X + COL_W + 18                        # the verdict's route down the right side
    x_m = (IN_X + IN_W + L_X) / 2                 # the point-position route's lane beside the column
    y_bA, y_bB = s3.bottom + 26, s3.bottom + 50   # the two input routes under the left column
    CH2, CH3 = 2 * CHIP_PAD + 2 * LH, 2 * CHIP_PAD + 3 * LH
    O1_Y = 16
    y_T = O1_Y + CH2 + 14                         # the verdict's horizontal above the right column
    assert y_T + 40 <= R_TOP, (y_T, R_TOP)
    GRID_TOP = max(s6.bottom + 30, y_bB + 34)
    ROW_H = [max(2 * CHIP_PAD + LH * len(o) for o in outputs[1:3]),
             max(2 * CHIP_PAD + LH * len(o) for o in outputs[3:5])]
    x_t = COL1_X + LEFT_W + GRID_GAP / 2          # trunk from stage 6 into the output grid
    assert GRID_GAP >= 80, GRID_GAP               # each stub keeps three dashes of shaft behind its head
    H = round(max(GRID_TOP + ROW_H[0] + 12 + ROW_H[1], GRID_TOP + 5 * 24) + 24)

    c = dl.Canvas(W, H, "Depth sensor post-processing: six stages",
                  "Six post-processing stages in two columns. The three renderer outputs used as "
                  "inputs are blue; the five depth-sensor outputs are green. DepthSensorImager is "
                  "produced by stage 1. Stage 6 writes the distance and visualization outputs and "
                  "applies the confidence result from stage 2 to the depth and point-cloud entries.")

    # --- stages and the chain
    for i, ((title, desc, disc, attrs), r) in enumerate(zip(stages, rects)):
        draw_stage(c, i, r, title, desc, disc, attrs)
    for a, b in ((s1, s2), (s2, s3), (s4, s5), (s5, s6)):
        dl.arrow(c, a.cx, a.bottom + 3, b.cx, b.top - 3, dl.DK, 2.4)
    elbow(c, [(s3.right, s3.cy), (x_a, s3.cy), (x_a, s4.cy), (s4.left - 2, s4.cy)], dl.DK, 2.4)

    # --- renderer inputs at the left edge, each beside the stage that reads it
    i1 = chip(c, IN_X, s1.cy - CH3 / 2, IN_W, inputs[0], dl.BLUE)
    i2 = chip(c, IN_X, s3.top + 48, IN_W, inputs[1], dl.BLUE)
    i3 = chip(c, IN_X, s3.bottom - 19 - CH3, IN_W, inputs[2], dl.BLUE)
    dl.arrow(c, i1.right + 4, i1.cy, L_X - 4, i1.cy, dl.BLUE, 2)
    dl.arrow(c, i2.right + 4, i2.cy, L_X - 4, i2.cy, dl.BLUE, 2)
    # Camera3dPositionSD and LdrColor also feed stage 5: under the left column and up the strip
    elbow(c, [(i3.right, i3.cy), (x_m, i3.cy), (x_m, y_bA), (x_A, y_bA), (x_A, s5.cy - 18),
              (R_X - 2, s5.cy - 18)], dl.BLUE, 2)
    elbow(c, [(i1.left, i1.cy + 22), (LANE_X, i1.cy + 22), (LANE_X, y_bB), (x_B, y_bB),
              (x_B, s5.cy + 18), (R_X - 2, s5.cy + 18)], dl.BLUE, 2)
    dl.text(c, L_X + 10, y_bA - 7, "point positions", BODY, "normal", "start", dl.GREY)
    dl.text(c, L_X + 10, y_bB + 20, "point color", BODY, "normal", "start", dl.GREY)

    # --- the confidence result of stage 2, carried over the right column into stage 6
    elbow(c, [(s2.right, s2.cy), (x_v, s2.cy), (x_v, y_T), (x_r, y_T), (x_r, s6.top - 16),
              (s6.right - 44, s6.top - 16), (s6.right - 44, s6.top - 2)], dl.ORANGE, 2, dashed=True)
    dl.text(c, x_v + 12, y_T + 20, "applied at the source pixel", BODY, "normal", "start", dl.DK)

    # --- depth outputs at the right edge: the stage-1 branch at the top, the stage-6 grid below
    o1 = chip(c, OUT_X, O1_Y, OUT_W, outputs[0], dl.GREEN)
    dl.arrow(c, s1.right + 4, o1.cy, o1.left - 4, o1.cy, dl.GREEN, 2, dashed=True)
    cys = [GRID_TOP + ROW_H[0] / 2, GRID_TOP + ROW_H[0] + 12 + ROW_H[1] / 2]
    y_t = GRID_TOP - 18                           # the trunk's horizontal: its own level below the
    assert y_t >= y_bB + 14, (y_t, y_bB)          # blue input routes and above the chips
    _path(c, [(s6.cx, s6.bottom), (s6.cx, y_t), (x_t, y_t), (x_t, cys[1])], dl.GREEN, 2)
    for cy, (left, right) in zip(cys, ((outputs[1], outputs[2]), (outputs[3], outputs[4]))):
        for x, w, lines in ((COL1_X, LEFT_W, left), (OUT_X, OUT_W, right)):
            h = 2 * CHIP_PAD + LH * len(lines)
            chip(c, x, cy - h / 2, w, lines, dl.GREEN)
        dl.arrow(c, x_t, cy, COL1_X + LEFT_W + 2, cy, dl.GREEN, 2)
        dl.arrow(c, x_t, cy, OUT_X - 2, cy, dl.GREEN, 2, dashed=right is outputs[4])

    dl.legend(c, 24, GRID_TOP, [
        ("renderer input", dl.BLUE),
        ("depth sensor output", dl.GREEN),
        ("what the stage discards or zeroes", dl.RED),
        ("confidence result", dl.ORANGE, "dashed"),
        ("branches off the chain", dl.GREEN, "dashed"),
    ], size=16, swatch=14, horizontal=False)

    dl.validate(c)
    dl.write_svg(out_dir / "depth_camera_stage_chain.svg", c.render())


def generate(out_dir: pathlib.Path) -> None:
    depth_disparity_geometry(out_dir)
    depth_camera_near_limit(out_dir)
    depth_camera_stage_chain(out_dir)


if __name__ == "__main__":
    generate(dl.output_dir(__file__))
