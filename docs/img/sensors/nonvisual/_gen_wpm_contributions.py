#!/usr/bin/env python3
"""The figure of the wave-propagation concept the Lidar generic wpm model and the Radar generic
wpmDmat model share: one traced path through the scene, reflected and transmitted surface by
surface, and the contributions it sends back to the receiver from every surface it meets.

One function per SVG; ``generate(out_dir)`` writes them all. Run in place with
``python3 -B _gen_wpm_contributions.py`` or through ``generate_diagrams.py``.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import _diagram_lib as dl  # noqa: E402


# ------------------------------------------------------------------------------- geometry ---
def _unit(v):
    n = math.hypot(v[0], v[1])
    return (v[0] / n, v[1] / n)


def _add(p, v, s=1.0):
    return (p[0] + v[0] * s, p[1] + v[1] * s)


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def _reflect(d, n):
    k = 2 * _dot(d, n)
    return (d[0] - k * n[0], d[1] - k * n[1])


def _normal_of(t):
    """The normal of a surface with tangent ``t``, rotated a quarter turn counter-clockwise."""
    return (-t[1], t[0])


def _neg(v):
    return (-v[0], -v[1])


def _refract(d, far_normal, tangent, exit_deg):
    """The direction a ray leaves a pane in: the incoming direction ``d`` bent toward the pane's
    normal, leaving at ``exit_deg`` from the far-side normal on the same side it came in."""
    side = 1.0 if _dot(d, tangent) >= 0 else -1.0
    a = math.radians(exit_deg)
    return _unit(_add((far_normal[0] * math.cos(a), far_normal[1] * math.cos(a)), tangent, side * math.sin(a)))


def _cross_line(p, d, q, t):
    """The point where the ray ``p + s d`` meets the line through ``q`` with direction ``t``."""
    den = d[0] * t[1] - d[1] * t[0]
    s = ((q[0] - p[0]) * t[1] - (q[1] - p[1]) * t[0]) / den
    return _add(p, d, s)


# -------------------------------------------------------------------------------- drawing ---
def _pt(p):
    return f"{dl.fmt(p[0])},{dl.fmt(p[1])}"


def _polyline(c, pts, stroke, width, dashed=False, opacity=None, cap="round"):
    d = "M" + " L".join(_pt(p) for p in pts)
    extra = f' stroke-dasharray="{dl._dash(width)}"' if dashed else ""
    if opacity is not None:
        extra += f' stroke-opacity="{dl.fmt(opacity)}"'
    c.add(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{dl.fmt(width)}" '
          f'stroke-linecap="{cap}" stroke-linejoin="round"{extra}/>')


def _circle(c, p, r, fill, stroke=None, sw=1.5):
    s = f' stroke="{stroke}" stroke-width="{dl.fmt(sw)}"' if stroke else ""
    c.add(f'<circle cx="{dl.fmt(p[0])}" cy="{dl.fmt(p[1])}" r="{dl.fmt(r)}" fill="{fill}"{s}/>')


def _slab(c, p1, p2, thickness, fill, stroke="none", sw=1.5):
    """A straight surface drawn as a thin rotated rectangle between ``p1`` and ``p2``."""
    t = _unit(_sub(p2, p1))
    n = _normal_of(t)
    h = thickness / 2
    corners = [_add(p1, n, h), _add(p2, n, h), _add(p2, n, -h), _add(p1, n, -h)]
    s = f' stroke="{stroke}" stroke-width="{dl.fmt(sw)}" stroke-linejoin="round"' if stroke != "none" else ""
    c.add(f'<polygon points="{" ".join(_pt(p) for p in corners)}" fill="{fill}"{s}/>')


SPREAD = 0.55                       # the lobe's angular width, radians


def _lobe_radius(radius, phi, phi_peak):
    return radius * (0.26 + 0.74 * math.exp(-((phi - phi_peak) / SPREAD) ** 2))


def _lobe(c, hit, normal, peak_dir, radius, color=dl.PURPLE):
    """A lobe of the surface's response on the side of ``normal``, peaking along ``peak_dir``."""
    t = _normal_of(normal)
    phi_peak = math.atan2(_dot(peak_dir, t), _dot(peak_dir, normal))
    pts = [hit]
    for k in range(-40, 41):
        phi = k * math.pi / 90           # -80 to +80 degrees from the normal, in 2-degree steps
        r = _lobe_radius(radius, phi, phi_peak)
        pts.append(_add(_add(hit, normal, r * math.cos(phi)), t, r * math.sin(phi)))
    pts.append(hit)
    d = "M" + " L".join(_pt(p) for p in pts) + " Z"
    c.add(f'<path d="{d}" fill="{color}" fill-opacity="0.13" stroke="{color}" stroke-width="1.4" '
          f'stroke-linejoin="round"/>')
    return phi_peak


def _lobe_point(hit, normal, direction, radius, phi_peak):
    """Where the lobe's outline is crossed by ``direction``: the sampled value in that direction."""
    t = _normal_of(normal)
    phi = math.atan2(_dot(direction, t), _dot(direction, normal))
    r = _lobe_radius(radius, phi, phi_peak)
    return _add(_add(hit, normal, r * math.cos(phi)), t, r * math.sin(phi))


def _sample(c, p):
    _circle(c, p, 3.6, dl.WHITE, dl.PURPLE, 1.6)


def _number(c, p, n):
    _circle(c, p, 9, dl.WHITE, dl.DK, 1.5)
    dl.text(c, p[0], p[1] + 4, str(n), 11, "bold", "middle", dl.DK)


# ------------------------------------------------------------------- wpm_contribution_paths ---
W, H = 960, 620
TX, RX = (380.0, 558.0), (452.0, 558.0)                     # the two ends of one sensor
HIT1 = (482.0, 300.0)                                       # where the primary ray meets the pane
PANE_T = _unit((150.0, -55.0))                              # the pane's direction
PANE_N = _normal_of(PANE_T)                                 # its normal, toward the sensor
L_WALL, L_OBJECT, L_STUB = 390.0, 170.0, 60.0               # path lengths: to the wall, to the object, the stub
EXIT_DEG = 12.0                                             # the transmitted continuation leaves the pane this far off its normal
RING = 9.0                                                  # the receiver's ring radius
WIDTHS = (2.6, 2.1, 1.7, 1.4)                               # the path thins with every hit
CONTRIB = (2.0, 1.6, 1.3, 1.1)                              # and so do the contributions, by hit
HALO = "#76B900"
LEGEND_XY = (28.0, 44.0)


def wpm_contribution_paths(out_dir: pathlib.Path) -> None:
    d_in = _unit(_sub(HIT1, TX))                            # the primary ray's direction
    d_refl1 = _reflect(d_in, PANE_N)                        # reflected at the pane
    HIT2 = _add(HIT1, d_refl1, L_WALL)                      # on the wall
    HIT3 = _add(HIT1, PANE_T, 72.0)                         # back on the pane, which the path now crosses
    d_out2 = _unit(_sub(HIT3, HIT2))
    WALL_N = _unit(_sub(d_out2, d_refl1))                   # the wall orientation that sends the path there
    WALL_T = (WALL_N[1], -WALL_N[0])
    d_trans = _refract(d_out2, _neg(PANE_N), PANE_T, EXIT_DEG)   # bent toward the pane's normal
    HIT4 = _add(HIT3, d_trans, L_OBJECT)                    # on the object behind the pane
    OBJ_T = _unit((0.966, 0.258))                           # tilted so that the path leaves it away from Rx
    OBJ_N = _normal_of(OBJ_T)
    d_stub = _reflect(d_trans, OBJ_N)
    hits = {1: HIT1, 2: HIT2, 3: HIT3, 4: HIT4}
    to_rx = {k: _unit(_sub(RX, h)) for k, h in hits.items()}
    rx_end = {k: _add(RX, v, -RING) for k, v in to_rx.items()}

    c = dl.Canvas(
        W, H, "How contributions arise along one traced path",
        "A sensor with a transmitter Tx and a receiver Rx side by side at the bottom. The primary ray "
        "leaves Tx and meets a transparent pane (hit 1), where it reflects to a wall (hit 2) and back to "
        "the pane (hit 3); there the path passes through the pane, bent toward its normal, to an object "
        "behind it (hit 4) and goes on toward the depth of the trace. From every hit a contribution ray "
        "runs straight back to Rx; the one from hit 4 crosses the pane again. At hits 1 and 2 the "
        "surface's response is drawn as a lobe, sampled in the continuation's direction and toward Rx; at "
        "hit 3 the lobe sits on both sides of the pane. The path Tx, pane, wall, Rx is highlighted as one "
        "contribution with its three segment lengths; the rays thin with every hit. A legend at the top "
        "left names the ray types.")

    # --- the highlighted contribution: one full path from Tx to Rx, under everything else
    _polyline(c, [TX, HIT1, HIT2, rx_end[2]], HALO, 14, opacity=0.16)

    # --- the surfaces
    pane_a, pane_b = _add(HIT1, PANE_T, -96), _add(HIT1, PANE_T, 96)
    _slab(c, pane_a, pane_b, 7, dl.WHITE, dl.BLUE, 1.6)
    dl.text(c, pane_a[0] - 10, pane_a[1] + 5, "transparent pane (wavelength dependent)", 12, "normal", "end", dl.GREY)
    obj_a, obj_b = _add(HIT4, OBJ_T, -50), _add(HIT4, OBJ_T, 50)
    _slab(c, obj_a, obj_b, 12, dl.GREY)
    dl.text(c, obj_b[0] + 12, obj_b[1] + 4, "object behind the pane", 12, "normal", "start", dl.GREY)
    wall_a, wall_b = _add(HIT2, WALL_T, -50), _add(HIT2, WALL_T, 88)     # shorter above the hit, where the labels sit
    _slab(c, wall_a, wall_b, 12, dl.GREY)
    wall_label = _add(HIT2, WALL_N, -30)
    dl.text(c, wall_label[0] + 4, wall_label[1] + 16, "wall", 12, "normal", "start", dl.GREY)

    # --- the sensor: Tx and Rx side by side
    box = dl.box(c, 352, 534, 128, 56, fill=dl.WHITE, stroke=dl.GREY, stroke_width=1.5, rx=8)
    _circle(c, TX, 7, dl.DK)
    _circle(c, RX, 8, dl.WHITE, dl.GREEN, 2.5)
    dl.text(c, TX[0], TX[1] + 24, "Tx", 12, "bold", "middle", dl.DK)
    dl.text(c, RX[0], RX[1] + 24, "Rx", 12, "bold", "middle", dl.DK)
    dl.text(c, box.cx, box.bottom + 17, "one sensor", 12, "normal", "middle", dl.GREY)

    # --- the lobes of the surfaces' response, smaller with every hit, under the rays
    pk1 = _lobe(c, HIT1, PANE_N, d_refl1, 50)
    pk2 = _lobe(c, HIT2, WALL_N, d_out2, 40)
    pk3 = _lobe(c, HIT3, _neg(PANE_N), d_trans, 28)        # the transmitted side of the pane's response
    pk3r = _lobe(c, HIT3, PANE_N, to_rx[3], 22)             # and its reflected side, sampled toward Rx

    # --- the rays: primary, continuations, the stub beyond the last hit
    dl.arrow(c, TX[0], TX[1] - 7, HIT1[0], HIT1[1], dl.DK, WIDTHS[0])
    dl.arrow(c, HIT1[0], HIT1[1], HIT2[0], HIT2[1], dl.ORANGE, WIDTHS[1])
    dl.arrow(c, HIT2[0], HIT2[1], HIT3[0], HIT3[1], dl.ORANGE, WIDTHS[2])
    dl.arrow(c, HIT3[0], HIT3[1], HIT4[0], HIT4[1], dl.ORANGE, WIDTHS[3], dashed=True)
    stub_end = _add(HIT4, d_stub, L_STUB)
    _polyline(c, [HIT4, stub_end], dl.MUTED, WIDTHS[3], dashed=True)
    dots = _add(stub_end, d_stub, 14)
    dl.text(c, dots[0], dots[1] + 5, "…", 16, "bold", "middle", dl.MUTED)

    # --- the contributions: straight back to Rx, thinner with every hit before them
    for k in (1, 2, 3):
        dl.arrow(c, hits[k][0], hits[k][1], rx_end[k][0], rx_end[k][1], dl.GREEN, CONTRIB[k - 1], dashed=True)
    crossing = _cross_line(HIT4, to_rx[4], HIT1, PANE_T)   # the one from behind the pane crosses it again
    _polyline(c, [HIT4, crossing], dl.GREEN, CONTRIB[3], dashed=True)
    dl.arrow(c, crossing[0], crossing[1], rx_end[4][0], rx_end[4][1], dl.GREEN, CONTRIB[3] * 0.65, dashed=True)

    # --- the sampled directions on the lobes, labeled once
    _sample(c, _lobe_point(HIT1, PANE_N, d_refl1, 50, pk1))
    _sample(c, _lobe_point(HIT1, PANE_N, to_rx[1], 50, pk1))
    s_cont = _lobe_point(HIT2, WALL_N, d_out2, 40, pk2)
    s_rx = _lobe_point(HIT2, WALL_N, to_rx[2], 40, pk2)
    _sample(c, s_cont)
    _sample(c, s_rx)
    label = (HIT2[0] + 14, HIT2[1] - 54)                   # above the wall's end, with a leader to the sample
    _polyline(c, [s_cont, (label[0] - 3, label[1] - 4)], dl.PURPLE, 0.9)
    dl.text(c, label[0], label[1], "continuation", 11, "normal", "start", dl.PURPLE)
    dl.text(c, s_rx[0] - 28, s_rx[1] + 30, "toward Rx", 11, "normal", "end", dl.PURPLE)
    _sample(c, _lobe_point(HIT3, _neg(PANE_N), d_trans, 28, pk3))
    _sample(c, _lobe_point(HIT3, PANE_N, to_rx[3], 22, pk3r))

    # --- the hits
    offsets = {1: (-0.5, -0.87), 2: (-0.196, -0.98), 3: (0.5, -0.87), 4: (0.0, -1.0)}
    for k, p in hits.items():
        _number(c, _add(p, offsets[k], 27), k)

    # --- the segment lengths of the highlighted contribution
    for a, b, text, side in ((TX, HIT1, "d₁", -1), (HIT1, HIT2, "d₂", -1), (HIT2, RX, "d₃", 1)):
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        n = _normal_of(_unit(_sub(b, a)))
        p = _add(mid, n, 15 * side)
        dl.text(c, p[0], p[1] + 5, text, 13, "bold", "middle", dl.GREEN)

    dl.legend(c, LEGEND_XY[0], LEGEND_XY[1], [
        ("primary ray, from Tx", dl.DK, "line"),
        ("continuation after a hit, reflected", dl.ORANGE, "line"),
        ("continuation after a hit, transmitted", dl.ORANGE, "dashed"),
        ("contribution, straight back to Rx", dl.GREEN, "dashed"),
        ("material response (BSDF), sampled at the hit", dl.PURPLE, "outline"),
        ("one contribution: the whole path Tx to Rx", "#D6E9B4", "box"),
        ("the path goes on, to the depth of the trace", dl.MUTED, "dashed"),
    ], size=12, horizontal=False)

    dl.validate(c)
    dl.write_svg(out_dir / "wpm_contribution_paths.svg", c.render())


# ------------------------------------------------------------------------------- entry point ---
def generate(out_dir: pathlib.Path) -> None:
    wpm_contribution_paths(out_dir)


if __name__ == "__main__":
    generate(dl.output_dir(__file__))
