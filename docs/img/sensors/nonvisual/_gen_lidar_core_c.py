#!/usr/bin/env python3
"""Lidar generic core model figures, group C.

Coordinates versus frame of reference, the three delivery cadences on one
timeline and the layout of one mapped ``PointCloud`` output.
``python3 -B _gen_lidar_core_c.py`` regenerates this group in place; the area's
``generate_diagrams.py`` runs it with the sibling groups.
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import _diagram_lib as dl  # noqa: E402

import math  # noqa: E402
import re  # noqa: E402

MIN_TEXT = 11.0            # smallest font size any label of this group may use
GREEN_TINT = "#D6EAB3"     # 30 % dl.GREEN over white: the "delivered" shading


# ------------------------------------------------------------------------------------ helpers ---
def _fits(label: str, width: float, size: float, weight="normal", family: str = dl.F) -> float:
    """Return ``size`` when ``label`` fits ``width`` px at it; raise instead of shrinking."""
    need = dl.text_width(label, size, weight, family)
    if need > width:
        raise ValueError(f"{label!r} needs {need} px at {size} px, has {width}")
    if size < MIN_TEXT:
        raise ValueError(f"{label!r} drawn at {size} px, below {MIN_TEXT}")
    return size


def _check_sizes(c: dl.Canvas) -> None:
    """Raise if any text the canvas holds (box labels included) is drawn below ``MIN_TEXT`` px."""
    small = sorted({m for e in c.elements for m in re.findall(r'font-size="([0-9.]+)"', e)
                    if float(m) < MIN_TEXT})
    if small:
        raise ValueError(f"{c.title!r}: text drawn at {', '.join(small)} px, below {MIN_TEXT}")


def _rich_line(c: dl.Canvas, x: float, y: float, parts, size: float = 12.0, fill: str = dl.GREY,
               anchor: str = "start", halo: str = "none") -> float:
    """One text line from ``(string, family)`` parts, so attribute names can be monospace.

    Punctuation belongs to the part before it (a gap precedes every part). ``halo`` paints a
    rectangle of that colour behind the line first, to interrupt lines running through it.
    Returns the x where the line ends. ``anchor`` is start, middle or end for the whole line.
    """
    gap = 0.3 * size + 1.5
    widths = [dl.text_width(s, size, "normal", fam) for s, fam in parts]
    total = sum(widths) + gap * (len(parts) - 1)
    if anchor == "middle":
        x -= total / 2
    elif anchor == "end":
        x -= total
    if halo != "none":
        _rect(c, x - 5, y - 0.78 * size - 3, total + 10, 1.02 * size + 6, halo)
    for (s, fam), w in zip(parts, widths):
        dl.text(c, x, y, s, size, "normal", "start", fill, fam)
        x += w + gap
    return x - gap


def _arc(cx: float, cy: float, r: float, a0: float, a1: float) -> str:
    """Path data for the arc of radius ``r`` from ``a0`` to ``a1`` degrees, counter-clockwise
    on paper (angles measured from +x, y up; SVG y grows down so the sweep flag is 0)."""
    x0, y0 = cx + r * math.cos(math.radians(a0)), cy - r * math.sin(math.radians(a0))
    x1, y1 = cx + r * math.cos(math.radians(a1)), cy - r * math.sin(math.radians(a1))
    large = 1 if a1 - a0 > 180 else 0
    return (f"M{dl.fmt(x0)},{dl.fmt(y0)} A{dl.fmt(r)},{dl.fmt(r)} 0 {large},0 "
            f"{dl.fmt(x1)},{dl.fmt(y1)}")


def _arc_stroke(c: dl.Canvas, cx, cy, r, a0, a1, stroke=dl.GREY, width=1.5, head=False) -> None:
    attrs = f'd="{_arc(cx, cy, r, a0, a1)}" fill="none" stroke="{stroke}" stroke-width="{dl.fmt(width)}"'
    if head:
        attrs += f' marker-end="url(#{c.marker(stroke, width)})"'
    c.add(f"<path {attrs}/>")


def _polar(cx: float, cy: float, r: float, a: float):
    return cx + r * math.cos(math.radians(a)), cy - r * math.sin(math.radians(a))


def _line(c: dl.Canvas, x1, y1, x2, y2, stroke=dl.GREY, width=1.5, dashed=False) -> None:
    attrs = (f'x1="{dl.fmt(x1)}" y1="{dl.fmt(y1)}" x2="{dl.fmt(x2)}" y2="{dl.fmt(y2)}" '
             f'stroke="{stroke}" stroke-width="{dl.fmt(width)}"')
    if dashed:
        attrs += f' stroke-dasharray="{dl.fmt(3 * width)} {dl.fmt(2 * width)}"'
    c.add(f"<line {attrs}/>")


def _dot(c: dl.Canvas, x, y, r, fill=dl.GREEN, stroke="none", width=1.5) -> None:
    attrs = f'cx="{dl.fmt(x)}" cy="{dl.fmt(y)}" r="{dl.fmt(r)}" fill="{fill}"'
    if stroke != "none":
        attrs += f' stroke="{stroke}" stroke-width="{dl.fmt(width)}"'
    c.add(f"<circle {attrs}/>")


def _rect(c: dl.Canvas, x, y, w, h, fill, stroke="none", width=1.0, rx=0, extra="") -> None:
    attrs = (f'x="{dl.fmt(x)}" y="{dl.fmt(y)}" width="{dl.fmt(w)}" height="{dl.fmt(h)}" '
             f'rx="{dl.fmt(rx)}" fill="{fill}"')
    if stroke != "none":
        attrs += f' stroke="{stroke}" stroke-width="{dl.fmt(width)}"'
    c.add(f"<rect {attrs}{extra}/>")


def _flash(c: dl.Canvas, x: float, y: float, y_to: float, color: str = dl.ORANGE) -> None:
    """A lightning-bolt glyph with its tip at ``(x, y)`` and a thin line down to ``y_to``."""
    pts = [(x + 2.5, y), (x - 4.5, y + 10), (x + 0.5, y + 10), (x - 2.5, y + 18),
           (x + 4.5, y + 7.5), (x + 0.5, y + 7.5)]
    c.add(f'<polygon points="{" ".join(f"{dl.fmt(px)},{dl.fmt(py)}" for px, py in pts)}" '
          f'fill="{color}"/>')
    _line(c, x, y + 17, x, y_to, color, 1.5)


def _bracket_h(c: dl.Canvas, x0: float, x1: float, y: float, tick: float = 6,
               stroke: str = dl.DK, width: float = 1.5) -> None:
    """A horizontal bracket at ``y`` whose end ticks point down."""
    c.add(f'<path d="M{dl.fmt(x0)},{dl.fmt(y + tick)} L{dl.fmt(x0)},{dl.fmt(y)} L{dl.fmt(x1)},{dl.fmt(y)} '
          f'L{dl.fmt(x1)},{dl.fmt(y + tick)}" fill="none" stroke="{stroke}" stroke-width="{dl.fmt(width)}"/>')


def _hatch_defs(c: dl.Canvas, pid: str = "hatch", color: str = dl.MUTED) -> None:
    c.add(f'<defs><pattern id="{pid}" patternUnits="userSpaceOnUse" width="7" height="7" '
          f'patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="7" stroke="{color}" '
          f'stroke-width="1.6"/></pattern></defs>')


# ------------------------------------------------------------------------------------ figures ---
def lidar_core_coords_vs_frame(out_dir: pathlib.Path) -> None:
    """One return written four ways: Cartesian or spherical, in the sensor or the world frame."""
    # canvas and panels
    W, H = 1136, 484
    SCENE_X, SCENE_Y, SCENE_W, SCENE_H = 24, 24, 340, 348
    GRID_X, GRID_Y = 384, 24
    AXIS_LBL_H = 26                 # the attribute-name labels above the grid
    HDR_W, HDR_H = 150, 54          # row header column, column header height
    CELL_W, CELL_H, GAP = 280, 128, 10
    FOOT_DY = 32                    # first footer baseline below the grid
    FOOT_LH = 20
    LEGEND_DY = 26                  # legend baseline offset below the scene panel
    # the scene (top view), 1 m = SCALE px
    SCALE = 25.0
    ORIGIN_DX, ORIGIN_DY = 50, 78   # world origin, from the panel's bottom-left corner
    AXIS_LEN, SENSOR_AXIS_LEN = 58, 44
    AXIS_LBL_GAP = 12               # axis name beyond the arrow tip
    Y_LBL_OFF = 11                  # the sensor's y name sits beside its arrowhead, on the side
    #                                 away from the world's dashed sight line (which it would
    #                                 otherwise land on)
    ARC_R_WORLD, ARC_R_SENSOR = 36, 34
    ARC_LBL_GAP = 13                # angle value beyond its arc, on the bisector
    ARC_LBL_GAP_WORLD = 20          # the world azimuth is flatter, so its label needs more air
    SENSOR_POS = (4.0, 0.5)         # world x, y in meters; the sensor sits 0.5 m up
    SENSOR_YAW = 30.0               # degrees, counter-clockwise about +z
    # one return: the same point in the four representations (sensor pose above, ISO 8855 axes;
    # sensor-frame spherical (40 deg, 5 deg, 6 m) is the input, the rest follows from it)
    CART_SENSOR = ("4.58", "3.84", "0.52")      # x, y, z in meters from the sensor
    SPH_SENSOR = ("40.00", "5.00", "6.00")      # azimuth deg, elevation deg, range m
    CART_WORLD = ("6.04", "6.12", "1.02")
    SPH_WORLD = ("45.34", "6.78", "8.66")
    HIT_WORLD_M = (6.044, 6.117)                # drawn position of the return (world x, y)
    RAY_DIR_DEG = SENSOR_YAW + float(SPH_SENSOR[0])   # the ray's direction on paper
    # cell sketch geometry
    SK_OX, SK_OY = 30, 34           # sketch origin from the cell's left / bottom edge
    SK_DX, SK_DY = 56, 50           # sketch target point offset (right, up)
    SK_AXIS = 20
    SK_ARC_R = 18
    NUM_X, NUM_Y0, NUM_LH = 112, 48, 24   # the three number lines in a cell
    NUM_SIZE = 13

    c = dl.Canvas(W, H, "One lidar return, two independent output choices",
                  "A 2 by 2 grid. Columns: Cartesian and spherical components, chosen by "
                  "elementsCoordsType. Rows: the sensor frame and the world frame, chosen by "
                  "outputFrameOfReference. A top view of the scene shows the world origin, a "
                  "displaced and rotated sensor and one return; each cell gives that return's three "
                  "numbers for its combination. The delivered params coordsType and frameOfReference "
                  "say which cell a frame is in.")

    # --- the scene ------------------------------------------------------------------------------
    dl.box(c, SCENE_X, SCENE_Y, SCENE_W, SCENE_H, fill=dl.PANEL)
    dl.text(c, SCENE_X + 14, SCENE_Y + 26, "The scene, seen from above", 14, "bold")
    ox, oy = SCENE_X + ORIGIN_DX, SCENE_Y + SCENE_H - ORIGIN_DY
    sx, sy = ox + SENSOR_POS[0] * SCALE, oy - SENSOR_POS[1] * SCALE
    px, py = ox + HIT_WORLD_M[0] * SCALE, oy - HIT_WORLD_M[1] * SCALE
    # world axes and origin
    dl.arrow(c, ox, oy, ox + AXIS_LEN, oy, dl.PURPLE, 2)
    dl.arrow(c, ox, oy, ox, oy - AXIS_LEN, dl.PURPLE, 2)
    dl.text(c, ox + AXIS_LEN + AXIS_LBL_GAP, oy + 4, "x", 12, "bold", "middle", dl.PURPLE)
    dl.text(c, ox, oy - AXIS_LEN - AXIS_LBL_GAP + 4, "y", 12, "bold", "middle", dl.PURPLE)
    _dot(c, ox, oy, 4, dl.PURPLE)
    dl.text(c, ox - 8, oy + 20, "world origin", 11.5, "normal", "start", dl.PURPLE)
    # the measurement from the world origin and its azimuth
    _line(c, ox, oy, px, py, dl.PURPLE, 1.5, dashed=True)
    az_world = math.degrees(math.atan2(oy - py, px - ox))
    _arc_stroke(c, ox, oy, ARC_R_WORLD, 0, az_world, dl.PURPLE, 1.5)
    lx, ly = _polar(ox, oy, ARC_R_WORLD + ARC_LBL_GAP_WORLD, az_world / 2)
    dl.text(c, lx, ly + 4, f"{float(SPH_WORLD[0]):.1f}°", 11, "normal", "middle", dl.PURPLE)
    # the sensor: displaced and yawed, with its own axes
    ex, ey = _polar(sx, sy, SENSOR_AXIS_LEN, SENSOR_YAW)
    dl.arrow(c, sx, sy, ex, ey, dl.BLUE, 2)
    tx, ty = _polar(sx, sy, SENSOR_AXIS_LEN + AXIS_LBL_GAP, SENSOR_YAW)
    dl.text(c, tx, ty + 4, "x", 12, "bold", "middle", dl.BLUE)
    ex, ey = _polar(sx, sy, SENSOR_AXIS_LEN, SENSOR_YAW + 90)
    dl.arrow(c, sx, sy, ex, ey, dl.BLUE, 2)
    tx, ty = _polar(ex, ey, Y_LBL_OFF, SENSOR_YAW + 180)
    dl.text(c, tx, ty + 4, "y", 12, "bold", "middle", dl.BLUE)
    _rect(c, sx - 9, sy - 6, 18, 12, dl.BLUE, rx=2,
          extra=f' transform="rotate({dl.fmt(-SENSOR_YAW)} {dl.fmt(sx)} {dl.fmt(sy)})"')
    dl.text(c, sx + 12, sy + 16, "sensor", 11.5, "normal", "start", dl.BLUE)
    # the ray, its azimuth in the sensor frame, the return and the object it hit
    _line(c, sx, sy, px, py, dl.GREEN, 2)
    _arc_stroke(c, sx, sy, ARC_R_SENSOR, SENSOR_YAW, RAY_DIR_DEG, dl.BLUE, 1.5)
    lx, ly = _polar(sx, sy, ARC_R_SENSOR + ARC_LBL_GAP, (SENSOR_YAW + RAY_DIR_DEG) / 2)
    dl.text(c, lx, ly + 4, f"{float(SPH_SENSOR[0]):.0f}°", 11, "normal", "middle", dl.BLUE)
    dx, dy = math.cos(math.radians(RAY_DIR_DEG)), -math.sin(math.radians(RAY_DIR_DEG))
    nx, ny = -dy, dx
    fx, fy = px + 6 * dx, py + 6 * dy
    _line(c, fx - 28 * nx, fy - 28 * ny, fx + 28 * nx, fy + 28 * ny, dl.GREY, 6)
    _dot(c, px, py, 5, dl.GREEN)
    dl.text(c, px + 26, py - 22, "object", 11.5, "normal", "start", dl.GREY)
    dl.text(c, px - 14, py + 6, "one return", 11.5, "normal", "end", dl.GREEN)
    # notes
    dl.text(c, SCENE_X + 14, SCENE_Y + SCENE_H - 30, "Top view; z is up, out of the page.", 11,
            "normal", "start", dl.GREY)
    dl.text(c, SCENE_X + 14, SCENE_Y + SCENE_H - 14,
            "Sensor at (4.0, 0.5, 0.5) m in the world, yawed 30°.", 11, "normal", "start", dl.GREY)

    # --- the grid -------------------------------------------------------------------------------
    col_x = [GRID_X + HDR_W + GAP, GRID_X + HDR_W + GAP + CELL_W + GAP]
    hdr_y = GRID_Y + AXIS_LBL_H
    row_y = [hdr_y + HDR_H + GAP, hdr_y + HDR_H + GAP + CELL_H + GAP]
    dl.text(c, GRID_X, GRID_Y + 15, "outputFrameOfReference", 12, "normal", "start", dl.GREY, dl.M)
    dl.text(c, (col_x[0] + col_x[1] + CELL_W) / 2, GRID_Y + 15, "elementsCoordsType", 12, "normal",
            "middle", dl.GREY, dl.M)
    columns = (("CARTESIAN", "x, y, z in meters", ("x", "y", "z"), ("m", "m", "m")),
               ("SPHERICAL", "azimuth, elevation (deg), range (m)",
                ("azimuth", "elevation", "range"), ("deg", "deg", "m")))
    for i, (token, sub, _names, _units) in enumerate(columns):
        dl.box(c, col_x[i], hdr_y, CELL_W, HDR_H, fill=dl.DK)
        dl.text(c, col_x[i] + CELL_W / 2, hdr_y + 23, token, 14, "bold", "middle", dl.WHITE, dl.M)
        dl.text(c, col_x[i] + CELL_W / 2, hdr_y + 42, sub,
                _fits(sub, CELL_W - 16, 11.5), "normal", "middle", dl.WHITE)
    rows = (("SENSOR", ("from the sensor,", "in its axes"), dl.BLUE, (CART_SENSOR, SPH_SENSOR)),
            ("WORLD", ("from the world origin,", "in world axes"), dl.PURPLE, (CART_WORLD, SPH_WORLD)))
    for j, (token, subs, color, values) in enumerate(rows):
        dl.box(c, GRID_X, row_y[j], HDR_W, CELL_H, fill=color)
        cy = row_y[j] + CELL_H / 2
        dl.text(c, GRID_X + HDR_W / 2, cy - 12, token, 14, "bold", "middle", dl.WHITE, dl.M)
        for k, s in enumerate(subs):
            dl.text(c, GRID_X + HDR_W / 2, cy + 10 + 16 * k, s, _fits(s, HDR_W - 16, 11.5),
                    "normal", "middle", dl.WHITE)
        for i, (_token, _sub, names, units) in enumerate(columns):
            cell = dl.box(c, col_x[i], row_y[j], CELL_W, CELL_H, fill=dl.PANEL)
            # sketch: the measuring origin in the row's colour, the return, Cartesian drop
            # lines or the spherical radial line and azimuth arc
            o_x, o_y = cell.x + SK_OX, cell.bottom - SK_OY
            t_x, t_y = o_x + SK_DX, o_y - SK_DY
            dl.arrow(c, o_x, o_y, o_x + SK_AXIS, o_y, color, 1.5)
            dl.arrow(c, o_x, o_y, o_x, o_y - SK_AXIS, color, 1.5)
            if j == 0:
                _rect(c, o_x - 6, o_y - 4, 12, 8, color, rx=1.5)
            else:
                _dot(c, o_x, o_y, 3.5, color)
            if i == 0:
                _line(c, o_x, o_y, t_x, o_y, dl.GREY, 1.2, dashed=True)
                _line(c, t_x, o_y, t_x, t_y, dl.GREY, 1.2, dashed=True)
            else:
                _line(c, o_x, o_y, t_x, t_y, dl.GREY, 1.2)
                _arc_stroke(c, o_x, o_y, SK_ARC_R, 0, math.degrees(math.atan2(SK_DY, SK_DX)),
                            dl.GREY, 1.2)
            _dot(c, t_x, t_y, 4.5, dl.GREEN)
            # the three numbers
            for k in range(3):
                line = f"{names[k]:<10}{values[i][k]:>6} {units[k]}"
                dl.text(c, cell.x + NUM_X, cell.y + NUM_Y0 + k * NUM_LH, line, NUM_SIZE, "normal",
                        "start", dl.DK, dl.M)

    # --- legend and footer ----------------------------------------------------------------------
    dl.legend(c, SCENE_X, SCENE_Y + SCENE_H + LEGEND_DY - 10,
              (("sensor frame", dl.BLUE), ("world frame", dl.PURPLE), ("the return", dl.GREEN)))
    fy = row_y[1] + CELL_H + FOOT_DY
    _rich_line(c, GRID_X, fy, (("The delivered params", dl.F), ("coordsType", dl.M), ("and", dl.F),
                               ("frameOfReference", dl.M), ("say which cell you are in.", dl.F)),
               12, dl.DK)
    _rich_line(c, GRID_X, fy + FOOT_LH, (("HitNormal", dl.M), ("and", dl.F), ("Velocity", dl.M),
                                         ("are rotated into the chosen frame, never translated, "
                                          "and stay Cartesian in every cell.", dl.F)), 12)
    _rich_line(c, GRID_X, fy + 2 * FOOT_LH, (("A third frame choice,", dl.F), ("CUSTOM", dl.M),
                                             ("measures from a frame you place with", dl.F),
                                             ("customFrameOfReferenceTrafo.", dl.M)), 12)
    _check_sizes(c)
    dl.validate(c)
    dl.write_svg(out_dir / "lidar_core_coords_vs_frame.svg", c.render())


def lidar_core_cadence_timeline(out_dir: pathlib.Path) -> None:
    """Accumulate, partial and instant cadences of one sensor stepped at half its scan period."""
    W = 1160
    PAD_X = 24
    LABEL_W = 206                           # label column
    TL_X0 = PAD_X + LABEL_W + 10            # timeline start
    TL_X1 = W - 36                          # timeline end
    SCANS = 2.5                             # scan periods shown
    T_PX = (TL_X1 - TL_X0) / SCANS
    STEP_PX = T_PX / 2                      # the application steps by T/2
    N_STEPS = 5
    HEAD_Y = 30                             # heading baseline
    AXIS_Y = 98
    SCAN_LBL_DY = 16                        # scan labels above the axis
    LANE_GAP = 14
    ROW1_Y, ROW1_H = AXIS_Y + 42, 78
    ROW2_Y, ROW2_H = ROW1_Y + ROW1_H + LANE_GAP, 134
    ROW2_SPLIT = 62                         # upper band height inside row 2
    ROW3_Y, ROW3_H = ROW2_Y + ROW2_H + LANE_GAP, 126
    LEGEND_Y = ROW3_Y + ROW3_H + 30
    H = LEGEND_Y + 44
    BOX_H = 30
    BOX_INSET = 4                           # gap between a frame box and its step boundaries
    DASH_Y, DASH_LBL_DY = 24, -8            # the grey "no output" dash inside row 1
    ROW1_BOX_DY = 38
    OFFSET_STEP = (1.75, 2.25)              # the boundary-crossing step, in scan periods
    FLASH_TOP_DY = 28                       # bolt tip below the lane top (row 3)
    ROW3_BOX_DY = 50
    ROW3_NOTE_DY = (20, 100, 118)           # flash note above; the two return notes below
    LBL_SIZE, SUB_SIZE = 14, 11.5
    NOTE = 11.5

    c = dl.Canvas(W, H, "Three delivery cadences of one lidar on one timeline",
                  "A time axis with scan boundaries at multiples of the scan period T and application "
                  "steps of T/2. Accumulate (partialOutputs false, the default) returns one frame "
                  "holding the whole scan on the step that completes it and nothing on the step in "
                  "between. Partial (partialOutputs true) returns a slice on every step, and a window "
                  "that crosses a scan boundary carries the end of one scan and the start of the next. "
                  "Instant (instantLidar true) "
                  "traces a whole scan as one flash at the start of every step; partialOutputs "
                  "decides whether that scan is returned on every step or only on the step that "
                  "completes the scan period.")

    def tx(t: float) -> float:          # scan periods -> px
        return TL_X0 + t * T_PX

    # heading, scan labels, axis
    _rich_line(c, TL_X0, HEAD_Y, (("One sensor. Scan period T = 1 /", dl.F), ("omni:sensor:frameRate;", dl.M),
                                  ("the application steps by T/2.", dl.F)), 13, dl.DK)
    for k in range(3):
        x0, x1 = tx(k), min(tx(k + 1), TL_X1)
        label = f"scan {k + 1}" if k < 2 else "scan 3 …"
        dl.text(c, (x0 + x1) / 2, AXIS_Y - SCAN_LBL_DY, label, 12.5, "bold", "middle", dl.DK)
    dl.tick_marks(c, TL_X0, AXIS_Y, TL_X1 - TL_X0, [k * STEP_PX for k in range(N_STEPS + 1)],
                  ["0", "T/2", "T", "3T/2", "2T", "5T/2"], tick=7, size=12)
    dl.text(c, TL_X0 - 10, AXIS_Y + 4, "time", 12, "normal", "end", dl.GREY)
    # lanes
    lanes = (("Accumulate", ("partialOutputs = false", "(default)"), ROW1_Y, ROW1_H),
             ("Partial", ("partialOutputs = true",), ROW2_Y, ROW2_H),
             ("Instant", ("instantLidar = true",), ROW3_Y, ROW3_H))
    for name, subs, y, h in lanes:
        _rect(c, PAD_X, y, TL_X1 + 12 - PAD_X, h, dl.PANEL, rx=4)
        _line(c, TL_X0 - 8, y + 8, TL_X0 - 8, y + h - 8, dl.FAINT, 1)
        base = y + (ROW2_SPLIT / 2 if name == "Partial" else h / 2) - 6
        dl.text(c, PAD_X + 12, base, name, LBL_SIZE, "bold")
        for k, s in enumerate(subs):
            fam = dl.M if "=" in s else dl.F
            dl.text(c, PAD_X + 12, base + 17 + 17 * k, s, _fits(s, LABEL_W - 16, SUB_SIZE, family=fam),
                    "normal", "start", dl.GREY, fam)
    # step and scan boundary lines through the lanes
    for k in range(N_STEPS + 1):
        x = tx(k / 2)
        if k % 2 == 0:                                        # scan boundary, around the tick labels
            _line(c, x, AXIS_Y - SCAN_LBL_DY - 14, x, AXIS_Y, dl.GREY, 1.2, dashed=True)
            _line(c, x, ROW1_Y, x, ROW3_Y + ROW3_H, dl.GREY, 1.2, dashed=True)
        else:                                                 # application step; not in row 2's lower band
            for name, _s, y, h in lanes:
                _line(c, x, y + 4, x, y + (ROW2_SPLIT if name == "Partial" else h) - 4, dl.FAINT, 1)

    # row 1: accumulate
    for k in range(3):
        a, b = tx(k), tx(k + 0.5)                            # the mid-scan step
        _line(c, a + 14, ROW1_Y + DASH_Y, b - 14, ROW1_Y + DASH_Y, dl.MUTED, 3, dashed=True)
        dl.text(c, (a + b) / 2, ROW1_Y + DASH_Y + DASH_LBL_DY, "no output for the product", NOTE,
                "normal", "middle", dl.GREY)
        if k < 2:
            dl.box(c, a + BOX_INSET, ROW1_Y + ROW1_BOX_DY, T_PX - 2 * BOX_INSET, BOX_H,
                   f"whole scan {k + 1}, delivered as one frame", fill=dl.GREEN, label_size=12)
    # row 2: partial, upper band: one slice per step
    for k in range(N_STEPS):
        a, b = tx(k / 2), tx((k + 1) / 2)
        dl.box(c, a + BOX_INSET, ROW2_Y + (ROW2_SPLIT - BOX_H) / 2 + 4, STEP_PX - 2 * BOX_INSET, BOX_H,
               f"slice of scan {k // 2 + 1}", fill=dl.GREEN, label_size=12)
    # row 2, lower band: a step whose boundaries do not line up with the scan
    low_y = ROW2_Y + ROW2_SPLIT
    _line(c, TL_X0 - 8, low_y, TL_X1 + 4, low_y, dl.FAINT, 1)
    for k, s in enumerate(("if a window crosses", "a scan boundary")):
        dl.text(c, PAD_X + 12, low_y + 30 + 17 * k, s, NOTE, "normal", "start", dl.GREY)
    a, b = tx(OFFSET_STEP[0]), tx(OFFSET_STEP[1])
    br_y = low_y + 24
    _rich_line(c, (a + b) / 2, br_y - 6, (("one application step", dl.F),), NOTE, dl.DK, anchor="middle",
               halo=dl.PANEL)                         # the 2T boundary line runs behind this label
    _bracket_h(c, a, b, br_y)
    dl.box(c, a + 2, br_y + 12, b - a - 4, BOX_H, "scan 2 / scan 3", fill=dl.GREEN, label_size=12)
    for k, s in enumerate(("one frame: the end of scan 2", "and the start of scan 3")):
        dl.text(c, a - 14, br_y + 12 + BOX_H / 2 - 4 + 17 * k, s, NOTE, "normal", "end", dl.GREY)
    # row 3: instant
    box_y = ROW3_Y + ROW3_BOX_DY
    for k in range(N_STEPS):
        a, b = tx(k / 2), tx((k + 1) / 2)
        _flash(c, a, ROW3_Y + FLASH_TOP_DY, box_y)
        completing = k % 2 == 1                               # steps 2 and 4 complete a scan
        if completing:
            dl.box(c, a + 8, box_y, STEP_PX - 8 - BOX_INSET, BOX_H, "whole scan", fill=dl.GREEN,
                   label_size=12)
        else:
            dl.box(c, a + 8, box_y, STEP_PX - 8 - BOX_INSET, BOX_H, "whole scan", fill=dl.WHITE,
                   stroke=dl.GREEN, dashed=True, label_fill=dl.GREY, label_size=12)
    _rich_line(c, tx(1.0) + 12, ROW3_Y + ROW3_NOTE_DY[0],
               (("whole scan traced as one flash at the window start;", dl.F), ("TimeOffsetNs = 0", dl.M)),
               NOTE, dl.DK, halo=dl.PANEL)
    _rich_line(c, tx(0.5) + 8, ROW3_Y + ROW3_NOTE_DY[1],
               (("returned with", dl.F), ("partialOutputs = false", dl.M)), NOTE, dl.DK, halo=dl.PANEL)
    _rich_line(c, tx(0.0) + 8, ROW3_Y + ROW3_NOTE_DY[2],
               (("traced; returned only with", dl.F), ("partialOutputs = true", dl.M)), NOTE, dl.GREY,
               halo=dl.PANEL)
    # legend
    leg = dl.legend(c, TL_X0, LEGEND_Y, (("one delivered frame", dl.GREEN),
                                         ("traced but not returned", dl.GREEN, "outline"),
                                         ("step with no output for the product", dl.MUTED, "dashed")))
    fx = leg.right + 26
    _flash(c, fx + 5, LEGEND_Y - 3, LEGEND_Y + 15)
    dl.text(c, fx + 16, LEGEND_Y + 10.5, "whole scan traced as one flash", 12, "normal", "start", dl.DK)
    _check_sizes(c)
    dl.validate(c)
    dl.write_svg(out_dir / "lidar_core_cadence_timeline.svg", c.render())


def lidar_core_pointcloud_layout(out_dir: pathlib.Path) -> None:
    """One mapped PointCloud output: tensors and shapes, the delivered range, Flags bits, params."""
    W, H = 1160, 556
    NAME_X = 24                              # tensor names
    CELLS_X = 186                            # first cell
    N_CELLS, CELL_W, ROW_H = 12, 26, 22      # Nmax drawn as 12 cells
    N_DELIV = 7                              # cells inside [0, Counts[0]) in the drawing
    CELLS_X1 = CELLS_X + N_CELLS * CELL_W
    BOUND_X = CELLS_X + N_DELIV * CELL_W
    SHAPE_X = CELLS_X1 + 16                  # shape labels
    PARAMS_X, PARAMS_W = 806, 330
    PARAMS_Y = 48
    TOP_LBL_Y = 38                           # "Counts[0]" over the boundary
    COUNTS_Y = 48
    COORD_Y = 98                             # three contiguous rows x, y, z
    ROW_GAP = 8
    INT_Y = COORD_Y + 3 * ROW_H + 10
    TIME_Y = INT_Y + ROW_H + ROW_GAP
    NORM_Y = TIME_Y + ROW_H + ROW_GAP
    FLAGS_Y = NORM_Y + ROW_H + ROW_GAP
    AXIS_LBL_Y = FLAGS_Y + ROW_H + 16
    ZOOM_CELL = 3                            # the Flags cell that is magnified
    ZOOM_Y, ZOOM_W, ZOOM_H = FLAGS_Y + ROW_H + 44, 28, 26
    ZOOM_X = CELLS_X + 10
    BITS_Y = ZOOM_Y + ZOOM_H + 24            # the two bit explanations
    TEST_Y = BITS_Y + 40                     # the two "test the bit" lines
    TEST_LH = 17
    OTHER_Y = TEST_Y + TEST_LH + 30
    LEGEND_Y = H - 36
    PARAM_LH, PARAM_SIZE = 17.5, 11.5
    PARAMS = (("frameId", "[1]"), ("timestampNs", "[1]"), ("modality", "[1]"), ("coordsType", "[1]"),
              ("frameOfReference", "[1]"), ("motionCompensationState", "[1]"), ("compactionType", "[1]"),
              ("maxPoints", "[1]  = Nmax"), ("frameStartTimeStampNs", "[1]"), ("frameStartPosM", "[3]"),
              ("frameStartOrientation", "[4]"), ("frameEndTimeStampNs", "[1]"), ("frameEndPosM", "[3]"),
              ("frameEndOrientation", "[4]"), ("modelToAppTransform", "[4, 4]"))
    PARAMS_H = 46 + PARAM_LH * len(PARAMS) + 10

    c = dl.Canvas(W, H, "One mapped PointCloud output of the Lidar generic core model",
                  "Left, the tensors of one mapped PointCloud output with their shapes: Counts [1]; "
                  "Coordinates [3, Nmax] as three stacked rows x, y, z, component-first; Intensity, "
                  "TimeOffsetNs and Flags [Nmax] as single rows; HitNormal [Nmax, 3] as Nmax groups "
                  "of three adjacent cells, point-first. In every per-point row the leading range "
                  "[0, Counts[0]) is shaded delivered and the remainder up to Nmax is hatched: it "
                  "holds whatever it held before. One Flags byte is magnified: bit 6 (0x40) marks a "
                  "real return, bit 5 (0x20) a return that belongs to the scan after the one the frame "
                  "started in. Right, the CPU-resident params that travel beside the tensors.")
    _hatch_defs(c)

    def per_point_row(y: float, sub: int = 1) -> None:
        """One per-point row: delivered shading, hatched remainder, cell separators."""
        _rect(c, CELLS_X, y, BOUND_X - CELLS_X, ROW_H, GREEN_TINT)
        _rect(c, BOUND_X, y, CELLS_X1 - BOUND_X, ROW_H, "url(#hatch)")
        _rect(c, CELLS_X, y, CELLS_X1 - CELLS_X, ROW_H, "none", dl.GREY, 1)
        for k in range(1, N_CELLS * sub):
            x = CELLS_X + k * CELL_W / sub
            strong = k % sub == 0
            _line(c, x, y, x, y + ROW_H, dl.GREY if strong else dl.FAINT, 1 if strong else 0.8)

    def name(y: float, s: str) -> None:
        dl.text(c, NAME_X, y + ROW_H / 2 + 4.5, s, 12.5, "bold")

    def shape(y: float, s: str, note: str = "") -> None:
        x = dl.text(c, SHAPE_X, y + ROW_H / 2 + 4.5, s, 12, "normal", "start", dl.DK, dl.M).x1
        if note:
            dl.text(c, x + 8, y + ROW_H / 2 + 4.5, note, 11, "normal", "start", dl.GREY)

    # Counts and the boundary it marks
    dl.text(c, BOUND_X, TOP_LBL_Y, "Counts[0]", 12, "bold", "middle", dl.DK, dl.M)
    _line(c, BOUND_X, TOP_LBL_Y + 6, BOUND_X, FLAGS_Y + ROW_H + 4, dl.DK, 1.5, dashed=True)
    _rect(c, CELLS_X, COUNTS_Y, CELL_W, ROW_H, dl.GREEN, dl.GREY, 1)
    name(COUNTS_Y, "Counts")
    dl.arrow(c, CELLS_X + CELL_W + 4, COUNTS_Y + ROW_H / 2, BOUND_X - 3, COUNTS_Y + ROW_H / 2, dl.DK, 1.5)
    dl.text(c, (CELLS_X + CELL_W + BOUND_X) / 2, COUNTS_Y + ROW_H + 13, "entries delivered this frame",
            11, "normal", "middle", dl.GREY)
    shape(COUNTS_Y, "[1]", "int32; always delivered")
    # Coordinates: three stacked component rows
    for k, comp in enumerate(("x", "y", "z")):
        y = COORD_Y + k * ROW_H
        per_point_row(y)
        dl.text(c, CELLS_X - 10, y + ROW_H / 2 + 4, comp, 11.5, "normal", "end", dl.GREY, dl.M)
    name(COORD_Y + ROW_H, "Coordinates")
    shape(COORD_Y + ROW_H - 9, "[3, Nmax]")
    dl.text(c, SHAPE_X, COORD_Y + 2 * ROW_H + 6, "component-first: all x, then all y, then all z", 11,
            "normal", "start", dl.GREY)
    # single rows
    for y, nm, shp, note in ((INT_Y, "Intensity", "[Nmax]", ""), (TIME_Y, "TimeOffsetNs", "[Nmax]", "")):
        per_point_row(y)
        name(y, nm)
        shape(y, shp, note)
    per_point_row(NORM_Y, sub=3)
    name(NORM_Y, "HitNormal")
    shape(NORM_Y, "[Nmax, 3]", "point-first: one point's x, y, z adjacent")
    per_point_row(FLAGS_Y)
    name(FLAGS_Y, "Flags")
    shape(FLAGS_Y, "[Nmax]", "uint8; always delivered")
    # index labels under the rows
    dl.text(c, CELLS_X, AXIS_LBL_Y, "0", 11.5, "normal", "start", dl.GREY, dl.M)
    dl.text(c, CELLS_X1, AXIS_LBL_Y, "Nmax", 11.5, "normal", "end", dl.GREY, dl.M)
    # one Flags byte, magnified
    zx0, zx1 = CELLS_X + ZOOM_CELL * CELL_W, CELLS_X + (ZOOM_CELL + 1) * CELL_W
    _rect(c, zx0, FLAGS_Y, CELL_W, ROW_H, "none", dl.DK, 1.5)
    _line(c, zx0, FLAGS_Y + ROW_H, ZOOM_X, ZOOM_Y, dl.MUTED, 1)
    _line(c, zx1, FLAGS_Y + ROW_H, ZOOM_X + 8 * ZOOM_W, ZOOM_Y, dl.MUTED, 1)
    dl.text(c, NAME_X, ZOOM_Y + ZOOM_H / 2 + 4.5, "one Flags byte", 12.5, "bold")
    for b in range(8):
        bit = 7 - b
        fill = dl.GREEN if bit == 6 else dl.ORANGE if bit == 5 else dl.WHITE
        _rect(c, ZOOM_X + b * ZOOM_W, ZOOM_Y, ZOOM_W, ZOOM_H, fill, dl.GREY, 1)
        dl.text(c, ZOOM_X + (b + 0.5) * ZOOM_W, ZOOM_Y + ZOOM_H / 2 + 4, str(bit), 11.5, "bold", "middle",
                dl.WHITE if bit in (5, 6) else dl.GREY, dl.M)
    dl.text(c, ZOOM_X + 8 * ZOOM_W + 10, ZOOM_Y + ZOOM_H / 2 + 4.5, "bit", 11.5, "normal", "start", dl.GREY)
    bx = dl.legend(c, ZOOM_X, BITS_Y - 10, (("bit 6, 0x40: a real return", dl.GREEN),), 12).right
    dl.legend(c, bx + 26, BITS_Y - 10, (("bit 5, 0x20: belongs to the next scan",
                                          dl.ORANGE),), 12)
    _rich_line(c, ZOOM_X, TEST_Y, (("Test the bit,", dl.F), ("Flags[i] & 0x40;", dl.M),
                                   ("never compare", dl.F), ("Flags[i] == 0x40,", dl.M)), 11.5)
    dl.text(c, ZOOM_X, TEST_Y + TEST_LH, "because bit 5 can be set on a real return as well.", 11.5,
            "normal", "start", dl.GREY)
    dl.text_block(c, NAME_X, OTHER_Y,
                  "Every other requested channel follows the same rule: EmitterId, ChannelId, TickId, "
                  "EchoId, TickState and MaterialId are [Nmax]; ObjectId [Nmax, 4] and Velocity "
                  "[Nmax, 3] are point-first like HitNormal.", PARAMS_X - NAME_X - 40, 11.5)
    # legend for the shading
    lg = dl.legend(c, NAME_X, LEGEND_Y, (("delivered: indices [0, Counts[0])", GREEN_TINT),), 12)
    hx = lg.right + 26
    _rect(c, hx, LEGEND_Y, 12, 12, "url(#hatch)", dl.MUTED, 1, rx=2)
    dl.text(c, hx + 19, LEGEND_Y + 10.5, "up to Nmax: holds whatever it held before; never read it", 12,
            "normal", "start", dl.DK)
    # params
    dl.box(c, PARAMS_X, PARAMS_Y, PARAMS_W, PARAMS_H, fill=dl.PANEL)
    dl.text(c, PARAMS_X + 16, PARAMS_Y + 26, "params (CPU-resident)", 13.5, "bold")
    for k, (pn, ps) in enumerate(PARAMS):
        dl.text(c, PARAMS_X + 16, PARAMS_Y + 50 + k * PARAM_LH, f"{pn:<25}{ps}", PARAM_SIZE, "normal",
                "start", dl.DK, dl.M)
    dl.text_block(c, PARAMS_X, PARAMS_Y + PARAMS_H + 22,
                  "Scalars and small vectors that describe the frame, readable the moment the output is "
                  "mapped. coordsType, frameOfReference, motionCompensationState and compactionType "
                  "echo the shaping values in force for this frame.", PARAMS_W, 11.5)
    _check_sizes(c)
    dl.validate(c)
    dl.write_svg(out_dir / "lidar_core_pointcloud_layout.svg", c.render())


def generate(out_dir: pathlib.Path) -> None:
    """Write every SVG of this group into ``out_dir``."""
    lidar_core_coords_vs_frame(out_dir)
    lidar_core_cadence_timeline(out_dir)
    lidar_core_pointcloud_layout(out_dir)


if __name__ == "__main__":
    generate(dl.output_dir(__file__))
