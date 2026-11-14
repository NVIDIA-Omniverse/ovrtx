import pathlib, sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent)); import _diagram_lib as dl  # noqa: E401,E702

# Figures of the overview group of the sensor documentation: the two diagrams of
# ``sensors/first_sensor.rst``.
#
#     python3 -B _gen_overview.py            # regenerate only this group, in place
#     python3 -B _gen_overview.py /tmp/check # write elsewhere, to diff against the committed files
#
# ``generate_diagrams.py`` beside this file runs every ``_gen_*.py`` module of the directory.
# Stdlib only; byte-for-byte reproducible (no timestamps, no randomness, fixed number formatting).

import math  # noqa: E402
from typing import List, Optional, Sequence, Tuple  # noqa: E402


# ------------------------------------------------------------------------------------ helpers ---
def _fits(s: str, size: float, max_width: float, weight: str = "normal", family: str = dl.F) -> None:
    """Raise if ``s`` would be wider than ``max_width`` px (a layout bug, not something to shrink)."""
    w = dl.text_width(s, size, weight, family)
    if w > max_width:
        raise ValueError(f"{s!r} at {size} px needs {w} px but only {max_width} px are available")


def _hline(c: dl.Canvas, x1: float, y: float, x2: float, stroke: str = dl.FAINT, width: float = 1) -> None:
    c.add(f'<line x1="{dl.fmt(x1)}" y1="{dl.fmt(y)}" x2="{dl.fmt(x2)}" y2="{dl.fmt(y)}" '
          f'stroke="{stroke}" stroke-width="{dl.fmt(width)}"/>')


def _line(c: dl.Canvas, x1: float, y1: float, x2: float, y2: float, stroke: str = dl.GREY,
          width: float = 1, dashed: bool = False) -> None:
    attrs = (f'x1="{dl.fmt(x1)}" y1="{dl.fmt(y1)}" x2="{dl.fmt(x2)}" y2="{dl.fmt(y2)}" '
             f'stroke="{stroke}" stroke-width="{dl.fmt(width)}"')
    if dashed:
        attrs += f' stroke-dasharray="{dl.fmt(3 * width)} {dl.fmt(2 * width)}"'
    c.add(f"<line {attrs}/>")


def _elbow(c: dl.Canvas, x0: float, y0: float, x1: float, y1: float, y_mid: float, stroke: str,
           width: float = 2, dashed: bool = False) -> None:
    """Orthogonal connector: down from (x0, y0) to y_mid, across to x1, down to (x1, y1) with a head."""
    pts: List[Tuple[float, float]] = [(x0, y0), (x0, y_mid), (x1, y_mid), (x1, y1)]
    head_len = dl._head(width)[0]                    # same head length as dl.arrow for this weight
    (ax, ay), (bx, by) = pts[-2], pts[-1]
    d = math.hypot(bx - ax, by - ay)
    if d > head_len:                                 # end the stroke at the base of the head
        pts[-1] = (bx - (bx - ax) / d * head_len, by - (by - ay) / d * head_len)
    path = "M" + " L".join(f"{dl.fmt(x)},{dl.fmt(y)}" for x, y in pts)
    attrs = (f'd="{path}" fill="none" stroke="{stroke}" stroke-width="{dl.fmt(width)}" '
             f'stroke-linejoin="round"')
    if dashed:
        attrs += f' stroke-dasharray="{dl.fmt(3 * width)} {dl.fmt(2 * width)}"'
    attrs += f' marker-end="url(#{c.marker(stroke, width)})"'
    c.add(f"<path {attrs}/>")


def _card(c: dl.Canvas, x: float, y: float, w: float, h: float, pad: float, title: str, path: str,
          role: str, body: Sequence[Tuple]) -> dl.Rect:
    """A USD prim card: type, prim path, its role in plain words, then the authored lines.

    Each body entry is ``(text, family, fill)`` or ``(text, family, fill, indent_px)``; the indent
    is a pixel offset, not leading whitespace, because some SVG rasterizers trim even non-breaking
    spaces at the start of a ``<text>`` element.
    """
    title_dy, path_dy, role_dy, sep_dy, body_dy, body_lh = 24, 43, 61, 70, 88, 18
    inner = w - 2 * pad
    r = dl.box(c, x, y, w, h, fill=dl.PANEL, rx=8)
    tx = x + pad
    _fits(title, 14, inner, "bold")
    _fits(path, 12, inner, family=dl.M)
    _fits(role, 12, inner)
    dl.text(c, tx, y + title_dy, title, 14, "bold")
    dl.text(c, tx, y + path_dy, path, 12, family=dl.M)
    dl.text(c, tx, y + role_dy, role, 12, fill=dl.GREY)
    if body:
        _hline(c, tx, y + sep_dy, x + w - pad)
        for i, entry in enumerate(body):
            s, family, fill = entry[0], entry[1], entry[2]
            indent = float(entry[3]) if len(entry) > 3 else 0.0
            _fits(s, 12, inner - indent, family=family)
            dl.text(c, tx + indent, y + body_dy + i * body_lh, s, 12, fill=fill, family=family)
    return r


def _pill(c: dl.Canvas, x: float, y: float, w: float, h: float, label: str) -> dl.Rect:
    """A call in the reader's program: a blue capsule with a monospace label."""
    return dl.box(c, x, y, w, h, label, fill=dl.BLUE, rx=h / 2, label_size=13,
                  label_weight="normal", label_family=dl.M)


def _labelled_arrow(c: dl.Canvas, x1: float, x2: float, y: float, label: Optional[str],
                    stroke: str = dl.GREY, width: float = 2, label_dy: float = 8,
                    label_family: str = dl.F, label_size: float = 12) -> None:
    """A horizontal arrow with an optional label centred above it; the label must fit the gap."""
    dl.arrow(c, x1, y, x2, y, stroke, width)
    if label:
        _fits(label, label_size, abs(x2 - x1) - 8, family=label_family)
        dl.text(c, (x1 + x2) / 2, y - label_dy, label, label_size, anchor="middle", fill=dl.GREY,
                family=label_family)


# ---------------------------------------------------------------------- first_sensor_pieces ---
def first_sensor_pieces(out_dir: pathlib.Path) -> None:
    """The five pieces of the worked example and how a step turns them into tensors."""
    W, H = 1200, 660
    MARGIN = 24
    CARD_PAD = 14
    CONTINUATION_INDENT = 22             # continuation lines of a USD list, about three monospace characters
    # row 1: the three prims authored in the scene
    HEAD1_Y = 34
    ROW1_Y, CARD_H = 50, 172
    LIDAR_X, LIDAR_W = MARGIN, 382
    PRODUCT_X, PRODUCT_W, PRODUCT_H = 502, 282, 88
    PRODUCT_Y = ROW1_Y + (CARD_H - PRODUCT_H) / 2
    VAR_X, VAR_W = 914, 254
    REL_LABEL_DY = 8
    # connectors between the rows
    Y_MID = 272
    ELBOW_LABEL_Y = 264
    ELBOW1_X = 172                       # where the product connector comes down onto the step pill
    ELBOW2_INSET = 40                    # the RenderVar connector lands this far from the output's right edge
    # row 2: what the program does and gets back
    HEAD2_Y = 330
    STACK_Y, TENSOR_H, TENSOR_GAP, ALWAYS_H = 348, 30, 6, 46   # ALWAYS_H: the two-line Counts and Flags boxes
    PARAMS_GAP, GROUP_PAD = 14, 10
    STEP_X, STEP_W, PILL_H = MARGIN, 170, 44
    RESULT_X, RESULT_W, DATA_H = 258, 116, 56
    FRAME_X, FRAME_W = 438, 80
    OUTPUT_X, OUTPUT_W, OUTPUT_H = 582, 236, 72
    MAP_X, MAP_W = 882, 70
    GROUP_X, GROUP_W = 1016, 160
    TENSOR_X, TENSOR_W = GROUP_X + GROUP_PAD, GROUP_W - 2 * GROUP_PAD
    OUTPUT_TITLE_DY, OUTPUT_NOTE_DY, OUTPUT_PATH_DY = 24, 43, 61   # baselines inside the output card
    ALWAYS_LABEL_DY, ALWAYS_NOTE_DY = -5, 14                    # baselines around a two-line box centre
    ALWAYS_NOTE = "always delivered"                            # Counts and Flags come with every PointCloud output
    ARROW_LABEL_DY = 8
    LEGEND_Y = 630

    c = dl.Canvas(
        W, H, "The pieces of the worked lidar example",
        "The lidar prim, the RenderProduct pointing at it through rel camera and at the PointCloud "
        "RenderVar through rel orderedVars, and the step result leading to the mapped channel "
        "tensors and params")

    # --- row 1: authored in the scene
    dl.text(c, MARGIN, HEAD1_Y, "Authored in the scene", 13, "bold", fill=dl.GREY)
    lidar = _card(
        c, LIDAR_X, ROW1_Y, LIDAR_W, CARD_H, CARD_PAD, "Sensor prim", "/World/Lidar",
        "where the sensor is and how it behaves",
        [("OmniLidar + OmniSensorGenericLidarCoreAPI", dl.M, dl.DK),
         ("selects the Lidar generic core model", dl.F, dl.GREY),
         ('omni:sensor:Core:elementsCoordsType = "CARTESIAN"', dl.M, dl.DK),
         ("omni:sensor:Core:includeInvalidPoints = false", dl.M, dl.DK),
         ("omni:sensor:frameRate = (10, 1)", dl.M, dl.DK)])
    product = _card(
        c, PRODUCT_X, PRODUCT_Y, PRODUCT_W, PRODUCT_H, CARD_PAD, "RenderProduct",
        "/World/Render/Products/LidarProduct", "the request", [])
    var = _card(
        c, VAR_X, ROW1_Y, VAR_W, CARD_H, CARD_PAD, "RenderVar", "/World/Render/Vars/PointCloud",
        "one requested output",
        [('sourceName = "PointCloud"', dl.M, dl.DK),
         ('channels = ["Coordinates",', dl.M, dl.DK),
         ('"Intensity", "Counts",', dl.M, dl.DK, CONTINUATION_INDENT),
         ('"TimeOffsetNs"]', dl.M, dl.DK, CONTINUATION_INDENT)])
    _labelled_arrow(c, product.left, lidar.right, product.cy, "rel camera", label_dy=REL_LABEL_DY,
                    label_family=dl.M)
    _labelled_arrow(c, product.right, var.left, product.cy, "rel orderedVars", label_dy=REL_LABEL_DY,
                    label_family=dl.M)

    # --- row 2: in the program
    dl.text(c, MARGIN, HEAD2_Y, "In your program", 13, "bold", fill=dl.GREY)
    tensor_stack_h = 3 * TENSOR_H + 2 * ALWAYS_H + 4 * TENSOR_GAP
    chain_cy = STACK_Y + tensor_stack_h / 2
    step = _pill(c, STEP_X, chain_cy - PILL_H / 2, STEP_W, PILL_H, "step(product path)")
    result = dl.box(c, RESULT_X, chain_cy - DATA_H / 2, RESULT_W, DATA_H, "result",
                    sublabel="one per product", sublabel_size=12)
    frame = dl.box(c, FRAME_X, chain_cy - DATA_H / 2, FRAME_W, DATA_H, "frame")
    output = dl.box(c, OUTPUT_X, chain_cy - OUTPUT_H / 2, OUTPUT_W, OUTPUT_H)
    _fits("render var output", 14, OUTPUT_W - 16, "bold")
    _fits("keyed by the RenderVar path", 12, OUTPUT_W - 16)
    _fits("/World/Render/Vars/PointCloud", 12, OUTPUT_W - 16, family=dl.M)
    dl.text(c, output.cx, output.top + OUTPUT_TITLE_DY, "render var output", 14, "bold", anchor="middle")
    dl.text(c, output.cx, output.top + OUTPUT_NOTE_DY, "keyed by the RenderVar path", 12, anchor="middle",
            fill=dl.GREY)
    dl.text(c, output.cx, output.top + OUTPUT_PATH_DY, "/World/Render/Vars/PointCloud", 12, anchor="middle",
            family=dl.M)
    mapped = _pill(c, MAP_X, chain_cy - PILL_H / 2, MAP_W, PILL_H, "map")

    # the mapped output: the channels produced only because the RenderVar listed them, then Counts
    # and Flags, which every PointCloud output carries whether or not the RenderVar lists them (the
    # example lists Counts and not Flags), and the params
    group_h = tensor_stack_h + PARAMS_GAP + TENSOR_H + 2 * GROUP_PAD
    group = dl.box(c, GROUP_X, STACK_Y - GROUP_PAD, GROUP_W, group_h, fill="none", stroke=dl.FAINT,
                   rx=8, stroke_width=1.5, dashed=True)
    ty = STACK_Y
    for name in ("Coordinates", "Intensity", "TimeOffsetNs"):
        dl.box(c, TENSOR_X, ty, TENSOR_W, TENSOR_H, name, fill=dl.GREEN, rx=5, label_size=13,
               label_weight="normal", label_family=dl.M)
        ty += TENSOR_H + TENSOR_GAP
    _fits(ALWAYS_NOTE, 12, TENSOR_W - 16)
    for name in ("Counts", "Flags"):
        always = dl.box(c, TENSOR_X, ty, TENSOR_W, ALWAYS_H, fill=dl.ORANGE, rx=5)
        dl.text(c, always.cx, always.cy + ALWAYS_LABEL_DY, name, 13, anchor="middle", fill=dl.WHITE,
                family=dl.M)
        dl.text(c, always.cx, always.cy + ALWAYS_NOTE_DY, ALWAYS_NOTE, 12, anchor="middle", fill=dl.WHITE)
        ty += ALWAYS_H + TENSOR_GAP
    ty += PARAMS_GAP - TENSOR_GAP                     # the params box sits PARAMS_GAP below the stack
    dl.box(c, TENSOR_X, ty, TENSOR_W, TENSOR_H, "params", fill=dl.PANEL, stroke=dl.FAINT, rx=5,
           stroke_width=1.5, label_size=13, label_weight="normal", label_family=dl.M)

    _labelled_arrow(c, step.right, result.left, chain_cy, "returns", label_dy=ARROW_LABEL_DY)
    _labelled_arrow(c, result.right, frame.left, chain_cy, "holds", label_dy=ARROW_LABEL_DY)
    _labelled_arrow(c, frame.right, output.left, chain_cy, "holds", label_dy=ARROW_LABEL_DY)
    _labelled_arrow(c, output.right, mapped.left, chain_cy, None)
    _labelled_arrow(c, mapped.right, group.left, chain_cy, "exposes", label_dy=ARROW_LABEL_DY)

    # --- the rows meet: the product is what you step, the RenderVar path is where you find the output
    _elbow(c, product.cx, product.bottom, ELBOW1_X, step.top, Y_MID, dl.GREY)
    dl.text(c, (product.cx + ELBOW1_X) / 2, ELBOW_LABEL_Y, "stepped by its path", 12, anchor="middle",
            fill=dl.GREY)
    elbow2_x = output.right - ELBOW2_INSET
    _elbow(c, var.cx, var.bottom, elbow2_x, output.top, Y_MID, dl.GREY, dashed=True)
    dl.text(c, (var.cx + elbow2_x) / 2, ELBOW_LABEL_Y, "found under its path", 12, anchor="middle",
            fill=dl.GREY)

    dl.legend(c, MARGIN, LEGEND_Y, [("produced only when listed", dl.GREEN),
                                    ("delivered whether or not listed", dl.ORANGE),
                                    ("a call in your program", dl.BLUE)])
    dl.validate(c)
    dl.write_svg(out_dir / "first_sensor_pieces.svg", c.render())


# -------------------------------------------------------------- first_sensor_scene_top_view ---
def first_sensor_scene_top_view(out_dir: pathlib.Path) -> None:
    """The example scene from above: whole ground plane at left, the sensor and the cube at right."""
    W, H = 960, 500
    MARGIN = 24
    HEAD_Y = 34
    # left panel: the whole ground plane, 400 m on a side
    OV_X, OV_Y, OV_SIDE = MARGIN, 70, 320
    OV_PX_PER_M = OV_SIDE / 400.0
    OV_CX, OV_CY = OV_X + OV_SIDE / 2, OV_Y + OV_SIDE / 2
    OV_LABEL_Y, OV_LABEL_LH, OV_NOTE_Y, OV_CORNER_PAD, OV_CORNER_TOP_DY = 112, 17, 362, 8, 18
    DOT_R = 2.5
    # right panel: the detail around the sensor, 30 px per meter
    ZM_X, ZM_Y, ZM_W, ZM_H = 420, 50, 510, 360
    S = 30.0
    X_MIN, Y_MAX = -3.0, 6.0                      # scene meters at the panel's left and top edges
    PLANE_LABEL_DX, PLANE_LABEL_DY = 60, 20
    LIDAR_R, VIEW_LEN_M, VIEW_W, SYMBOL_GAP = 8, 1.5, 2.5, 2      # SYMBOL_GAP: air between a symbol and its lines
    CUBE_SIDE_M, CUBE_X_M, CUBE_Z_M = 1.5, 10.0, 0.75
    LIDAR_LABEL_X, LIDAR_LABEL_Y1, LIDAR_LABEL_Y2 = 452, 196, 213
    CUBE_LABEL_Y1, CUBE_LABEL_Y2 = 180, 197
    DIM_Y_M, DIM_EXT_OVER, DIM_LABEL_DY = -2.5, 7, 7
    TICK, TICK_LABEL_SIZE = 6, 12
    Y_TICK_LABEL_DX, Y_TICK_LABEL_DY = 11, 4.3   # Y labels sit inside the panel, right of the axis
    Y_AXIS_TITLE_Y = 62
    X_AXIS_TITLE_Y = 450
    LEGEND_Y, NOTE_GAP, NOTE_BASELINE_DY = 468, 30, 4.3        # the note's baseline sits on the legend's centre line

    def px(x_m: float) -> float:
        return ZM_X + (x_m - X_MIN) * S

    def py(y_m: float) -> float:
        return ZM_Y + (Y_MAX - y_m) * S

    c = dl.Canvas(
        W, H, "The example scene from above",
        "Top view of the example scene: the lidar at the origin looking along +X, the cube ten "
        "meters ahead, the ground plane extending 200 meters in every direction")

    # --- left: the whole plane
    dl.text(c, OV_X, HEAD_Y, "Whole ground plane, 400 m by 400 m", 13, "bold", fill=dl.GREY)
    dl.box(c, OV_X, OV_Y, OV_SIDE, OV_SIDE, fill=dl.PANEL, stroke=dl.FAINT, rx=2, stroke_width=1.5)
    _fits("-200 m to 200 m in X and Y", 12, OV_SIDE - 2 * OV_CORNER_PAD)
    dl.text(c, OV_CX, OV_LABEL_Y, "asphalt ground plane", 12, anchor="middle", fill=dl.GREY)
    dl.text(c, OV_CX, OV_LABEL_Y + OV_LABEL_LH, "-200 m to 200 m in X and Y", 12, anchor="middle", fill=dl.GREY)
    dl.text(c, OV_X + OV_CORNER_PAD, OV_Y + OV_SIDE - OV_CORNER_PAD, "(-200, -200)", 12, fill=dl.GREY,
            family=dl.M)
    dl.text(c, OV_X + OV_SIDE - OV_CORNER_PAD, OV_Y + OV_CORNER_TOP_DY, "(200, 200)", 12, anchor="end", fill=dl.GREY,
            family=dl.M)
    # the detail frame, at the plane's scale, and the guide lines to the detail panel
    fx0, fx1 = OV_CX + X_MIN * OV_PX_PER_M, OV_CX + (X_MIN + ZM_W / S) * OV_PX_PER_M
    fy0, fy1 = OV_CY - Y_MAX * OV_PX_PER_M, OV_CY + (ZM_H / S - Y_MAX) * OV_PX_PER_M
    c.add(f'<rect x="{dl.fmt(fx0)}" y="{dl.fmt(fy0)}" width="{dl.fmt(fx1 - fx0)}" '
          f'height="{dl.fmt(fy1 - fy0)}" fill="none" stroke="{dl.BLUE}" stroke-width="1.5"/>')
    c.add(f'<circle cx="{dl.fmt(OV_CX)}" cy="{dl.fmt(OV_CY)}" r="{dl.fmt(DOT_R)}" fill="{dl.GREEN}"/>')
    _line(c, fx1, fy0, ZM_X, ZM_Y, dl.MUTED, 1, dashed=True)
    _line(c, fx1, fy1, ZM_X, ZM_Y + ZM_H, dl.MUTED, 1, dashed=True)
    dl.text(c, OV_X + OV_CORNER_PAD, OV_NOTE_Y, "sensor and cube at the center: detail at right", 12,
            fill=dl.GREY)

    # --- right: the detail around the sensor
    dl.text(c, ZM_X, HEAD_Y, "Detail around the sensor", 13, "bold", fill=dl.GREY)
    dl.box(c, ZM_X, ZM_Y, ZM_W, ZM_H, fill=dl.PANEL, stroke=dl.FAINT, rx=0, stroke_width=1.5)
    dl.text(c, ZM_X + PLANE_LABEL_DX, ZM_Y + PLANE_LABEL_DY, "asphalt ground plane", 12, fill=dl.GREY)
    # axes in meters: X to the right, Y up
    dl.tick_marks(c, ZM_X, ZM_Y + ZM_H, ZM_W, [px(0) - ZM_X, px(5) - ZM_X, px(10) - ZM_X],
                  ["0", "5", "10"], tick=TICK, size=TICK_LABEL_SIZE)
    for y_m, label in ((5, "5"), (0, "0"), (-5, "-5")):   # Y ticks point into the panel, labels beside them
        _line(c, ZM_X, py(y_m), ZM_X + TICK, py(y_m), dl.GREY, 1.5)
        dl.text(c, ZM_X + Y_TICK_LABEL_DX, py(y_m) + Y_TICK_LABEL_DY, label, TICK_LABEL_SIZE, fill=dl.GREY)
    dl.text(c, ZM_X + ZM_W / 2, X_AXIS_TITLE_Y, "X (m)", 12, anchor="middle", fill=dl.GREY)
    dl.text(c, ZM_X + Y_TICK_LABEL_DX, Y_AXIS_TITLE_Y, "Y (m)", 12, fill=dl.GREY)
    # the cube, 1.5 m on a side, centred ten meters ahead
    cube_px = CUBE_SIDE_M * S
    c.add(f'<rect x="{dl.fmt(px(CUBE_X_M) - cube_px / 2)}" y="{dl.fmt(py(0) - cube_px / 2)}" '
          f'width="{dl.fmt(cube_px)}" height="{dl.fmt(cube_px)}" fill="{dl.MUTED}" stroke="{dl.DK}" '
          f'stroke-width="1.5"/>')
    dl.text(c, px(CUBE_X_M), CUBE_LABEL_Y1, "concrete cube, 1.5 m,", 12.5, anchor="middle")
    dl.text(c, px(CUBE_X_M), CUBE_LABEL_Y2, f"at ({dl.fmt(CUBE_X_M)}, 0, {dl.fmt(CUBE_Z_M)})", 12.5,
            anchor="middle")
    # the lidar at the origin, one meter up, looking along +X
    c.add(f'<circle cx="{dl.fmt(px(0))}" cy="{dl.fmt(py(0))}" r="{dl.fmt(LIDAR_R)}" fill="{dl.GREEN}"/>')
    dl.arrow(c, px(0) + LIDAR_R + SYMBOL_GAP, py(0), px(VIEW_LEN_M), py(0), dl.BLUE, VIEW_W)
    dl.text(c, LIDAR_LABEL_X, LIDAR_LABEL_Y1, "OmniLidar at (0, 0, 1)", 12.5, "bold")
    dl.text(c, LIDAR_LABEL_X, LIDAR_LABEL_Y2, "looks along +X, 1 m above the plane", 12.5)
    # the 10 m between the sensor and the cube's center
    dim_y = py(DIM_Y_M)
    _line(c, px(0), py(0) + LIDAR_R + SYMBOL_GAP, px(0), dim_y + DIM_EXT_OVER, dl.GREY, 1)
    _line(c, px(CUBE_X_M), py(0) + cube_px / 2 + SYMBOL_GAP, px(CUBE_X_M), dim_y + DIM_EXT_OVER, dl.GREY, 1)
    dim_mid = (px(0) + px(CUBE_X_M)) / 2
    dl.arrow(c, dim_mid, dim_y, px(0), dim_y, dl.GREY, 1.5)
    dl.arrow(c, dim_mid, dim_y, px(CUBE_X_M), dim_y, dl.GREY, 1.5)
    dl.text(c, dim_mid, dim_y - DIM_LABEL_DY, "10 m", 13, "bold", anchor="middle")

    lg = dl.legend(c, MARGIN, LEGEND_Y, [("lidar", dl.GREEN), ("looks along +X", dl.BLUE, "line"),
                                         ("concrete cube", dl.MUTED)])
    dl.text(c, lg.right + NOTE_GAP, lg.cy + NOTE_BASELINE_DY, "the Z-up scene seen from above: +X to the right, +Y up",
            12, fill=dl.GREY)
    dl.validate(c)
    dl.write_svg(out_dir / "first_sensor_scene_top_view.svg", c.render())


# -------------------------------------------------------------------------------- entry point ---
def generate(out_dir: pathlib.Path) -> None:
    first_sensor_pieces(out_dir)
    first_sensor_scene_top_view(out_dir)


if __name__ == "__main__":
    generate(dl.output_dir(__file__))
