#!/usr/bin/env python3
"""Figures of the Camera generic core model pages and of the rendered-visual-sensors hub.

One function per SVG. ``python3 -B _gen_visual_camera_core.py`` run in this directory
regenerates only this group in place; ``generate_diagrams.py`` runs every group.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import _diagram_lib as dl  # noqa: E402


# ------------------------------------------------------------------------------------ helpers ---
def _vbracket(c: dl.Canvas, x: float, y0: float, y1: float, color: str, tick: float,
              width: float = 2.5) -> None:
    """A vertical bracket at ``x`` from ``y0`` to ``y1`` whose end ticks point right."""
    d = (f"M{dl.fmt(x + tick)},{dl.fmt(y0)} L{dl.fmt(x)},{dl.fmt(y0)} "
         f"L{dl.fmt(x)},{dl.fmt(y1)} L{dl.fmt(x + tick)},{dl.fmt(y1)}")
    c.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{dl.fmt(width)}" '
          f'stroke-linecap="round" stroke-linejoin="round"/>')


def _hbracket(c: dl.Canvas, x0: float, x1: float, y: float, tick: float, color: str = dl.GREY,
              width: float = 1.5) -> None:
    """A horizontal bracket under a group of cells, from ``x0`` to ``x1`` at ``y``, ticks up."""
    d = (f"M{dl.fmt(x0)},{dl.fmt(y - tick)} L{dl.fmt(x0)},{dl.fmt(y)} "
         f"L{dl.fmt(x1)},{dl.fmt(y)} L{dl.fmt(x1)},{dl.fmt(y - tick)}")
    c.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{dl.fmt(width)}"/>')


def companding_alignment(out_dir: pathlib.Path) -> None:
    """A 12-bit code in a 16-bit unsigned integer for compandingAlignment 15 and 11."""
    MARGIN = 24
    HEAD_Y = 30                      # heading baseline
    LEGEND_Y = 16                    # legend top (top right corner)
    LABEL_X = MARGIN                 # row label column (left edge)
    CELL_X0 = 250                    # left edge of bit 15
    CELL = 36                        # cell size
    N_BITS = 16
    CODE_BITS = 12
    ROW1_Y = 94                      # top of the first row of cells
    ROW_PITCH = 128
    MARK_TEXT_DY = -30               # code MSB label baseline, relative to the row top
    MARK_ARROW_TOP = -24             # arrow start, relative to the row top
    GROUP_LINE_DY = 44               # bracket under the cells, relative to the row top
    GROUP_TEXT_DY = 62               # group label baseline, relative to the row top
    GROUP_TICK = 5
    ROW_LABEL_DY1, ROW_LABEL_DY2 = 14, 31
    FOOT_DY = 34                     # footnote baseline below the last group label
    WIDTH = CELL_X0 + N_BITS * CELL + 34
    ROW2_Y = ROW1_Y + ROW_PITCH
    FOOT_Y = ROW2_Y + GROUP_TEXT_DY + FOOT_DY
    HEIGHT = FOOT_Y + 8 + MARGIN

    c = dl.Canvas(
        WIDTH, HEIGHT, "Companding alignment: a 12-bit code in a 16-bit unsigned integer",
        "Two 16-bit unsigned integers drawn as rows of bit cells numbered 15 to 0. In the upper row "
        "the 12-bit code occupies bits 15 to 4 and bits 3 to 0 are padding; in the lower row the code "
        "occupies bits 11 to 0 and bits 15 to 12 are padding.")

    dl.text(c, MARGIN, HEAD_Y, "12-bit code in a 16-bit unsigned integer (bit 15 on the left)",
            13, fill=dl.DK)
    legend_entries = [("code bits", dl.GREEN), ("padding bits", dl.GREY, "outline")]
    legend_w = sum(dl.text_width(e[0], 12) + 12 + 7 for e in legend_entries) + 22
    dl.legend(c, WIDTH - MARGIN - legend_w, LEGEND_Y, legend_entries)

    def cell_x(bit: int) -> float:
        return CELL_X0 + (N_BITS - 1 - bit) * CELL

    rows = (
        # (row top, alignment, code bit positions, shift)
        (ROW1_Y, 15, "bits 15–4 (most significant)", "shift left by 4"),
        (ROW2_Y, 11, "bits 11–0 (least significant)", "no shift"),
    )
    for row_y, alignment, where, shift in rows:
        msb = alignment
        lsb = alignment - CODE_BITS + 1
        for bit in range(N_BITS - 1, -1, -1):
            is_code = lsb <= bit <= msb
            dl.box(c, cell_x(bit), row_y, CELL, CELL, str(bit),
                   fill=dl.GREEN if is_code else dl.PANEL,
                   stroke=dl.WHITE if is_code else dl.GREY, stroke_width=1.5, rx=2,
                   dashed=not is_code, label_size=12,
                   label_fill=dl.WHITE if is_code else dl.GREY)
        # row label
        dl.text(c, LABEL_X, row_y + ROW_LABEL_DY1, f"compandingAlignment = {alignment}", 13,
                family=dl.M, fill=dl.DK)
        dl.text(c, LABEL_X, row_y + ROW_LABEL_DY2, where, 11.5, fill=dl.GREY)
        # MSB marker
        mx = cell_x(msb) + CELL / 2
        dl.text(c, mx, row_y + MARK_TEXT_DY, "code's most significant bit", 12, "bold", "middle",
                dl.DK)
        dl.arrow(c, mx, row_y + MARK_ARROW_TOP, mx, row_y - 1, stroke=dl.DK, width=2)
        # group brackets and labels
        code_x0, code_x1 = cell_x(msb) + 3, cell_x(lsb) + CELL - 3
        _hbracket(c, code_x0, code_x1, row_y + GROUP_LINE_DY, GROUP_TICK)
        dl.text(c, (code_x0 + code_x1) / 2, row_y + GROUP_TEXT_DY, f"12-bit code ({shift})", 12,
                anchor="middle", fill=dl.DK)
        if lsb > 0:
            pad_x0, pad_x1 = cell_x(lsb - 1) + 3, cell_x(0) + CELL - 3
        else:
            pad_x0, pad_x1 = cell_x(N_BITS - 1) + 3, cell_x(msb + 1) + CELL - 3
        _hbracket(c, pad_x0, pad_x1, row_y + GROUP_LINE_DY, GROUP_TICK)
        dl.text(c, (pad_x0 + pad_x1) / 2, row_y + GROUP_TEXT_DY, "padding", 12, anchor="middle",
                fill=dl.GREY)

    dl.text(c, MARGIN, FOOT_Y,
            "shift = alignment − code width + 1:  15 − 12 + 1 = 4 (shift left by 4),  "
            "11 − 12 + 1 = 0 (no shift)", 12, fill=dl.GREY)

    dl.validate(c)
    dl.write_svg(out_dir / "companding_alignment.svg", c.render())


def camera_core_pipeline(out_dir: pathlib.Path) -> None:
    """The seven stages from HdrColor to the two primary outputs, with each AOV and format."""
    MARGIN = 24
    LABEL_W = 176                    # bracket label column, right-anchored text
    BR_GAP = 14                      # label column -> outer bracket
    BR_STEP = 16                     # outer bracket -> inner bracket
    TICK = 8                         # bracket tick length
    STAGE_GAP = 12                   # inner bracket tick -> stage box
    STAGE_W, STAGE_H, ISP_H = 250, 64, 84
    NUM_R = 11                       # radius of the stage-number disc
    NUM_X = 22                       # disc center, relative to the stage box
    ROW_GAP = 26                     # air between stage boxes (holds the flow arrow)
    INPUT_H, INPUT_GAP = 48, 30
    CONN_LEN = 120                   # stage box -> AOV box
    AOV_W, AOV_H = 304, 64
    AOV_NAME_DY, AOV_FMT_DY, AOV_FMT_PITCH = 21, 39, 17   # baselines inside the AOV box
    LEGEND_GAP, NOTE_GAP = 30, 30
    TAG_DY_UP, TAG_DY_DOWN = -7, 15  # connector tag baselines relative to the connector line
    LABEL_RIGHT = MARGIN + LABEL_W
    BR_OUTER_X = LABEL_RIGHT + BR_GAP
    BR_INNER_X = BR_OUTER_X + BR_STEP
    STAGE_X = BR_INNER_X + TICK + STAGE_GAP
    AOV_X = STAGE_X + STAGE_W + CONN_LEN
    WIDTH = AOV_X + AOV_W + MARGIN
    INPUT_Y = MARGIN
    STAGE_Y0 = INPUT_Y + INPUT_H + INPUT_GAP

    stages = (
        # (stage, AOV, element format, role) -- role: tap / pre (RAW) / full (processed)
        ("Read the rendered image", "OmniCameraSensorInputSource",
         "4 components, 16-bit float RGBA", "tap"),
        ("Color correction", "OmniCameraSensorPostColorCorrection",
         "4 components, 16-bit float RGBA", "tap"),
        ("Color filter array", "OmniCameraSensorPostCfa",
         "1 component, 32-bit unsigned integer, or 32-bit float with FLOAT32", "tap"),
        ("Sensor noise", "OmniCameraSensorPostNoise",
         "1 component, 32-bit unsigned integer", "tap"),
        ("Companding", "OmniCameraSensorPreIsp",
         "1 component, 16-bit unsigned integer; 32-bit if the curve exceeds 16 bits", "pre"),
        ("ISP", "OmniCameraSensorPostYuvIsp",
         "4 components, 16-bit unsigned integer AYUV, not RGB", "tap"),
        ("YUV decode", "OmniCameraSensorPostIsp",
         "4 components, 8-bit unsigned integer RGBA", "full"),
    )
    heights = [ISP_H if name == "ISP" else STAGE_H for name, _, _, _ in stages]
    tops = []
    y = STAGE_Y0
    for h in heights:
        tops.append(y)
        y += h + ROW_GAP
    LAST_BOTTOM = tops[-1] + heights[-1]
    LEGEND_Y = LAST_BOTTOM + LEGEND_GAP
    NOTE_Y = LEGEND_Y + NOTE_GAP
    note = ("Request at least one primary output. Requesting both builds the full pipeline and also "
            "publishes the companded RAW image. Diagnostic taps publish only when their stage is built.")
    note_lines = dl.wrap_text(note, WIDTH - 2 * MARGIN, 11.5)
    HEIGHT = NOTE_Y + (len(note_lines) - 1) * 11.5 * 1.45 + 4 + MARGIN

    c = dl.Canvas(
        WIDTH, HEIGHT, "Camera generic core model: pipeline stages and outputs",
        "The seven stages in order from HdrColor to the two primary outputs: read the rendered "
        "image, color correction, color filter array, sensor noise, companding, ISP and YUV decode, "
        "each labeled with the AOV it publishes and that AOV's element format. OmniCameraSensorPreIsp "
        "is marked as the primary RAW output after companding and OmniCameraSensorPostIsp as the "
        "primary processed output after the YUV decode; the other five AOVs are marked as optional taps.")

    # input
    inp = dl.box(c, STAGE_X, INPUT_Y, STAGE_W, INPUT_H, fill=dl.PANEL, stroke=dl.GREY,
                 stroke_width=1.5)
    dl.text(c, inp.cx, inp.cy - 3, "HdrColor", 14, "bold", "middle", dl.DK, dl.M)
    dl.text(c, inp.cx, inp.cy + 14, "the rendered image, the only input", 11.5, anchor="middle",
            fill=dl.GREY)
    dl.arrow(c, inp.cx, inp.bottom + 1, inp.cx, STAGE_Y0 - 1, stroke=dl.GREY, width=2)

    # stages, connectors, AOVs
    for i, (name, aov, fmt_text, role) in enumerate(stages):
        top, h = tops[i], heights[i]
        st = dl.box(c, STAGE_X, top, STAGE_W, h, fill=dl.PANEL)
        c.add(f'<circle cx="{dl.fmt(st.x + NUM_X)}" cy="{dl.fmt(st.cy)}" r="{dl.fmt(NUM_R)}" '
              f'fill="{dl.GREY}"/>')
        dl.text(c, st.x + NUM_X, st.cy + 4.5, str(i + 1), 12, "bold", "middle", dl.WHITE)
        name_cx = st.x + NUM_X + NUM_R + 8 + (STAGE_W - NUM_X - NUM_R - 16) / 2
        name_w = STAGE_W - NUM_X - NUM_R - 16
        if name == "ISP":
            dl.text(c, name_cx, st.cy - 14, name, 13, "bold", "middle", dl.DK)
            dl.text(c, name_cx, st.cy + 5, "runs the program in", 11.5, anchor="middle", fill=dl.GREY)
            dl.text(c, name_cx, st.cy + 22, "ispSmodelCameraProgram", 11.5, anchor="middle",
                    fill=dl.DK, family=dl.M)
        else:
            size = dl.fit_label(name, name_w, 13, min_size=12)
            dl.text(c, name_cx, st.cy + 5, name, size, "bold", "middle", dl.DK)
        if i + 1 < len(stages):
            dl.arrow(c, st.cx, st.bottom + 1, st.cx, tops[i + 1] - 1, stroke=dl.GREY, width=2)

        primary_output = role != "tap"
        color = dl.GREEN if primary_output else dl.GREY
        cy = st.cy
        dl.arrow(c, st.right + 1, cy, AOV_X - 1, cy, stroke=color, width=2.5 if primary_output else 2,
                 dashed=not primary_output)
        tag_x = st.right + CONN_LEN / 2
        if primary_output:
            dl.text(c, tag_x, cy + TAG_DY_UP, "primary output", 11.5, "bold", "middle", dl.GREEN)
            which = "RAW" if role == "pre" else "processed"
            dl.text(c, tag_x, cy + TAG_DY_DOWN, f"({which})", 11, anchor="middle", fill=dl.GREEN)
        else:
            dl.text(c, tag_x, cy + TAG_DY_UP, "optional tap", 11.5, anchor="middle", fill=dl.GREY)

        ab = dl.box(c, AOV_X, cy - AOV_H / 2, AOV_W, AOV_H, fill=dl.WHITE,
                    stroke=dl.GREEN if primary_output else dl.FAINT,
                    stroke_width=2.5 if primary_output else 1.5, dashed=not primary_output)
        dl.text(c, ab.x + 12, ab.y + AOV_NAME_DY, aov, 12.5, "bold" if primary_output else "normal",
                "start", dl.DK, dl.M)
        lines = dl.wrap_text(fmt_text, AOV_W - 24, 11.5)
        assert len(lines) <= 2, (aov, lines)
        for j, ln in enumerate(lines):
            dl.text(c, ab.x + 12, ab.y + AOV_FMT_DY + j * AOV_FMT_PITCH, ln, 11.5, fill=dl.GREY)

    # brackets: stages 1-5 (pre-ISP pipeline) and 1-7 (full pipeline)
    pre_y0, pre_y1 = tops[0], tops[4] + heights[4]
    full_y0, full_y1 = tops[0], LAST_BOTTOM
    _vbracket(c, BR_INNER_X, pre_y0, pre_y1, dl.BLUE, TICK)
    _vbracket(c, BR_OUTER_X, full_y0, full_y1, dl.PURPLE, TICK)
    LABEL_PITCH = 17                 # baseline pitch inside a bracket label block
    for (y0, y1, color, head, lines) in (
            (pre_y0, pre_y1, dl.BLUE, "pre-ISP pipeline",
             (("OmniCameraSensorPreIsp", dl.M, dl.DK), ("requested without", dl.F, dl.GREY),
              ("OmniCameraSensorPostIsp", dl.M, dl.DK))),
            (full_y0, full_y1, dl.PURPLE, "full pipeline",
             (("OmniCameraSensorPostIsp", dl.M, dl.DK), ("requested", dl.F, dl.GREY)))):
        mid = (y0 + y1) / 2
        head_y = mid - len(lines) * LABEL_PITCH / 2 + 4      # block centered on the bracket
        dl.text(c, LABEL_RIGHT, head_y, head, 12.5, "bold", "end", color)
        for j, (ln, family, fill) in enumerate(lines):
            dl.text(c, LABEL_RIGHT, head_y + (j + 1) * LABEL_PITCH, ln, 11.5, anchor="end",
                    fill=fill, family=family)

    dl.legend(c, MARGIN, LEGEND_Y, [
        ("primary output", dl.GREEN, "line"),
        ("optional tap", dl.GREY, "dashed"),
        ("pre-ISP pipeline, stages 1–5", dl.BLUE, "line"),
        ("full pipeline, stages 1–7", dl.PURPLE, "line"),
    ])
    dl.text_block(c, MARGIN, NOTE_Y, note, WIDTH - 2 * MARGIN, 11.5, fill=dl.GREY)

    dl.validate(c)
    dl.write_svg(out_dir / "camera_core_pipeline.svg", c.render())


def generate(out_dir: pathlib.Path) -> None:
    companding_alignment(out_dir)
    camera_core_pipeline(out_dir)


if __name__ == "__main__":
    generate(dl.output_dir(__file__))
