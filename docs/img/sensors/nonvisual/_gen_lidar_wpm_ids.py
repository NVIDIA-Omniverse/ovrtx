#!/usr/bin/env python3
"""Figures of the Lidar generic wpm model and the Idealized depth model pages.

One function per SVG; ``generate(out_dir)`` writes them all. Run in place with
``python3 -B _gen_lidar_wpm_ids.py`` or through ``generate_diagrams.py``.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import _diagram_lib as dl  # noqa: E402

# ------------------------------------------------------------------- private drawing helpers ---
_COS30, _SIN30 = math.cos(math.radians(30)), 0.5


def _iso(ox, oy, s, p):
    """Isometric projection of a sensor-frame point (X forward, Y left, Z up).

    +X runs right and up the screen, +Y left and up, +Z straight up; ``s`` scales the frame.
    """
    x, y, z = p
    return ox + s * _COS30 * (x - y), oy - s * (_SIN30 * (x + y) + z)


def _sph(az_deg, el_deg, r=1.0):
    """Sensor-frame point at azimuth/elevation (degrees) and distance ``r``."""
    az, el = math.radians(az_deg), math.radians(el_deg)
    return r * math.cos(el) * math.cos(az), r * math.cos(el) * math.sin(az), r * math.sin(el)


def _dot(c, x, y, r, fill, stroke=None, stroke_width=1.5):
    s = f' stroke="{stroke}" stroke-width="{dl.fmt(stroke_width)}"' if stroke else ""
    c.add(f'<circle cx="{dl.fmt(x)}" cy="{dl.fmt(y)}" r="{dl.fmt(r)}" fill="{fill}"{s}/>')


def _line(c, x1, y1, x2, y2, stroke, width, dashed=False):
    dl.arrow(c, x1, y1, x2, y2, stroke, width, head=False, dashed=dashed)


def _path(c, pts, stroke, width, dashed=False, closed=False, fill="none"):
    d = "M" + " L".join(f"{dl.fmt(x)},{dl.fmt(y)}" for x, y in pts) + (" Z" if closed else "")
    attrs = f'd="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{dl.fmt(width)}"'
    if dashed:
        attrs += f' stroke-dasharray="{dl.fmt(3 * width)} {dl.fmt(2 * width)}"'
    c.add(f"<path {attrs}/>")


def _ellipse(c, cx, cy, rx, ry, stroke, width, dashed=False):
    attrs = (f'cx="{dl.fmt(cx)}" cy="{dl.fmt(cy)}" rx="{dl.fmt(rx)}" ry="{dl.fmt(ry)}" '
             f'fill="none" stroke="{stroke}" stroke-width="{dl.fmt(width)}"')
    if dashed:
        attrs += f' stroke-dasharray="{dl.fmt(3 * width)} {dl.fmt(2 * width)}"'
    c.add(f"<ellipse {attrs}/>")


def _bracket(c, x1, x2, y, depth, stroke=dl.GREY, width=1.5):
    """A horizontal bracket at ``y`` with end ticks of ``depth`` px (negative: ticks upward)."""
    _path(c, [(x1, y + depth), (x1, y), (x2, y), (x2, y + depth)], stroke, width)


def _cross(c, x, y, size, stroke=dl.RED, width=2.5):
    h = size / 2
    _line(c, x - h, y - h, x + h, y + h, stroke, width)
    _line(c, x - h, y + h, x + h, y - h, stroke, width)


def _bump(c, cx, base_y, height, half_width, stroke, width=2.2, n=24):
    """A Gaussian peak standing on ``base_y`` (a signal lobe on a time axis)."""
    sigma = half_width / 2.5
    pts = []
    for k in range(n + 1):
        x = cx - half_width + 2 * half_width * k / n
        pts.append((x, base_y - height * math.exp(-((x - cx) ** 2) / (2 * sigma * sigma))))
    _path(c, pts, stroke, width)


def _rows_fit(lines, max_w, size):
    """Assert that every (text, family) note line fits ``max_w`` px at ``size``."""
    for s, fam in lines:
        w = dl.text_width(s, size, "normal", fam)
        if w > max_w:
            raise ValueError(f"note line too wide ({dl.fmt(w)} > {max_w}): {s!r}")


def _legend_marks(c, x, y, entries, size=12, gap=22):
    """A legend whose swatches are marks: ``(label, color, kind)`` with kind line/arrow/dashed/
    dot/ring/cross."""
    cx = float(x)
    sw = 18.0
    mid = float(y) + sw / 2
    for label, color, kind in entries:
        if kind in ("line", "dashed"):
            _line(c, cx, mid, cx + sw, mid, color, 2, dashed=(kind == "dashed"))
        elif kind == "arrow":
            dl.arrow(c, cx, mid, cx + sw + 4, mid, color, 2)
        elif kind == "dot":
            _dot(c, cx + sw / 2, mid, 4, color)
        elif kind == "ring":
            _dot(c, cx + sw / 2, mid, 4, color, stroke=dl.DK, stroke_width=1.5)
        elif kind == "cross":
            _cross(c, cx + sw / 2, mid, 9, color)
        tb = dl.text(c, cx + sw + 10, mid + 0.36 * size, label, size, "normal", "start", dl.DK)
        cx = tb.x1 + gap
    return cx


# ------------------------------------------------------------- idealized_depth_emitter_shapes ---
def idealized_depth_emitter_shapes(out_dir: pathlib.Path) -> None:
    W, H = 1200, 492
    PAD = 32
    PANEL_W, PANEL_GAP, PANEL_Y, PANEL_H = 224, 4, 18, 332
    TITLE_DY, TITLE_SIZE = 26, 13
    NOTE_DY0, NOTE_LH, NOTE_SIZE = 258, 16, 11
    NOTE_W = PANEL_W - 20
    RAY_COLOR, RAY_W = dl.BLUE, 1.2
    MAX_COLOR, ARC_COLOR = dl.MUTED, dl.FAINT
    DOT_R, PT_R, LBL = 3.2, 2.6, 11
    # SPHERICAL: origin, radius, sampled azimuths/elevations and the unsampled maxima (degrees);
    # the fan points forward (+X) so that the grid patch faces the viewer instead of being seen
    # edge-on, and three columns keep every ray clear of the other rays' arrowheads
    S_OX, S_OY, S_R = 58, 184, 74
    S_AZ, S_AZ_MAX = (-20.0, 5.0, 30.0), 55.0
    S_EL, S_EL_MAX = (-10.0, 5.0, 20.0), 35.0
    # PLANAR: plane reference point, grid steps along x and y, grid counts, ray length
    P_OX, P_OY, P_DX, P_DY, P_NX, P_NY, P_RAY = 92, 140, 30, 20, 4, 3, 40
    # CYLINDRICAL: origin, ring radius, ring spacing, ring count, rays per ring
    C_OX, C_OY, C_R, C_DZ, C_RINGS, C_AZ_N = 82, 196, 44, 36, 3, 8
    # GRIDLESS_SPHERICAL: origin, radius, rows, elevation step, azimuth span
    G_OX, G_OY, G_R = 30, 144, 80
    G_EL, G_DEL, G_AZ_MIN, G_AZ_MAX = (-60, -40, -20, 0, 20, 40, 60), 20.0, -50.0, 50.0
    # BOX: origin on screen, box corners relative to the origin, face spacing, ray overshoot.
    # A flat box one spacing tall: with three levels of points on the side faces, some ray
    # from the interior origin always passes through another face point in this projection.
    B_OX, B_OY = 104, 144
    B_LO, B_HI, B_D, B_EXT = (-34, -50, -15), (44, 28, 24), 39, 1.25
    # frame strip and legend
    SEP_Y, FX, FY, F_LEN = 362, PAD + 74, 432, 46
    F_TEXT_X, F_TEXT_DY, LEGEND_Y = PAD + 230, -40, 462

    c = dl.Canvas(W, H, "The five emitter shapes of the Idealized depth model",
                  "Five panels: SPHERICAL fans rays from one origin on a regular grid of azimuth "
                  "and elevation; PLANAR spreads ray origins over a horizontal grid and points every "
                  "ray straight down; CYLINDRICAL stacks horizontal rings of rays from the origin's "
                  "height to maxRowUnit above it; GRIDLESS_SPHERICAL keeps a constant arc spacing so "
                  "rows away from the horizontal plane hold fewer rays; BOX aims rays from one origin "
                  "through evenly spaced points on the six faces of a box. A strip shows the sensor "
                  "frame: +X forward, +Y left, +Z up, azimuth from +X toward +Y, elevation from the "
                  "horizontal plane toward +Z.")

    def ray(ox, oy, p, color=RAY_COLOR, width=RAY_W, head=True, dashed=False):
        ex, ey = _iso(ox, oy, 1, p)
        dl.arrow(c, ox, oy, ex, ey, color, width, head=head, dashed=dashed)
        return ex, ey

    def row_arc(ox, oy, el, az0, az1, r, color=ARC_COLOR, width=1.0, n=24, dashed=False):
        pts = [_iso(ox, oy, 1, _sph(az0 + (az1 - az0) * k / n, el, r)) for k in range(n + 1)]
        _path(c, pts, color, width, dashed=dashed)

    def col_arc(ox, oy, az, el0, el1, r, color=ARC_COLOR, width=1.0, n=12, dashed=False):
        pts = [_iso(ox, oy, 1, _sph(az, el0 + (el1 - el0) * k / n, r)) for k in range(n + 1)]
        _path(c, pts, color, width, dashed=dashed)

    def panel(i, token, notes):
        px, py = PAD + i * (PANEL_W + PANEL_GAP), PANEL_Y
        dl.box(c, px, py, PANEL_W, PANEL_H, fill=dl.PANEL, rx=8)
        dl.text(c, px + PANEL_W / 2, py + TITLE_DY, token, TITLE_SIZE, "bold", "middle", dl.DK, dl.M)
        _rows_fit(notes, NOTE_W, NOTE_SIZE)
        for k, (s, fam) in enumerate(notes):
            dl.text(c, px + 10, py + NOTE_DY0 + k * NOTE_LH, s, NOTE_SIZE, "normal", "start",
                    dl.DK if fam == dl.M else dl.GREY, fam)
        return px, py

    # (1) SPHERICAL -------------------------------------------------------------------------------
    px, py = panel(0, "SPHERICAL", [
        ("One origin; a regular angular grid,", dl.F),
        ("rows: minRowUnit to maxRowUnit", dl.M),
        ("cols: minColUnit to maxColUnit", dl.M),
        ("in degrees; the last row and column", dl.F),
        ("one step short of the maximum.", dl.F)])
    ox, oy = px + S_OX, py + S_OY
    # the sampled grid: a row arc per elevation, a column arc per azimuth, then the rays
    for el in S_EL:
        row_arc(ox, oy, el, S_AZ[0], S_AZ[-1], S_R)
    for az in S_AZ:
        col_arc(ox, oy, az, S_EL[0], S_EL[-1], S_R)
    # the maxima, one step beyond the last row and the last column, are not sampled
    row_arc(ox, oy, S_EL_MAX, S_AZ[0], S_AZ[-1], S_R, MAX_COLOR, dashed=True)
    col_arc(ox, oy, S_AZ_MAX, S_EL[0], S_EL[-1], S_R, MAX_COLOR, dashed=True)
    for el in S_EL:
        for az in S_AZ:
            ray(ox, oy, _sph(az, el, S_R))
    _dot(c, ox, oy, DOT_R, dl.DK)
    dl.text(c, ox, oy + 17, "origin", LBL, "normal", "middle", dl.DK, dl.M)
    # the first row ends and the first column starts at the lowest-right ray: its row label
    # continues the row to the right, its column label continues the column downward
    dl.text(c, ox + 89, oy - 5, "minRowUnit", LBL, "normal", "start", dl.DK, dl.M)
    dl.text(c, ox + 81, oy + 12, "minColUnit", LBL, "normal", "middle", dl.DK, dl.M)
    dl.text(c, ox + 58, oy - 96, "maxRowUnit", LBL, "normal", "middle", dl.GREY, dl.M)
    dl.text(c, ox - 15, oy - 84, "maxColUnit", LBL, "normal", "middle", dl.GREY, dl.M)

    # (2) PLANAR ----------------------------------------------------------------------------------
    px, py = panel(1, "PLANAR", [
        ("Origins on a grid in the XY plane", dl.F),
        ("through origin, in meters:", dl.F),
        ("x: minColUnit to maxColUnit", dl.M),
        ("y: minRowUnit to maxRowUnit", dl.M),
        ("Every ray points straight down -Z.", dl.F)])
    ox, oy = px + P_OX, py + P_OY
    spanx, spany = P_NX * P_DX, P_NY * P_DY
    outline = [_iso(ox, oy, 1, p) for p in ((0, 0, 0), (spanx, 0, 0), (spanx, spany, 0), (0, spany, 0))]
    _path(c, outline, dl.MUTED, 1.0, dashed=True, closed=True)
    for j in range(P_NY):
        for k in range(P_NX):
            x, y = _iso(ox, oy, 1, (k * P_DX, j * P_DY, 0))
            dl.arrow(c, x, y, x, y + P_RAY, RAY_COLOR, RAY_W)
            _dot(c, x, y, DOT_R, dl.DK)
    cx, cy = _iso(ox, oy, 1, (spanx, 0, 0))
    dl.text(c, cx + 7, cy + 2, "x", LBL, "normal", "start", dl.GREY, dl.M)
    cx, cy = _iso(ox, oy, 1, (0, spany, 0))
    dl.text(c, cx - 7, cy + 2, "y", LBL, "normal", "end", dl.GREY, dl.M)
    cx, cy = _iso(ox, oy, 1, ((P_NX - 1) * P_DX, 0, 0))
    dl.text(c, cx + 12, cy + P_RAY - 6, "-Z", LBL, "normal", "start", dl.GREY, dl.M)

    # (3) CYLINDRICAL -----------------------------------------------------------------------------
    px, py = panel(2, "CYLINDRICAL", [
        ("Horizontal rings of rays stacked", dl.F),
        ("along +Z from the origin's height;", dl.F),
        ("top ring one spacing short of", dl.F),
        ("maxRowUnit above the origin", dl.M),
        ("minRowUnit: not used", dl.M)])
    ox, oy = px + C_OX, py + C_OY
    rx, ry = C_R * _COS30 * math.sqrt(2), C_R * _SIN30 * math.sqrt(2)
    zmax = oy - C_RINGS * C_DZ
    _line(c, ox, oy, ox, zmax, dl.MUTED, 1.0, dashed=True)
    _ellipse(c, ox, zmax, rx, ry, MAX_COLOR, 1.0, dashed=True)
    for r in range(C_RINGS):
        cy = oy - r * C_DZ
        _ellipse(c, ox, cy, rx, ry, ARC_COLOR, 1.0)
        for k in range(C_AZ_N):
            ray(ox, cy, _sph(22.5 + k * 360.0 / C_AZ_N, 0, C_R))
        _dot(c, ox, cy, DOT_R if r == 0 else PT_R, dl.DK)
    dl.text(c, ox, oy + ry + 14, "origin", LBL, "normal", "middle", dl.DK, dl.M)
    dl.text(c, ox + rx + 8, zmax + 4, "maxRowUnit", LBL, "normal", "start", dl.GREY, dl.M)

    # (4) GRIDLESS_SPHERICAL ----------------------------------------------------------------------
    px, py = panel(3, "GRIDLESS_SPHERICAL", [
        ("One origin, constant arc spacing:", dl.F),
        ("elementSize at distance radius", dl.M),
        ("between neighboring rays; fewer", dl.F),
        ("rays per row away from the", dl.F),
        ("horizontal plane, above and below.", dl.F)])
    ox, oy = px + G_OX, py + G_OY
    for el in G_EL:
        row_arc(ox, oy, el, G_AZ_MIN, G_AZ_MAX, G_R)
    for el in G_EL:
        step = G_DEL / math.cos(math.radians(el))
        az = G_AZ_MIN
        while az < G_AZ_MAX - 1e-9:
            ray(ox, oy, _sph(az, el, G_R))
            az += step
    row_arc(ox, oy, 0, G_AZ_MIN, G_AZ_MIN + G_DEL, G_R, dl.ORANGE, 2.2, n=8)
    ray(ox, oy, _sph(G_AZ_MIN, 0, G_R), dl.ORANGE, 1.6)
    _dot(c, ox, oy, DOT_R, dl.DK)
    dl.text(c, ox + 104, oy - 4, "elementSize", LBL, "normal", "start", dl.DK, dl.M)
    dl.text(c, ox + 104, oy + 12, "radius", LBL, "normal", "start", dl.DK, dl.M)

    # (5) BOX -------------------------------------------------------------------------------------
    px, py = panel(4, "BOX", [
        ("Rays from origin through points", dl.F),
        ("elementSize apart (per axis)", dl.M),
        ("on all six faces of the box", dl.F),
        ("bottomLeft to topRight;", dl.M),
        ("adjacent faces share edge points.", dl.F)])
    ox, oy = px + B_OX, py + B_OY
    lo, hi = B_LO, B_HI
    corners = [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    far_bottom = (hi[0], hi[1], lo[2])                      # the one vertex behind everything
    for u in corners:
        for v in corners:
            if u < v and sum(1 for i in range(3) if u[i] != v[i]) == 1:
                hidden = far_bottom in (u, v)
                _line(c, *_iso(ox, oy, 1, u), *_iso(ox, oy, 1, v),
                      dl.FAINT if hidden else dl.MUTED, 1.0, dashed=hidden)
    xs = [lo[0] + k * B_D for k in range(int((hi[0] - lo[0]) / B_D) + 1)]
    ys = [lo[1] + k * B_D for k in range(int((hi[1] - lo[1]) / B_D) + 1)]
    zs = [lo[2] + k * B_D for k in range(int((hi[2] - lo[2]) / B_D) + 1)]
    faces = ([(x, y, hi[2]) for x in xs for y in ys]        # top face (+Z)
             + [(lo[0], y, z) for y in ys for z in zs]       # near face (-X)
             + [(x, lo[1], z) for x in xs for z in zs])      # near face (-Y)
    count = {}
    for p in faces:
        count[p] = count.get(p, 0) + 1
    for p in sorted(count):
        ray(ox, oy, tuple(B_EXT * v for v in p))
    for p in sorted(count):
        x, y = _iso(ox, oy, 1, p)
        if count[p] > 1:
            _dot(c, x, y, PT_R + 0.6, dl.ORANGE, stroke=dl.DK, stroke_width=1.3)
        else:
            _dot(c, x, y, PT_R, dl.ORANGE)
    _dot(c, ox, oy, DOT_R, dl.DK)
    _line(c, ox - 56, oy + 44, ox - 3, oy + 2, dl.DK, 1.0)
    dl.text(c, ox - 60, oy + 48, "origin", LBL, "normal", "end", dl.DK, dl.M)
    bx, by = _iso(ox, oy, 1, lo)
    dl.text(c, bx, by + 32, "bottomLeft", LBL, "normal", "middle", dl.DK, dl.M)
    tx, ty = _iso(ox, oy, 1, hi)
    dl.text(c, tx, ty - 24, "topRight", LBL, "normal", "middle", dl.DK, dl.M)

    # sensor frame strip --------------------------------------------------------------------------
    _line(c, PAD, SEP_Y, W - PAD, SEP_Y, dl.FAINT, 1.0)
    for axis, lbl, anchor, dx, dy in (((F_LEN, 0, 0), "+X forward", "start", F_LEN, -26),
                                       ((0, F_LEN, 0), "+Y left", "end", -F_LEN, -26),
                                       ((0, 0, F_LEN), "+Z up", "middle", 0, -60)):
        ex, ey = _iso(FX, FY, 1, axis)
        dl.arrow(c, FX, FY, ex, ey, dl.DK, 1.6)
        dl.text(c, FX + dx, FY + dy, lbl, 12, "bold", anchor, dl.DK)
    az_arc = [_iso(FX, FY, 1, _sph(70.0 * k / 12, 0, 22)) for k in range(13)]
    dl.curve(c, az_arc, dl.ORANGE, 1.6, head=True, smooth=0)
    el_arc = [_iso(FX, FY, 1, _sph(0, 60.0 * k / 12, 28)) for k in range(13)]
    dl.curve(c, el_arc, dl.ORANGE, 1.6, head=True, smooth=0)
    dl.text(c, FX + 22, FY + 5, "azimuth", 11, "normal", "start", dl.DK)
    dl.text(c, FX + 30, FY - 42, "elevation", 11, "normal", "start", dl.DK)
    _dot(c, FX, FY, DOT_R, dl.DK)
    dl.text_block(c, F_TEXT_X, FY + F_TEXT_DY,
                  "Sensor frame (ISO 8855): +X forward, +Y left, +Z up; origin is authored in this "
                  "frame, relative to the prim's position. Azimuth is measured from +X toward +Y, "
                  "elevation from the horizontal plane toward +Z. Grids start at the minimum and "
                  "stop one step short of the maximum (dashed).",
                  W - PAD - F_TEXT_X, 12, dl.GREY)
    _legend_marks(c, PAD, LEGEND_Y, [
        ("ray", RAY_COLOR, "arrow"), ("ray origin", dl.DK, "dot"),
        ("point a ray passes through", dl.ORANGE, "dot"),
        ("point shared by adjacent faces", dl.ORANGE, "ring"),
        ("maximum, not sampled", MAX_COLOR, "dashed"), ("annotated length", dl.ORANGE, "line")])
    dl.validate(c)
    dl.write_svg(out_dir / "idealized_depth_emitter_shapes.svg", c.render())


# -------------------------------------------------------------- lidar_wpm_tiled_subsampling ---

def lidar_wpm_tiled_subsampling(out_dir: pathlib.Path) -> None:
    """What tiledSubSampling = 2 keeps: one row of every two over a rotary sweep, and inside each pattern."""
    W, H = 1000, 514
    PANEL_Y, PANEL_H = 24, 430
    LEFT_X, LEFT_W = 24, 540
    RIGHT_X, RIGHT_W = 580, 396
    TITLE_DY = 28
    # rotary panel: the emitter rows of one sweep as ticks around the revolution, in firing order
    CX, CY = LEFT_X + 190, PANEL_Y + 224
    R_RING = 118
    TICK_KEPT, TICK_DROP = 20, 14
    N_ROWS = 24                              # drawn rows; one of every two kept
    R_SENSOR = 16
    R_SPIN = 34                              # the rotation arrow around the sensor
    R_Q = R_RING + 42                        # the quantile bracket
    # solid-state panel: two firing patterns of eight rows each
    N_ROWS_SS = 8
    ROW_DY = 30
    PAT_W, PAT_GAP = 150, 26
    PAT_X0 = RIGHT_X + 34
    PAT_Y, PAT_H = PANEL_Y + 56, 318
    DOT_R = 10
    LEGEND_Y = PANEL_Y + PANEL_H + 20

    def polar(r, deg):
        a = math.radians(deg)
        return CX + r * math.cos(a), CY + r * math.sin(a)

    c = dl.Canvas(W, H, "What a tiledSubSampling factor of 2 keeps on the Lidar generic wpm model",
                  "Two panels. Left, a rotary scan: the emitter rows of one sweep drawn as ticks around the "
                  "full revolution in firing order, one of every two kept and the other faded, so the kept "
                  "rows are spread evenly over the complete scan and the sweep is still covered. Right, a "
                  "solid-state scan: two firing patterns of eight rows each, one of every two rows kept "
                  "inside each pattern independently, because only one pattern fires in a scan. The row "
                  "counts are illustrative.")

    for x, w, title in ((LEFT_X, LEFT_W, "Rotary"), (RIGHT_X, RIGHT_W, "Solid-state")):
        dl.box(c, x, PANEL_Y, w, PANEL_H, fill=dl.PANEL)
        dl.text(c, x + 16, PANEL_Y + TITLE_DY, title, 15, "bold")
        dl.text(c, x + w - 16, PANEL_Y + TITLE_DY, "tiledSubSampling = 2", 12.5, "normal", "end",
                dl.GREY, dl.M)

    # --- rotary -------------------------------------------------------------------------------
    _dot(c, CX, CY, R_RING, "none", dl.FAINT, 1.5)
    step = 360.0 / N_ROWS
    for i in range(N_ROWS):
        ang = -90 + i * step                 # firing order, clockwise from the top
        kept = i % 2 == 1                    # the second row of each pair: the quantile's midpoint
        x0, y0 = polar(R_RING, ang)
        x1, y1 = polar(R_RING + (TICK_KEPT if kept else TICK_DROP), ang)
        _line(c, x0, y0, x1, y1, dl.GREEN if kept else dl.MUTED, 2.5 if kept else 1.5, dashed=not kept)
    _dot(c, CX, CY, R_SENSOR, dl.DK)
    dl.curve(c, [polar(R_SPIN, a) for a in range(-60, 241, 20)], dl.GREY, 1.5, head=True)
    dl.text(c, CX, CY + R_SPIN + 24, "complete sweep,", 12.5, "normal", "middle", dl.DK)
    dl.text(c, CX, CY + R_SPIN + 42, "half the rows", 12.5, "normal", "middle", dl.DK)
    dl.text(c, CX, CY - R_SPIN - 14, "sensor", 11.5, "normal", "middle", dl.GREY)
    # one quantile: two consecutive rows, of which the model keeps one
    qa0, qa1 = -90 + 1.5 * step, -90 + 3.5 * step
    dl.curve(c, [polar(R_Q, qa0 + (qa1 - qa0) * k / 6) for k in range(7)], dl.DK, 1.5, head=False)
    for a in (qa0, qa1):
        e0x, e0y = polar(R_Q - 5, a)
        e1x, e1y = polar(R_Q + 5, a)
        _line(c, e0x, e0y, e1x, e1y, dl.DK, 1.5)
    lx, ly = polar(R_Q + 12, (qa0 + qa1) / 2)
    dl.text(c, lx, ly - 4, "one quantile of the sweep:", 12.5, "normal", "start", dl.DK)
    dl.text(c, lx, ly + 14, "two rows, one kept", 12.5, "normal", "start", dl.DK)
    dl.text(c, CX, CY + R_RING + 48, "24 rows in firing order, 12 kept", 12.5, "normal", "middle", dl.DK)
    dl.text(c, CX, CY + R_RING + 66, "spread evenly over the whole scan", 11.5, "normal", "middle", dl.GREY)

    # --- solid-state --------------------------------------------------------------------------
    for p in range(2):
        px = PAT_X0 + p * (PAT_W + PAT_GAP)
        pat = dl.box(c, px, PAT_Y, PAT_W, PAT_H, fill=dl.WHITE, stroke=dl.FAINT, rx=8)
        dl.text(c, pat.cx, PAT_Y + 22, f"pattern {p + 1}", 12.5, "bold", "middle", dl.DK)
        dl.text(c, pat.cx, PAT_Y + 39, "8 rows", 11.5, "normal", "middle", dl.GREY)
        y0 = PAT_Y + 52 + DOT_R
        for i in range(N_ROWS_SS):
            y = y0 + i * ROW_DY
            kept = i % 2 == 1
            if kept:
                _dot(c, pat.cx, y, DOT_R, dl.GREEN)
            else:
                _dot(c, pat.cx, y, DOT_R, dl.WHITE, dl.MUTED, 1.5)
            dl.text(c, pat.cx, y + 4, str(i + 1), 11, "bold", "middle", dl.WHITE if kept else dl.MUTED, dl.M)
        dl.text(c, pat.cx, PAT_Y + PAT_H - 10, "4 of 8 kept", 11.5, "normal", "middle", dl.GREEN)
    dl.text(c, RIGHT_X + RIGHT_W / 2, PANEL_Y + PANEL_H - 32, "one row of every two, inside each pattern",
            12.5, "normal", "middle", dl.DK)
    dl.text(c, RIGHT_X + RIGHT_W / 2, PANEL_Y + PANEL_H - 14, "only one pattern fires in a scan",
            11.5, "normal", "middle", dl.GREY)

    dl.legend(c, LEFT_X, LEGEND_Y, (("kept: still fired at factor 2", dl.GREEN),
                                     ("dropped by the factor", dl.MUTED, "dashed")))
    dl.validate(c)
    dl.write_svg(out_dir / "lidar_wpm_tiled_subsampling.svg", c.render())


# ------------------------------------------------------ lidar_wpm_pattern_selection_timeline ---
def lidar_wpm_pattern_selection_timeline(out_dir: pathlib.Path) -> None:
    W, H = 960, 414
    X0 = 30
    TITLE_Y, SUBTITLE_Y = 30, 48
    # top row: rotary
    HEAD1_Y = 80
    SCAN_LABEL_Y, SCAN_BR_Y, BR_DEPTH = 104, 112, 6
    TICK_Y, TICK_H, TICK_W, TICK_GAP, TICKS_PER_SCAN, SCAN_GAP = 122, 44, 66, 6, 5, 24
    UNDER_BR_Y, UNDER_LABEL_Y = 176, 198
    # bottom row: solid state
    HEAD2_Y = 234
    JUMP_NOTE_Y, JUMP_TOP_Y = 256, 268
    SCAN_Y, SCAN_H, SCAN_W, SCAN_PITCH, SCANS = 282, 44, 110, 114, 6
    AXIS_Y, AXIS_TICK, AXIS_CAPTION_Y = 338, 6, 372
    FORMULA_X, FORMULA_DY = 790, 6
    LEGEND_Y = 388
    DWELL, PATTERNS = 2, ("p001", "p002")
    COLORS = {"p001": dl.BLUE, "p002": dl.PURPLE}

    c = dl.Canvas(W, H, "Pattern selection with two patterns and a dwell of two ticks",
                  "Top: a rotary sensor numbers its ticks from 0 at every scan boundary; with "
                  "patterns p001 and p002 and firingPatternDwellTicks = 2, ticks 0 and 1 fire p001, "
                  "ticks 2 and 3 fire p002, tick 4 fires p001, and the next scan starts with p001 "
                  "again, three p001 ticks in a row across the boundary. Bottom: a solid-state "
                  "sensor's tick is the scan itself, counted from time zero, so scans 0 and 1 fire "
                  "p001, scans 2 and 3 fire p002 and scans 4 and 5 fire p001; a jump in time from "
                  "scan 1 to scan 4 lands on the pattern of that scan index.")

    def pattern(index):
        return PATTERNS[(index // DWELL) % len(PATTERNS)]

    dl.text(c, X0, TITLE_Y, "Which pattern fires: two patterns, each held for two ticks",
            15, "bold", "start", dl.DK)
    dl.text(c, X0, SUBTITLE_Y, "patterns p001, p002; firingPatternDwellTicks = 2",
            12, "normal", "start", dl.GREY, dl.M)

    # rotary row ----------------------------------------------------------------------------------
    dl.text(c, X0, HEAD1_Y, "Rotary: ticks numbered from 0 at every scan boundary", 14, "bold",
            "start", dl.DK)
    scan_w = TICKS_PER_SCAN * TICK_W + (TICKS_PER_SCAN - 1) * TICK_GAP
    tick_x = {}
    for s, name in enumerate(("scan n", "scan n+1")):
        sx = X0 + s * (scan_w + SCAN_GAP)
        _bracket(c, sx, sx + scan_w, SCAN_BR_Y, BR_DEPTH)
        dl.text(c, sx + scan_w / 2, SCAN_LABEL_Y, name, 12, "bold", "middle", dl.DK)
        for t in range(TICKS_PER_SCAN):
            x = sx + t * (TICK_W + TICK_GAP)
            tick_x[(s, t)] = x
            p = pattern(t)
            dl.box(c, x, TICK_Y, TICK_W, TICK_H, str(t), fill=COLORS[p], sublabel=p,
                   label_family=dl.M, label_size=14, sublabel_size=11)
    boundary_x = X0 + scan_w + SCAN_GAP / 2
    _line(c, boundary_x, SCAN_LABEL_Y + 6, boundary_x, UNDER_BR_Y + 2, dl.GREY, 1.5, dashed=True)
    dl.text(c, boundary_x, SCAN_LABEL_Y, "numbering restarts", 12, "normal", "middle", dl.GREY)
    run_x0, run_x1 = tick_x[(0, TICKS_PER_SCAN - 1)], tick_x[(1, 1)] + TICK_W
    _bracket(c, run_x0, run_x1, UNDER_BR_Y, -BR_DEPTH, dl.BLUE)
    dl.text(c, (run_x0 + run_x1) / 2, UNDER_LABEL_Y, "three p001 ticks in a row", 12, "normal",
            "middle", dl.BLUE)
    fy = TICK_Y + TICK_H / 2
    dl.text(c, FORMULA_X, fy - FORMULA_DY, "pattern index", 11, "normal", "start", dl.GREY)
    dl.text(c, FORMULA_X, fy + FORMULA_DY + 10, "(tickIndex / 2) % 2", 12, "normal", "start", dl.DK, dl.M)

    # solid-state row -----------------------------------------------------------------------------
    dl.text(c, X0, HEAD2_Y, "Solid state: one tick per scan, counted from time zero", 14, "bold",
            "start", dl.DK)
    for s in range(SCANS):
        x = X0 + s * SCAN_PITCH
        p = pattern(s)
        dl.box(c, x, SCAN_Y, SCAN_W, SCAN_H, f"scan {s}", fill=COLORS[p], sublabel=p,
               label_family=dl.M, label_size=13, sublabel_size=11)
    from_x, to_x = X0 + 1 * SCAN_PITCH + SCAN_W / 2, X0 + 4 * SCAN_PITCH + SCAN_W / 2
    dl.curve(c, [(from_x, SCAN_Y - 2), ((from_x + to_x) / 2, JUMP_TOP_Y), (to_x, SCAN_Y - 2)],
             dl.GREY, 1.8, head=True)
    dl.text(c, (from_x + to_x) / 2, JUMP_NOTE_Y,
            "a jump in time lands on the pattern of that scan index (p001)", 12, "normal", "middle",
            dl.GREY)
    dl.tick_marks(c, X0, AXIS_Y, SCANS * SCAN_PITCH + 10, [k * SCAN_PITCH for k in range(SCANS + 1)],
                  [str(k) for k in range(SCANS + 1)], tick=AXIS_TICK)
    dl.text(c, X0, AXIS_CAPTION_Y, "t, in scan periods from time zero (one scan period is 0.1 s in "
            "the example)", 12, "normal", "start", dl.GREY)
    fy = SCAN_Y + SCAN_H / 2
    dl.text(c, FORMULA_X, fy - FORMULA_DY, "pattern index", 11, "normal", "start", dl.GREY)
    dl.text(c, FORMULA_X, fy + FORMULA_DY + 10, "(scanIndex / 2) % 2", 12, "normal", "start", dl.DK, dl.M)

    dl.legend(c, FORMULA_X, LEGEND_Y - 2, [(p, COLORS[p]) for p in PATTERNS])
    dl.validate(c)
    dl.write_svg(out_dir / "lidar_wpm_pattern_selection_timeline.svg", c.render())


# ------------------------------------------------------- lidar_wpm_return_path_transmissive ---
def lidar_wpm_return_path_transmissive(out_dir: pathlib.Path) -> None:
    W, H = 1100, 300
    PAD, PANEL_W, PANEL_GAP, PANEL_Y, PANEL_H = 12, 352, 10, 14, 240
    TITLE_DY = 26
    SENSOR_DX, SENSOR_DY, SENSOR_W, SENSOR_H = 14, 80, 70, 48
    OUT_DY, RET_DY = 100, 124                      # pulse out; return arrival at the sensor
    PANE_W, PANE_TOP_DY, PANE_BOT_DY = 6, 52, 170
    WALL_DX, WALL_W = 318, 14
    STATUS_DY, GEOM_LABEL_DY = 188, 208
    OUT_W, RET_W, RET_W_THIN, CROSS = 2.2, 2, 1.2, 12
    LEGEND_Y = 270
    PANELS = (("waveform", (200,), None, "return accepted (attenuated)"),
              ("directDetector / directMaterial", (200,), 200, "return blocked"),
              ("waveform, two panes", (150, 230), 150, "return blocked"))

    c = dl.Canvas(W, H, "What each return-processing mode can see through",
                  "Three plan views of a pulse that passes a glass pane and hits a wall. Left, "
                  "waveform mode: the return from the wall crosses the pane on its way back and is "
                  "accepted, attenuated. Middle, directDetector or directMaterial mode: the return "
                  "is blocked at the pane, so only the pane itself can be reported. Right, waveform "
                  "mode with two panes: the return crosses the first pane it meets and is blocked "
                  "at the second.")

    for i, (title, panes, blocked_at, status) in enumerate(PANELS):
        px, py = PAD + i * (PANEL_W + PANEL_GAP), PANEL_Y
        dl.box(c, px, py, PANEL_W, PANEL_H, fill=dl.PANEL, rx=8)
        dl.text(c, px + PANEL_W / 2, py + TITLE_DY, title, 14, "bold", "middle", dl.DK, dl.M)
        sensor = dl.box(c, px + SENSOR_DX, py + SENSOR_DY, SENSOR_W, SENSOR_H, "sensor",
                        fill=dl.WHITE, stroke=dl.GREY, stroke_width=1.5, label_size=13)
        for pane in panes:
            dl.box(c, px + pane - PANE_W / 2, py + PANE_TOP_DY, PANE_W, PANE_BOT_DY - PANE_TOP_DY,
                   fill=dl.WHITE, stroke=dl.BLUE, stroke_width=1.5, rx=1)
        dl.box(c, px + WALL_DX, py + PANE_TOP_DY, WALL_W, PANE_BOT_DY - PANE_TOP_DY, fill=dl.GREY, rx=1)
        hit_x, hit_y = px + WALL_DX, py + OUT_DY
        dl.arrow(c, sensor.right, py + OUT_DY, hit_x - 1, hit_y, dl.DK, OUT_W)
        _dot(c, hit_x, hit_y, 4, dl.DK)
        # the return: a straight line from the hit back to the sensor, pane by pane
        end_x, end_y = sensor.right, py + RET_DY

        def ret_y(x):
            return hit_y + (end_y - hit_y) * (hit_x - x) / (hit_x - end_x)

        cur_x, cur_y, width = hit_x, hit_y, RET_W
        for pane in sorted(panes, reverse=True):
            pane_x = px + pane
            _line(c, cur_x, cur_y, pane_x, ret_y(pane_x), dl.BLUE, width, dashed=True)
            cur_x, cur_y = pane_x, ret_y(pane_x)
            if pane == blocked_at:
                _cross(c, cur_x, cur_y, CROSS)
                break
            width = RET_W_THIN
        else:
            dl.arrow(c, cur_x, cur_y, end_x, end_y, dl.BLUE, width, dashed=True)
        status_x = px + blocked_at if blocked_at else (sensor.right + px + panes[0]) / 2
        dl.text(c, status_x, py + STATUS_DY, status, 12, "bold", "middle",
                dl.RED if blocked_at else dl.GREEN)
        pane_label = "glass (transmissive)" if len(panes) == 1 else "glass (transmissive), two panes"
        dl.text(c, px + sum(panes) / len(panes), py + GEOM_LABEL_DY, pane_label, 12, "normal",
                "middle", dl.GREY)
        dl.text(c, px + WALL_DX + WALL_W / 2, py + GEOM_LABEL_DY, "wall", 12, "normal", "middle", dl.GREY)

    _legend_marks(c, PAD + 4, LEGEND_Y, [("pulse out", dl.DK, "arrow"),
                                         ("return to the receiver", dl.BLUE, "dashed"),
                                         ("blocked", dl.RED, "cross")])
    dl.validate(c)
    dl.write_svg(out_dir / "lidar_wpm_return_path_transmissive.svg", c.render())


# ------------------------------------------------------------- lidar_wpm_pulse_through_glass ---
def lidar_wpm_pulse_through_glass(out_dir: pathlib.Path) -> None:
    W, H = 900, 424
    SENSOR_X, SENSOR_Y, SENSOR_W, SENSOR_H = 30, 66, 170, 90
    PULSE_Y, GLASS_RET_Y, WALL_RET_Y = 90, 120, 150
    PANE_X, PANE_W, PANE_TOP, PANE_BOT = 440, 6, 40, 172
    WALL_X, WALL_W = 800, 14
    GEOM_LABEL_Y, PULSE_LABEL_DY = 192, 10
    PULSE_W, CONT_W, RET_W, RET_W_THIN = 2.4, 1.6, 2, 1.2
    AXIS_X0, AXIS_X1, AXIS_Y, SIG_AXIS_TOP = 200, 800, 358, 250
    THRESH_Y = 316
    GLASS_PEAK_X, GLASS_PEAK_H = 330, 72
    WALL_PEAK_X, WALL_PEAK_H = 600, 96
    PEAK_HALF_W, PEAK_LABEL_DY = 50, 10
    LEGEND_Y = 396

    c = dl.Canvas(W, H, "One pulse, two returns",
                  "A pulse leaves the emitter and meets a glass pane: part of it returns to the "
                  "detector from the pane and part continues to a wall behind it, whose return "
                  "crosses the pane once on its way back and is attenuated. A time axis below shows "
                  "the detector signal with two peaks above the detection threshold, an earlier one "
                  "from the glass and a later one from the wall.")

    sensor = dl.box(c, SENSOR_X, SENSOR_Y, SENSOR_W, SENSOR_H, "emitter / detector",
                    fill=dl.WHITE, stroke=dl.GREY, stroke_width=1.5, label_size=13)
    dl.box(c, PANE_X, PANE_TOP, PANE_W, PANE_BOT - PANE_TOP, fill=dl.WHITE, stroke=dl.BLUE,
           stroke_width=1.5, rx=1)
    dl.box(c, WALL_X, PANE_TOP, WALL_W, PANE_BOT - PANE_TOP, fill=dl.GREY, rx=1)
    # pulse out, the hit on the pane, the continuation and the hit on the wall
    dl.arrow(c, sensor.right, PULSE_Y, PANE_X - 1, PULSE_Y, dl.DK, PULSE_W)
    dl.text(c, (sensor.right + PANE_X) / 2, PULSE_Y - PULSE_LABEL_DY, "pulse", 12, "bold", "middle", dl.DK)
    dl.arrow(c, PANE_X + PANE_W, PULSE_Y, WALL_X - 1, PULSE_Y, dl.DK, CONT_W)
    dl.text(c, (PANE_X + WALL_X) / 2, PULSE_Y - PULSE_LABEL_DY, "part of the pulse continues "
            "through the pane", 12, "normal", "middle", dl.GREY)
    _dot(c, PANE_X, PULSE_Y, 4, dl.DK)
    _dot(c, WALL_X, PULSE_Y, 4, dl.DK)
    # the return from the glass: straight back, the shorter path
    dl.arrow(c, PANE_X, PULSE_Y, sensor.right, GLASS_RET_Y, dl.BLUE, RET_W, dashed=True)
    # the return from the wall: through the pane once, thinner after the crossing
    far_x = PANE_X + PANE_W
    far_y = PULSE_Y + (WALL_RET_Y - PULSE_Y) * (WALL_X - far_x) / (WALL_X - sensor.right)
    _line(c, WALL_X, PULSE_Y, far_x, far_y, dl.PURPLE, RET_W, dashed=True)
    dl.arrow(c, far_x, far_y, sensor.right, WALL_RET_Y, dl.PURPLE, RET_W_THIN, dashed=True)
    dl.text(c, PANE_X + PANE_W / 2, GEOM_LABEL_Y, "glass (transmissive)", 12, "normal", "middle", dl.GREY)
    dl.text(c, WALL_X + WALL_W / 2, GEOM_LABEL_Y, "wall", 12, "normal", "middle", dl.GREY)
    # detector signal over time
    dl.arrow(c, AXIS_X0, AXIS_Y, AXIS_X1 + 10, AXIS_Y, dl.GREY, 1.5)
    dl.arrow(c, AXIS_X0, AXIS_Y, AXIS_X0, SIG_AXIS_TOP, dl.GREY, 1.5)
    dl.text(c, AXIS_X1 + 20, AXIS_Y + 4, "t", 13, "normal", "start", dl.DK, dl.M)
    dl.text(c, AXIS_X0, SIG_AXIS_TOP - 10, "detector signal", 12, "normal", "middle", dl.GREY)
    _line(c, AXIS_X0, THRESH_Y, AXIS_X1, THRESH_Y, dl.GREY, 1.5, dashed=True)
    dl.text(c, AXIS_X1 - 4, THRESH_Y - 6, "detection threshold", 12, "normal", "end", dl.GREY)
    _bump(c, GLASS_PEAK_X, AXIS_Y, GLASS_PEAK_H, PEAK_HALF_W, dl.BLUE)
    _bump(c, WALL_PEAK_X, AXIS_Y, WALL_PEAK_H, PEAK_HALF_W, dl.PURPLE)
    dl.text(c, GLASS_PEAK_X, AXIS_Y - GLASS_PEAK_H - PEAK_LABEL_DY, "glass", 12, "bold", "middle", dl.BLUE)
    dl.text(c, WALL_PEAK_X, AXIS_Y - WALL_PEAK_H - PEAK_LABEL_DY, "wall", 12, "bold", "middle", dl.PURPLE)
    _legend_marks(c, SENSOR_X, LEGEND_Y, [("pulse", dl.DK, "arrow"),
                                          ("return from the glass", dl.BLUE, "dashed"),
                                          ("return from the wall", dl.PURPLE, "dashed"),
                                          ("detection threshold", dl.GREY, "dashed")])
    dl.validate(c)
    dl.write_svg(out_dir / "lidar_wpm_pulse_through_glass.svg", c.render())


# ------------------------------------------------------------------- lidar_wpm_point_layouts ---
def lidar_wpm_point_layouts(out_dir: pathlib.Path) -> None:
    W, H = 1060, 560
    LEFT_X = 90                                   # right edge of the strip labels
    BOX_X0, BOX_W, BOX_GAP, TILE_GAP, BOX_H = 104, 70, 4, 16, 44
    TILES, ROWS, RETURNS = 2, 3, 2
    VALID = (0, 2, 3, 6, 9, 10)
    HEAD1_Y = 34
    TILE_LABEL_Y, TILE_BR_Y, BR_DEPTH = 62, 70, 6
    ROW_LABEL_Y, DENSE_Y = 92, 100
    RETURN_STRIP_Y, FLAGS1_Y = 162, 180
    RSTRIDE_BR_Y, RSTRIDE_LABEL_Y = 198, 216
    TSTRIDE_BR_Y, TSTRIDE_LABEL_Y = 230, 248
    ARROW_Y0, ARROW_Y1 = 262, 300
    HEAD2_Y = 326
    COUNTS_LABEL_Y, COUNTS_BR_Y = 352, 360
    TPC_LABEL_Y, TPC_BR_Y = 378, 392
    TPO_LABEL_Y, TPO_ARROW_Y0 = 408, 414
    COMPACT_Y = 434
    INDEX_STRIP_Y, FLAGS2_Y = 496, 514
    LEGEND_Y = 534
    HEAD_SIZE, DETAIL_SIZE, STRIP_SIZE = 14, 12, 11

    per_tile = ROWS * RETURNS
    n = TILES * per_tile
    c = dl.Canvas(W, H, "Dense and compact point layouts of a two-tile aggregate",
                  "Top, dense output: twelve capacity slots in tile-major, row-major, return-major "
                  "order for two tiles with receiversPerTile 3 and maxReturns 2; the VALID bit of Flags "
                  "marks the six slots that hold a return, tileStridePoints = 6 and receiverStridePoints = 2 locate "
                  "a slot and Counts[0] = 12 is the capacity. Bottom, compact output: the same six "
                  "returns gathered into a prefix of length Counts[0] = 6 in the same order, "
                  "TilePointOffsets = [0, 3, 6] and TilePointCounts = [3, 3] saying where each tile's "
                  "returns are, and the six remaining slots unspecified with Flags 0.")

    def slot_x(i):
        return BOX_X0 + i * (BOX_W + BOX_GAP) + (TILE_GAP if i >= per_tile else 0)

    def heading(y, title, detail):
        tb = dl.text(c, BOX_X0, y, title, HEAD_SIZE, "bold", "start", dl.DK)
        dl.text(c, tb.x1 + 14, y, detail, DETAIL_SIZE, "normal", "start", dl.GREY, dl.M)

    def strip(y, name, values, family=dl.M):
        dl.text(c, LEFT_X, y, name, STRIP_SIZE, "normal", "end", dl.GREY, family)
        for i, v in enumerate(values):
            dl.text(c, slot_x(i) + BOX_W / 2, y, v, STRIP_SIZE, "normal", "middle", dl.DK, dl.M)

    # dense layout --------------------------------------------------------------------------------
    heading(HEAD1_Y, "Dense output",
            "includeInvalidPoints = true · Counts[0] = 12 (capacity) · compactionType = 1")
    for t in range(TILES):
        x0, x1 = slot_x(t * per_tile), slot_x(t * per_tile + per_tile - 1) + BOX_W
        _bracket(c, x0, x1, TILE_BR_Y, BR_DEPTH)
        dl.text(c, (x0 + x1) / 2, TILE_LABEL_Y, f"tile {t}", 12, "bold", "middle", dl.DK, dl.M)
        for r in range(ROWS):
            s = t * per_tile + r * RETURNS
            dl.text(c, slot_x(s) + BOX_W + BOX_GAP / 2, ROW_LABEL_Y, f"row {r}", STRIP_SIZE,
                    "normal", "middle", dl.GREY, dl.M)
    for i in range(n):
        if i in VALID:
            dl.box(c, slot_x(i), DENSE_Y, BOX_W, BOX_H, str(i), fill=dl.GREEN, label_family=dl.M)
        else:
            dl.box(c, slot_x(i), DENSE_Y, BOX_W, BOX_H, str(i), fill=dl.WHITE, stroke=dl.GREY,
                   stroke_width=1.5, label_family=dl.M)
    strip(RETURN_STRIP_Y, "return", [str(i % RETURNS) for i in range(n)], dl.F)
    strip(FLAGS1_Y, "VALID bit", ["set" if i in VALID else "clear" for i in range(n)])
    _bracket(c, slot_x(0), slot_x(RETURNS), RSTRIDE_BR_Y, -BR_DEPTH)
    dl.text(c, (slot_x(0) + slot_x(RETURNS)) / 2, RSTRIDE_LABEL_Y, "receiverStridePoints = 2",
            DETAIL_SIZE, "normal", "middle", dl.DK, dl.M)
    _bracket(c, slot_x(0), slot_x(per_tile), TSTRIDE_BR_Y, -BR_DEPTH)
    dl.text(c, (slot_x(0) + slot_x(per_tile)) / 2, TSTRIDE_LABEL_Y, "tileStridePoints = 6",
            DETAIL_SIZE, "normal", "middle", dl.DK, dl.M)

    # compaction ----------------------------------------------------------------------------------
    ax = (slot_x(0) + slot_x(n - 1) + BOX_W) / 2
    dl.arrow(c, ax, ARROW_Y0, ax, ARROW_Y1, dl.GREY, 2)
    dl.text(c, ax + 12, (ARROW_Y0 + ARROW_Y1) / 2 + 4, "compaction (stable order: tile, row, return)",
            DETAIL_SIZE, "normal", "start", dl.GREY)

    # compact layout ------------------------------------------------------------------------------
    heading(HEAD2_Y, "Compact output (the default)",
            "includeInvalidPoints = false · Counts[0] = 6 · compactionType = 2")
    valid_n = len(VALID)
    x0, x1 = slot_x(0), slot_x(valid_n - 1) + BOX_W
    _bracket(c, x0, x1, COUNTS_BR_Y, BR_DEPTH)
    dl.text(c, (x0 + x1) / 2, COUNTS_LABEL_Y, "Counts[0] = 6", DETAIL_SIZE, "bold", "middle", dl.DK, dl.M)
    offsets = [0]
    for t in range(TILES):
        cnt = sum(1 for s in VALID if s // per_tile == t)
        bx0, bx1 = slot_x(offsets[-1]), slot_x(offsets[-1] + cnt - 1) + BOX_W
        _bracket(c, bx0, bx1, TPC_BR_Y, -5)
        dl.text(c, (bx0 + bx1) / 2, TPC_LABEL_Y, f"TilePointCounts[{t}] = {cnt}", DETAIL_SIZE,
                "normal", "middle", dl.DK, dl.M)
        offsets.append(offsets[-1] + cnt)
    for k, off in enumerate(offsets):
        x = slot_x(off) if off < n else slot_x(off - 1) + BOX_W
        if off == valid_n:
            x = slot_x(off - 1) + BOX_W
        dl.arrow(c, x, TPO_ARROW_Y0, x, COMPACT_Y - 1, dl.GREY, 2)
        dl.text(c, x, TPO_LABEL_Y, f"TilePointOffsets[{k}] = {off}", DETAIL_SIZE, "normal",
                "middle", dl.DK, dl.M)
    tail_x0, tail_x1 = slot_x(valid_n), slot_x(n - 1) + BOX_W
    dl.text(c, (tail_x0 + tail_x1) / 2, TPO_LABEL_Y, "unspecified, Flags = 0", DETAIL_SIZE,
            "normal", "middle", dl.GREY)
    for i in range(n):
        if i < valid_n:
            dl.box(c, slot_x(i), COMPACT_Y, BOX_W, BOX_H, f"slot {VALID[i]}", fill=dl.GREEN,
                   label_family=dl.M, label_size=11)
        else:
            dl.box(c, slot_x(i), COMPACT_Y, BOX_W, BOX_H, fill=dl.FAINT)
    strip(INDEX_STRIP_Y, "index", [str(i) for i in range(n)], dl.F)
    strip(FLAGS2_Y, "VALID bit", ["set" if i < valid_n else "clear" for i in range(n)])
    dl.legend(c, BOX_X0, LEGEND_Y, [("slot holding a return (VALID bit set)", dl.GREEN),
                                    ("empty slot (VALID bit clear)", dl.GREY, "outline"),
                                    ("unspecified tail", dl.FAINT)])
    dl.validate(c)
    dl.write_svg(out_dir / "lidar_wpm_point_layouts.svg", c.render())


# ------------------------------------------------------------------------------- entry point ---
def generate(out_dir: pathlib.Path) -> None:
    idealized_depth_emitter_shapes(out_dir)
    lidar_wpm_pattern_selection_timeline(out_dir)
    lidar_wpm_return_path_transmissive(out_dir)
    lidar_wpm_pulse_through_glass(out_dir)
    lidar_wpm_tiled_subsampling(out_dir)
    lidar_wpm_point_layouts(out_dir)


if __name__ == "__main__":
    generate(dl.output_dir(__file__))
