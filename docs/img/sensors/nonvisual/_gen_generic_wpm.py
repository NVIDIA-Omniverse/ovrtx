#!/usr/bin/env python3
"""Generic WPM trace definition, directional sampling, geometry, and output layout.

Figures serve Generic wpm model USD Attributes, Outputs, and sampling how-tos.
Run ``python3 -B _gen_generic_wpm.py [out_dir]`` or this area's
``python3 -B generate_diagrams.py [out_dir]``. Logical schematics illustrate
relationships and sampling, not physical dimensions or measured sensor output.
"""
import math
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import _diagram_lib as dl


def patterns(out_dir):
    # Retain the presentation's stored rows/cells and page/group hierarchy, but
    # attach bundle/group associations to a whole Tx pattern, as the public API
    # requires. The selected map example is consistent: two Tx, three rays, three
    # Rx, and two distinct ordered receiver entries, Rx 2 followed by Rx 0.
    width, height = 1000, 1140
    left, right, left_width, right_width = 24, 552, 430, 424
    top, bottom, top_height, bottom_height = 166, 617, 380, 430
    cell_size, cell_gap, small_text = 54, 6, 16
    c = dl.Canvas(width, height, "Generic wpm model trace definition",
                  "Global propagation settings sit above four connected panels. At upper left, "
                  "activeTxPatternIndex selects transmitter pattern 0, containing Tx 0 and Tx 1. "
                  "Its shared rayPatternIndices entry selects ray pattern 1, a three-ray Gaussian "
                  "bundle at upper right. Its shared mappingTargetRxGroups entry selects group 0 "
                  "in mapping page 0 at lower right; activeMappingPageIndex selects that page. "
                  "Group 0 contains the ordered receiver indices 2, 0. Separate purple arrows "
                  "connect entry 2 to the Rx 2 cell and entry 0 to the Rx 0 cell in receiver "
                  "pattern 0 at lower left, selected independently by activeRxPatternIndex. "
                  "Unselected pattern rows and stacked mapping pages remain visible. Green, blue, "
                  "purple and orange outlines mark the selected Tx, ray, Rx and mapping data. "
                  "The illustrated map connection is one of nton, 1to1 with bloom, and map.")
    dl.text(c, left, 34, "One trace definition connects the stored patterns", 23, weight="bold")
    dl.box(c, left, 60, width - 2 * left, 78)
    dl.text(c, left + 18, 88, "Global propagation settings", 20, weight="bold")
    dl.text(c, left + 18, 118, "waveType · wavelengthNm · maxBounces · maxHitDistanceM", 17, family=dl.M)
    for x, y, w, h in [(left, top, left_width, top_height), (right, top, right_width, top_height),
                        (left, bottom, left_width, bottom_height), (right, bottom, right_width, bottom_height)]:
        dl.box(c, x, y, w, h)

    def cells(x, y, labels, color, w=cell_size):
        for i, label in enumerate(labels):
            dl.box(c, x + i * (w + cell_gap), y, w, 36, label, fill=dl.WHITE,
                   stroke=color, stroke_width=1, rx=2, label_size=small_text, label_weight="normal")

    # Tx rows. The associations are inside the selected pattern's outline,
    # below its element cells, rather than in an individual Tx-cell callout.
    dl.text(c, left + 18, 195, "Transmitter patterns", 21, weight="bold")
    dl.text(c, left + 18, 224, "Free / Grid", 17)
    dl.text(c, left + 18, 253, "activeTxPatternIndex = 0", small_text, family=dl.M)
    dl.arrow(c, left + 34, 263, left + 34, 280, dl.GREEN, 2)
    dl.box(c, left + 16, 282, left_width - 32, 164, fill=dl.WHITE, stroke=dl.GREEN, stroke_width=3)
    dl.text(c, left + 32, 312, "0 · Free", 18, weight="bold")
    cells(left + 188, 290, ["Tx 0", "Tx 1"], dl.GREEN)
    dl.text(c, left + 32, 348, "Each Tx: pose + firing offset", small_text)
    dl.text(c, left + 32, 375, "Shared by this Tx pattern:", small_text, weight="bold")
    dl.text(c, left + 32, 402, "tx:rayPatternIndices[0] = 1", small_text, family=dl.M)
    dl.text(c, left + 32, 429, "tx:mappingTargetRxGroups[0] = 0", small_text, family=dl.M)
    dl.box(c, left + 16, 464, left_width - 32, 50, fill=dl.WHITE, stroke=dl.FAINT, stroke_width=1)
    dl.text(c, left + 32, 495, "1 · Grid", 18)
    cells(left + 188, 471, ["Tx 0", "Tx 1", "Tx 2"], dl.FAINT)
    dl.text(c, left + 18, 535, "Tx = transmitter; each cell is an element", small_text)

    # Ray rows. Pattern indices are local to the ray role; a selected Tx
    # pattern points to an entire row, with no separate active-ray selector.
    dl.text(c, right + 18, 195, "Ray patterns", 21, weight="bold")
    dl.text(c, right + 18, 224, "Free / Grid / Gaussian", 17)
    dl.box(c, right + 16, 260, right_width - 32, 50, fill=dl.WHITE, stroke=dl.FAINT, stroke_width=1)
    dl.text(c, right + 32, 291, "0 · Free", 18)
    cells(right + 176, 267, ["Ray 0", "Ray 1"], dl.FAINT, w=70)
    dl.box(c, right + 16, 330, right_width - 32, 116, fill=dl.WHITE, stroke=dl.BLUE, stroke_width=3)
    dl.text(c, right + 32, 358, "1 · Gaussian", 18, weight="bold")
    cells(right + 32, 377, ["Ray 0", "Ray 1", "Ray 2"], dl.BLUE, w=78)
    dl.text(c, right + 32, 435, "Whole bundle reused at every selected Tx", small_text)
    dl.box(c, right + 16, 464, right_width - 32, 50, fill=dl.WHITE, stroke=dl.FAINT, stroke_width=1)
    dl.text(c, right + 32, 495, "2 · Grid", 18)
    cells(right + 176, 471, ["Ray 0", "Ray 1", "…"], dl.FAINT, w=68)
    dl.text(c, right + 18, 535, "Each ray: origin, direction, firing offset", small_text)

    # Receiver rows are selected independently. They carry coordinate frames;
    # this topology drawing does not imply receiver cones or angular gain.
    dl.text(c, left + 18, 646, "Receiver patterns", 21, weight="bold")
    dl.text(c, left + 18, 675, "Free / Grid", 17)
    dl.text(c, left + 18, 704, "activeRxPatternIndex = 0", small_text, family=dl.M)
    dl.arrow(c, left + 34, 714, left + 34, 728, dl.PURPLE, 2)
    dl.box(c, left + 16, 730, left_width - 32, 64, fill=dl.WHITE, stroke=dl.PURPLE, stroke_width=3)
    dl.text(c, left + 32, 768, "0 · Free", 18, weight="bold")
    cells(left + 188, 744, ["Rx 0", "Rx 1", "Rx 2"], dl.PURPLE)
    dl.box(c, left + 16, 930, left_width - 32, 50, fill=dl.WHITE, stroke=dl.FAINT, stroke_width=1)
    dl.text(c, left + 32, 961, "1 · Grid", 18)
    cells(left + 188, 937, ["Rx 0", "Rx 1", "…"], dl.FAINT)
    dl.text(c, left + 18, 1015, "Each Rx: position + orientation", small_text)

    # Mapping pages preserve the slide's third dimension. Only the front
    # page's group rows are expanded; cells are ordered receiver IDs, not poses.
    dl.text(c, right + 18, 646, "Receiver mappings · map", 21, weight="bold")
    dl.text(c, right + 18, 675, "activeMappingPageIndex = 0", small_text, family=dl.M)
    for offset in (20, 10):
        dl.box(c, right + 16 + offset, 718 - offset, right_width - 48, 278,
               fill=dl.WHITE, stroke=dl.FAINT, stroke_width=1, rx=2)
    dl.box(c, right + 16, 718, right_width - 48, 278,
           fill=dl.WHITE, stroke=dl.ORANGE, stroke_width=2, rx=2)
    dl.text(c, right + 32, 746, "Page 0", 18, weight="bold")
    dl.box(c, right + 32, 765, right_width - 80, 51, fill=dl.WHITE, stroke=dl.ORANGE, stroke_width=3)
    dl.text(c, right + 48, 797, "Group 0", 17, weight="bold")
    cells(right + 170, 773, ["2", "0"], dl.ORANGE, w=48)
    dl.text(c, right + 48, 962, "Group 1", 17)
    cells(right + 170, 938, ["1", "2"], dl.FAINT, w=48)
    dl.text(c, right + 18, 1030, "Entries index the active Rx pattern", small_text)

    # Pattern-assignment routes stay in the central gutter and touch whole
    # selected rows/groups, never one Tx element. Separate nested lookup paths
    # connect each selected group entry to its exact receiver cell. Blank lanes
    # before the inactive rows keep these paths clear of labels and crossings.
    dl.arrow(c, left + left_width - 16, 402, 528, 402, dl.BLUE, 2, head=False)
    dl.arrow(c, 528, 402, 528, 354, dl.BLUE, 2, head=False)
    dl.arrow(c, 528, 354, right + 14, 354, dl.BLUE, 2)
    dl.arrow(c, left + left_width - 16, 429, 502, 429, dl.ORANGE, 2, head=False)
    dl.arrow(c, 502, 429, 502, 790, dl.ORANGE, 2, head=False)
    dl.arrow(c, 502, 790, right + 30, 790, dl.ORANGE, 2)
    group_cell_width, group_cells_x, group_cells_bottom = 48, right + 170, 809
    receiver_cells_x, receiver_cells_bottom = left + 188, 780
    lookup_lanes = (846, 904)
    for slot, receiver_index in enumerate((2, 0)):
        source_x = group_cells_x + slot * (group_cell_width + cell_gap) + group_cell_width / 2
        target_x = receiver_cells_x + receiver_index * (cell_size + cell_gap) + cell_size / 2
        lane_y = lookup_lanes[slot]
        dl.arrow(c, source_x, group_cells_bottom, source_x, lane_y, dl.PURPLE, 2, head=False)
        dl.arrow(c, source_x, lane_y, target_x, lane_y, dl.PURPLE, 2, head=False)
        dl.arrow(c, target_x, lane_y, target_x, receiver_cells_bottom + 1, dl.PURPLE, 2)
    dl.text(c, left + 18, 827, "Receiver lookup", small_text, weight="bold")
    dl.text(c, left, 1069, "Receiver connections: nton · 1to1 + bloom · map", 18, weight="bold")
    dl.text(c, left, 1096, "map: the selected page holds ordered groups of active-Rx indices.", 17)
    dl.text(c, left, 1122, "Outlined rows are selected; pattern cells are elements, group cells are receiver indices.", small_text)
    dl.validate(c)
    dl.write_svg(out_dir / "generic_wpm_patterns.svg", c.render())


def directivity_sampling(out_dir):
    # The presentation's antenna lobes motivate angular sampling, but the
    # Generic API does not author calibrated gain or per-ray power. Plot a
    # one-dimensional Gaussian angular-density section as a polar radius, and
    # use its midpoint quantiles for an illustrative finite direction set.
    # The runtime uses seeded Box-Muller samples in both angles; these are
    # schematic quantiles, not a captured runtime seed or a finite FOV limit.
    # Peak-normalizing the drawn curve is a plotting convention only. It says
    # nothing about normalization of the model's independent path powers.
    width, height = 1000, 800
    left, right, panel_width = 24, 552, 424
    row_tops, panel_height = (110, 420), 285
    density_origin_x, ray_origin_x = 112, 690
    density_radius, ray_length, ray_count = 190, 150, 17
    curve_samples = 360
    c = dl.Canvas(width, height, "Generic wpm model directivity and ray sampling",
                  "Two rows relate a directional shape to sampled rays. The upper row shows a "
                  "broad blue polar angular-density curve on the left and seventeen equal-length "
                  "blue ray arrows on the right. The lower row shows a narrower green density "
                  "curve and the same seventeen ray arrows concentrated around the forward axis. "
                  "Both curves and samples use corresponding Gaussian azimuth distributions. "
                  "The curves show relative angular sampling density, without a gain or distance "
                  "scale. Green dots mark a common local origin. The diagrams are illustrative "
                  "azimuth sections; finite samples do not bound the Gaussian distribution.")
    dl.text(c, left, 34, "From directional shape to ray samples", 23, weight="bold")
    dl.text(c, left + 18, 82, "Relative angular density", 20, weight="bold")
    dl.text(c, right + 18, 82, "Sampled ray directions", 20, weight="bold")
    for row, (sigma_degrees, name, color) in enumerate([(25, "Broad", dl.BLUE), (10, "Narrow", dl.GREEN)]):
        top = row_tops[row]
        cy = top + 137
        dl.box(c, left, top, panel_width, panel_height)
        dl.box(c, right, top, panel_width, panel_height)
        dl.text(c, left + 18, top + 30, name, 21, weight="bold")
        dl.text(c, right + 18, top + 30, f"{ray_count} rays", 21, weight="bold")

        # Both axes are local to the bundle, whose orientation can rotate this
        # whole distribution relative to its transmitter. Neither curve radius
        # nor arrow length represents propagation distance or emitted power.
        dl.arrow(c, density_origin_x - 20, cy, left + panel_width - 85, cy, dl.FAINT, 1.5)
        dl.text(c, left + panel_width - 73, cy + 5, "Forward", 16)
        dl.arrow(c, ray_origin_x - 20, cy, right + panel_width - 85, cy, dl.FAINT, 1.5)
        dl.text(c, right + panel_width - 73, cy + 5, "Forward", 16)

        points = []
        for i in range(curve_samples + 1):
            angle = -math.pi + 2 * math.pi * i / curve_samples
            density = math.exp(-0.5 * (math.degrees(angle) / sigma_degrees) ** 2)
            radius = density_radius * density
            points.append((density_origin_x + radius * math.cos(angle), cy - radius * math.sin(angle)))
        path = "M" + " L".join(f"{dl.fmt(x)},{dl.fmt(y)}" for x, y in points) + " Z"
        c.add(f'<path d="{path}" fill="{color}" fill-opacity="0.13" stroke="{color}" stroke-width="2.5"/>')
        _dot(c, density_origin_x, cy, dl.GREEN, 5)
        dl.text(c, density_origin_x - 8, cy + 32, "Origin", 16, anchor="end")

        normal = statistics.NormalDist(0, sigma_degrees)
        for i in range(ray_count):
            angle = math.radians(normal.inv_cdf((i + 0.5) / ray_count))
            end = (ray_origin_x + ray_length * math.cos(angle), cy - ray_length * math.sin(angle))
            dl.arrow(c, ray_origin_x, cy, *end, color, 1.3)
        _dot(c, ray_origin_x, cy, dl.GREEN, 5)
        dl.text(c, ray_origin_x - 8, cy + 32, "Origin", 16, anchor="end")
        dl.arrow(c, left + panel_width + 12, cy, right - 12, cy, dl.GREY, 2)
        dl.text(c, left + 18, top + panel_height - 23,
                "Larger angular spread" if row == 0 else "Smaller angular spread", 17)
        dl.text(c, right + 18, top + panel_height - 23,
                "Same count, wider sampled angles" if row == 0 else "Same count, concentrated directions", 17)

    dl.text(c, left, 740, "Curve radius: relative sampling density · arrow direction: one sampled ray", 17)
    dl.text(c, left, 773, "Illustrative azimuth sections; the curves carry no gain or distance scale.", 17)
    dl.validate(c)
    dl.write_svg(out_dir / "generic_wpm_directivity_sampling.svg", c.render())


def layout(out_dir):
    c = dl.Canvas(1000, 370, "Generic wpm contribution layout",
                  "Receiver slot varies fastest in aligned contribution channels; Valid gates payload reads.")
    dl.text(c, 32, 34, "Dense slot order", 20, weight="bold")
    labels = ["tile", "transmitter", "ray", "bounce", "receiver slot"]
    for i, label in enumerate(labels):
        dl.box(c, 32 + i * 193, 62, 164, 56, label, fill=dl.BLUE if i < 4 else dl.ORANGE)
        if i < 4:
            dl.arrow(c, 202 + i * 193, 90, 219 + i * 193, 90)
    dl.text(c, 32, 151, "Slower varying", 13, fill=dl.GREY)
    dl.text(c, 968, 151, "Faster varying", 13, fill=dl.GREY, anchor="end")
    dl.text(c, 32, 200, "Example group [2, 0, 2]", 17, weight="bold")
    xs = [450, 620, 790]
    for x, slot, rx in zip(xs, range(3), [2, 0, 2]):
        dl.text(c, x, 199, f"slot {slot} → Rx {rx}", 14, anchor="middle")
    for y, name, values in [(235, "Valid", ["1", "0", "1"]),
                            (285, "Every payload channel", ["read", "do not read", "read"])]:
        dl.text(c, 32, y + 19, name, 15)
        for x, value in zip(xs, values):
            dl.box(c, x - 73, y, 146, 36, value,
                   fill=dl.FAINT if value in ("0", "do not read") else dl.GREEN)
    dl.text(c, 32, 350, "CPU parameters describe dimensions and the accepted selectors.", 14, fill=dl.GREY)
    dl.validate(c)
    dl.write_svg(out_dir / "generic_wpm_output_layout.svg", c.render())


def _dot(c, x, y, color, radius=4):
    c.add(f'<circle cx="{dl.fmt(x)}" cy="{dl.fmt(y)}" r="{dl.fmt(radius)}" '
          f'fill="{color}" stroke="{dl.WHITE}" stroke-width="1.2"/>')


def _project(origin, point, scale=1):
    """Oblique view shared by the three local grid geometries."""
    x, y, z = point
    return origin[0] + scale * (0.83 * x - 0.50 * y), origin[1] - scale * (0.30 * x + 0.20 * y + 0.85 * z)


def _direction(azimuth, elevation=0):
    az, el = math.radians(azimuth), math.radians(elevation)
    return math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)


def _grid_poses(c, origin, poses, length):
    for position, direction in poses:
        start = _project(origin, position)
        end = _project(origin, tuple(p + length * d for p, d in zip(position, direction)))
        dl.arrow(c, *start, *end, dl.BLUE, 2.0)
    for position, _ in poses:
        _dot(c, *_project(origin, position), dl.GREEN, 5)


def grid_geometry(out_dir):
    c = dl.Canvas(1000, 550, "Generic wpm model grid geometry",
                  "Three illustrative three-by-three grids before the pattern pose. Spherical grids "
                  "share one origin and vary elevation by row and azimuth by column. Planar grids "
                  "place origins in Y and Z with every local X axis pointing in the positive X direction. "
                  "Cylindrical grids place origins along Z and vary azimuth by column. Green dots mark "
                  "element origins; blue arrows show element orientation, not receiver acceptance cones.")
    dl.text(c, 24, 34, "Grid element poses, before the pattern pose", 23, weight="bold")
    for x, name, summary in [(24, "SPHERICAL", "One origin, angular directions"),
                             (350, "PLANAR", "YZ origins, parallel directions"),
                             (676, "CYLINDRICAL", "Z origins, azimuth directions")]:
        dl.box(c, x, 70, 300, 365)
        dl.text(c, x + 18, 104, name, 21, weight="bold")
        dl.text(c, x + 18, 134, summary, 16)

    spherical = [((0, 0, 0), _direction(az, el)) for el in (-25, 0, 25) for az in (-35, 0, 35)]
    _grid_poses(c, (90, 285), spherical, 170)
    planar_origin = (482, 268)
    corners = [_project(planar_origin, p) for p in [(0, -55, -55), (0, 55, -55),
                                                    (0, 55, 55), (0, -55, 55)]]
    c.add('<polygon points="' + ' '.join(f'{dl.fmt(x)},{dl.fmt(y)}' for x, y in corners) +
          f'" fill="{dl.WHITE}" stroke="{dl.FAINT}" stroke-width="1.5"/>')
    planar = [((0, y, z), (1, 0, 0)) for z in (-50, 0, 50) for y in (-50, 0, 50)]
    _grid_poses(c, planar_origin, planar, 125)
    cylindrical = [((0, 0, z), _direction(az)) for z in (-60, 0, 60) for az in (-35, 0, 35)]
    dl.arrow(c, *_project((742, 270), (0, 0, -60)), *_project((742, 270), (0, 0, 60)),
             dl.FAINT, 1.5, head=False)
    _grid_poses(c, (742, 270), cylindrical, 165)

    for x, rows, cols in [(42, "Rows: elevation (degrees)", "Columns: azimuth (degrees)"),
                           (368, "Rows: Z position (meters)", "Columns: Y position (meters)"),
                           (694, "Rows: height Z (meters)", "Columns: azimuth (degrees)")]:
        dl.text(c, x, 380, rows, 17)
        dl.text(c, x, 410, cols, 17)
    _dot(c, 34, 471, dl.GREEN, 5)
    dl.text(c, 50, 477, "Element origin", 17)
    dl.arrow(c, 240, 471, 280, 471, dl.BLUE, 2)
    dl.text(c, 294, 477, "Element local +X direction", 17)
    dl.text(c, 24, 524, "3 × 3 elements in each example · schematic, not to scale", 17, fill=dl.GREY)
    for axis, point, offset in [("+X", (55, 0, 0), (12, 5)),
                                 ("+Y", (0, 55, 0), (-12, 5)),
                                 ("+Z", (0, 0, 55), (0, -10))]:
        p = _project((868, 511), point)
        dl.arrow(c, 868, 511, *p, dl.GREY, 1.6)
        dl.text(c, p[0] + offset[0], p[1] + offset[1], axis, 16,
                anchor="middle", fill=dl.GREY)
    dl.validate(c)
    dl.write_svg(out_dir / "generic_wpm_grid_geometry.svg", c.render())


def _ray_bundle(c, origin, angle, scale=1):
    """The same three local poses, composed with each illustrative transmitter pose."""
    ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))

    def point(x, y):
        return origin[0] + scale * (ca * x - sa * y), origin[1] - scale * (sa * x + ca * y)

    for x, y, degrees in [(0, 30, 15), (22, 0, 0), (0, -30, -15)]:
        dx, dy, _ = _direction(degrees)
        start, end = point(x, y), point(x + 130 * dx, y + 130 * dy)
        dl.arrow(c, *start, *end, dl.BLUE, 2.4)
        _dot(c, *start, dl.BLUE, 4)
    _dot(c, *origin, dl.GREEN, 6)


def pattern_roles(out_dir):
    c = dl.Canvas(1000, 645, "Local ray poses reused at every transmitter",
                  "One selected ray pattern contains three illustrative ray origins and orientations. "
                  "The entire pattern is repeated at both elements of the selected transmitter pattern. "
                  "The second transmitter is rotated, so all three ray origins and directions rotate "
                  "with it. Transmitter and receiver poses are relative to the sensor; ray poses are "
                  "relative to each transmitter. Receiver markers show independent positions, not "
                  "acceptance cones. Ray, transmitter, and sensor poses compose into a world ray pose.")
    dl.text(c, 24, 34, "One ray pattern is reused at every transmitter", 23, weight="bold")
    dl.box(c, 24, 70, 280, 410)
    dl.box(c, 344, 70, 632, 410)
    dl.text(c, 44, 104, "Selected ray pattern", 21, weight="bold")
    dl.text(c, 44, 134, "3 local ray poses", 17)
    dl.text(c, 366, 104, "Selected transmitter and receiver patterns", 21, weight="bold")
    dl.text(c, 366, 134, "2 transmitter poses (Tx) and 2 receiver poses (Rx)", 17)
    dl.arrow(c, 80, 300, 276, 300, dl.FAINT, 1.4)
    dl.arrow(c, 80, 300, 80, 180, dl.FAINT, 1.4)
    dl.text(c, 269, 326, "+X", 16, fill=dl.GREY, anchor="middle")
    dl.text(c, 58, 187, "+Y", 16, fill=dl.GREY, anchor="middle")
    _ray_bundle(c, (80, 300), 0, 1.25)
    dl.arrow(c, 80, 308, 80, 374, dl.GREY, 1.3, head=False)
    dl.text(c, 54, 400, "Tx frame origin", 17)
    dl.text(c, 44, 448, "Dots: ray origins", 17, fill=dl.BLUE)
    dl.arrow(c, 311, 270, 337, 270, dl.BLUE, 2.0)
    _ray_bundle(c, (455, 270), 0, 0.85)
    _ray_bundle(c, (780, 310), 90, 0.85)
    dl.text(c, 478, 355, "Tx 0", 18, weight="bold", anchor="middle")
    dl.text(c, 780, 355, "Tx 1", 18, weight="bold", anchor="middle")
    for x, y, label in [(640, 420, "Rx 0"), (885, 420, "Rx 1")]:
        dl.box(c, x - 7, y - 7, 14, 14, fill=dl.PURPLE, rx=2)
        dl.text(c, x, y + 35, label, 18, weight="bold", anchor="middle")
    dl.arrow(c, 400, 430, 466, 430, dl.GREY, 1.6)
    dl.arrow(c, 400, 430, 400, 374, dl.GREY, 1.6)
    dl.text(c, 485, 436, "+X", 16, fill=dl.GREY, anchor="middle")
    dl.text(c, 400, 363, "+Y", 16, fill=dl.GREY, anchor="middle")
    dl.text(c, 400, 465, "Sensor frame", 16, fill=dl.GREY)
    dl.text(c, 24, 516, "Pose composition", 19, weight="bold")
    for i, label in enumerate(["Ray pose", "Transmitter pose", "Sensor pose", "World ray pose"]):
        dl.box(c, 24 + 244 * i, 537, 220, 48, label, label_size=18,
               fill=dl.BLUE if i == 0 else dl.GREEN if i == 1 else dl.PANEL)
        if i < 3:
            dl.arrow(c, 248 + 244 * i, 561, 264 + 244 * i, 561, dl.GREY, 1.5)
    dl.text(c, 24, 622, "Tx and Rx poses are sensor-relative; ray poses are transmitter-relative.", 18)
    dl.validate(c)
    dl.write_svg(out_dir / "generic_wpm_pattern_roles.svg", c.render())


def receiver_connections(out_dir):
    c = dl.Canvas(1000, 800, "Generic wpm model receiver connections",
                  "Four logical connection examples. nton connects every transmitter to all active "
                  "receivers. Zero-bloom 1to1 pairs equal flat element indices. map gives each "
                  "transmitter in the selected pattern the same ordered group, here receiver indices "
                  "2, 0, 2 in slots 0, 1, 2, preserving the repeated receiver. Radius-one bloom on "
                  "matching three-by-three row-major grids gives the interior transmitter at index 4 "
                  "nine receiver slots, ordered row by row; the center is slot 4. Connections select "
                  "receiver candidates, not guaranteed valid contributions, and bloom adds no emitted rays.")
    dl.text(c, 24, 34, "Choose receiver connections for the selected transmitter pattern", 23, weight="bold")
    for x, y, h in [(24, 70, 270), (512, 70, 270), (24, 365, 345), (512, 365, 345)]:
        dl.box(c, x, y, 464, h)
    dl.text(c, 48, 104, "nton · all receivers", 22, weight="bold")
    dl.text(c, 48, 133, "Each Tx uses every active Rx", 17)
    for ty in (175, 255):
        for ry in (160, 220, 280):
            dl.arrow(c, 172, ty + 20, 340, ry + 20, dl.GREY, 1.5)
    for i, y in enumerate((175, 255)):
        dl.box(c, 80, y, 92, 40, f"Tx {i}", fill=dl.GREEN, label_size=18)
    for i, y in enumerate((160, 220, 280)):
        dl.box(c, 340, y, 92, 40, f"Rx {i}", fill=dl.PURPLE, label_size=18)

    dl.text(c, 536, 104, "1to1 · zero bloom", 22, weight="bold")
    dl.text(c, 536, 133, "Pairs equal flat element indices", 17)
    for i, y in enumerate((160, 220, 280)):
        dl.arrow(c, 662, y + 20, 852, y + 20, dl.GREY, 1.5)
        dl.box(c, 570, y, 92, 40, f"Tx {i}", fill=dl.GREEN, label_size=18)
        dl.box(c, 852, y, 92, 40, f"Rx {i}", fill=dl.PURPLE, label_size=18)

    dl.text(c, 48, 399, "map · ordered receiver group", 22, weight="bold")
    dl.text(c, 48, 428, "One shared group: [2, 0, 2]", 17)
    dl.box(c, 270, 465, 185, 195, fill=dl.WHITE, stroke=dl.FAINT)
    for i, y in enumerate((485, 575)):
        dl.arrow(c, 154, y + 20, 270, 562, dl.GREY, 1.5)
        dl.box(c, 62, y, 92, 40, f"Tx {i}", fill=dl.GREEN, label_size=18)
    for i, rx in enumerate((2, 0, 2)):
        dl.box(c, 285, 480 + 60 * i, 155, 45, f"slot {i} → Rx {rx}",
               fill=dl.PURPLE, label_size=17, label_weight="normal")
    dl.text(c, 48, 687, "Repeated Rx 2 keeps two slots.", 17)

    dl.text(c, 536, 399, "1to1 · bloom radius 1", 22, weight="bold")
    dl.text(c, 536, 428, "Matching 3 × 3 grids, rowMajor", 17)
    for row in range(3):
        for col in range(3):
            i = row * 3 + col
            x, y = 536 + 65 * col, 466 + 65 * row
            dl.box(c, x, y, 60, 60, fill=dl.WHITE,
                   stroke=dl.GREEN if i == 4 else dl.FAINT, stroke_width=3 if i == 4 else 1.5)
            dl.text(c, x + 30, y + 23, f"Rx {i}", 16, weight="bold", anchor="middle", fill=dl.PURPLE)
            dl.text(c, x + 30, y + 47, f"slot {i}", 16, anchor="middle")
    dl.arrow(c, 814, 561, 746, 561, dl.GREY, 1.6)
    dl.box(c, 814, 541, 116, 40, "Tx 4", fill=dl.GREEN, label_size=18)
    dl.text(c, 872, 515, "Interior element", 16, anchor="middle")
    dl.text(c, 872, 611, "9 receiver slots", 16, anchor="middle")
    dl.text(c, 536, 687, "Center slot 4; no extra emitted rays.", 17)
    dl.text(c, 24, 747, "Tx = transmitter · Rx = receiver · lines show connections, not physical return paths", 17)
    dl.text(c, 24, 773, "Schematic; a connected receiver does not guarantee a valid contribution.", 17, fill=dl.GREY)
    dl.validate(c)
    dl.write_svg(out_dir / "generic_wpm_receiver_connections.svg", c.render())


def generate(out_dir):
    patterns(out_dir)
    directivity_sampling(out_dir)
    layout(out_dir)
    grid_geometry(out_dir)
    pattern_roles(out_dir)
    receiver_connections(out_dir)


if __name__ == "__main__":
    generate(dl.output_dir(__file__))
