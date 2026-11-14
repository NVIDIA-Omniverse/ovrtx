#!/usr/bin/env python3
"""Figures of the Acoustic generic wpm model pages.

The array topology of the attributes page (mounts, receiver groups and a firing
sequence as four parallel arrays), the worked two-mount array of the how-to and the
layout of one SignalWays frame on the outputs page. Run in place with
``python3 -B _gen_acoustic.py`` or through ``generate_diagrams.py``.
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import _diagram_lib as dl

import math

_fmt = dl.fmt


# ------------------------------------------------------------------------ local helpers ---
def _lcg(seed: int, n: int):
    """A fixed pseudo-random sequence in [0, 1): the same numbers on every run."""
    x = seed & 0x7FFFFFFF
    out = []
    for _ in range(n):
        x = (1103515245 * x + 12345) & 0x7FFFFFFF
        out.append(x / 0x7FFFFFFF)
    return out


def _disc_mount(c, x, y, r, bore, color):
    """A transducer as a disc with a short arrow for its pointing direction (+x)."""
    c.add(f'<circle cx="{_fmt(x)}" cy="{_fmt(y)}" r="{_fmt(r)}" fill="{color}"/>')
    c.add(f'<circle cx="{_fmt(x)}" cy="{_fmt(y)}" r="{_fmt(r * 0.4)}" fill="{dl.WHITE}"/>')
    dl.arrow(c, x + r + 2, y, x + r + 2 + bore, y, stroke=color, width=2)


def _transducer(c, x, y, hw, hh, color):
    """A transducer seen from above: a housing with its membrane on the +x face."""
    c.add(f'<rect x="{_fmt(x - hw)}" y="{_fmt(y - hh)}" width="{_fmt(2 * hw)}" '
          f'height="{_fmt(2 * hh)}" rx="3" fill="{dl.DK}"/>')
    c.add(f'<circle cx="{_fmt(x + hw)}" cy="{_fmt(y)}" r="{_fmt(hh * 0.55)}" fill="{color}" '
          f'stroke="{dl.WHITE}" stroke-width="2"/>')


def _lobe(c, x, y, radii, half_angle_deg, color):
    """Nested arcs in front of a transducer: the outgoing pulse, spread about +x."""
    a = math.radians(half_angle_deg)
    for r in radii:
        x1, y1 = x + r * math.cos(a), y - r * math.sin(a)
        x2, y2 = x + r * math.cos(a), y + r * math.sin(a)
        c.add(f'<path d="M{_fmt(x1)},{_fmt(y1)} A{_fmt(r)},{_fmt(r)} 0 0 1 {_fmt(x2)},{_fmt(y2)}" '
              f'fill="none" stroke="{color}" stroke-width="1.5"/>')


def _bracket(c, x, y0, y1, tick, color, width=1.5):
    """A square bracket from y0 to y1 at x, opening toward -x, with a mid tick toward +x."""
    mid = (y0 + y1) / 2
    c.add(f'<path d="M{_fmt(x - tick)},{_fmt(y0)} L{_fmt(x)},{_fmt(y0)} L{_fmt(x)},{_fmt(y1)} '
          f'L{_fmt(x - tick)},{_fmt(y1)} M{_fmt(x)},{_fmt(mid)} L{_fmt(x + tick)},{_fmt(mid)}" '
          f'fill="none" stroke="{color}" stroke-width="{_fmt(width)}"/>')


def _dim_h(c, x0, x1, y, tick, color=dl.GREY):
    """A horizontal dimension line with end ticks."""
    c.add(f'<path d="M{_fmt(x0)},{_fmt(y - tick)} L{_fmt(x0)},{_fmt(y + tick)} '
          f'M{_fmt(x1)},{_fmt(y - tick)} L{_fmt(x1)},{_fmt(y + tick)} '
          f'M{_fmt(x0)},{_fmt(y)} L{_fmt(x1)},{_fmt(y)}" fill="none" stroke="{color}" stroke-width="1.5"/>')


def _dim_v(c, x, y0, y1, tick, color=dl.GREY):
    """A vertical dimension line with end ticks."""
    c.add(f'<path d="M{_fmt(x - tick)},{_fmt(y0)} L{_fmt(x + tick)},{_fmt(y0)} '
          f'M{_fmt(x - tick)},{_fmt(y1)} L{_fmt(x + tick)},{_fmt(y1)} '
          f'M{_fmt(x)},{_fmt(y0)} L{_fmt(x)},{_fmt(y1)}" fill="none" stroke="{color}" stroke-width="1.5"/>')


def _elbow(c, x1, y1, x2, y2, ym, r, stroke, width=2):
    """A connector that drops from (x1, y1) to y = ym, runs across to x2 and drops onto (x2, y2).

    Rounded corners of radius r; the arrowhead tip lands on (x2, y2). Unlike the library's S-curve
    it never sweeps diagonally through whatever lies between its two ends.
    """
    sx = 1 if x2 > x1 else -1
    d = (f"M{_fmt(x1)},{_fmt(y1)} V{_fmt(ym - r)} "
         f"A{_fmt(r)},{_fmt(r)} 0 0 {0 if sx > 0 else 1} {_fmt(x1 + sx * r)},{_fmt(ym)} "
         f"H{_fmt(x2 - sx * r)} "
         f"A{_fmt(r)},{_fmt(r)} 0 0 {1 if sx > 0 else 0} {_fmt(x2)},{_fmt(ym + r)}")
    c.add(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{_fmt(width)}"/>')
    dl.arrow(c, x2, ym + r, x2, y2, stroke=stroke, width=width)


def _hatch_defs(c, pattern_id, step, fill, stroke):
    """A diagonal hatch pattern usable as fill="url(#<pattern_id>)"."""
    c.add(f'<defs><pattern id="{pattern_id}" width="{_fmt(step)}" height="{_fmt(step)}" '
          f'patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
          f'<rect width="{_fmt(step)}" height="{_fmt(step)}" fill="{fill}"/>'
          f'<line x1="0" y1="0" x2="0" y2="{_fmt(step)}" stroke="{stroke}" stroke-width="2"/>'
          f'</pattern></defs>')


# ------------------------------------------------------------- 1. array topology (attributes) ---
def acoustic_array_topology(out_dir: pathlib.Path) -> None:
    W, H = 1180, 552
    HEAD_Y, SUB_Y = 36, 54                       # panel headings and their grey subtitles
    # left panel: the sensor frame with two mounts
    LX = 30
    OX, OY = 150, 290                            # frame origin
    XTIP, ZTIP = 400, 112                        # x axis tip (x), z axis tip (y)
    YTIP_X, YTIP_Y = 60, 225                     # y axis tip (up-left: away from the viewer)
    XLBL_Y, ZLBL_Y, YLBL_Y, YLBL_X = 306, 100, 196, 140   # axis label baselines; y label right edge
    M1 = (262, 250)                              # m001: ahead and to the left (+y side)
    M2 = (345, 332)                              # m002: ahead and to the right (-y side)
    M1_NAME_Y, M1_POS_Y, M1_ROT_Y = 196, 213, 229
    M2_NAME_Y, M2_POS_Y, M2_ROT_Y = 361, 378, 394
    MR, BORE = 9, 30
    # middle panel: receiver groups
    MX, GW, GH = 452, 200, 52
    G1_Y, G2_Y = 92, 186
    # right panel: the firing sequence as four parallel arrays
    RX = 700
    ROWLBL_X = 835                               # right edge of the row labels
    COL0_X, COL1_X, CW, CH = 848, 926, 70, 34
    ROW0_Y, ROW_STEP = 108, 42
    EVHDR_Y = 97
    BRK_X, BRK_TICK = 1012, 8
    BRKLBL_X = 1024
    # bottom: the signal ways of one frame
    SW_Y, SW_W, SW_H, SW_X0, SW_STEP = 418, 185, 52, 400, 193
    RES_Y, LEG_Y, FOOT_Y = 414, 430, 528

    c = dl.Canvas(W, H, "Mounts, receiver groups and firing sequences of an acoustic array",
                  "Two mounts m001 and m002 placed in the sensor frame, two receiver groups as sets of "
                  "mount indices, a firing sequence as four parallel arrays with one column per event, "
                  "and the signal ways the two events write.")

    # ---- left: sensor frame and mounts
    dl.text(c, LX, HEAD_Y, "Sensor mounts", 14, "bold")
    dl.text(c, LX, SUB_Y, "placed in the sensor's own frame", 12, fill=dl.GREY)
    dl.arrow(c, OX, OY, XTIP, OY, stroke=dl.GREY, width=2)
    dl.arrow(c, OX, OY, OX, ZTIP, stroke=dl.GREY, width=2)
    dl.arrow(c, OX, OY, YTIP_X, YTIP_Y, stroke=dl.GREY, width=2)
    c.add(f'<circle cx="{_fmt(OX)}" cy="{_fmt(OY)}" r="3.5" fill="{dl.DK}"/>')
    dl.text(c, OX - 8, OY + 14, "origin", 11, anchor="end", fill=dl.GREY)
    dl.text(c, XTIP, XLBL_Y, "x forward: the firing axis (prim's local -Z)", 12, anchor="end", fill=dl.DK)
    dl.text(c, OX + 8, ZLBL_Y, "z up (prim's local +Y)", 12, fill=dl.DK)
    dl.text(c, YLBL_X, YLBL_Y, "y left", 12, anchor="end", fill=dl.DK)
    dl.text(c, YLBL_X, YLBL_Y + 17, "(prim's local -X)", 12, anchor="end", fill=dl.DK)
    for (mx, my), name, ny, py, ry in ((M1, "m001 (index 0)", M1_NAME_Y, M1_POS_Y, M1_ROT_Y),
                                        (M2, "m002 (index 1)", M2_NAME_Y, M2_POS_Y, M2_ROT_Y)):
        _disc_mount(c, mx, my, MR, BORE, dl.DK)
        dl.text(c, mx, ny, name, 12, "bold", anchor="middle")
        dl.text(c, mx, py, "position [x, y, z] m", 11, anchor="middle", fill=dl.GREY)
        dl.text(c, mx, ry, "rotation [roll, pitch, yaw] deg", 11, anchor="middle", fill=dl.GREY)

    # ---- middle: receiver groups
    dl.text(c, MX, HEAD_Y, "Receiver groups", 14, "bold")
    dl.text(c, MX, SUB_Y, "receiverIndices: sets of mount indices", 12, fill=dl.GREY)
    for gy, label, note in ((G1_Y, "g001 = [0, 1]", "m001 and m002 listen together"),
                            (G2_Y, "g002 = [0, 1]", "both listen again, on another channel id")):
        dl.box(c, MX, gy, GW, GH, label, fill=dl.PANEL, label_size=14, label_weight="normal",
               label_family=dl.M)
        dl.text(c, MX + GW / 2, gy + GH + 16, note, 11, anchor="middle", fill=dl.GREY)

    # ---- right: firing sequence
    dl.text(c, RX, HEAD_Y, "Firing sequence seq001", 14, "bold")
    dl.text(c, RX, SUB_Y, "four parallel arrays, one entry per event", 12, fill=dl.GREY)
    dl.text(c, COL0_X + CW / 2, EVHDR_Y, "event 0", 12, "bold", anchor="middle", fill=dl.BLUE)
    dl.text(c, COL1_X + CW / 2, EVHDR_Y, "event 1", 12, "bold", anchor="middle", fill=dl.PURPLE)
    rows = (("eventTimeNs", "0", "5000"), ("txSensorId", "0", "1"),
            ("rxGroupId", "0", "1"), ("channel", "0", "1"))
    for i, (name, v0, v1) in enumerate(rows):
        ry = ROW0_Y + i * ROW_STEP
        dl.text(c, ROWLBL_X, ry + CH / 2 + 4.5, name, 12, anchor="end", family=dl.M)
        dl.box(c, COL0_X, ry, CW, CH, v0, fill=dl.WHITE, stroke=dl.BLUE, stroke_width=1.5,
               label_size=13, label_weight="normal", label_family=dl.M)
        dl.box(c, COL1_X, ry, CW, CH, v1, fill=dl.WHITE, stroke=dl.PURPLE, stroke_width=1.5,
               label_size=13, label_weight="normal", label_family=dl.M)
    rows_bottom = ROW0_Y + (len(rows) - 1) * ROW_STEP + CH
    _bracket(c, BRK_X, ROW0_Y, rows_bottom, BRK_TICK, dl.GREY)
    mid = (ROW0_Y + rows_bottom) / 2
    dl.text(c, BRKLBL_X, mid - 3, "column i", 12, fill=dl.GREY)
    dl.text(c, BRKLBL_X, mid + 14, "is one event", 12, fill=dl.GREY)

    # ---- bottom: the signal ways the two events write
    dl.text(c, LX, RES_Y, "Signal ways of one frame", 13, "bold")
    dl.legend(c, LX, LEG_Y, (
        ("event 0: mount 0 fires into g001 = [0, 1], channel id 0", dl.BLUE, "line"),
        ("event 1: mount 1 fires into g002 = [0, 1], channel id 1", dl.PURPLE, "line"),
    ), horizontal=False)
    sw = []
    specs = (("receiver 0, channel id 0", dl.BLUE), ("receiver 1, channel id 0", dl.BLUE),
             ("receiver 0, channel id 1", dl.PURPLE), ("receiver 1, channel id 1", dl.PURPLE))
    for i, (label, color) in enumerate(specs):
        x = SW_X0 + i * SW_STEP
        r = dl.box(c, x, SW_Y, SW_W, SW_H, label, fill=dl.PANEL, stroke=color, stroke_width=2,
                   label_size=13)
        sw.append(r)
    col0_cx, col1_cx = COL0_X + CW / 2, COL1_X + CW / 2
    dl.connector(c, col0_cx, rows_bottom + 2, sw[0].cx, SW_Y - 2, stroke=dl.BLUE, width=2, vertical=True)
    dl.connector(c, col0_cx, rows_bottom + 2, sw[1].cx, SW_Y - 2, stroke=dl.BLUE, width=2, vertical=True)
    dl.connector(c, col1_cx, rows_bottom + 2, sw[2].cx, SW_Y - 2, stroke=dl.PURPLE, width=2, vertical=True)
    dl.connector(c, col1_cx, rows_bottom + 2, sw[3].cx, SW_Y - 2, stroke=dl.PURPLE, width=2, vertical=True)
    dl.text(c, LX, FOOT_Y, "numSignalWays = mounts × distinct channel ids = 2 × 2 = 4, and both events together fill all four",
            13, fill=dl.DK)

    dl.validate(c)
    dl.write_svg(out_dir / "acoustic_array_topology.svg", c.render())


# ------------------------------------------------------- 2. worked two-mount array (how-to) ---
def acoustic_array_worked_example(out_dir: pathlib.Path) -> None:
    W, H = 1180, 390
    SCALE = 100.0                                 # px per meter
    OX, OY = 90, 170                              # prim origin in the drawing
    XAX_LEN, YAX_LEN = 110, 85                    # short frame axes at the origin
    M1 = (OX + 4.0 * SCALE, OY - 0.5 * SCALE)     # m001 at (4.0, 0.5): ahead, to the left
    M2 = (OX + 4.0 * SCALE, OY + 0.5 * SCALE)     # m002 at (4.0, -0.5): ahead, to the right
    HW, HH = 11, 13                               # transducer housing half size
    LOBE_R, LOBE_HALF = (16, 24, 32), 38
    SURF_X, SURF_W, SURF_Y0, SURF_Y1 = 800, 10, 56, 290   # right of the event labels
    BOW = 26                                      # how far a same-mount echo bows off its pulse
    DIM4_Y, DIM1_X = 302, OX + 4.0 * SCALE - HW - 12   # dimension lines: 4 m ahead, 1 m apart
    BRK1_X, BRK2_X, BRK_Y0, BRK_Y1, BRK_TICK = 430, 416, 101, 239, 6
    GRP_LBL_X = 404
    EV0_X, EV0_Y = 580, 64                       # event annotations beside the pulses
    EV1_X, EV1_Y = 580, 278
    # right: the 2 x 2 grid of signal ways
    GX_LBL, GC0_X, GC1_X, GCW, GCH = 978, 986, 1066, 70, 56
    GHDR_Y, GR0_Y, GR1_Y = 112, 120, 188
    GTITLE_Y, GNOTE_Y, GNOTE2_Y = 76, 278, 296
    LEG_Y0, LEG_Y1 = 336, 360

    c = dl.Canvas(W, H, "The worked two-mount acoustic array, seen from above",
                  "Top view of the sensor frame with mounts m001 and m002 four meters ahead of the "
                  "prim origin and one meter apart, both receiver groups listening, event 0 from m001 "
                  "on channel id 0 and event 1 from m002 on channel id 1, each echo returning to both "
                  "mounts, and the two-by-two grid of the four signal ways they fill.")

    # ---- frame axes and origin
    dl.arrow(c, OX, OY, OX + XAX_LEN, OY, stroke=dl.GREY, width=2)
    dl.arrow(c, OX, OY, OX, OY - YAX_LEN, stroke=dl.GREY, width=2)
    c.add(f'<circle cx="{_fmt(OX)}" cy="{_fmt(OY)}" r="4" fill="{dl.DK}"/>')
    dl.text(c, OX + XAX_LEN + 6, OY + 4, "x forward", 12)
    dl.text(c, OX + 8, OY - YAX_LEN + 4, "y left", 12)
    dl.text(c, OX, OY + 24, "prim origin", 12, anchor="middle", fill=dl.GREY)
    dl.text(c, OX, OY + 40, "(z up, out of the page)", 11, anchor="middle", fill=dl.GREY)

    # ---- mounts, their labels, the 4 m and 1 m dimensions
    for (mx, my), name, pos, ny, py, color in (
            (M1, "m001 (index 0)", "position (4.0, 0.5, 0.5) m", M1[1] - HH - 30, M1[1] - HH - 13, dl.BLUE),
            (M2, "m002 (index 1)", "position (4.0, -0.5, 0.5) m", M2[1] + HH + 20, M2[1] + HH + 37, dl.PURPLE)):
        _transducer(c, mx, my, HW, HH, color)
        dl.text(c, mx, ny, name, 12, "bold", anchor="middle")
        dl.text(c, mx, py, pos, 11, anchor="middle", fill=dl.GREY)
    _dim_h(c, OX, M1[0], DIM4_Y, 5)
    dl.text(c, (OX + M1[0]) / 2, DIM4_Y - 7, "4.0 m ahead of the origin", 12, anchor="middle", fill=dl.GREY)
    _dim_v(c, DIM1_X, M1[1], M2[1], 5)
    dl.text(c, DIM1_X + 9, OY + 4, "1 m", 12, fill=dl.GREY)

    # ---- receiver groups: both bracket both mounts
    _bracket(c, BRK1_X, BRK_Y0, BRK_Y1, BRK_TICK, dl.GREY)
    _bracket(c, BRK2_X, BRK_Y0 - 6, BRK_Y1 + 6, BRK_TICK, dl.MUTED)
    dl.text(c, GRP_LBL_X, OY - 12, "g001 = [0, 1]", 12, anchor="end", family=dl.M)
    dl.text(c, GRP_LBL_X, OY + 6, "g002 = [0, 1]", 12, anchor="end", family=dl.M)
    dl.text(c, GRP_LBL_X, OY + 24, "both groups: m001 and m002 listen", 11, anchor="end", fill=dl.GREY)

    # ---- the reflecting surface and the two events
    c.add(f'<rect x="{_fmt(SURF_X)}" y="{_fmt(SURF_Y0)}" width="{_fmt(SURF_W)}" '
          f'height="{_fmt(SURF_Y1 - SURF_Y0)}" fill="{dl.FAINT}"/>')
    dl.text(c, SURF_X + SURF_W / 2, SURF_Y0 - 10, "a reflecting surface ahead", 11, anchor="middle",
            fill=dl.GREY)
    front1, front2 = M1[0] + HW + HH * 0.55 + 2, M2[0] + HW + HH * 0.55 + 2
    _lobe(c, M1[0] + HW, M1[1], LOBE_R, LOBE_HALF, dl.BLUE)
    _lobe(c, M2[0] + HW, M2[1], LOBE_R, LOBE_HALF, dl.PURPLE)
    # event 0: m001 fires, the echo comes back to m001 (bowed) and to m002 (diagonal)
    dl.arrow(c, front1 + LOBE_R[-1], M1[1], SURF_X - 2, M1[1], stroke=dl.BLUE, width=2)
    dl.curve(c, [(SURF_X, M1[1] - 6), ((SURF_X + front1) / 2, M1[1] - BOW), (front1, M1[1] - 4)],
             stroke=dl.BLUE, width=2, dashed=True)
    dl.curve(c, [(SURF_X, M1[1] + 6), (front2 + 2, M2[1] - 6)], stroke=dl.BLUE, width=2, dashed=True)
    # event 1: m002 fires, the echo comes back to m002 (bowed) and to m001 (diagonal)
    dl.arrow(c, front2 + LOBE_R[-1], M2[1], SURF_X - 2, M2[1], stroke=dl.PURPLE, width=2)
    dl.curve(c, [(SURF_X, M2[1] + 6), ((SURF_X + front2) / 2, M2[1] + BOW), (front2, M2[1] + 4)],
             stroke=dl.PURPLE, width=2, dashed=True)
    dl.curve(c, [(SURF_X, M2[1] - 6), (front1 + 2, M1[1] + 6)], stroke=dl.PURPLE, width=2, dashed=True)
    dl.text(c, EV0_X, EV0_Y, "event 0, t = 0", 12, "bold", fill=dl.BLUE)
    dl.text(c, EV0_X, EV0_Y + 17, "m001 fires into g001, channel id 0", 11, fill=dl.GREY)
    dl.text(c, EV1_X, EV1_Y, "event 1, t = 5000 ns", 12, "bold", fill=dl.PURPLE)
    dl.text(c, EV1_X, EV1_Y + 17, "m002 fires into g002, channel id 1", 11, fill=dl.GREY)

    # ---- right: the four signal ways
    dl.text(c, GX_LBL - 148, GTITLE_Y, "Signal ways of one frame", 13, "bold")
    dl.text(c, GC0_X + GCW / 2, GHDR_Y, "channel id 0", 12, anchor="middle", fill=dl.DK)
    dl.text(c, GC1_X + GCW / 2, GHDR_Y, "channel id 1", 12, anchor="middle", fill=dl.DK)
    for gy, name, idx in ((GR0_Y, "receiver m001", "(index 0)"), (GR1_Y, "receiver m002", "(index 1)")):
        dl.text(c, GX_LBL, gy + GCH / 2 - 4, name, 12, anchor="end")
        dl.text(c, GX_LBL, gy + GCH / 2 + 13, idx, 11, anchor="end", fill=dl.GREY)
        dl.box(c, GC0_X, gy, GCW, GCH, "event 0", fill=dl.WHITE, stroke=dl.BLUE, stroke_width=2,
               label_size=12, label_fill=dl.BLUE)
        dl.box(c, GC1_X, gy, GCW, GCH, "event 1", fill=dl.WHITE, stroke=dl.PURPLE, stroke_width=2,
               label_size=12, label_fill=dl.PURPLE)
    dl.text(c, GX_LBL - 148, GNOTE_Y, "numSignalWays = 2 mounts × 2 channel ids = 4", 12, "bold")
    dl.text(c, GX_LBL - 148, GNOTE2_Y, "with a reflecting surface ahead, all four can be VALID", 11,
            fill=dl.GREY)

    # ---- legend
    dl.legend(c, 30, LEG_Y0, (
        ("event 0: m001 fires at t = 0 into g001 on channel id 0", dl.BLUE, "line"),
        ("event 1: m002 fires at t = 5000 ns into g002 on channel id 1", dl.PURPLE, "line"),
    ))
    dl.legend(c, 30, LEG_Y1, (
        ("outgoing pulse", dl.DK, "line"),
        ("echo back to a receiving mount", dl.DK, "dashed"),
    ))

    dl.validate(c)
    dl.write_svg(out_dir / "acoustic_array_worked_example.svg", c.render())


# ------------------------------------------------------- 3. SignalWays frame layout (outputs) ---
def signal_ways_layout(out_dir: pathlib.Path) -> None:
    W, H = 1180, 648
    TITLE_Y, SUB_Y, HDR_Y, OVER_Y = 28, 46, 64, 44   # title, its subtitle, column headers, "one entry per row"
    NS, N_ROWS, N_IDS = 320, 6, 2                 # samples per signal way, rows, channel ids
    GRID_X, GRID_W = 196, 420
    ROW_Y, ROW_H = 74, 48
    PX = GRID_W / NS
    W_X, LBL_X, AXL_X = 36, 184, 172              # w column center, right edge of row labels, of axis titles
    COLS_X, COL_W, COL_GAP = 636, 96, 6           # the five one-entry-per-row channels
    AX1_Y, AX2_Y = ROW_Y + N_ROWS * ROW_H + 10, ROW_Y + N_ROWS * ROW_H + 50
    EXPL_X, EXPL_Y, EXPL2_Y = 650, AX1_Y + 14, AX1_Y + 31  # range-axis explanation, right of the axes
    STRIP_X, STRIP_Y, STRIP_W, STRIP_H = 196, 512, 940, 24
    NOTE_Y, NOTE2_Y = 560, 578
    PAR_X, PAR_Y, PAR_W, PAR_H = 960, 548, 210, 84
    LEG_X, LEG_Y = 650, 424                       # legend under the explanation
    MARK_W, MARK_S = 5, 260                       # the highlighted cell: last row, sample 260
    ELBOW_Y, ELBOW_R = 482, 10                    # the cell-to-strip connector runs across at this y
    SAMPLE_M = 102.4e-6 * 343.21 / 2              # meters of range per sample, basic mode
    BASE_UP, PEAK_H, NOISE = 7, 32, 0.07          # envelope geometry inside a row

    c = dl.Canvas(W, H, "Layout of one SignalWays frame",
                  "Amplitudes reshaped to six rows of 320 samples, one per signal way of a three-mount, "
                  "two-channel-id sensor; the row index is the receiving mount index times two plus the "
                  "channel id. Beside the grid the five per-signal-way channels hold one entry per row, "
                  "and only the VALID bit of Flags separates a silent row from one that received an echo. "
                  "Axes under the grid convert the sample index to range, and a strip below shows the "
                  "flat storage order.")
    _hatch_defs(c, "hatch", 6, dl.PANEL, dl.FAINT)

    dl.text(c, 30, TITLE_Y, "Amplitudes, reshaped: one row per signal way, 320 samples each", 14, "bold")
    dl.text(c, 30, SUB_Y, "a three-mount sensor whose firing sequences use channel ids 0 and 1: 3 × 2 = 6 signal ways",
            12, fill=dl.GREY)
    dl.text(c, LBL_X, HDR_Y, "w = mount × 2 + channel id", 11, anchor="end", fill=dl.DK)
    cols = ("TransmitterIds", "ReceiverIds", "ChannelIds", "TimeOffsetNs", "Flags")
    col_x = [COLS_X + i * (COL_W + COL_GAP) for i in range(len(cols))]
    dl.text(c, (col_x[0] + col_x[-1] + COL_W) / 2, OVER_Y, "one entry per signal way", 12,
            anchor="middle", fill=dl.GREY)
    for x, name in zip(col_x, cols):
        dl.text(c, x + COL_W / 2, HDR_Y, name, 11, anchor="middle", family=dl.M)

    # rows: (mount, id, echo?, peaks [(sample, amplitude)], tx, rx, cid, t)
    rows = (
        (0, 0, True, ((170, 0.85), (214, 0.3)), "0", "0", "0", "0"),
        (0, 1, False, (), "0", "0", "0", "0"),
        (1, 0, True, ((173, 0.7),), "0", "1", "0", "0"),
        (1, 1, False, (), "0", "0", "0", "0"),
        (2, 0, True, ((177, 0.6), (240, 0.25)), "0", "2", "0", "0"),
        (2, 1, True, ((128, 0.75), (186, 0.35)), "1", "2", "1", "5000"),
    )
    c.add(f'<rect x="{_fmt(GRID_X)}" y="{_fmt(ROW_Y)}" width="{_fmt(GRID_W)}" '
          f'height="{_fmt(N_ROWS * ROW_H)}" fill="{dl.WHITE}" stroke="{dl.GREY}" stroke-width="1.5"/>')
    for w, (mount, cid, echo, peaks, tx, rx, ch, t) in enumerate(rows):
        y0 = ROW_Y + w * ROW_H
        if w:
            c.add(f'<line x1="{_fmt(GRID_X)}" y1="{_fmt(y0)}" x2="{_fmt(GRID_X + GRID_W)}" '
                  f'y2="{_fmt(y0)}" stroke="{dl.FAINT}" stroke-width="1"/>')
        dl.text(c, W_X, y0 + ROW_H / 2 + 4.5, str(w), 12, anchor="middle", family=dl.M)
        dl.text(c, LBL_X, y0 + ROW_H / 2 + 4.5, f"mount {mount}, channel id {cid}", 12, anchor="end")
        # the envelope: a noisy baseline, plus peaks in the rows that received an echo
        base = y0 + ROW_H - BASE_UP
        noise = _lcg(1000 + w, NS)
        pts = []
        for s in range(0, NS, 2):
            v = NOISE * noise[s]
            for ps, pa in peaks:
                v += pa * math.exp(-((s - ps) ** 2) / (2 * 5.0 ** 2))
            pts.append(f"{_fmt(GRID_X + s * PX)},{_fmt(base - min(v, 1.0) * PEAK_H)}")
        c.add(f'<path d="M{" L".join(pts)}" fill="none" stroke="{dl.GREEN if echo else dl.GREY}" '
              f'stroke-width="1.5"/>')
        # the five one-entry channels
        for x, val in zip(col_x, (tx, rx, ch, t)):
            dl.box(c, x, y0 + 4, COL_W, ROW_H - 8, val, fill=dl.WHITE, stroke=dl.FAINT, stroke_width=1,
                   rx=3, label_size=12, label_weight="normal", label_family=dl.M)
        fx = col_x[4]
        if echo:
            dl.box(c, fx, y0 + 4, COL_W, ROW_H - 8, "0x40", fill=dl.GREEN, rx=3, label_size=12,
                   label_weight="bold", label_family=dl.M)
        else:
            dl.box(c, fx, y0 + 4, COL_W, ROW_H - 8, "0", fill="url(#hatch)", stroke=dl.FAINT,
                   stroke_width=1, rx=3, label_size=12, label_weight="normal", label_family=dl.M,
                   label_fill=dl.DK)

    # the highlighted cell and its place in the flat tensor
    mark_x = GRID_X + MARK_S * PX
    mark_y0 = ROW_Y + MARK_W * ROW_H
    c.add(f'<rect x="{_fmt(mark_x - 2)}" y="{_fmt(mark_y0 + 2)}" width="4" height="{_fmt(ROW_H - 4)}" '
          f'rx="1" fill="{dl.ORANGE}"/>')

    # axes: sample index, then range at the default sample duration
    s_ticks = (0, 80, 160, 240, 319)
    dl.tick_marks(c, GRID_X, AX1_Y, GRID_W, [s * PX for s in s_ticks], [str(s) for s in s_ticks])
    dl.text(c, AXL_X, AX1_Y + 18, "sample index s", 12, anchor="end", fill=dl.GREY)
    m_ticks = (1, 2, 3, 4, 5)
    # Bin s begins at (s + 1) sample periods of round-trip time.
    r_pos = [0] + [(m / SAMPLE_M - 1) * PX for m in m_ticks] + [(NS - 1) * PX]
    r_lbl = ["0.018 m"] + [f"{m} m" for m in m_ticks] + ["≈ 5.6 m"]
    dl.tick_marks(c, GRID_X, AX2_Y, GRID_W, r_pos, r_lbl)
    dl.text(c, AXL_X - 20, AX2_Y + 18, "range", 12, anchor="end", fill=dl.GREY)
    dl.text(c, EXPL_X, EXPL_Y, "bin lower bound at sampleDuration = 102.4 us:", 12, fill=dl.GREY)
    dl.text(c, EXPL_X, EXPL2_Y, "about 1.8 cm per sample; the 320 samples reach about 5.6 m", 12, fill=dl.GREY)

    # params box
    dl.box(c, PAR_X, PAR_Y, PAR_W, PAR_H, fill=dl.PANEL)
    dl.text(c, PAR_X + 12, PAR_Y + 18, "params", 11, "bold", fill=dl.GREY)
    for i, line in enumerate(("numSignalWays = 6", "numSamplesPerSignalWay = 320", "numElements = 1920")):
        dl.text(c, PAR_X + 12, PAR_Y + 38 + i * 18, line, 11, family=dl.M)

    # the flat Amplitudes tensor: row after row
    n_el = N_ROWS * NS
    epx = STRIP_W / n_el
    c.add(f'<rect x="{_fmt(STRIP_X)}" y="{_fmt(STRIP_Y)}" width="{_fmt(STRIP_W)}" height="{_fmt(STRIP_H)}" '
          f'rx="3" fill="{dl.WHITE}" stroke="{dl.GREY}" stroke-width="1.5"/>')
    for w in range(N_ROWS):
        x0 = STRIP_X + w * NS * epx
        if w:
            c.add(f'<line x1="{_fmt(x0)}" y1="{_fmt(STRIP_Y)}" x2="{_fmt(x0)}" y2="{_fmt(STRIP_Y + STRIP_H)}" '
                  f'stroke="{dl.FAINT}" stroke-width="1"/>')
        dl.text(c, x0 + NS * epx / 2, STRIP_Y + STRIP_H / 2 + 4, f"w = {w}", 11, anchor="middle",
                family=dl.M, fill=dl.GREY)
    dl.text(c, LBL_X, STRIP_Y + 8, "Amplitudes as stored", 12, anchor="end", fill=dl.GREY)
    dl.text(c, LBL_X, STRIP_Y + 25, "(1920 entries)", 11, anchor="end", fill=dl.GREY)
    entry = MARK_W * NS + MARK_S
    ex = STRIP_X + entry * epx
    c.add(f'<rect x="{_fmt(ex - 1.5)}" y="{_fmt(STRIP_Y)}" width="3" height="{_fmt(STRIP_H)}" '
          f'fill="{dl.ORANGE}"/>')
    _elbow(c, mark_x, mark_y0 + ROW_H, ex, STRIP_Y - 1, ELBOW_Y, ELBOW_R, dl.ORANGE, width=2)
    dl.text(c, GRID_X, NOTE_Y, "sample s of signal way w is entry w × numSamplesPerSignalWay + s", 13)
    dl.text(c, GRID_X, NOTE2_Y, f"here w = {MARK_W}, s = {MARK_S}: entry {MARK_W} × {NS} + {MARK_S} = {entry}",
            12, fill=dl.GREY)

    # legend
    dl.legend(c, LEG_X, LEG_Y, (
        ("VALID (0x40): this signal way received an echo", dl.GREEN),
    ))
    hy = LEG_Y + 24
    c.add(f'<rect x="{_fmt(LEG_X)}" y="{_fmt(hy)}" width="12" height="12" rx="2" fill="url(#hatch)" '
          f'stroke="{dl.FAINT}" stroke-width="1"/>')
    dl.text(c, LEG_X + 19, hy + 10.5, "Flags 0: silent, though its ids read 0, 0, 0, 0 too", 12)

    dl.validate(c)
    dl.write_svg(out_dir / "signal_ways_layout.svg", c.render())


# ----------------------------------------------------------------------------------- entry ---
def generate(out_dir: pathlib.Path) -> None:
    acoustic_array_topology(out_dir)
    acoustic_array_worked_example(out_dir)
    signal_ways_layout(out_dir)


if __name__ == "__main__":
    generate(dl.output_dir(__file__))
