#!/usr/bin/env python3
"""Sensor documentation figures, group ``common_b``: configuration and the output path.

Four diagrams embedded by ``sensors/common/sensor_configuration.rst`` and
``sensors/common/sensor_outputs.rst``:

* ``sensor_prim_schema_model.svg`` -- prim, applied schema, the three attribute
  namespace shapes and the model they select;
* ``prim_orientation_iso8855.svg`` -- the prim's camera-style local axes beside the
  ISO 8855 output frame in a Z-up stage;
* ``output_path.svg`` -- step result, frames, render var outputs and the mapped
  container of tensors and params;
* ``capacity_vs_count.svg`` -- capacity ``Nmax`` versus ``Counts[0]`` and the valid bit.

``generate_diagrams.py`` beside this file imports the module and calls
:func:`generate`; ``python3 -B _gen_common_b.py`` regenerates only this group.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import _diagram_lib as dl  # noqa: E402

fmt = dl.fmt


# ------------------------------------------------------------------------------ local helpers ---
def _hatch(c: dl.Canvas, pid: str = "hatch", color: str = dl.FAINT, spacing: float = 7,
           width: float = 1.5) -> str:
    """Define a diagonal hatch pattern and return the ``fill`` value that uses it."""
    c.add(f'<defs><pattern id="{pid}" patternUnits="userSpaceOnUse" width="{fmt(spacing)}" '
          f'height="{fmt(spacing)}" patternTransform="rotate(45)">'
          f'<line x1="0" y1="0" x2="0" y2="{fmt(spacing)}" stroke="{color}" '
          f'stroke-width="{fmt(width)}"/></pattern></defs>')
    return f"url(#{pid})"


def _hbracket(c: dl.Canvas, x1: float, x2: float, y: float, tick: float = 8, toward: int = 1,
              stroke: str = dl.GREY, width: float = 1.5) -> None:
    """A horizontal bracket from ``x1`` to ``x2`` at ``y``; its end ticks point ``toward`` (+1 = down)."""
    d = (f"M{fmt(x1)},{fmt(y + toward * tick)} L{fmt(x1)},{fmt(y)} L{fmt(x2)},{fmt(y)} "
         f"L{fmt(x2)},{fmt(y + toward * tick)}")
    c.add(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{fmt(width)}"/>')


def _vbracket(c: dl.Canvas, x: float, y1: float, y2: float, tick: float = 8, toward: int = -1,
              stroke: str = dl.GREY, width: float = 1.5) -> None:
    """A vertical bracket from ``y1`` to ``y2`` at ``x``; its end ticks point ``toward`` (-1 = left)."""
    d = (f"M{fmt(x + toward * tick)},{fmt(y1)} L{fmt(x)},{fmt(y1)} L{fmt(x)},{fmt(y2)} "
         f"L{fmt(x + toward * tick)},{fmt(y2)}")
    c.add(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{fmt(width)}"/>')


def _polygon(c: dl.Canvas, pts, fill: str, stroke: str = "none", width: float = 1.2) -> None:
    p = " ".join(f"{fmt(x)},{fmt(y)}" for x, y in pts)
    attrs = f'points="{p}" fill="{fill}"'
    if stroke != "none":
        attrs += f' stroke="{stroke}" stroke-width="{fmt(width)}" stroke-linejoin="round"'
    c.add(f"<polygon {attrs}/>")


def _hull(pts):
    """Convex hull (monotone chain) of 2-D points; deterministic for a given input."""
    pts = sorted(set((round(x, 3), round(y, 3)) for x, y in pts))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _titled_box(c: dl.Canvas, x, y, w, h, label: str, sub=None, fill=dl.PANEL, stroke="none",
                dashed=False, label_size=12, sub_size=11, label_fill=None, sub_fill=dl.GREY,
                label_family=dl.M, label_weight="normal", rx=6, stroke_width=1.5) -> dl.Rect:
    """A box with a (mono) label and a proportional sublabel; both centered."""
    r = dl.box(c, x, y, w, h, fill=fill, stroke=stroke, rx=rx, dashed=dashed, stroke_width=stroke_width)
    fg = label_fill or dl.contrast_text(fill)
    if sub is None:
        dl.text(c, r.cx, r.cy + 0.36 * label_size, label, label_size, label_weight, "middle", fg, label_family)
    else:
        dl.text(c, r.cx, r.cy - 5, label, label_size, label_weight, "middle", fg, label_family)
        dl.text(c, r.cx, r.cy + 5 + 0.78 * sub_size, sub, sub_size, "normal", "middle", sub_fill)
    return r


def _header_band(c: dl.Canvas, x, y, w, h, label: str, fill=dl.DK, size=13) -> None:
    """A dark header band with rounded top corners and a centered bold mono label."""
    c.add(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" rx="8" fill="{fill}"/>')
    c.add(f'<rect x="{fmt(x)}" y="{fmt(y + h / 2)}" width="{fmt(w)}" height="{fmt(h / 2)}" fill="{fill}"/>')
    dl.text(c, x + w / 2, y + h / 2 + 0.36 * size, label, size, "bold", "middle", dl.WHITE, dl.M)


# ------------------------------------------------------------- sensor_prim_schema_model.svg ---
def sensor_prim_schema_model(out_dir: pathlib.Path) -> None:
    W = 1120
    SX, SW = 30, 300                      # schema column
    PX, PW = 390, 390                     # typed sensor prim box
    MX, MW = 896, 204                     # model boxes (sublabels stay at 11 px)
    PY = 36                               # prim box top
    HDR_H, TAG_H = 36, 26                 # header band, apiSchemas tag
    PAD, TXT = 14, 10                     # prim inner padding, panel text inset
    G1_Y, G1_H = PY + 82, 82              # omni:sensor:*
    G2_Y, G2_H = PY + 174, 66             # omni:sensor:<Model>:*
    G3_Y, G3_H = PY + 250, 82             # omni:sensor:<Model>:<group>:<instance>:*
    PH = G3_Y + G3_H + PAD - PY           # prim box height
    SB_H = 44                             # schema box height
    MOUNT_Y, MOUNT_H = G3_Y + 12, 38      # first mount instance
    M002_Y, M002_H = G3_Y + 56, 34        # second mount instance (added by you)
    PREP_X = SX + 36                      # x of the vertical "prepends" arrows
    MODEL_Y, MODEL_H = PY + 50, 70
    BR_X = PX + PW + 10                   # bracket joining prim type and applied schema
    DIV_Y = PY + PH + 28                  # rule above the Camera strip
    CY = DIV_Y + 40                       # Camera strip top
    CAM_W, CAM_H, CAM_HDR_H, CAM_TAG_H = 410, 70, 30, 26
    RP_X, RP_W = 470, 250                 # RenderProduct box
    LEG_Y = CY + 128
    H = LEG_Y + 36

    c = dl.Canvas(
        W, H, "Sensor prim, applied schema and model",
        "On a typed sensor prim the prim type and the single-apply OmniSensorGeneric<Model>API schema "
        "select the model. The schema prepends OmniSensorAPI and the first instance of each multiple-apply "
        "schema the model needs, which fill the omni:sensor:*, omni:sensor:<Model>:* and "
        "omni:sensor:<Model>:<group>:<instance>:* attribute namespaces on the prim. On a Camera, the "
        "RenderProduct's requested output enables the model and the schema supplies its parameters.")

    # --- typed sensor prim: header, apiSchemas tag, three attribute groups --------------------
    dl.box(c, PX, PY, PW, PH, fill=dl.PANEL, rx=8)
    _header_band(c, PX, PY, PW, HDR_H, "def OmniLidar / OmniRadar / OmniAcoustic")
    dl.box(c, PX + PAD, PY + 44, PW - 2 * PAD, TAG_H, 'prepend apiSchemas = ["OmniSensorGeneric<Model>API"]',
           fill=dl.WHITE, stroke=dl.FAINT, stroke_width=1, rx=4, label_size=11, label_weight="normal",
           label_family=dl.M)

    def panel(y, h, title, descr, lines):
        r = dl.box(c, PX + PAD, y, PW - 2 * PAD, h, fill=dl.WHITE, stroke=dl.FAINT, stroke_width=1, rx=4)
        tx = r.x + TXT
        dl.text(c, tx, y + 18, title, 12, "bold", fill=dl.DK, family=dl.M)
        dl.text(c, tx, y + 34, descr, 11, fill=dl.GREY)
        for i, (s, fill) in enumerate(lines):
            if s:
                dl.text(c, tx, y + 54 + 16 * i, s, 11, fill=fill, family=dl.M)
        return r

    g1 = panel(G1_Y, G1_H, "omni:sensor:*", "shared by every model: identification and scheduling",
               [("", dl.DK), ("frameRate  startTime  frameLimit", dl.DK)])
    tx = g1.x + TXT
    dl.text(c, tx, G1_Y + 54, "modelName", 11, "bold", fill=dl.GREEN, family=dl.M)
    rest_x = tx + dl.text_width("modelName", 11, "bold", dl.M) + 2 * dl.text_width(" ", 11, "normal", dl.M)
    dl.text(c, rest_x, G1_Y + 54, "modelVendor  marketName  modelVersion", 11, fill=dl.DK, family=dl.M)
    panel(G2_Y, G2_H, "omni:sensor:<Model>:*", "the model's own parameters",
          [("omni:sensor:Core:scanType", dl.DK)])
    panel(G3_Y, G3_H, "omni:sensor:<Model>:<group>:<instance>:*", "multiple-apply instance attributes",
          [("omni:sensor:WpmAcoustic:sensorMount:m001:position", dl.DK),
           ("omni:sensor:WpmAcoustic:sensorMount:m002:position", dl.MUTED)])

    # --- schema column: the applied schema and what it prepends ------------------------------
    shared = _titled_box(c, SX, G1_Y + (G1_H - SB_H) / 2, SW, SB_H, "OmniSensorAPI", "the shared sensor schema")
    generic = _titled_box(c, SX, G2_Y + (G2_H - SB_H) / 2, SW, SB_H, "OmniSensorGeneric<Model>API",
                          "the applied single-apply schema")
    mount = _titled_box(c, SX, MOUNT_Y, SW, MOUNT_H, "OmniSensorWpmAcousticSensorMountAPI:m001",
                        "first instance, prepended for you", label_size=11)
    m002 = _titled_box(c, SX, M002_Y, SW, M002_H, "OmniSensorWpmAcousticSensorMountAPI:m002", "added by you",
                       fill=dl.WHITE, stroke=dl.MUTED, dashed=True, label_size=11, label_fill=dl.MUTED)
    # "prepends": from the applied schema up to the shared schema and down to the instance
    dl.arrow(c, PREP_X, generic.top - 2, PREP_X, shared.bottom + 2, stroke=dl.GREY, width=1.5)
    dl.text(c, PREP_X + 9, (generic.top + shared.bottom) / 2 + 4, "prepends", 11, fill=dl.GREY)
    dl.arrow(c, PREP_X, generic.bottom + 2, PREP_X, mount.top - 2, stroke=dl.GREY, width=1.5)
    dl.text(c, PREP_X + 9, (generic.bottom + mount.top) / 2 + 4, "prepends", 11, fill=dl.GREY)
    # attributes each schema brings onto the prim
    for r, dashed in ((shared, False), (generic, False), (mount, False), (m002, True)):
        dl.arrow(c, r.right + 3, r.cy, PX + PAD, r.cy, stroke=dl.GREY, width=1.5 if dashed else 2, dashed=dashed)

    # --- the model and what selects it --------------------------------------------------------
    model = dl.box(c, MX, MODEL_Y, MW, MODEL_H, "sensor model", fill=dl.GREEN,
                   sublabel="e.g. Lidar generic core model", label_size=14, sublabel_size=11)
    _vbracket(c, BR_X, PY + 6, PY + 44 + TAG_H, tick=6, toward=-1, stroke=dl.GREEN, width=2)
    br_mid = (PY + 6 + PY + 44 + TAG_H) / 2
    dl.arrow(c, BR_X, br_mid, MX - 2, MODEL_Y + 22, stroke=dl.GREEN, width=2.5)
    lx = (BR_X + MX) / 2
    dl.text(c, BR_X + 14, PY + 16, "prim type + applied schema", 11, fill=dl.GREY)
    dl.text(c, lx, PY + 36, "selects", 12, "bold", "middle", dl.GREEN)
    dl.arrow(c, PX + PW + 2, G1_Y + 50, MX - 2, MODEL_Y + MODEL_H - 10, stroke=dl.GREEN, width=1.5)
    dl.text(c, model.cx, model.bottom + 22, "OmniLidar only: modelName", 11, fill=dl.GREEN, anchor="middle")
    dl.text(c, model.cx, model.bottom + 38, "LidarCore / LidarWpm", 11, fill=dl.GREEN, anchor="middle",
            family=dl.M)

    # --- Camera: the request enables the model, the schema supplies parameters -------------------
    c.add(f'<line x1="{fmt(SX)}" y1="{fmt(DIV_Y)}" x2="{fmt(W - 30)}" y2="{fmt(DIV_Y)}" '
          f'stroke="{dl.FAINT}" stroke-width="1"/>')
    dl.text(c, SX, DIV_Y + 22, "On a Camera the request enables the model", 12, "bold", fill=dl.GREY)
    dl.box(c, SX, CY, CAM_W, CAM_H, fill=dl.PANEL, rx=8)
    _header_band(c, SX, CY, CAM_W, CAM_HDR_H, "def Camera")
    dl.box(c, SX + 10, CY + CAM_HDR_H + 7, CAM_W - 20, CAM_TAG_H,
           'prepend apiSchemas = ["OmniSensorGenericCameraCoreAPI"]', fill=dl.WHITE, stroke=dl.FAINT,
           stroke_width=1, rx=4, label_size=11, label_weight="normal", label_family=dl.M)
    rp = dl.box(c, RP_X, CY, RP_W, CAM_H, "RenderProduct", sublabel="orderedVars: a visual model's output",
                label_size=13, sublabel_size=11)
    vis = dl.box(c, MX, CY, MW, CAM_H, "visual model", fill=dl.GREEN,
                 sublabel="e.g. Camera generic core model", label_size=14, sublabel_size=11)
    dl.arrow(c, rp.right + 3, rp.cy, vis.left - 2, vis.cy, stroke=dl.GREEN, width=2.5)
    dl.text(c, (rp.right + vis.left) / 2, rp.cy - 10, "request enables the model", 12, "bold", "middle", dl.GREEN)
    cam_cx = SX + CAM_W / 2
    dl.curve(c, [(cam_cx, CY + CAM_H + 2), (cam_cx, CY + 100), (vis.cx, CY + 100), (vis.cx, vis.bottom + 2)],
             stroke=dl.GREY, width=1.5, dashed=True, smooth=0)
    dl.text(c, (cam_cx + vis.cx) / 2, CY + 115, "supplies parameters", 11, fill=dl.GREY, anchor="middle")

    dl.legend(c, SX, LEG_Y, [("selects or enables the model", dl.GREEN, "line"),
                             ("prepended by the applied schema", dl.GREY, "line"),
                             ("supplies parameters", dl.GREY, "dashed"),
                             ("added by you", dl.MUTED, "outline")], size=11)
    dl.validate(c)
    dl.write_svg(out_dir / "sensor_prim_schema_model.svg", c.render())


# ------------------------------------------------------------- prim_orientation_iso8855.svg ---
def prim_orientation_iso8855(out_dir: pathlib.Path) -> None:
    W, H = 1000, 510
    OX, OY = 420, 340                     # the prim's origin on the canvas
    EX, EY, EZ = (0.52, -0.49), (-0.86, -0.29), (0.0, -0.83)   # world axes on screen (viewed from behind-right-above)
    L_WORLD, L_ISO, L_PRIM = 300, 200, 130
    T_TARGET = 345                        # distance of the target along world +X
    HX, HY, HZ = 22, 34, 18               # sensor box half extents along X, Y, Z
    BARREL_L, BARREL_R = 62, 12           # lens barrel on the forward (+X) face
    CALL_X, CALL_Y, CALL_W, CALL_H = 680, 102, 280, 52
    LEG_Y = 470

    def P(x, y, z):
        return (OX + x * EX[0] + y * EY[0] + z * EZ[0], OY + x * EX[1] + y * EY[1] + z * EZ[1])

    c = dl.Canvas(
        W, H, "Prim orientation and the ISO 8855 output frame",
        "A sensor prim seen from behind in a Z-up stage. Its camera-style local axes after "
        "xformOp:rotateXYZ = (90, 0, -90): local -Z is forward along world +X, local +Y is up along world +Z, "
        "local +X is right along world -Y. The ISO 8855 output frame at the same origin, +X forward "
        "(azimuth 0), +Y left, +Z up, coincides with the world axes. A target straight ahead of the prim is "
        "reported on output +X.")

    # --- world axes, faint ---------------------------------------------------------------------
    for (x, y, z), lbl, anchor, dx, dy in (((L_WORLD, 0, 0), "world +X", "start", 8, 19),
                                           ((0, L_WORLD, 0), "world +Y", "end", -6, -5),
                                           ((0, 0, L_WORLD), "world +Z", "start", 8, 8)):
        tip = P(x, y, z)
        dl.arrow(c, OX, OY, tip[0], tip[1], stroke=dl.FAINT, width=1.5)
        dl.text(c, tip[0] + dx, tip[1] + dy, lbl, 11, fill=dl.MUTED, anchor=anchor)
    ztip = P(0, 0, L_WORLD)
    dl.text(c, ztip[0], ztip[1] - 16, "stage (Z-up)", 11, "bold", "middle", dl.MUTED)

    # --- the sensor prim: lens barrel first (it is further from the viewer), then the box -----
    rim_near = [P(HX, BARREL_R * math.cos(t), BARREL_R * math.sin(t)) for t in
                (2 * math.pi * i / 24 for i in range(24))]
    rim_far = [P(HX + BARREL_L, BARREL_R * math.cos(t), BARREL_R * math.sin(t)) for t in
               (2 * math.pi * i / 24 for i in range(24))]
    _polygon(c, _hull(rim_near + rim_far), "#CFCFCF", stroke=dl.GREY)
    _polygon(c, rim_far, "#B5B5B5", stroke=dl.GREY)
    top = [P(-HX, -HY, HZ), P(HX, -HY, HZ), P(HX, HY, HZ), P(-HX, HY, HZ)]
    back = [P(-HX, -HY, -HZ), P(-HX, HY, -HZ), P(-HX, HY, HZ), P(-HX, -HY, HZ)]
    right = [P(-HX, -HY, -HZ), P(HX, -HY, -HZ), P(HX, -HY, HZ), P(-HX, -HY, HZ)]
    _polygon(c, back, "#DADADA", stroke=dl.GREY)
    _polygon(c, right, "#C9C9C9", stroke=dl.GREY)
    _polygon(c, top, "#EDEDED", stroke=dl.GREY)
    box_bottom = max(p[1] for p in back + right)
    dl.text(c, OX, box_bottom + 24, "sensor prim", 12, "bold", "middle", dl.DK)
    dl.text(c, OX, box_bottom + 41, "xformOp:rotateXYZ = (90, 0, -90)", 11, fill=dl.DK, anchor="middle",
            family=dl.M)

    # --- ISO 8855 output frame on the world axes -----------------------------------------------
    for (x, y, z), lbl, anchor, dx, dy in (((L_ISO, 0, 0), "ISO +X forward (azimuth 0)", "start", 14, 22),
                                           ((0, L_ISO, 0), "ISO +Y left", "end", -4, 22),
                                           ((0, 0, L_ISO), "ISO +Z up", "start", 10, -10)):
        tip = P(x, y, z)
        dl.arrow(c, OX, OY, tip[0], tip[1], stroke=dl.PURPLE, width=2.5)
        dl.text(c, tip[0] + dx, tip[1] + dy, lbl, 12, "bold", anchor, dl.PURPLE)
    ytip = P(0, L_ISO, 0)
    dl.text_block(c, ytip[0] - 4, ytip[1] + 44, "the ISO 8855 axes coincide with the world axes in a Z-up stage",
                  200, 11, fill=dl.PURPLE, anchor="end")

    # --- the prim's local axes after the rotation ----------------------------------------------
    for (x, y, z), lbl, anchor, dx, dy in (((L_PRIM, 0, 0), "local -Z = forward", "start", 12, 22),
                                           ((0, 0, L_PRIM), "local +Y = up", "end", -10, -6),
                                           ((0, -L_PRIM, 0), "local +X = right", "start", 8, 14)):
        tip = P(x, y, z)
        dl.arrow(c, OX, OY, tip[0], tip[1], stroke=dl.BLUE, width=2.5, dashed=True)
        dl.text(c, tip[0] + dx, tip[1] + dy, lbl, 12, "bold", anchor, dl.BLUE)
    c.add(f'<circle cx="{fmt(OX)}" cy="{fmt(OY)}" r="4" fill="{dl.DK}"/>')

    # --- a target straight ahead, and where it is reported --------------------------------------
    tgt = P(T_TARGET, 0, 0)
    c.add(f'<circle cx="{fmt(tgt[0])}" cy="{fmt(tgt[1])}" r="9" fill="none" stroke="{dl.DK}" stroke-width="1.5"/>')
    c.add(f'<circle cx="{fmt(tgt[0])}" cy="{fmt(tgt[1])}" r="4" fill="{dl.DK}"/>')
    dl.text(c, tgt[0] + 10, tgt[1] + 22, "target straight ahead of the prim", 11, fill=dl.GREY)
    call = dl.box(c, CALL_X, CALL_Y, CALL_W, CALL_H, "reported on output +X", fill=dl.PANEL,
                  sublabel="a point straight ahead comes back on ISO +X", label_size=12, sublabel_size=11)
    ddx, ddy = call.left - tgt[0], call.cy - tgt[1]
    dist = math.hypot(ddx, ddy)
    dl.arrow(c, tgt[0] + 12 * ddx / dist, tgt[1] + 12 * ddy / dist, call.left - 2, call.cy, stroke=dl.GREY, width=1.5)

    dl.legend(c, 30, LEG_Y, [("prim local axes (camera convention)", dl.BLUE, "dashed"),
                             ("ISO 8855 output frame", dl.PURPLE, "line"),
                             ("stage axes (Z-up world)", dl.FAINT, "line")], size=11)
    dl.validate(c)
    dl.write_svg(out_dir / "prim_orientation_iso8855.svg", c.render())


# -------------------------------------------------------------------------- output_path.svg ---
def output_path(out_dir: pathlib.Path) -> None:
    W, H = 1200, 418
    TOP = 40
    SR_X, SR_W, SR_H = 30, 390, 324       # (1) step result
    LANE_X, LANE_W, LBL_W = SR_X + 14, SR_W - 28, 96
    LANE_A_Y, LANE_B_Y, LANE_H = TOP + 80, TOP + 146, 56
    XS, XE = 206, 392                     # simulation_start_time / simulation_end_time
    F2_X0, F2_X1 = 158, 258               # frame completing a capture begun in an earlier step
    F1_X0, F1_X1 = 272, 386               # frame wholly inside the step window
    BAR_Y, BAR_H = LANE_B_Y + 18, 20
    AXIS_Y = LANE_B_Y + LANE_H + 16
    NOTE_Y = AXIS_Y + 60
    LIST_X, LIST_W, LIST_Y, LIST_H = 480, 240, TOP + 78, 170   # (3) render var outputs
    ROW_H, ROW_GAP = 26, 6
    CT_X, CT_W, CT_Y = 850, 320, TOP + 40                      # (5) the mapped container
    COL_W, COL_GAP = 142, 12
    BOX_H, BOX_GAP = 26, 6
    CT_H = 118 + 4 * BOX_H + 3 * BOX_GAP + 12
    LEG_Y = 384

    c = dl.Canvas(
        W, H, "From a step result to a mapped output",
        "A step result holds zero or more frames per RenderProduct, each with its own capture window "
        "(start_time .. end_time) that may begin before the step's simulation_start_time. A frame holds one "
        "render var output per RenderVar, keyed by the RenderVar's prim path. Mapping an output with DEFAULT, "
        "CPU, CUDA or CUDA_ARRAY hands you a container: name, type, status, version and one wait_event, a list "
        "of named tensors on the mapped device and a list of named host-resident params.")

    # --- (1) + (2): the step result with its two RenderProduct lanes --------------------------
    dl.box(c, SR_X, TOP, SR_W, SR_H, fill=dl.PANEL, rx=8)
    dl.text(c, SR_X + 16, TOP + 24, "step result", 14, "bold")
    dl.text(c, SR_X + 16, TOP + 42, "zero or more frames per RenderProduct you stepped", 11, fill=dl.GREY)
    lane_a = dl.lane(c, LANE_X, LANE_A_Y, LANE_W, LANE_H, "product A", fill=dl.WHITE, label_width=LBL_W,
                     label_size=12)
    dl.lane(c, LANE_X, LANE_B_Y, LANE_W, LANE_H, "product B", fill=dl.WHITE, label_width=LBL_W, label_size=12)
    # the step window [t, t + delta_time]: a tinted band between two dashed lines
    c.add(f'<rect x="{fmt(XS)}" y="{fmt(LANE_A_Y - 8)}" width="{fmt(XE - XS)}" '
          f'height="{fmt(AXIS_Y - LANE_A_Y + 8)}" fill="{dl.DK}" fill-opacity="0.06"/>')
    for x in (XS, XE):
        c.add(f'<line x1="{fmt(x)}" y1="{fmt(LANE_A_Y - 8)}" x2="{fmt(x)}" y2="{fmt(AXIS_Y)}" '
              f'stroke="{dl.GREY}" stroke-width="1" stroke-dasharray="3 2"/>')
    wl = dl.text(c, (XS + XE) / 2 - 3, LANE_A_Y - 14, "step window", 11, fill=dl.GREY, anchor="end")
    dl.text(c, wl.x1 + 6, LANE_A_Y - 14, "[t, t + delta_time]", 11, fill=dl.DK, family=dl.M)
    dl.text(c, lane_a.cx, lane_a.cy + 4, "absent, or an empty frame list", 11, fill=dl.GREY, anchor="middle")
    # frames of product B
    dl.box(c, F2_X0, BAR_Y, XS - F2_X0, BAR_H, fill=dl.WHITE, stroke=dl.MUTED, stroke_width=1.5, dashed=True, rx=3)
    dl.box(c, XS, BAR_Y, F2_X1 - XS, BAR_H, fill=dl.MUTED, rx=3)
    dl.box(c, F1_X0, BAR_Y, F1_X1 - F1_X0, BAR_H, fill=dl.MUTED, rx=3)
    dl.text(c, F1_X1, BAR_Y - 5, "end_time", 11, fill=dl.DK, anchor="end", family=dl.M)
    dl.text(c, F1_X0, BAR_Y + BAR_H + 13, "start_time", 11, fill=dl.DK, family=dl.M)
    # the step's own window on the time axis
    dl.tick_marks(c, lane_a.x, AXIS_Y, lane_a.w, [XS - lane_a.x, XE - lane_a.x], stroke=dl.GREY)
    dl.text(c, XS - 4, AXIS_Y + 20, "simulation_start_time", 11, fill=dl.DK, family=dl.M)
    dl.text(c, XE + 4, AXIS_Y + 37, "simulation_end_time", 11, fill=dl.DK, anchor="end", family=dl.M)
    dl.arrow(c, F2_X0 + 20, NOTE_Y - 10, F2_X0 + 20, BAR_Y + BAR_H + 3, stroke=dl.GREY, width=1)
    dl.text_block(c, SR_X + 16, NOTE_Y, "completes a capture begun in an earlier step: its start_time "
                  "precedes simulation_start_time. In C the frame fields are frame_start_time and "
                  "frame_end_time.", SR_W - 32, 11, fill=dl.GREY)

    # --- (3): the frame's render var outputs ----------------------------------------------------
    dl.box(c, LIST_X, LIST_Y, LIST_W, LIST_H, fill=dl.PANEL, rx=8)
    dl.text(c, LIST_X + 12, LIST_Y + 22, "render var outputs", 13, "bold")
    dl.text(c, LIST_X + 12, LIST_Y + 38, "one per RenderVar of the product,", 11, fill=dl.GREY)
    dl.text(c, LIST_X + 12, LIST_Y + 54, "keyed by its full prim path", 11, fill=dl.GREY)
    rows = []
    for i, path in enumerate(("/World/Render/Vars/PointCloud", "/Render/Camera/LdrColor")):
        rows.append(dl.box(c, LIST_X + 12, LIST_Y + 66 + i * (ROW_H + ROW_GAP), LIST_W - 24, ROW_H, path,
                           fill=dl.WHITE, stroke=dl.FAINT, stroke_width=1, rx=4, label_size=11,
                           label_weight="normal", label_family=dl.M))
    dl.text(c, LIST_X + 12, LIST_Y + LIST_H - 30, "keys taken from the lidar example", 11, fill=dl.MUTED)
    dl.text(c, LIST_X + 12, LIST_Y + LIST_H - 14, "and from the camera example", 11, fill=dl.MUTED)
    dl.connector(c, F1_X1 + 3, BAR_Y + BAR_H / 2, LIST_X - 2, rows[0].cy + 8, stroke=dl.GREY, width=2)
    dl.text(c, (SR_X + SR_W + LIST_X) / 2, BAR_Y - 14, "frame", 11, fill=dl.GREY, anchor="middle")

    # --- (4): map, and (5): the container ----------------------------------------------------
    r0 = rows[0]
    mx = (r0.right + CT_X) / 2
    dl.arrow(c, r0.right + 3, r0.cy, CT_X - 2, r0.cy, stroke=dl.GREY, width=2.5)
    dl.text(c, mx, r0.cy - 42, "map", 12, "bold", "middle", dl.DK)
    dl.text(c, mx, r0.cy - 26, "DEFAULT | CPU", 11, fill=dl.DK, anchor="middle", family=dl.M)
    dl.text(c, mx, r0.cy - 10, "CUDA | CUDA_ARRAY", 11, fill=dl.DK, anchor="middle", family=dl.M)

    dl.box(c, CT_X, CT_Y, CT_W, CT_H, fill=dl.PANEL, rx=8)
    hx = CT_X + 12
    dl.text(c, hx, CT_Y + 24, "name = /World/Render/Vars/PointCloud", 11, fill=dl.DK, family=dl.M)
    dl.text(c, hx, CT_Y + 42, "type = PointCloud   status   version", 11, fill=dl.DK, family=dl.M)
    dl.text(c, hx, CT_Y + 60, "one wait_event covers every tensor of the container", 11, fill=dl.GREY)
    cols = (("tensors", "CPU or CUDA", dl.BLUE, ("Coordinates", "Intensity", "Flags", "Counts")),
            ("params", "host resident", dl.PURPLE, ("frameId", "timestampNs", "modelToAppTransform", "coordsType")))
    for i, (title, badge, color, names) in enumerate(cols):
        x = hx + i * (COL_W + COL_GAP)
        dl.text(c, x, CT_Y + 86, title, 12, "bold", fill=color)
        bw = dl.text_width(badge, 11) + 16
        dl.box(c, x, CT_Y + 92, bw, 18, badge, fill=color, rx=9, label_size=11, label_weight="normal")
        for j, name in enumerate(names):
            dl.box(c, x, CT_Y + 118 + j * (BOX_H + BOX_GAP), COL_W, BOX_H, name, fill=dl.WHITE, stroke=color,
                   stroke_width=1.5, rx=4, label_size=11, label_weight="normal", label_family=dl.M)

    dl.legend(c, SR_X, LEG_Y, [("frame: its own capture window", dl.MUTED, "box"),
                               ("portion rendered in an earlier step", dl.MUTED, "outline"),
                               ("tensors: bulk data, on the mapped device", dl.BLUE, "box"),
                               ("params: metadata, always host resident", dl.PURPLE, "box")], size=11)
    dl.validate(c)
    dl.write_svg(out_dir / "output_path.svg", c.render())


# -------------------------------------------------------------------- capacity_vs_count.svg ---
def capacity_vs_count(out_dir: pathlib.Path) -> None:
    W, H = 1000, 372
    N, K = 20, 12                         # cells drawn, delivered cells [0, k)
    CLEAR = (3, 7, 10)                    # delivered entries whose valid bit is clear
    CX0, CY0, CW, CH = 80, 160, 42, 44    # the array of cells
    TITLE_Y = 64
    BR_TOP_Y, BR_TOP_LBL_Y = 142, 128
    COUNTS_X, COUNTS_Y, COUNTS_W, COUNTS_H = 630, 86, 80, 36
    IDX_Y = CY0 + CH + 18
    BR_BOT_Y, BR_BOT_LBL_Y = 242, 264
    LEG_Y = 292
    NOTE_Y = 346

    c = dl.Canvas(
        W, H, "Capacity versus count",
        "A per-entry channel is allocated for Nmax entries (its shape, also the maxPoints param). The "
        "delivered entries, indices [0, Counts[0]), sit at the front; inside that range an entry is a real "
        "return when Flags[i] & 0x40 is set, and a few entries have the bit clear. Everything past Counts[0] "
        "holds whatever it held before and is never read.")
    hatch = _hatch(c)
    xk = CX0 + K * CW

    tw = dl.text(c, CX0, TITLE_Y, "per-entry channel", 13, "bold")
    dl.text(c, tw.x1 + 8, TITLE_Y, "(shape = capacity Nmax = maxPoints)", 12, fill=dl.GREY, family=dl.M)

    for i in range(N):
        if i >= K:
            fill = hatch
        elif i in CLEAR:
            fill = dl.FAINT
        else:
            fill = dl.GREEN
        dl.box(c, CX0 + i * CW, CY0, CW, CH, fill=fill, stroke=dl.GREY, stroke_width=1, rx=2)
    for i, lbl in ((0, "0"), (K - 1, "k-1"), (K, "k"), (N - 1, "Nmax-1")):
        dl.text(c, CX0 + (i + 0.5) * CW, IDX_Y, lbl, 11, fill=dl.DK, anchor="middle", family=dl.M)

    # delivered range and the Counts tensor that bounds it
    _hbracket(c, CX0, xk, BR_TOP_Y, tick=8, toward=1, stroke=dl.DK)
    dw = dl.text(c, (CX0 + xk) / 2 - 3, BR_TOP_LBL_Y, "delivered: indices", 12, fill=dl.DK, anchor="end")
    dl.text(c, dw.x1 + 6, BR_TOP_LBL_Y, "[0, Counts[0])", 12, fill=dl.DK, family=dl.M)
    counts = dl.box(c, COUNTS_X, COUNTS_Y, COUNTS_W, COUNTS_H, "[k]", fill=dl.WHITE, stroke=dl.DK,
                    stroke_width=1.5, rx=4, label_size=13, label_family=dl.M)
    dl.text(c, counts.cx, COUNTS_Y - 10, "Counts", 12, "bold", "middle", dl.DK)
    dl.text(c, counts.right + 10, counts.cy + 4, "one int32: the delivered count", 11, fill=dl.GREY)
    dl.arrow(c, counts.left - 2, counts.bottom - 4, xk + 3, BR_TOP_Y - 3, stroke=dl.DK, width=1.5)

    # past the count
    _hbracket(c, xk, CX0 + N * CW, BR_BOT_Y, tick=8, toward=-1, stroke=dl.GREY)
    dl.text(c, (xk + CX0 + N * CW) / 2, BR_BOT_LBL_Y, "whatever it held before: never read", 12, fill=dl.GREY,
            anchor="middle")

    leg = dl.legend(c, CX0, LEG_Y, [("Flags[i] & 0x40 set: real entry", dl.GREEN, "box"),
                                    ("bit clear: not a return", dl.FAINT, "box")], size=11)
    sx = leg.right + 22
    c.add(f'<rect x="{fmt(sx)}" y="{fmt(LEG_Y)}" width="12" height="12" rx="2" fill="{hatch}" '
          f'stroke="{dl.GREY}" stroke-width="1"/>')
    dl.text(c, sx + 19, LEG_Y + 6 + 0.36 * 11, "past Counts[0]: never read", 11, fill=dl.DK)

    c.add(f'<rect x="{fmt(CX0 - 14)}" y="{fmt(NOTE_Y - 13)}" width="4" height="17" rx="1" fill="{dl.ORANGE}"/>')
    dl.text(c, CX0, NOTE_Y, "read Counts[0], not the tensor's length; test the bit (Flags[i] & 0x40), not == 0x40",
            12, fill=dl.DK)
    dl.validate(c)
    dl.write_svg(out_dir / "capacity_vs_count.svg", c.render())


# ----------------------------------------------------------------------------------- entry ---
def generate(out_dir: pathlib.Path) -> None:
    sensor_prim_schema_model(out_dir)
    prim_orientation_iso8855(out_dir)
    output_path(out_dir)
    capacity_vs_count(out_dir)


if __name__ == "__main__":
    generate(dl.output_dir(__file__))
