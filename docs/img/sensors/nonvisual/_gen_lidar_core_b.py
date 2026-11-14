import pathlib, sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))  # noqa: E401,E702
import _diagram_lib as dl  # noqa: E402
import math  # noqa: E402

# Lidar generic core model, group B: the detection floor under each processing mode, the
# beam waist / divergence pair, and the motion BVH and compensation grid. One function per
# figure; ``generate`` writes them all.


# ------------------------------------------------------------------------------ small helpers ---
def _poly(c, pts, stroke, width=2, dashed=False, fill="none", opacity=None, close=False, dotted=False):
    """A polyline (or closed polygon) through ``pts``, written as one path."""
    d = " ".join(("M" if i == 0 else "L") + f"{dl.fmt(x)},{dl.fmt(y)}" for i, (x, y) in enumerate(pts))
    if close:
        d += " Z"
    attrs = f'd="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{dl.fmt(width)}"'
    if dotted:
        attrs += f' stroke-dasharray="{dl.fmt(width)} {dl.fmt(2.5 * width)}"'
    elif dashed:
        attrs += f' stroke-dasharray="{dl.fmt(3 * width)} {dl.fmt(2 * width)}"'
    if opacity is not None:
        attrs += f' fill-opacity="{dl.fmt(opacity)}"'
    if stroke != "none":
        attrs += ' stroke-linejoin="round" stroke-linecap="round"'
    c.add(f"<path {attrs}/>")


def _line(c, x1, y1, x2, y2, stroke, width=1.5, dashed=False, dotted=False):
    _poly(c, [(x1, y1), (x2, y2)], stroke, width, dashed=dashed, dotted=dotted)


def _dot(c, x, y, r, fill, stroke="none", width=1):
    attrs = f'cx="{dl.fmt(x)}" cy="{dl.fmt(y)}" r="{dl.fmt(r)}" fill="{fill}"'
    if stroke != "none":
        attrs += f' stroke="{stroke}" stroke-width="{dl.fmt(width)}"'
    c.add(f"<circle {attrs}/>")


def _ellipse(c, cx, cy, rx, ry, fill, opacity, stroke, width=1.2):
    c.add(f'<ellipse cx="{dl.fmt(cx)}" cy="{dl.fmt(cy)}" rx="{dl.fmt(rx)}" ry="{dl.fmt(ry)}" '
          f'fill="{fill}" fill-opacity="{dl.fmt(opacity)}" stroke="{stroke}" stroke-width="{dl.fmt(width)}"/>')


def _vtext(c, x, y, s, size=12, fill=dl.GREY, weight="normal", family=dl.F):
    """One line of text rotated to read bottom-to-top, centered on (x, y); registered for the checks."""
    attrs = (f'x="{dl.fmt(x)}" y="{dl.fmt(y)}" font-family="{family}" font-size="{dl.fmt(size)}" '
             f'fill="{fill}" text-anchor="middle" transform="rotate(-90 {dl.fmt(x)} {dl.fmt(y)})"')
    if str(weight) != "normal":
        attrs += f' font-weight="{weight}"'
    c.add(f"<text {attrs}>{dl.esc(s)}</text>")
    w = dl.text_width(s, size, weight, family)
    c.note_text(dl.TextBox(round(x - 0.78 * size, 2), round(y - w / 2, 2),
                           round(x + 0.24 * size, 2), round(y + w / 2, 2), s))


def _mixed(c, x, y, parts, anchor="start"):
    """Several text runs on one baseline, each ``(string, size, weight, family, fill)``.

    Returns the x where the last run ends. ``anchor`` is start/middle/end for the whole line.
    """
    total = sum(dl.text_width(s, size, weight, family) for s, size, weight, family, _ in parts)
    cur = float(x) - (total / 2 if anchor == "middle" else total if anchor == "end" else 0.0)
    boxes = []
    for s, size, weight, family, fill in parts:
        boxes.append(dl.text(c, cur, y, s, size, weight, "start", fill, family))
        cur += dl.text_width(s, size, weight, family)
    # the runs are one line: register them as one box, so they do not count as touching labels
    del c.texts[len(c.texts) - len(boxes):]
    c.note_text(dl.TextBox(boxes[0].x0, min(b.y0 for b in boxes), boxes[-1].x1, max(b.y1 for b in boxes),
                           "".join(p[0] for p in parts)))
    return cur


def _dimension_h(c, x1, x2, y, color=dl.DK, width=1.2, tick=5):
    """A horizontal dimension line between two extension ticks, arrowheads at both ends."""
    mid = (float(x1) + float(x2)) / 2
    dl.arrow(c, mid, y, x1, y, stroke=color, width=width)
    dl.arrow(c, mid, y, x2, y, stroke=color, width=width)
    for x in (x1, x2):
        _line(c, x, y - tick, x, y + tick, color, 1)


def _sensor(c, x, y_ground, fill=dl.DK, ghost=False):
    """A small scanning-sensor glyph standing on ``y_ground`` at ``x``: a body and a round head."""
    BODY_W, BODY_H, HEAD_R = 18.0, 8.0, 3.6
    bx, by = float(x) - BODY_W / 2, float(y_ground) - BODY_H
    if ghost:
        c.add(f'<rect x="{dl.fmt(bx)}" y="{dl.fmt(by)}" width="{dl.fmt(BODY_W)}" height="{dl.fmt(BODY_H)}" '
              f'rx="2" fill="none" stroke="{dl.MUTED}" stroke-width="1" stroke-dasharray="2 2"/>')
        _dot(c, x, by - HEAD_R, HEAD_R, "none", dl.MUTED, 1)
    else:
        c.add(f'<rect x="{dl.fmt(bx)}" y="{dl.fmt(by)}" width="{dl.fmt(BODY_W)}" height="{dl.fmt(BODY_H)}" '
              f'rx="2" fill="{fill}"/>')
        _dot(c, x, by - HEAD_R, HEAD_R, fill)
    return float(y_ground) - BODY_H - 2 * HEAD_R  # top of the head, where the rays leave


def _sensor_top_offset():
    """Height of the sensor glyph, from the ground to the top of its head."""
    return 8.0 + 2 * 3.6


# =============================================================== detection floor vs mode ===
def lidar_core_detection_floor_vs_mode(out_dir: pathlib.Path) -> None:
    # --- layout -------------------------------------------------------------------------------
    PW, PH = 300.0, 230.0            # plot area of one panel
    GAP = 64.0                       # air between panels
    LEFT = 66.0                      # x of the first panel's y axis
    TOP = 108.0                      # y of the plot top
    TITLE_Y, SUB_Y = 36.0, 58.0      # baselines of the mode token and its subtitle
    SHIFT_ARROW_Y = TOP - 14.0       # "longer promised range" arrow, above the plot
    AXIS_LABEL_DY = 6.0 + 12.0       # tick labels: tick length + font size
    AXIS_TITLE_DY = AXIS_LABEL_DY + 17.0
    LEGEND_Y1 = TOP + PH + 72.0
    LEGEND_DY = 24.0
    W = LEFT + 3 * PW + 2 * GAP + 36.0
    H = LEGEND_Y1 + LEGEND_DY + 22.0
    # --- data (schematic; only the stated numbers are real) ----------------------------------
    RMAX = 260.0                     # m, extent of the range axis ("0 to about 250 m")
    YMAX = 1.25                      # processed signal at the plot top; the clip is at 1
    R_DEFAULT = 200.0                # minReflectionRangeM default, m
    R_LONGER = 250.0                 # "a longer promised range"
    KNEE = 10.0                      # CORRECTION knee position (illustrative; no page publishes the distance)
    FLOOR_RAW, FLOOR_COR, FLOOR_NORM = 0.36, 0.5, 0.3  # schematic floor heights at R_DEFAULT
    NORM_RISE = 0.0004               # NORMALIZATION: nearly flat, rising slightly with range
    CURVE_W, LINE_W = 2.5, 1.5
    TICKS = (0.0, 100.0, 200.0)

    def raw(r):
        return FLOOR_RAW * (R_DEFAULT / r) ** 2

    def correction(r):
        if r >= KNEE:
            return FLOOR_COR * (R_DEFAULT / r)
        return FLOOR_COR * (R_DEFAULT / KNEE) * (KNEE / r) ** 2

    def normalization(r):
        return FLOOR_NORM + (r - R_DEFAULT) * NORM_RISE

    panels = (
        ("RAW", None, "the same surface reads weaker\nthe farther away it is", raw, FLOOR_RAW),
        ("CORRECTION", None, "as detected to a fixed near distance,\nthen lifted in proportion to range", correction, FLOOR_COR),
        ("NORMALIZATION", "(default)", "a surface reads about the same\nat any range", normalization, FLOOR_NORM),
    )

    c = dl.Canvas(W, H, "Detection floor under each processing mode",
                  "Three schematic panels, one per intensity processing mode, show the processed signal of a "
                  "target of the promised reflectance against range. The detection floor is where the curve "
                  "meets the promised range: under RAW and CORRECTION a longer promised range lowers the floor, "
                  "under NORMALIZATION the curve is nearly flat and the floor barely moves. The clip at 1 "
                  "applies to the output only.")

    for i, (token, suffix, subtitle, f, floor) in enumerate(panels):
        x0 = LEFT + i * (PW + GAP)       # y axis
        y_axis = TOP + PH

        def px(r):
            return x0 + r / RMAX * PW

        def py(s):
            return y_axis - s / YMAX * PH

        # title and subtitle
        parts = [(token, 15, "bold", dl.M, dl.DK)]
        if suffix:
            parts.append((" " + suffix, 12, "normal", dl.F, dl.GREY))
        _mixed(c, x0 + PW / 2, TITLE_Y, parts, anchor="middle")
        dl.text_block(c, x0 + PW / 2, SUB_Y, subtitle, PW, size=12, fill=dl.GREY, anchor="middle")
        # frame: axes
        _line(c, x0, TOP, x0, y_axis, dl.GREY, 1.5)
        dl.tick_marks(c, x0, y_axis, PW, [px(t) - x0 for t in TICKS], [dl.fmt(t) for t in TICKS])
        dl.text(c, x0, y_axis + AXIS_TITLE_DY, "range (m)", 11, fill=dl.GREY)
        dl.text(c, px(R_DEFAULT), y_axis + AXIS_TITLE_DY, "minReflectionRangeM", 11, anchor="middle",
                fill=dl.DK, family=dl.M)
        # clip at 1
        _line(c, x0, py(1.0), x0 + PW, py(1.0), dl.ORANGE, LINE_W)
        _line(c, x0, py(1.0), x0 - 6, py(1.0), dl.GREY, 1.5)
        dl.text(c, x0 - 11, py(1.0) + 4, "1", 12, anchor="end", fill=dl.GREY)
        if i == 0:
            _vtext(c, x0 - 38, TOP + PH / 2, "processed signal", 12, dl.GREY)
        if i == 2:
            dl.text(c, x0 + 6, py(1.0) - 6, "clip at 1 (output only)", 11, fill=dl.ORANGE)
        # CORRECTION knee
        if token == "CORRECTION":
            _line(c, px(KNEE), TOP, px(KNEE), y_axis, dl.MUTED, 1, dotted=True)
            dl.text(c, px(KNEE) + 5, TOP + 14, "near distance", 11, fill=dl.GREY)
        # promised range and a longer one
        _line(c, px(R_DEFAULT), TOP - 18, px(R_DEFAULT), y_axis, dl.DK, LINE_W, dashed=True)
        _line(c, px(R_LONGER), TOP - 18, px(R_LONGER), y_axis, dl.PURPLE, LINE_W, dashed=True)
        dl.arrow(c, px(R_DEFAULT) + 3, SHIFT_ARROW_Y, px(R_LONGER) - 3, SHIFT_ARROW_Y, stroke=dl.PURPLE, width=1.5)
        dl.text(c, px(R_DEFAULT) - 8, SHIFT_ARROW_Y + 4, "longer promised range", 11, anchor="end", fill=dl.PURPLE)
        # floors: derived where the curve meets the promised range
        floor2 = f(R_LONGER)
        _line(c, x0, py(floor), px(R_DEFAULT), py(floor), dl.RED, LINE_W, dashed=True)
        _line(c, x0, py(floor2), px(R_LONGER), py(floor2), dl.PURPLE, LINE_W, dashed=True)
        _dot(c, px(R_DEFAULT), py(floor), 3.2, dl.RED)
        _dot(c, px(R_LONGER), py(floor2), 3.2, dl.PURPLE)
        if token == "NORMALIZATION":
            dl.text(c, px(R_DEFAULT) - 10, py(floor) + 20, "floor barely moves", 11, anchor="end", fill=dl.DK)
        else:
            ax = px(R_DEFAULT) - 30
            dl.arrow(c, ax, py(floor) + 2, ax, py(floor2) - 2, stroke=dl.DK, width=1.2)
            dl.text(c, ax - 7, py(floor2) + 14, "floor lowers", 11, anchor="end", fill=dl.DK)
        # the curve, clipped to the plot top
        pts = []
        prev = None
        r = 1.0
        while r <= RMAX + 1e-9:
            s = f(r)
            if s <= YMAX:
                if prev is not None and prev[1] > YMAX:
                    rp, sp = prev
                    t = (YMAX - sp) / (s - sp)
                    pts.append((px(rp + t * (r - rp)), py(YMAX)))
                pts.append((px(r), py(s)))
            prev = (r, s)
            r += 1.0
        _poly(c, pts, dl.BLUE, CURVE_W)

    dl.legend(c, LEFT, LEGEND_Y1, [
        ("signal of a target of the promised reflectance", dl.BLUE, "line"),
        ("detection floor at the promised range", dl.RED, "dashed"),
        ("clip at 1 (output only)", dl.ORANGE, "line"),
    ])
    dl.legend(c, LEFT, LEGEND_Y1 + LEGEND_DY, [
        ("promised range, default 200 m", dl.DK, "dashed"),
        ("a longer promised range and the floor it gives", dl.PURPLE, "dashed"),
    ])
    dl.validate(c)
    dl.write_svg(out_dir / "lidar_core_detection_floor_vs_mode.svg", c.render())


# ================================================================ beam waist and divergence ===
def lidar_core_beam_waist_divergence(out_dir: pathlib.Path) -> None:
    # --- layout -------------------------------------------------------------------------------
    W, H = 1100.0, 596.0
    AX_Y = 240.0                       # beam axis
    EM_X, EM_W, EM_H = 40.0, 74.0, 60.0   # emitter box, wide enough for its label at 12 px
    Z0_X = 250.0                       # focus distance: where the waist is
    END_X = 1040.0                     # far end of the drawn beam
    W0 = 14.0                          # waist half-width, px
    ZR = 150.0                         # Rayleigh range of the ideal beam, px
    M2 = 1.4                           # beam quality factor of the dashed envelope (the default)
    DISC_XS = (380.0, 520.0, 660.0)    # footprint discs along the axis
    DISC_ASPECT = 0.3                  # rx / ry of a disc seen from the side
    ARC_R = 560.0                      # radius of the divergence angle arc, from the focus
    ASYM_FROM_X = Z0_X                 # the far-field asymptote leaves its vertex, the waist center
    LEGEND_Y = 36.0
    M2_LABEL_Y = 116.0
    WAIST_LABEL_Y1, WAIST_LABEL_Y2 = AX_Y - 76.0, AX_Y - 60.0
    WAIST_LEADER_TOP = AX_Y - 54.0
    DIV_LABEL_X, DIV_LABEL_Y1, DIV_LABEL_Y2 = 826.0, AX_Y - 28.0, AX_Y - 12.0   # inside the half-angle
    FOCUS_DIM_Y = AX_Y + 62.0
    FOCUS_LABEL_Y = FOCUS_DIM_Y + 22.0
    FOOT_LABEL_Y = AX_Y + 86.0
    ROW_Y_A, ROW_Y_B, ROW_H = 406.0, 464.0, 46.0
    C1_X, C1_W = 40.0, 320.0
    PLUS_X = 380.0
    C2_X, C2_W = 400.0, 364.0
    ARROW_X1, ARROW_X2 = 774.0, 804.0
    C3_X, C3_W = 806.0, 254.0
    RELATION_Y = 548.0
    STEP = 10.0                        # sampling step of the envelope, px

    def w_ideal(x):
        return W0 * math.sqrt(1 + ((x - Z0_X) / ZR) ** 2)

    def w_m2(x):
        return W0 * math.sqrt(1 + ((x - Z0_X) / (ZR / M2)) ** 2)

    c = dl.Canvas(W, H, "Beam waist, divergence and beam quality factor",
                  "Side view of one beam leaving an emitter: it narrows to its waist at the focus distance and "
                  "widens beyond it along the divergence angle, with a wider dashed envelope for a beam quality "
                  "factor above 1 and footprint discs growing with range. Two rows below state which pair is "
                  "authored and which the model derives, through divergence = M-squared times lambda over pi "
                  "times waist.")

    # legend
    dl.legend(c, EM_X, LEGEND_Y, [
        ("beam envelope of an ideal beam (M² = 1)", dl.BLUE, "line"),
        ("beam quality factor above 1 (default 1.4)", dl.ORANGE, "dashed"),
        ("far-field asymptote", dl.DK, "dashed"),
    ])

    # emitter and axis
    em = dl.box(c, EM_X, AX_Y - EM_H / 2, EM_W, EM_H, "emitter", fill=dl.DK, label_size=12)
    _line(c, em.right, AX_Y, END_X, AX_Y, dl.GREY, 1, dashed=True)

    # envelopes
    xs = []
    x = em.right
    while x < END_X:
        xs.append(x)
        x += STEP
    xs.append(END_X)
    upper = [(x, AX_Y - w_ideal(x)) for x in xs]
    lower = [(x, AX_Y + w_ideal(x)) for x in xs]
    _poly(c, upper + lower[::-1], "none", 0, fill=dl.BLUE, opacity=0.08, close=True)
    _poly(c, [(x, AX_Y - w_m2(x)) for x in xs], dl.ORANGE, 2, dashed=True)
    _poly(c, [(x, AX_Y + w_m2(x)) for x in xs], dl.ORANGE, 2, dashed=True)
    _poly(c, upper, dl.BLUE, 2)
    _poly(c, lower, dl.BLUE, 2)

    # footprint discs
    for dx in DISC_XS:
        r = w_ideal(dx)
        _ellipse(c, dx, AX_Y, DISC_ASPECT * r, r, dl.BLUE, 0.14, dl.BLUE)
    dl.text(c, DISC_XS[1], FOOT_LABEL_Y, "footprint grows with range", 11, anchor="middle", fill=dl.GREY)

    # far-field asymptote and the divergence half-angle
    theta = math.atan(W0 / ZR)
    _line(c, ASYM_FROM_X, AX_Y - (ASYM_FROM_X - Z0_X) * math.tan(theta),
          END_X, AX_Y - (END_X - Z0_X) * math.tan(theta), dl.DK, 1.2, dashed=True)
    ax0, ay0 = Z0_X + ARC_R, AX_Y
    ax1, ay1 = Z0_X + ARC_R * math.cos(theta), AX_Y - ARC_R * math.sin(theta)
    c.add(f'<path d="M{dl.fmt(ax0)},{dl.fmt(ay0)} A{dl.fmt(ARC_R)},{dl.fmt(ARC_R)} 0 0 0 '
          f'{dl.fmt(ax1)},{dl.fmt(ay1)}" fill="none" stroke="{dl.DK}" stroke-width="1.2"/>')
    dl.text(c, DIV_LABEL_X, DIV_LABEL_Y1, "divergence: half-angle, degrees", 12, "bold")
    dl.text(c, DIV_LABEL_X, DIV_LABEL_Y2, "divergenceHorDeg / divergenceVerDeg", 11, family=dl.M, fill=dl.DK)

    # beam quality factor label, above the dashed envelope
    _mixed(c, END_X, M2_LABEL_Y, [
        ("Msquared", 12, "bold", dl.M, dl.ORANGE),
        (" > 1 widens the far-field spread (default 1.4)", 12, "normal", dl.F, dl.ORANGE),
    ], anchor="end")

    # waist: radius at the focus
    dl.text(c, Z0_X, WAIST_LABEL_Y1, "beam waist: radius at the focus, meters", 12, "bold", "middle")
    dl.text(c, Z0_X, WAIST_LABEL_Y2, "beamWaistHorM / beamWaistVerM", 11, anchor="middle", family=dl.M, fill=dl.DK)
    dl.arrow(c, Z0_X, WAIST_LEADER_TOP, Z0_X, AX_Y - W0 - 1, stroke=dl.DK, width=1.2)
    _line(c, Z0_X - 8, AX_Y - W0, Z0_X + 8, AX_Y - W0, dl.DK, 1)
    _line(c, Z0_X, AX_Y - W0, Z0_X, AX_Y, dl.DK, 1.2)

    # focus distance, from the emitter face to the waist
    _line(c, em.right, em.bottom + 4, em.right, FOCUS_DIM_Y + 6, dl.MUTED, 1, dotted=True)
    _line(c, Z0_X, AX_Y + W0 + 4, Z0_X, FOCUS_DIM_Y + 6, dl.MUTED, 1, dotted=True)
    _dimension_h(c, em.right, Z0_X, FOCUS_DIM_Y)
    _mixed(c, (em.right + Z0_X) / 2, FOCUS_LABEL_Y, [
        ("focusDistM", 12, "bold", dl.M, dl.DK),
        (" (default 0.15 m)", 12, "normal", dl.F, dl.GREY),
    ], anchor="middle")

    # which pair is authored, which is derived
    def cell(x, y, w, title, code, fill):
        r = dl.box(c, x, y, w, ROW_H, fill=fill)
        fg = dl.contrast_text(fill)
        dl.text(c, r.cx, y + 19, title, 12, "bold", "middle", fg)
        dl.text(c, r.cx, y + 36, code, 11, anchor="middle", fill=fg if fg == dl.WHITE else dl.DK, family=dl.M)
        return r

    for y, c1, c2, c3 in (
        (ROW_Y_A,
         ("you author the waists", "beamWaistHorM, beamWaistVerM"),
         ("divergences left at 0 (schema defaults)", "divergenceHorDeg = divergenceVerDeg = 0"),
         ("the divergence is derived", "divergenceHorDeg, divergenceVerDeg")),
        (ROW_Y_B,
         ("you author the divergences", "divergenceHorDeg, divergenceVerDeg"),
         ("waists authored as 0 (one zero is enough)", "beamWaistHorM = beamWaistVerM = 0"),
         ("the waist is derived", "beamWaistHorM, beamWaistVerM")),
    ):
        cell(C1_X, y, C1_W, c1[0], c1[1], dl.GREEN)
        dl.text(c, PLUS_X, y + ROW_H / 2 + 6, "+", 18, anchor="middle", fill=dl.GREY)
        cell(C2_X, y, C2_W, c2[0], c2[1], dl.PANEL)
        dl.arrow(c, ARROW_X1, y + ROW_H / 2, ARROW_X2, y + ROW_H / 2, stroke=dl.GREY, width=2)
        cell(C3_X, y, C3_W, c3[0], c3[1], dl.BLUE)
    dl.text(c, W / 2, RELATION_Y, "divergence = M² · λ / (π · waist), per axis, in radians", 13,
            anchor="middle", fill=dl.DK)

    dl.validate(c)
    dl.write_svg(out_dir / "lidar_core_beam_waist_divergence.svg", c.render())


# ====================================================== motion BVH and compensation grid ===
def motion_bvh_and_compensation(out_dir: pathlib.Path) -> None:
    # --- layout -------------------------------------------------------------------------------
    W = 1110.0
    COL_BVH_X, COL_BVH_W = 40.0, 130.0
    COL_CMP_X, COL_CMP_W = 180.0, 210.0
    TRACE_X, TRACE_W = 410.0, 430.0
    OUT_X, OUT_W = 860.0, 210.0
    HEAD_Y1, HEAD_Y2 = 34.0, 51.0            # header baselines
    AXIS_Y = 84.0                            # the shared time axis
    ROW_Y0, ROW_H, ROW_GAP = 118.0, 124.0, 12.0
    CHIP_H = 28.0
    N_TICKS = 6
    SENSOR_X0, SENSOR_DX = TRACE_X + 32.0, 56.0   # sensor pose at t0 and the step per tick
    POLE_DX = 40.0                           # pole, from the trace panel's right edge
    GROUND_DY = 14.0                         # ground line above the row bottom
    HIT_H0, HIT_DH = 44.0, 10.0              # hit heights on the pole above the ground
    POLE_H = 100.0
    OUT_POLE_DX = 30.0                       # where the pole is, in the output frame
    OUT_SHEAR = 0.4                          # output px per trace px of sensor travel
    NOTE_DY = 17.0                           # baseline of the per-row note, from the row top
    LEGEND_Y = ROW_Y0 + 3 * ROW_H + 2 * ROW_GAP + 26.0
    H = LEGEND_Y + 30.0
    RAY_W, DOT_R = 1.2, 3.4

    c = dl.Canvas(W, H, "Motion BVH and compensation state",
                  "A grid of three rows sharing one time axis of a single scan while the sensor moves to the "
                  "right toward a fixed pole. Row 1, motion BVH off: every ray leaves the frame-end pose and "
                  "meets a scene that does not move, so the reported points show no motion. Row 2, motion BVH "
                  "on and NONCOMPENSATED: each ray leaves the pose at its own tick and the reported pole looks "
                  "slanted. Row 3, motion BVH on and COMPENSATED: the same hits, re-expressed in one frame, "
                  "and the pole looks vertical. Two left columns show the two independent controls.")

    # headers
    dl.text(c, COL_BVH_X + COL_BVH_W / 2, HEAD_Y1, "renderer:", 12, "bold", "middle")
    dl.text(c, COL_BVH_X + COL_BVH_W / 2, HEAD_Y2, "motion BVH", 12, anchor="middle", fill=dl.GREY)
    dl.text(c, COL_CMP_X + COL_CMP_W / 2, HEAD_Y1, "prim:", 12, "bold", "middle")
    dl.text(c, COL_CMP_X + COL_CMP_W / 2, HEAD_Y2, "outputMotionCompensationState", 11, anchor="middle",
            family=dl.M, fill=dl.DK)
    dl.text(c, TRACE_X + TRACE_W / 2, HEAD_Y1, "what the rays meet", 12, "bold", "middle")
    dl.text(c, TRACE_X + TRACE_W / 2, HEAD_Y2, "the sensor moves to the right during the scan", 11,
            anchor="middle", fill=dl.GREY)
    dl.text(c, OUT_X + OUT_W / 2, HEAD_Y1, "how the points are reported", 12, "bold", "middle")
    dl.text(c, OUT_X + OUT_W / 2, HEAD_Y2, "in the output frame", 11, anchor="middle", fill=dl.GREY)

    # one time axis for the whole scan
    sensor_xs = [SENSOR_X0 + i * SENSOR_DX for i in range(N_TICKS)]
    tick_labels = [f"t{i}" for i in range(N_TICKS - 1)] + ["tN"]
    dl.arrow(c, sensor_xs[0] - 14, AXIS_Y, sensor_xs[-1] + 44, AXIS_Y, stroke=dl.GREY, width=1.5)
    dl.tick_marks(c, sensor_xs[0], AXIS_Y, 0, [x - sensor_xs[0] for x in sensor_xs], tick_labels, axis=False)
    dl.text(c, sensor_xs[-1] + 50, AXIS_Y + 4, "time", 11, fill=dl.GREY)

    pole_x = TRACE_X + TRACE_W - POLE_DX
    hit_hs = [HIT_H0 + i * HIT_DH for i in range(N_TICKS)]
    rows = (
        ("off", dl.MUTED, "NONCOMPENSATED", False, False,
         "every ray from the frame-end pose; the scene does not move", "no motion effects"),
        ("on", dl.GREEN, "NONCOMPENSATED", True, False,
         "each ray from the sensor pose at its own tick", "the pole looks slanted"),
        ("on", dl.GREEN, "COMPENSATED", True, True,
         "same rays and hits as the row above", "the pole looks vertical"),
    )
    for i, (bvh, bvh_fill, state, moving, compensated, trace_note, out_note) in enumerate(rows):
        y = ROW_Y0 + i * (ROW_H + ROW_GAP)
        ground = y + ROW_H - GROUND_DY
        dl.box(c, COL_BVH_X, y, OUT_X + OUT_W - COL_BVH_X, ROW_H, fill=dl.PANEL, rx=6)
        # the two controls
        dl.box(c, COL_BVH_X + 20, y + ROW_H / 2 - CHIP_H / 2, COL_BVH_W - 40, CHIP_H, bvh, fill=bvh_fill,
               label_size=13)
        dl.box(c, COL_CMP_X + 10, y + ROW_H / 2 - CHIP_H / 2, COL_CMP_W - 20, CHIP_H, state, fill=dl.WHITE,
               stroke=dl.DK, stroke_width=1.5, label_size=12, label_family=dl.M)
        # trace panel: ground, pole, sensor poses, rays, hits
        _line(c, TRACE_X + 8, ground, TRACE_X + TRACE_W - 8, ground, dl.GREY, 1.5)
        _line(c, pole_x, ground, pole_x, ground - POLE_H, dl.DK, 4)
        dl.text(c, TRACE_X + 8, y + NOTE_DY, trace_note, 11, fill=dl.GREY)
        if moving:
            origins = [(sx, ground - _sensor_top_offset()) for sx in sensor_xs]
            for sx in sensor_xs:
                _sensor(c, sx, ground)
        else:
            for sx in sensor_xs[:-1]:
                _sensor(c, sx, ground, ghost=True)
            _sensor(c, sensor_xs[-1], ground)
            origins = [(sensor_xs[-1], ground - _sensor_top_offset())] * N_TICKS
        for (ox, oy), h in zip(origins, hit_hs):
            _line(c, ox, oy, pole_x, ground - h, dl.GREY, RAY_W)
        for h in hit_hs:
            _dot(c, pole_x, ground - h, 3.0, dl.ORANGE)
        # output frame
        dl.box(c, OUT_X, y + 6, OUT_W, ROW_H - 12, fill=dl.WHITE, stroke=dl.FAINT, stroke_width=1.5, rx=4)
        dl.text(c, OUT_X + OUT_W - 10, y + NOTE_DY + 3, out_note, 11, anchor="end", fill=dl.GREY)
        _line(c, OUT_X + 10, ground, OUT_X + OUT_W - 10, ground, dl.GREY, 1.5)
        out_pole = OUT_X + OUT_POLE_DX
        _line(c, out_pole, ground, out_pole, ground - POLE_H + 2, dl.GREY, 1.2, dashed=True)
        for j, h in enumerate(hit_hs):
            shear = 0.0
            if moving and not compensated:
                shear = (sensor_xs[-1] - sensor_xs[j]) * OUT_SHEAR
            _dot(c, out_pole + shear, ground - h, DOT_R, dl.BLUE)

    # legend: the marks of the drawing (the chips carry their own meaning)
    lx, ly = COL_BVH_X, LEGEND_Y
    entries = (
        ("sensor pose at a tick", "sensor"), ("pose the trace ignores", "ghost"), ("ray", "ray"),
        ("hit on the pole", dl.ORANGE), ("reported point", dl.BLUE), ("where the pole is", "dashed"),
    )
    for label, kind in entries:
        if kind == "sensor":
            _sensor(c, lx + 9, ly + 12)
        elif kind == "ghost":
            _sensor(c, lx + 9, ly + 12, ghost=True)
        elif kind == "ray":
            _line(c, lx, ly + 6, lx + 18, ly + 6, dl.GREY, RAY_W)
        elif kind == "dashed":
            _line(c, lx, ly + 6, lx + 18, ly + 6, dl.GREY, 1.2, dashed=True)
        else:
            _dot(c, lx + 9, ly + 6, DOT_R, kind)
        tb = dl.text(c, lx + 26, ly + 10, label, 12)
        lx = tb.x1 + 24

    dl.validate(c)
    dl.write_svg(out_dir / "motion_bvh_and_compensation.svg", c.render())


def generate(out_dir: pathlib.Path) -> None:
    lidar_core_detection_floor_vs_mode(out_dir)
    lidar_core_beam_waist_divergence(out_dir)
    motion_bvh_and_compensation(out_dir)


if __name__ == "__main__":
    generate(dl.output_dir(__file__))
