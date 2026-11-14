#!/usr/bin/env python3
"""Figures of the ``sensors/common`` pages: materials, runtime updates and validation.

Run through ``generate_diagrams.py`` beside this file, or on its own to regenerate
only this group::

    python3 -B _gen_common_a.py             # in place
    python3 -B _gen_common_a.py /tmp/check  # elsewhere, to diff against the committed files
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import _diagram_lib as dl  # noqa: E402


# ------------------------------------------------------------------------------ small helpers ---
def _lines(c, x, y, lines, size, fill, family=dl.F, anchor="start", weight="normal", lh=None):
    """Draw ``lines`` one under the other; ``y`` is the first baseline. Returns the last baseline."""
    step = lh if lh is not None else round(size * 1.45, 2)
    for i, ln in enumerate(lines):
        dl.text(c, x, y + i * step, ln, size, weight, anchor, fill, family)
    return y + (len(lines) - 1) * step


def _bracket(c, x0, x1, y, label, size=12, fill=dl.DK, tick=6, stroke=dl.GREY):
    """A horizontal range bracket from ``x0`` to ``x1`` at ``y`` (ticks up) with a centred label below."""
    sw = f'stroke="{stroke}" stroke-width="1.5"'
    c.add(f'<line x1="{dl.fmt(x0)}" y1="{dl.fmt(y)}" x2="{dl.fmt(x1)}" y2="{dl.fmt(y)}" {sw}/>')
    for x in (x0, x1):
        c.add(f'<line x1="{dl.fmt(x)}" y1="{dl.fmt(y)}" x2="{dl.fmt(x)}" y2="{dl.fmt(y - tick)}" {sw}/>')
    dl.text(c, (x0 + x1) / 2, y + 6 + size, label, size, "normal", "middle", fill)


def _vline(c, x, y0, y1, stroke, width=2, dashed=False):
    attrs = (f'x1="{dl.fmt(x)}" y1="{dl.fmt(y0)}" x2="{dl.fmt(x)}" y2="{dl.fmt(y1)}" '
             f'stroke="{stroke}" stroke-width="{dl.fmt(width)}"')
    if dashed:
        attrs += f' stroke-dasharray="{dl.fmt(3 * width)} {dl.fmt(2 * width)}"'
    c.add(f"<line {attrs}/>")


def _tag(c, x, cy, label, color, size=11.5):
    """A small outlined tag (white fill, colored border and text) whose left edge is at ``x``."""
    w = dl.text_width(label, size, "bold") + 22      # 16 px of box padding plus 6 px of air
    h = size + 8
    dl.box(c, x, cy - h / 2, w, h, label, fill=dl.WHITE, stroke=color, rx=3, label_size=size,
           label_fill=color, stroke_width=1.5)
    return dl.Rect(x, cy - h / 2, w, h)


def _elbow(c, x0, y0, xe, x1, y1, color, width=2):
    """A dashed two-corner link: right from (x0, y0) to ``xe``, vertical to ``y1``, right to (x1, y1).

    The arrowhead tip lands on (x1, y1); the last run is shortened by the head length the
    library uses (5.5 line widths), as :func:`_diagram_lib.arrow` does.
    """
    hl = 5.5 * width
    d = (f"M{dl.fmt(x0)},{dl.fmt(y0)} L{dl.fmt(xe)},{dl.fmt(y0)} L{dl.fmt(xe)},{dl.fmt(y1)} "
         f"L{dl.fmt(x1 - hl)},{dl.fmt(y1)}")
    c.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{dl.fmt(width)}" '
          f'stroke-dasharray="{dl.fmt(3 * width)} {dl.fmt(2 * width)}" stroke-linejoin="round" '
          f'marker-end="url(#{c.marker(color, width)})"/>')


# ----------------------------------------------------------------- material_prim_two_systems ---
def material_prim_two_systems(out_dir: pathlib.Path) -> None:
    # columns
    PAD = 32
    MESH_X, MESH_W, MESH_H = PAD, 110, 64
    BIND_GAP = 136                                  # arrow + "material:binding" label
    MAT_X = MESH_X + MESH_W + BIND_GAP              # 278
    MAT_W = 396
    MAT_R = MAT_X + MAT_W                           # 674
    DEST_GAP = 222                                  # arrows + the optional link and its label
    DEST_X = MAT_R + DEST_GAP                       # 896
    DEST_W = 250
    W = DEST_X + DEST_W + PAD                       # 1178
    # rows inside the Material prim frame: the labels on top, the shader network below, so the
    # optional link from the shader network to one lidar model crosses neither path
    MAT_Y = 40
    HDR_Y = MAT_Y + 26                              # "Material prim" baseline
    GRP_X, GRP_W = MAT_X + 14, MAT_W - 28           # inner groups
    LAB_Y, LAB_H = MAT_Y + 44, 112                  # the three attribute rows
    ROW_Y0, ROW_DY = LAB_Y + 52, 24
    GRP_GAP = 50
    SHADER_Y, SHADER_H = LAB_Y + LAB_H + GRP_GAP, 92      # the visual shader network
    SUB_Y, SUB_H = SHADER_Y + 40, 36                   # its sub-box
    MAT_H = SHADER_Y + SHADER_H + 14 - MAT_Y              # 312
    LAB_CY = LAB_Y + LAB_H / 2                      # 140: the non-visual path
    SHADER_CY = SHADER_Y + SHADER_H / 2                      # 292: the visual path
    # destinations: each arrow lands on the header line of its box
    CAP = 0.36                                      # half the cap height, in em
    HDR_DY, SUBHDR_DY = 24, 42                      # header and sub-header baselines below the top
    ENTRY_DY0, ENTRY_DY = 60, 18                    # first entry baseline, entry spacing
    SIZE_HDR, SIZE_SUBHDR, SIZE_ENTRY, SIZE_ROW = 14, 11.5, 13, 13
    NV_Y = round(LAB_CY + CAP * SIZE_HDR - HDR_DY)  # 121
    NV_H = ENTRY_DY0 + 3 * ENTRY_DY + 12            # 126
    VIS_Y = round(SHADER_CY + CAP * SIZE_HDR - HDR_DY) # 273
    VIS_H = ENTRY_DY0 + 1 * ENTRY_DY + 12           # 90
    WPM_CY = NV_Y + ENTRY_DY0 + ENTRY_DY - CAP * SIZE_ENTRY   # centre of the "Lidar generic wpm model" entry
    # the optional link leaves the shader network high on its right edge, turns up at once and
    # runs level into that entry; its label sits inside the corner, well clear of the two paths
    OPT_Y0 = SHADER_Y + 12
    ELBOW_X = MAT_R + 24
    OPT_LBL_R, OPT_LBL_Y, OPT_LBL_DY = DEST_X - 12, WPM_CY + 28, 18
    LEG_Y = VIS_Y + VIS_H + 26
    H = LEG_Y + 14 + PAD

    c = dl.Canvas(W, H, "One UsdShade material, two systems",
                  "One UsdShade material serves two systems. Geometry binds it through material:binding; "
                  "the visual shader network feeds visual rendering, and the three omni:simready:nonvisual "
                  "attributes feed the lidar, radar and acoustic models.")

    # geometry prim and its binding
    mesh = dl.box(c, MESH_X, MAT_Y + MAT_H / 2 - MESH_H / 2, MESH_W, MESH_H, "Mesh",
                  sublabel="geometry prim")
    dl.arrow(c, mesh.right + 6, mesh.cy, MAT_X - 6, mesh.cy, dl.GREY, 2)
    dl.text(c, (mesh.right + MAT_X) / 2, mesh.cy - 10, "material:binding", 12, "normal", "middle",
            dl.DK, dl.M)

    # the Material prim and its two groups
    dl.box(c, MAT_X, MAT_Y, MAT_W, MAT_H, fill=dl.WHITE, stroke=dl.GREY, rx=8)
    dl.text(c, MAT_X + MAT_W / 2, HDR_Y, "UsdShade Material prim", 15, "bold", "middle", dl.DK)
    dl.box(c, GRP_X, LAB_Y, GRP_W, LAB_H, fill=dl.PANEL, stroke=dl.PURPLE, rx=6)
    dl.text(c, GRP_X + GRP_W / 2, LAB_Y + 26, "SimReady non-visual labels", 14, "bold", "middle",
            dl.PURPLE)
    rows = (("omni:simready:nonvisual:base", "token"),
            ("omni:simready:nonvisual:coating", "token"),
            ("omni:simready:nonvisual:attributes", "token[]"))
    for i, (name, typ) in enumerate(rows):
        y = ROW_Y0 + i * ROW_DY
        dl.text(c, GRP_X + 12, y, name, SIZE_ROW, "normal", "start", dl.DK, dl.M)
        dl.text(c, GRP_X + GRP_W - 12, y, typ, SIZE_ROW, "normal", "end", dl.GREY, dl.M)
    dl.box(c, GRP_X, SHADER_Y, GRP_W, SHADER_H, fill=dl.PANEL, stroke=dl.BLUE, rx=6)
    dl.text(c, GRP_X + GRP_W / 2, SHADER_Y + 26, "Visual shader network", 14, "bold", "middle", dl.BLUE)
    dl.box(c, GRP_X + 12, SUB_Y, GRP_W - 24, SUB_H, "surface shader, textures, parameters",
           fill=dl.WHITE, label_size=12, label_weight="normal")

    # destinations
    nv = dl.box(c, DEST_X, NV_Y, DEST_W, NV_H, fill=dl.WHITE, stroke=dl.PURPLE, rx=6)
    dl.text(c, nv.x + 14, nv.y + HDR_DY, "Non-visual sensing", SIZE_HDR, "bold", "start", dl.PURPLE)
    dl.text(c, nv.x + 14, nv.y + SUBHDR_DY, "reads the labels, not the shader", SIZE_SUBHDR, "normal",
            "start", dl.MUTED)
    _lines(c, nv.x + 14, nv.y + ENTRY_DY0,
           ["Lidar generic core model", "Lidar generic wpm model", "Radar generic wpmDmat model",
            "Acoustic generic wpm model"], SIZE_ENTRY, dl.DK, lh=ENTRY_DY)
    vis = dl.box(c, DEST_X, VIS_Y, DEST_W, VIS_H, fill=dl.WHITE, stroke=dl.BLUE, rx=6)
    dl.text(c, vis.x + 14, vis.y + HDR_DY, "Visual rendering", SIZE_HDR, "bold", "start", dl.BLUE)
    dl.text(c, vis.x + 14, vis.y + SUBHDR_DY, "reads the shader network", SIZE_SUBHDR, "normal",
            "start", dl.MUTED)
    _lines(c, vis.x + 14, vis.y + ENTRY_DY0, ["cameras", "Visual Sensors"], SIZE_ENTRY,
           dl.DK, lh=ENTRY_DY)

    # the two independent paths
    dl.arrow(c, MAT_R + 6, LAB_CY, DEST_X - 6, LAB_CY, dl.PURPLE, 2)
    dl.arrow(c, MAT_R + 6, SHADER_CY, DEST_X - 6, SHADER_CY, dl.BLUE, 2)
    # the one optional cross-link
    _elbow(c, MAT_R + 6, OPT_Y0, ELBOW_X, DEST_X - 6, WPM_CY, dl.ORANGE, 2)
    dl.text(c, OPT_LBL_R, OPT_LBL_Y, "optional, off by default:", 12, "normal", "end", dl.ORANGE)
    dl.text(c, OPT_LBL_R, OPT_LBL_Y + OPT_LBL_DY, "useVisualMaterialInputs", 12, "normal", "end",
            dl.ORANGE, dl.M)

    dl.legend(c, MAT_X, LEG_Y, [("non-visual path", dl.PURPLE, "line"),
                                ("visual path", dl.BLUE, "line"),
                                ("optional: the Lidar generic wpm model may also read the visual material",
                                 dl.ORANGE, "dashed")])
    dl.validate(c)
    dl.write_svg(out_dir / "material_prim_two_systems.svg", c.render())


# ------------------------------------------------------------------- runtime_update_timeline ---
def runtime_update_timeline(out_dir: pathlib.Path) -> None:
    PAD = 32
    LANE_LABEL_W = 128
    N_FRAMES = 6                                    # frame n-1 ... frame n+4
    FRAME_W, FRAME_GAP, INSET = 144, 6, 10
    ROW_W = N_FRAMES * FRAME_W + (N_FRAMES - 1) * FRAME_GAP
    LANE_W = LANE_LABEL_W + ROW_W + 2 * INSET
    W = PAD + LANE_W + PAD                          # 1106
    LANE_H = 84
    FR_H = LANE_H - 2 * INSET
    LANE1_Y = 56
    ANN1_Y = LANE1_Y + LANE_H + 8                   # annotation zone under lane 1
    LANE2_Y = 226
    ANN2_Y = LANE2_Y + LANE_H + 8
    MARK_LBL_DY = 10                                # marker label baseline above the lane top
    MARK_OVER = 6                                   # marker line overshoot above and below the lane
    EDIT_AT = 0.24                                  # the edit lands this far into frame n
    FIX_AT = 0.84                                   # the correction lands this far into frame n+2
    AXIS_Y = 384
    LEG_Y = 414
    H = LEG_Y + 14 + PAD
    FRAME_NAMES = ["frame n-1", "frame n", "frame n+1", "frame n+2", "frame n+3", "frame n+4"]
    LANE1_FILL = [dl.BLUE, dl.BLUE, dl.GREEN, dl.GREEN, dl.GREEN, dl.GREEN]
    LANE2_FILL = [dl.BLUE, dl.BLUE, dl.BLUE, dl.BLUE, dl.GREEN, dl.GREEN]

    c = dl.Canvas(W, H, "A parameter edit on a running sensor",
                  "How an edit lands on a running sensor. The frame in flight finishes with its "
                  "starting values; the next frame built after the edit uses the new ones. A refused "
                  "batch changes nothing, and every later frame stays on the accepted configuration "
                  "until the offending value is corrected.")

    def frame_x(i: int) -> float:
        return PAD + LANE_LABEL_W + INSET + i * (FRAME_W + FRAME_GAP)

    def draw_lane(y: float, label: str, fills) -> None:
        dl.lane(c, PAD, y, LANE_W, LANE_H, label, label_width=LANE_LABEL_W)
        for i, name in enumerate(FRAME_NAMES):
            dl.box(c, frame_x(i), y + INSET, FRAME_W, FR_H, name, fill=fills[i], label_size=13)

    draw_lane(LANE1_Y, "edit applied", LANE1_FILL)
    draw_lane(LANE2_Y, "batch refused", LANE2_FILL)

    # lane 1: the edit lands inside frame n
    mx = frame_x(1) + EDIT_AT * FRAME_W
    _vline(c, mx, LANE1_Y - MARK_OVER, LANE1_Y + LANE_H + MARK_OVER, dl.DK, 2.5)
    dl.text(c, mx + 7, LANE1_Y - MARK_LBL_DY, "edit at t", 12, "normal", "start", dl.DK)
    fx1 = frame_x(1)
    _lines(c, fx1 + FRAME_W / 2, ANN1_Y + 12,
           dl.wrap_text("in flight: finishes with its starting values", FRAME_W - 4, 12),
           12, dl.DK, anchor="middle", lh=17)
    _bracket(c, frame_x(2) + 4, frame_x(5) + FRAME_W - 4, ANN1_Y + 4,
             "new values: every frame built after the edit")

    # lane 2: the batch is refused at the same instant; the value is corrected inside frame n+2
    _vline(c, mx, LANE2_Y - MARK_OVER, LANE2_Y + LANE_H + MARK_OVER, dl.RED, 2.5, dashed=True)
    tb = dl.text(c, mx + 7, LANE2_Y - MARK_LBL_DY, "refused batch at t", 12, "normal", "start", dl.DK)
    _tag(c, tb.x1 + 10, LANE2_Y - MARK_LBL_DY - 0.36 * 12, "error logged", dl.RED)
    cx = frame_x(3) + FIX_AT * FRAME_W
    _vline(c, cx, LANE2_Y - MARK_OVER, LANE2_Y + LANE_H + MARK_OVER, dl.DK, 2.5)
    dl.text(c, cx + 7, LANE2_Y - MARK_LBL_DY, "value corrected", 12, "normal", "start", dl.DK)
    _bracket(c, frame_x(1) + 4, frame_x(3) + FRAME_W - 4, ANN2_Y + 4,
             "accepted configuration kept: the refused batch changed nothing")
    _bracket(c, frame_x(4) + 4, frame_x(5) + FRAME_W - 4, ANN2_Y + 4, "new values")

    # one time axis under both lanes
    ax0 = frame_x(0)
    ax_len = ROW_W + 20
    dl.arrow(c, ax0 - 10, AXIS_Y, ax0 + ax_len, AXIS_Y, dl.GREY, 1.5)
    dl.tick_marks(c, ax0, AXIS_Y, ROW_W, [i * (FRAME_W + FRAME_GAP) for i in range(N_FRAMES)]
                  + [ROW_W], axis=False)
    dl.tick_marks(c, ax0, AXIS_Y, ROW_W, [mx - ax0], ["t"], axis=False, tick=9, width=2, fill=dl.DK)
    dl.text(c, ax0 + ax_len, AXIS_Y + 9 + 12, "time", 12, "normal", "end", dl.GREY)

    dl.legend(c, PAD, LEG_Y, [("values before the edit", dl.BLUE), ("new values", dl.GREEN),
                              ("edit or correction", dl.DK, "line"),
                              ("refused batch", dl.RED, "dashed")])
    dl.validate(c)
    dl.write_svg(out_dir / "runtime_update_timeline.svg", c.render())


# ---------------------------------------------------------------------------- validation_flow ---
def validation_flow(out_dir: pathlib.Path) -> None:
    PAD = 32
    IN_X, IN_W, IN_H, IN_GAP = PAD, 240, 52, 14
    IN_HDR_Y = 44                                   # column header baseline
    IN_Y0 = 58
    IN_CY = IN_Y0 + (3 * IN_H + 2 * IN_GAP) / 2     # 150
    UT_X = IN_X + IN_W + 54                         # 326
    UT_W = 340
    UT_R = UT_X + UT_W                              # 666
    RULES_H = 110
    UT_H = 62 + RULES_H + 14                        # 186
    UT_Y = IN_CY - UT_H / 2                         # 57
    RULES_Y = UT_Y + 62
    NOTE_Y, NOTE_H = UT_Y + UT_H + 20, 50
    TRUNK_X1 = UT_R + 92                            # the fork point
    FORK_LBL_X, FORK_LBL_Y = UT_R + 10, IN_CY - 10
    OUT_X, OUT_W = UT_R + 240, 250                  # 906
    W = OUT_X + OUT_W + PAD                         # 1188
    VG_Y = 36                                       # frame around what a valid check hands back
    VG_HDR_Y = VG_Y + 16
    A_Y, A_H = VG_Y + 26, 52
    B_Y, B_H = A_Y + A_H + 10, 84
    VG_H = B_Y + B_H + 10 - VG_Y
    VG_CY = VG_Y + VG_H / 2
    INV_Y, INV_H = 248, 52
    INV_CY = INV_Y + INV_H / 2
    VALID_LBL_CX, VALID_LBL_Y = TRUNK_X1 + 61, 120
    INVALID_LBL_CX, INVALID_LBL_Y = TRUNK_X1 + 10, 268
    LEG_Y = 336
    H = LEG_Y + 14 + PAD

    c = dl.Canvas(W, H, "One validation check, end to end",
                  "A sensor definition enters the sensor introspection utility, which was initialized "
                  "for one model. The utility applies the model's own validation rules and "
                  "returns either no error, after which the validated parameters and the scheduler "
                  "information can be read, or a reason string.")

    # what you give it: one of three forms
    dl.text(c, IN_X, IN_HDR_Y, "the definition, in one of three forms", 12, "normal", "start", dl.GREY)
    inputs = (("parameter set", "names, types, vector lengths, values"),
              ("USD file + prim path", "the layer's file and the prim's path"),
              ("opened Usd.Prim", "Python; a UsdPrim address in C++"))
    for i, (label, sub) in enumerate(inputs):
        r = dl.box(c, IN_X, IN_Y0 + i * (IN_H + IN_GAP), IN_W, IN_H, label, sublabel=sub, label_size=13,
                   sublabel_size=12)
        dl.arrow(c, r.right + 6, r.cy, UT_X - 6, r.cy, dl.BLUE, 2)

    # the utility, initialized for one model, with that model's rules inside
    dl.box(c, UT_X, UT_Y, UT_W, UT_H, fill=dl.WHITE, stroke=dl.GREY, rx=8)
    dl.text(c, UT_X + UT_W / 2, UT_Y + 26, "sensor introspection utility", 15, "bold", "middle", dl.DK)
    dl.text(c, UT_X + UT_W / 2, UT_Y + 46, "init(ModelInfo)", 12, "normal", "middle",
            dl.GREY, dl.M)
    dl.box(c, UT_X + 14, RULES_Y, UT_W - 28, RULES_H, fill=dl.PANEL)
    dl.text(c, UT_X + UT_W / 2, RULES_Y + 24, "the model's own validation rules", 13, "bold", "middle",
            dl.DK)
    dl.text(c, UT_X + UT_W / 2, RULES_Y + 44, "one library per model, chosen by modelName:", 12,
            "normal", "middle", dl.DK)
    dl.text(c, UT_X + UT_W / 2, RULES_Y + 62, "lidar.core, lidar.wpm,", 12, "normal", "middle", dl.DK,
            dl.M)
    dl.text(c, UT_X + UT_W / 2, RULES_Y + 80, "radar.dmatapprox, acoustic", 12, "normal", "middle",
            dl.DK, dl.M)
    dl.text(c, UT_X + UT_W / 2, RULES_Y + 98, "the camera models have no check", 12, "normal",
            "middle", dl.MUTED)
    # the same rules in the renderer
    _vline(c, UT_X + UT_W / 2, UT_Y + UT_H, NOTE_Y, dl.GREY, 1.5, dashed=True)
    dl.box(c, UT_X, NOTE_Y, UT_W, NOTE_H, fill=dl.WHITE, stroke=dl.GREY, rx=6, stroke_width=1.5,
           dashed=True)
    _lines(c, UT_X + UT_W / 2, NOTE_Y + 21,
           dl.wrap_text("the renderer applies the same rules at sensor creation and on a live update",
                        UT_W - 28, 12), 12, dl.GREY, anchor="middle", lh=17)

    # the verdict: a fork into the valid and the invalid outcome
    dl.arrow(c, UT_R + 6, IN_CY, TRUNK_X1, IN_CY, dl.GREY, 2, head=False)
    c.add(f'<circle cx="{dl.fmt(TRUNK_X1)}" cy="{dl.fmt(IN_CY)}" r="4" fill="{dl.GREY}"/>')
    dl.text(c, FORK_LBL_X, FORK_LBL_Y, "validateParams", 12, "normal", "start", dl.DK, dl.M)
    dl.connector(c, TRUNK_X1, IN_CY, OUT_X - 6, VG_CY, dl.GREEN, 2)
    dl.connector(c, TRUNK_X1, IN_CY, OUT_X - 6, INV_CY, dl.RED, 2)
    dl.text(c, VALID_LBL_CX, VALID_LBL_Y, "valid: None / nullptr", 12, "normal", "middle", dl.GREEN,
            dl.M)
    dl.text(c, INVALID_LBL_CX, INVALID_LBL_Y, "invalid: reason string", 12, "normal", "middle", dl.RED,
            dl.M)

    # what comes back after a valid check
    dl.box(c, OUT_X, VG_Y, OUT_W, VG_H, fill="none", stroke=dl.GREEN, rx=8)
    dl.text(c, OUT_X + 12, VG_HDR_Y, "after a valid check, read back:", 12, "normal", "start", dl.GREEN)
    dl.box(c, OUT_X + 10, A_Y, OUT_W - 20, A_H, "getValidatedParams()",
           sublabel="the accepted parameter set", label_size=13, sublabel_size=12, label_family=dl.M)
    b = dl.box(c, OUT_X + 10, B_Y, OUT_W - 20, B_H, fill=dl.PANEL)
    dl.text(c, b.cx, b.y + 22, "getSchedulerInfo()", 13, "bold", "middle", dl.DK, dl.M)
    _lines(c, b.cx, b.y + 41, ["frameRate, startTime,", "captureDuration, frameLimit,",
                               "partialOutputs, errorString"], 12, dl.GREY, dl.M, anchor="middle",
           lh=16.5)
    # what comes back otherwise
    dl.box(c, OUT_X, INV_Y, OUT_W, INV_H, "reason string", sublabel="why the definition was refused",
           fill=dl.WHITE, stroke=dl.RED, label_size=13, sublabel_size=12)

    dl.legend(c, IN_X, LEG_Y, [("the definition", dl.BLUE, "line"), ("valid", dl.GREEN, "line"),
                               ("invalid", dl.RED, "line")])
    dl.validate(c)
    dl.write_svg(out_dir / "validation_flow.svg", c.render())


# ------------------------------------------------------------------------------------ entry ---
def generate(out_dir: pathlib.Path) -> None:
    material_prim_two_systems(out_dir)
    runtime_update_timeline(out_dir)
    validation_flow(out_dir)


if __name__ == "__main__":
    generate(dl.output_dir(__file__))
