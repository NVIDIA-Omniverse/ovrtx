#!/usr/bin/env python3
"""Radar figures, group A: the attribute namespaces, the half-angle field of view, the scan
cycle timeline and the custom gain grid layout.

``generate_diagrams.py`` imports this module and calls :func:`generate`; running the module
on its own regenerates only these figures::

    python3 -B _gen_radar_a.py            # in place
    python3 -B _gen_radar_a.py /tmp/check # elsewhere, to diff against the committed SVGs
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import _diagram_lib as dl  # noqa: E402

fmt = dl.fmt


# ------------------------------------------------------------------------------ local helpers ---
def _polar_right(cx, cy, r, a):
    """Point at radius ``r`` and angle ``a`` (degrees) off a boresight pointing right; +a turns up."""
    t = math.radians(a)
    return cx + r * math.cos(t), cy - r * math.sin(t)


def _angle_right(cx, cy, x, y):
    """Inverse of :func:`_polar_right`: the (angle in degrees, radius) of a point."""
    return math.degrees(math.atan2(cy - y, x - cx)), math.hypot(x - cx, y - cy)


def _arc_d(cx, cy, r, a0, a1, pos):
    """SVG path data of the arc from angle ``a0`` to ``a1`` (``a1 > a0``) on the circle (cx, cy, r)."""
    if a1 <= a0:
        raise ValueError("arc angles must increase")
    x0, y0 = pos(cx, cy, r, a0)
    x1, y1 = pos(cx, cy, r, a1)
    xm, ym = pos(cx, cy, r, a0 + 1.0)
    # sweep-flag 1 is the direction that looks clockwise on screen (SVG's y grows downward)
    sweep = 1 if (x0 - cx) * (ym - cy) - (y0 - cy) * (xm - cx) > 0 else 0
    large = 1 if a1 - a0 > 180 else 0
    return f"M{fmt(x0)},{fmt(y0)} A{fmt(r)},{fmt(r)} 0 {large} {sweep} {fmt(x1)},{fmt(y1)}"


def _sector(c, cx, cy, r, a0, a1, pos, fill, stroke, width=1.5, opacity=None, dashed=False):
    """A filled circular sector (a wedge) with its apex at (cx, cy)."""
    arc = _arc_d(cx, cy, r, a0, a1, pos)
    attrs = (f'd="M{fmt(cx)},{fmt(cy)} L{arc[1:]} Z" fill="{fill}" stroke="{stroke}" '
             f'stroke-width="{fmt(width)}" stroke-linejoin="round"')
    if opacity is not None:
        attrs += f' fill-opacity="{fmt(opacity)}"'
    if dashed:
        attrs += f' stroke-dasharray="{fmt(3 * width)} {fmt(2 * width)}"'
    c.add(f"<path {attrs}/>")


def _arc_brace(c, cx, cy, r, a0, a1, pos, stroke=dl.GREY, width=1.5, tick=5.0):
    """An arc from ``a0`` to ``a1`` at radius ``r`` with a short radial tick at each end."""
    c.add(f'<path d="{_arc_d(cx, cy, r, a0, a1, pos)}" fill="none" stroke="{stroke}" '
          f'stroke-width="{fmt(width)}"/>')
    for a in (a0, a1):
        xa, ya = pos(cx, cy, r - tick, a)
        xb, yb = pos(cx, cy, r + tick, a)
        c.add(f'<line x1="{fmt(xa)}" y1="{fmt(ya)}" x2="{fmt(xb)}" y2="{fmt(yb)}" '
              f'stroke="{stroke}" stroke-width="{fmt(width)}"/>')


def _ray(c, cx, cy, r, a, pos, stroke=dl.DK, width=1.5, dashed=False):
    """A straight line from the apex to radius ``r`` at angle ``a``."""
    x, y = pos(cx, cy, r, a)
    dl.arrow(c, cx, cy, x, y, stroke, width, head=False, dashed=dashed)


def _cosine_lobe(c, cx, cy, r, amax, pos, color=dl.GREEN, width=2, opacity=0.18):
    """Polar plot of a gain that peaks on boresight and falls as a cosine to zero at ±amax."""
    n = 66
    pts = []
    for i in range(n + 1):
        a = -amax + 2.0 * amax * i / n
        pts.append(pos(cx, cy, r * math.cos(math.pi / 2 * a / amax), a))
    d = f"M{fmt(cx)},{fmt(cy)} " + " ".join(f"L{fmt(x)},{fmt(y)}" for x, y in pts) + " Z"
    c.add(f'<path d="{d}" fill="{color}" fill-opacity="{fmt(opacity)}" stroke="{color}" '
          f'stroke-width="{fmt(width)}" stroke-linejoin="round"/>')


def _assert_inside_lobe(tb, cx, cy, r, amax, margin=4.0):
    """Raise if a corner of the text box ``tb`` lies outside the cosine lobe drawn with
    :func:`_cosine_lobe` around a boresight that points right."""
    for x, y in ((tb.x0, tb.y0), (tb.x1, tb.y0), (tb.x0, tb.y1), (tb.x1, tb.y1)):
        a, rr = _angle_right(cx, cy, x, y)
        lobe = r * math.cos(math.pi / 2 * a / amax) if abs(a) < amax else 0.0
        if rr + margin > lobe:
            raise ValueError(f"{tb.label!r} leaves the gain lobe at ({fmt(x)},{fmt(y)})")


def _dot(c, x, y, r=5.0, fill=dl.DK):
    c.add(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r)}" fill="{fill}"/>')


def _edge(c, x1, y1, x2, y2, stroke=dl.MUTED, width=1.5):
    """A tree edge: a plain line without an arrowhead."""
    dl.arrow(c, x1, y1, x2, y2, stroke, width, head=False)


def _segments(c, x, y, segs, anchor="start", gap=4.5):
    """Draw text pieces of different fonts on one baseline, a space-sized ``gap`` apart; ``segs``
    are ``(text, size, weight, fill, family)``. Returns the total width."""
    widths = [dl.text_width(s, size, weight, family) for s, size, weight, fill, family in segs]
    total = sum(widths) + gap * (len(segs) - 1)
    cur = x - (total / 2 if anchor == "middle" else total if anchor == "end" else 0.0)
    for (s, size, weight, fill, family), w in zip(segs, widths):
        dl.text(c, cur, y, s, size, weight, "start", fill, family)
        cur += w + gap
    return total


def _lane(c, x, y, w, h, label_w, label, sub=None, fill=dl.PANEL):
    """A timeline lane with a bold label and an optional grey sublabel in its label column."""
    c.add(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" rx="4" fill="{fill}"/>')
    if sub is None:
        dl.text(c, x + 12, y + h / 2 + 4.7, label, 13, "bold", "start", dl.DK)
    else:
        dl.text(c, x + 12, y + h / 2 - 4, label, 13, "bold", "start", dl.DK)
        dl.text(c, x + 12, y + h / 2 + 14, sub, 11.5, "normal", "start", dl.GREY)
    c.add(f'<line x1="{fmt(x + label_w)}" y1="{fmt(y + 6)}" x2="{fmt(x + label_w)}" y2="{fmt(y + h - 6)}" '
          f'stroke="{dl.FAINT}" stroke-width="1"/>')
    return dl.Rect(x + label_w, y, w - label_w, h)


# ------------------------------------------------------------------------------------ figures ---
def radar_attribute_namespaces(out_dir: pathlib.Path) -> None:
    """The three attribute namespaces of a radar prim, as a tree."""
    PAD = 32
    COL1_X, COL1_W = 32, 180                  # omni:sensor:*
    COL2_X, COL2_W = 232, 244                 # omni:sensor:WpmDmat:*
    COL3_X, COL3_W = 496, 660                 # omni:sensor:WpmDmat:scan:<instance>:*
    INST_W, INST_GAP = 320, 20                # the two scan instance boxes
    W = COL3_X + COL3_W + PAD
    ROOT_W, ROOT_H, ROOT_Y = 400, 56, 28
    BUS_Y = 108                               # root -> namespace headers
    HDR_Y, HDR_H = 124, 40
    NOTE_Y = 180
    LIST_Y, ROW = 192, 22                     # attribute lists of columns 1 and 2
    FRAME_Y, FRAME_H = 200, 90                # the highlighted output group
    INST_Y = 214                              # top of the two instance boxes
    GROUP_Y0, GROUP_ROW = 90, 20              # per-scan groups inside an instance box
    FOOT_Y = 596
    LEGEND_X = 770
    H = 630

    SHARED = ["modelName", "modelVendor", "modelVersion", "marketName", "frameRate", "startTime",
              "frameLimit"]
    OUTPUT_GROUP = ["elementsCoordsType", "outputFrameOfReference", "customFrameOfReferenceTrafo"]
    SENSOR_LEVEL = ["waveLengthMm", "traceTreeDepth", "cfarMode"]
    GROUPS = [  # (per-scan attribute group, one example attribute of the group)
        ("sampling and power", "raysPerDeg"),
        ("processing mode", "datacubeMode"),
        ("field of view and range", "maxAzAngDeg"),
        ("resolution and bins", "rangeResM"),
        ("aliasing", "enableRangeAliasing"),
        ("velocity sequence and RCS", "maxVelMpsSequence"),
        ("CFAR cells", "cfarRnT"),
        ("noise", "rangeNoiseSDev"),
        ("waveform", "chirpDuration"),
        ("Tx/Rx elements", "txAntennaGainMode"),
        ("gain grids", "txAntennaCoGain"),
        ("aperture", "apertureArrayAzimuthElements"),
    ]
    INSTANCES = [
        ("s001", "brought by the main schema, which prepends", "OmniSensorGenericRadarWpmDmatScanCfgAPI:s001"),
        ("s002", "applied separately, as a second instance", "OmniSensorGenericRadarWpmDmatScanCfgAPI:s002"),
    ]
    INST_H = GROUP_Y0 + GROUP_ROW * (len(GROUPS) - 1) + 16

    c = dl.Canvas(
        W, H, "Radar attribute namespaces",
        "A tree with one OmniRadar prim at the root and three branches: omni:sensor:* with the seven "
        "identification and rate attributes, omni:sensor:WpmDmat:* with its six per-sensor attributes, "
        "the three output attributes highlighted, and omni:sensor:WpmDmat:scan:s001:* and :s002:* "
        "instance branches that each hold the per-scan attributes.")

    # root
    root = dl.box(c, W / 2 - ROOT_W / 2, ROOT_Y, ROOT_W, ROOT_H, fill=dl.DK)
    dl.text(c, root.cx, ROOT_Y + 23, "OmniRadar prim", 15, "bold", "middle", dl.WHITE)
    dl.text(c, root.cx, ROOT_Y + 44, "OmniSensorGenericRadarWpmDmatAPI", 12, "normal", "middle",
            dl.FAINT, dl.M)

    # the three namespace headers
    cols = [(COL1_X, COL1_W, "omni:sensor:*", "shared by every sensor model"),
            (COL2_X, COL2_W, "omni:sensor:WpmDmat:*", "once per sensor"),
            (COL3_X, COL3_W, "omni:sensor:WpmDmat:scan:<instance>:*",
             "once per scan instance, under the instance name")]
    centers = [x + w / 2 for x, w, _, _ in cols]
    _edge(c, root.cx, root.bottom, root.cx, BUS_Y)
    _edge(c, centers[0], BUS_Y, centers[-1], BUS_Y)
    for (x, w, label, note), cx in zip(cols, centers):
        _edge(c, cx, BUS_Y, cx, HDR_Y)
        dl.box(c, x, HDR_Y, w, HDR_H, label, fill=dl.GREY, label_size=13, label_family=dl.M)
        dl.text(c, cx, NOTE_Y, note, 11.5, "normal", "middle", dl.GREY)

    # column 1: the shared attributes
    dl.box(c, COL1_X, LIST_Y, COL1_W, len(SHARED) * ROW + 12, fill=dl.PANEL)
    for i, name in enumerate(SHARED):
        dl.text(c, COL1_X + 14, LIST_Y + 22 + i * ROW, name, 13, "normal", "start", dl.DK, dl.M)

    # column 2: the six sensor-level attributes, the output group framed
    col2_h = FRAME_Y - LIST_Y + FRAME_H + len(SENSOR_LEVEL) * ROW + 16
    dl.box(c, COL2_X, LIST_Y, COL2_W, col2_h, fill=dl.PANEL)
    frame = dl.box(c, COL2_X + 8, FRAME_Y, COL2_W - 16, FRAME_H, fill=dl.WHITE, stroke=dl.GREEN,
                   stroke_width=2)
    dl.text(c, frame.right - 10, FRAME_Y + 15, "output group", 11.5, "bold", "end", dl.GREEN)
    for i, name in enumerate(OUTPUT_GROUP):
        dl.text(c, COL2_X + 14, FRAME_Y + 15 + ROW * (i + 1), name, 13, "normal", "start", dl.DK, dl.M)
    for i, name in enumerate(SENSOR_LEVEL):
        dl.text(c, COL2_X + 14, FRAME_Y + FRAME_H + 22 + i * ROW, name, 13, "normal", "start",
                dl.DK, dl.M)

    # column 3: one box per scan instance, each with every per-scan group
    # one stem per instance, straight down from the header: a central stem would cut through
    # the note under the header
    inst_x = [COL3_X, COL3_X + INST_W + INST_GAP]
    for x, (name, note, schema) in zip(inst_x, INSTANCES):
        _edge(c, x + INST_W / 2, HDR_Y + HDR_H, x + INST_W / 2, INST_Y)
        dl.box(c, x, INST_Y, INST_W, INST_H, fill=dl.PANEL)
        dl.text(c, x + 14, INST_Y + 24, name, 14, "bold", "start", dl.DK, dl.M)
        dl.text(c, x + 14, INST_Y + 42, note, 11.5, "normal", "start", dl.GREY)
        dl.text(c, x + 14, INST_Y + 58, schema, 11, "normal", "start", dl.GREY, dl.M)
        c.add(f'<line x1="{fmt(x + 10)}" y1="{fmt(INST_Y + 70)}" x2="{fmt(x + INST_W - 10)}" '
              f'y2="{fmt(INST_Y + 70)}" stroke="{dl.FAINT}" stroke-width="1"/>')
        for i, (group, example) in enumerate(GROUPS):
            yb = INST_Y + GROUP_Y0 + i * GROUP_ROW
            dl.text(c, x + 14, yb, group, 12, "normal", "start", dl.DK)
            dl.text(c, x + INST_W - 14, yb, example, 11, "normal", "end", dl.GREY, dl.M)

    dl.text(c, PAD, FOOT_Y, "No attribute name appears at two levels: a value authored at the wrong "
            "level is read by nothing.", 12.5, "normal", "start", dl.DK)
    # the legend swatch is drawn by hand so that it matches the frame: a solid green outline
    sx, sy = LEGEND_X, FOOT_Y - 10
    c.add(f'<rect x="{fmt(sx + 1)}" y="{fmt(sy + 1)}" width="10" height="10" rx="2" fill="{dl.WHITE}" '
          f'stroke="{dl.GREEN}" stroke-width="2"/>')
    dl.text(c, sx + 19, FOOT_Y, "output group: the three attributes that reshape the output", 12,
            "normal", "start", dl.DK)

    dl.validate(c)
    dl.write_svg(out_dir / "radar_attribute_namespaces.svg", c.render())


def radar_half_angle_field_of_view(out_dir: pathlib.Path) -> None:
    """Top and side view of the symmetric half-angle limits with the COSINE_FALLOFF gain lobe."""
    W, H = 1080, 660
    TITLE_Y = 36
    R = 235                                   # drawn radius of both wedges
    LOBE_R = 0.9 * R                          # radius of the gain lobe on boresight
    AZ, EL = 66, 20                           # the schema defaults, used as the drawn half-angles
    AX, AY = 150, 338                         # apex of the top view
    BX, BY = 650, 338                         # apex of the side view
    BRACE_GAP, LABEL_GAP = 16, 14             # brace radius beyond R; label gap beyond the brace
    LEGEND_X, LEGEND_Y = 580, 72
    ELEV_NOTE_X, ELEV_NOTE_Y = 690, 494
    CALLOUT_W, CALLOUT_H, CALLOUT_Y = 560, 40, 596

    c = dl.Canvas(
        W, H, "Radar half-angle field of view",
        "A top view and a side view of a radar. In the top view the azimuth field of view spans from "
        "minus maxAzAngDeg to plus maxAzAngDeg, with the COSINE_FALLOFF gain curve at its peak on "
        "boresight and falling to zero at both limits; a 150-degree field of view is labeled as "
        "authored with maxAzAngDeg = 75. The side view shows the same symmetric interval for "
        "elevation, from minus maxElAngDeg to plus maxElAngDeg.")

    # ---- top view: azimuth -------------------------------------------------------------------
    dl.text(c, AX + 160, TITLE_Y, "Top view: azimuth", 15, "bold", "middle")
    _sector(c, AX, AY, R, -AZ, AZ, _polar_right, dl.PANEL, dl.MUTED)
    _cosine_lobe(c, AX, AY, LOBE_R, AZ, _polar_right)
    _ray(c, AX, AY, R, AZ, _polar_right)
    _ray(c, AX, AY, R, -AZ, _polar_right)
    _ray(c, AX, AY, R, 0, _polar_right, dl.GREY, dashed=True)
    _dot(c, AX, AY)
    dl.text(c, AX - 12, AY + 18, "radar", 11.5, "normal", "end", dl.GREY)
    dl.text(c, AX - 14, AY - 60, "outside the limits:", 12, "normal", "end", dl.GREY)
    dl.text(c, AX - 14, AY - 42, "gain 0", 12, "normal", "end", dl.GREY)
    dl.text(c, AX - 14, AY - 24, "(every profile)", 12, "normal", "end", dl.GREY)

    # labels inside the lobe (the lobe pinches to zero at the apex, so they sit in its middle)
    LOBE_TEXT_X = AX + 64
    for tb in (dl.text(c, AX + 48, AY + 14, "boresight (+X)", 11, "normal", "start", dl.GREY),
               dl.text(c, LOBE_TEXT_X, AY - 20, "COSINE_FALLOFF", 13, "bold", "start", dl.GREEN, dl.M),
               dl.text(c, LOBE_TEXT_X, AY + 36, "peak on boresight", 11.5, "normal", "start", dl.GREY),
               dl.text(c, LOBE_TEXT_X, AY + 52, "zero at the limits", 11.5, "normal", "start", dl.GREY)):
        _assert_inside_lobe(tb, AX, AY, LOBE_R, AZ)

    # edge labels and the field-of-view brace
    px, py = _polar_right(AX, AY, R, AZ)
    dl.text(c, px + 12, py - 4, "+maxAzAngDeg", 13, "bold", "start", dl.DK, dl.M)
    dl.text(c, px + 12, py + 14, "the half-angle; drawn at the default, 66°", 11.5, "normal", "start",
            dl.GREY)
    mx, my = _polar_right(AX, AY, R, -AZ)
    dl.text(c, mx + 12, my + 6, "−maxAzAngDeg", 13, "bold", "start", dl.DK, dl.M)
    dl.text(c, mx + 12, my + 24, "the half-angle; drawn at the default, 66°", 11.5, "normal", "start",
            dl.GREY)
    _arc_brace(c, AX, AY, R + BRACE_GAP, -AZ, AZ, _polar_right)
    fx = AX + R + BRACE_GAP + LABEL_GAP
    dl.text(c, fx, AY - 6, "field of view", 13, "normal", "start", dl.DK)
    dl.text(c, fx, AY + 12, "= 2 × maxAzAngDeg", 13, "normal", "start", dl.DK, dl.M)

    # ---- side view: elevation ----------------------------------------------------------------
    dl.text(c, BX + 170, TITLE_Y, "Side view: elevation", 15, "bold", "middle")
    _sector(c, BX, BY, R, -EL, EL, _polar_right, dl.PANEL, dl.MUTED)
    _cosine_lobe(c, BX, BY, LOBE_R, EL, _polar_right)
    _ray(c, BX, BY, R, EL, _polar_right)
    _ray(c, BX, BY, R, -EL, _polar_right)
    _ray(c, BX, BY, R, 0, _polar_right, dl.GREY, dashed=True)
    _dot(c, BX, BY)
    dl.text(c, BX - 12, BY + 18, "radar", 11.5, "normal", "end", dl.GREY)
    px, py = _polar_right(BX, BY, R, EL)
    dl.text(c, px + 30, py - 10, "+maxElAngDeg", 13, "bold", "start", dl.DK, dl.M)
    dl.text(c, px + 30, py + 8, "drawn at the default, 20°", 11.5, "normal", "start", dl.GREY)
    mx, my = _polar_right(BX, BY, R, -EL)
    dl.text(c, mx + 30, my + 14, "−maxElAngDeg", 13, "bold", "start", dl.DK, dl.M)
    dl.text(c, mx + 30, my + 32, "drawn at the default, 20°", 11.5, "normal", "start", dl.GREY)
    _arc_brace(c, BX, BY, R + BRACE_GAP, -EL, EL, _polar_right)
    fx = BX + R + BRACE_GAP + LABEL_GAP
    dl.text(c, fx, BY - 6, "field of view", 13, "normal", "start", dl.DK)
    dl.text(c, fx, BY + 12, "= 2 × maxElAngDeg", 13, "normal", "start", dl.DK, dl.M)
    dl.text(c, ELEV_NOTE_X, ELEV_NOTE_Y, "subject to elevMode", 12.5, "bold", "start", dl.DK)
    dl.text_block(c, ELEV_NOTE_X, ELEV_NOTE_Y + 18,
                  "FULL_EL reports both halves, POS_EL only non-negative elevation, "
                  "NO_EL zero elevation for every detection", 340, 11.5)

    # legend and the worked example
    dl.legend(c, LEGEND_X, LEGEND_Y, [
        ("COSINE_FALLOFF gain: peak on boresight, zero at the limits", dl.GREEN),
        ("field of view: the symmetric interval between the two limits", dl.PANEL),
    ], horizontal=False)
    callout = dl.box(c, W / 2 - CALLOUT_W / 2, CALLOUT_Y, CALLOUT_W, CALLOUT_H, fill=dl.PANEL)
    _segments(c, callout.cx, callout.cy + 4.7, [
        ("worked example — spec sheet: 150° field of view →", 13, "normal", dl.DK, dl.F),
        ("maxAzAngDeg = 75", 13, "bold", dl.DK, dl.M),
    ], anchor="middle")

    dl.validate(c)
    dl.write_svg(out_dir / "radar_half_angle_field_of_view.svg", c.render())


def radar_scan_cycle_timeline(out_dir: pathlib.Path) -> None:
    """Eight capture windows: the pending scan and each scan's velocity-sequence position, which
    advance only on firings."""
    PAD = 24
    LABEL_W = 200                             # lane label column
    STEPS, CW = 8, 96                         # step columns
    CELLS_X = PAD + LABEL_W
    W = CELLS_X + STEPS * CW + PAD
    NOTE_Y = 36
    HDR_Y = 68
    LANE_Y0, LANE_H, LANE_GAP = 82, 52, 10
    CELL_W, CELL_H = CW - 14, 34
    NO_SCAN_WINDOWS = (3, 6)                  # windows that hold no scheduled scan time
    SEQ = ("50", "55")                        # maxVelMpsSequence
    SCANS = (("s001", dl.BLUE), ("s002", dl.PURPLE))
    BRACKET_DROP = 22                         # leader from the lanes down to the bracket
    H = 446

    lanes_bottom = LANE_Y0 + 3 * LANE_H + 2 * LANE_GAP
    BRACKET_Y = lanes_bottom + BRACKET_DROP
    ANNOT_Y = BRACKET_Y + 20
    LEGEND_Y = ANNOT_Y + 28
    FOOT_Y = LEGEND_Y + 3 * 20 + 24

    c = dl.Canvas(
        W, H, "Radar scan cycle and velocity sequence",
        "Eight capture windows for scans s001 and s002, each with maxVelMpsSequence [50, 55] meters per "
        "second. Firings alternate scans and advance only that scan's sequence. Windows three and six "
        "contain no acquisition and publish no radar frame; the pending scan and both sequence entries "
        "remain unchanged.")

    def col_x(step):
        return CELLS_X + (step - 1) * CW

    def col_cx(step):
        return col_x(step) + CW / 2

    # notes above the timeline
    _segments(c, PAD, NOTE_Y, [
        ("maxVelMpsSequence = [50, 55]", 12.5, "normal", dl.DK, dl.M),
        ("(m/s); two scans, s001 and s002", 12.5, "normal", dl.GREY, dl.F),
    ])
    dl.text(c, W - PAD, NOTE_Y, "only firings advance the active scan and its sequence →",
            12, "normal", "end", dl.GREY)

    # capture-window header
    dl.text(c, PAD + 12, HDR_Y, "capture window", 12.5, "bold", "start", dl.GREY)
    for s in range(1, STEPS + 1):
        dl.text(c, col_cx(s), HDR_Y, str(s), 12.5, "bold", "middle", dl.GREY)

    # lanes, then the grey bands of the non-firing windows, then the cells
    lane_specs = [("active scan", None), ("s001 sequence position", "advances only when s001 fires"),
                  ("s002 sequence position", "advances only when s002 fires")]
    lane_y = [LANE_Y0 + i * (LANE_H + LANE_GAP) for i in range(3)]
    for y, (label, sub) in zip(lane_y, lane_specs):
        _lane(c, PAD, y, W - 2 * PAD, LANE_H, LABEL_W, label, sub)
    for s in NO_SCAN_WINDOWS:
        c.add(f'<rect x="{fmt(col_x(s) + 2)}" y="{fmt(LANE_Y0 - 4)}" width="{fmt(CW - 4)}" '
              f'height="{fmt(lanes_bottom - LANE_Y0 + 8)}" rx="4" fill="{dl.FAINT}" fill-opacity="0.55"/>')

    pending = 0                               # the scan whose turn it is; moves on firings only
    fired = [0] * len(SCANS)                  # accepted firings per scan: its sequence position
    for s in range(1, STEPS + 1):
        turn = pending
        no_scan = s in NO_SCAN_WINDOWS
        name, color = SCANS[turn]
        x = col_cx(s) - CELL_W / 2
        y = lane_y[0] + (LANE_H - CELL_H) / 2
        if no_scan:
            dl.box(c, x, y, CELL_W, CELL_H, name, fill=dl.WHITE, stroke=dl.MUTED, stroke_width=1.5,
                   dashed=True, label_size=13, label_family=dl.M, label_fill=dl.MUTED)
        else:
            dl.box(c, x, y, CELL_W, CELL_H, name, fill=color, label_size=13, label_family=dl.M)
        for k in range(len(SCANS)):
            entry = SEQ[fired[k] % len(SEQ)]  # each scan sits on its own next entry
            y = lane_y[k + 1] + (LANE_H - CELL_H) / 2
            if turn == k and not no_scan:
                dl.box(c, x, y, CELL_W, CELL_H, entry, fill=dl.GREEN, label_size=13, label_family=dl.M)
            elif turn == k:
                dl.box(c, x, y, CELL_W, CELL_H, entry, fill=dl.WHITE, stroke=dl.GREEN, stroke_width=2,
                       dashed=True, label_size=13, label_family=dl.M)
            else:
                dl.box(c, x, y, CELL_W, CELL_H, entry, fill=dl.WHITE, stroke=dl.FAINT, stroke_width=1.5,
                       label_size=13, label_family=dl.M, label_weight="normal")
        if not no_scan:                       # a firing: this scan's position and the cycle move
            fired[turn] += 1
            pending = (pending + 1) % len(SCANS)

    # the two non-firing windows share one annotation
    for s in NO_SCAN_WINDOWS:
        _edge(c, col_cx(s), lanes_bottom + 6, col_cx(s), BRACKET_Y, dl.GREY, 1.2)
    _edge(c, col_cx(NO_SCAN_WINDOWS[0]), BRACKET_Y, col_cx(NO_SCAN_WINDOWS[-1]), BRACKET_Y, dl.GREY, 1.2)
    mid = (col_cx(NO_SCAN_WINDOWS[0]) + col_cx(NO_SCAN_WINDOWS[-1])) / 2
    _segments(c, mid, ANNOT_Y, [
        ("no scheduled scan time in this window →", 12, "normal", dl.DK, dl.F),
        ("no radar frame", 12, "normal", dl.DK, dl.F),
    ], anchor="middle")

    dl.legend(c, PAD, LEGEND_Y, [
        ("the scan fires in this window and meets this entry", dl.GREEN),
        ("its turn, but no scan time in the window: no scan fires and the position stays unchanged",
         dl.GREEN, "outline"),
        ("window with no scheduled scan time: no radar frame is published", dl.FAINT),
    ], horizontal=False)
    _segments(c, PAD, FOOT_Y, [
        ("Each scan visits every entry as it fires. Read",
         12.5, "normal", dl.DK, dl.F),
        ("maxVelMps", 12.5, "normal", dl.DK, dl.M),
        ("from the frame.", 12.5, "normal", dl.DK, dl.F),
    ])

    dl.validate(c)
    dl.write_svg(out_dir / "radar_scan_cycle_timeline.svg", c.render())


def radar_custom_gain_grid_layout(out_dir: pathlib.Path) -> None:
    """A 2 x 3 gain grid and the one-dimensional array it is authored as."""
    W, H = 1000, 504
    RH_X, RH_W = 44, 96                       # row header column (ElDeg)
    GX, CW, PITCH = 150, 96, 104              # grid and array cells
    TITLE_Y = 44
    HDR_Y, HDR_H = 60, 40                     # column headers (AzDeg)
    ROW_Y0, ROW_H, ROW_PITCH = 116, 56, 64
    AZ = ("−66", "0", "66")
    EL = ("−20", "20")
    ROW_COLORS = (dl.BLUE, dl.PURPLE)
    ORDER_NOTE_Y = 262                        # "ordered lowest to highest" under the row headers
    ARR_Y, ARR_H = 330, 56
    IDX_Y = ARR_Y + ARR_H + 16
    BR_Y, BR_TICK = 414, 6                    # bracket under each array segment
    BR_TEXT_Y = 444
    ANN_X, ANN_Y, ANN_LH = 500, 72, 22        # annotation block
    ROUTE_LEFT_X, ROUTE_RIGHT_X, ROUTE_Y = 26, 480, 300   # the two row -> segment routes
    LEGEND_Y = 470

    grid_right = GX + len(AZ) * PITCH - (PITCH - CW)

    c = dl.Canvas(
        W, H, "Radar custom gain grid layout",
        "A grid with the azimuth angles of AzDeg along the top and the elevation angles of ElDeg down "
        "the side, each cell holding the sum of a co-polarization and a cross-polarization gain. "
        "Beside it the same values laid out as the one-dimensional gain array: the first row of the "
        "grid, for the first elevation angle, walking every azimuth angle, then the second row, and "
        "so on.")

    # grid
    title_w = dl.text_width("AzDeg", 12, "normal", dl.M)
    dl.text(c, GX, TITLE_Y, "AzDeg", 12, "normal", "start", dl.GREY, dl.M)
    dl.text(c, GX + title_w + 12, TITLE_Y, "lowest → highest", 11.5, "normal", "start", dl.GREY)
    dl.text(c, RH_X, TITLE_Y, "ElDeg", 12, "normal", "start", dl.GREY, dl.M)
    for i, az in enumerate(AZ):
        dl.box(c, GX + i * PITCH, HDR_Y, CW, HDR_H, az, sublabel=f"[{i}]", label_size=13,
               label_family=dl.M)
    for k, el in enumerate(EL):
        y = ROW_Y0 + k * ROW_PITCH
        dl.box(c, RH_X, y, RH_W, ROW_H, el, sublabel=f"[{k}]", label_size=13, label_family=dl.M)
        for i in range(len(AZ)):
            dl.box(c, GX + i * PITCH, y, CW, ROW_H, "co + cross", fill=dl.WHITE, stroke=ROW_COLORS[k],
                   stroke_width=2, label_size=12.5, label_weight="normal")
    dl.text(c, RH_X, ORDER_NOTE_Y, "lowest ↓ highest", 11.5, "normal", "start", dl.GREY)

    # the one-dimensional array: row after row, each walking the azimuth angles
    n_az = len(AZ)
    for j in range(len(EL) * n_az):
        k, i = divmod(j, n_az)
        x = GX + j * PITCH
        b = dl.box(c, x, ARR_Y, CW, ARR_H, fill=dl.WHITE, stroke=ROW_COLORS[k], stroke_width=2)
        dl.text(c, b.cx, ARR_Y + 22, f"El {EL[k]}", 11.5, "normal", "middle", dl.GREY, dl.M)
        dl.text(c, b.cx, ARR_Y + 42, f"Az {AZ[i]}", 12.5, "bold", "middle", dl.DK, dl.M)
        dl.text(c, b.cx, IDX_Y, f"[{j}]", 11.5, "normal", "middle", dl.GREY, dl.M)
    for k in range(len(EL)):
        x0 = GX + k * n_az * PITCH
        x1 = x0 + (n_az - 1) * PITCH + CW
        color = ROW_COLORS[k]
        c.add(f'<path d="M{fmt(x0)},{fmt(BR_Y - BR_TICK)} L{fmt(x0)},{fmt(BR_Y)} L{fmt(x1)},{fmt(BR_Y)} '
              f'L{fmt(x1)},{fmt(BR_Y - BR_TICK)}" fill="none" stroke="{color}" stroke-width="1.5"/>')
        dl.text(c, (x0 + x1) / 2, BR_TEXT_Y, f"row for ElDeg[{k}] walking AzDeg[0..{n_az - 1}]", 12,
                "normal", "middle", dl.DK, dl.M)

    # routes: row 0 leaves the grid on the left, row 1 on the right, so the two never cross
    row_cy = [ROW_Y0 + k * ROW_PITCH + ROW_H / 2 for k in range(len(EL))]
    seg_cx = [GX + (k * n_az + 1) * PITCH + CW / 2 for k in range(len(EL))]
    dl.curve(c, [(RH_X, row_cy[0]), (ROUTE_LEFT_X, row_cy[0]), (ROUTE_LEFT_X, ROUTE_Y),
                 (seg_cx[0], ROUTE_Y), (seg_cx[0], ARR_Y - 2)], ROW_COLORS[0], 2, smooth=0)
    dl.curve(c, [(grid_right, row_cy[1]), (ROUTE_RIGHT_X, row_cy[1]), (ROUTE_RIGHT_X, ROUTE_Y),
                 (seg_cx[1], ROUTE_Y), (seg_cx[1], ARR_Y - 2)], ROW_COLORS[1], 2, smooth=0)

    # rules
    dl.text(c, ANN_X, ANN_Y, "Rules for a custom grid", 13, "bold", "start", dl.DK)
    _segments(c, ANN_X, ANN_Y + ANN_LH, [
        ("AzDeg and ElDeg:", 12.5, "normal", dl.DK, dl.F),
        ("txAntennaAzDeg, txAntennaElDeg", 12.5, "normal", dl.DK, dl.M),
    ])
    _segments(c, ANN_X, ANN_Y + ANN_LH * 2, [
        ("length = len(ElDeg) × len(AzDeg)", 12.5, "normal", dl.DK, dl.M),
        ("→ 2 × 3 = 6 here", 12.5, "normal", dl.GREY, dl.F),
    ])
    for n, line in enumerate(("angles ordered lowest to highest", "at least two angles per axis",
                              "zero gain outside the grid extent",
                              "gain at a grid point = co + cross, the sum of")):
        dl.text(c, ANN_X, ANN_Y + ANN_LH * (n + 3), line, 12.5, "normal", "start", dl.DK)
    dl.text(c, ANN_X, ANN_Y + ANN_LH * 7, "txAntennaCoGain + txAntennaCrossGain", 12.5, "normal",
            "start", dl.DK, dl.M)
    dl.text(c, ANN_X, ANN_Y + ANN_LH * 8, "the rx arrays follow the same layout and rules", 12,
            "normal", "start", dl.GREY)

    dl.legend(c, GX, LEGEND_Y, [("row for ElDeg[0] = −20°", dl.BLUE), ("row for ElDeg[1] = 20°", dl.PURPLE)])

    dl.validate(c)
    dl.write_svg(out_dir / "radar_custom_gain_grid_layout.svg", c.render())


def generate(out_dir: pathlib.Path) -> None:
    radar_attribute_namespaces(out_dir)
    radar_half_angle_field_of_view(out_dir)
    radar_scan_cycle_timeline(out_dir)
    radar_custom_gain_grid_layout(out_dir)


if __name__ == "__main__":
    generate(dl.output_dir(__file__))
