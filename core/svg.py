"""SVG writer for hobby lasers."""
import math
from xml.sax.saxutils import escape

from . import geom2d as G

CUT, ENGR, UP, DOWN, DIM = '#000000', '#ff0000', '#d08a00', '#0050ff', '#1f4e9a'


def g(v):
    return f'{round(v, 1):g}'


def _path(v, closed, tf):
    p0 = tf(v[0][:2])
    d = [f'M{p0[0]:.3f},{p0[1]:.3f}']
    n = len(v) if closed else len(v) - 1
    for i in range(n):
        a, b = v[i], v[(i + 1) % len(v)]
        q = tf(b[:2])
        bul = a[2] if len(a) > 2 else 0.0
        if abs(bul) < 1e-9:
            d.append(f'L{q[0]:.3f},{q[1]:.3f}')
        else:
            _, r, th = G.arc_center(a[:2], b[:2], bul)
            r *= tf.k
            large = 1 if abs(th) > math.pi else 0
            sweep = 0 if bul > 0 else 1
            d.append(f'A{r:.3f},{r:.3f} 0 {large} {sweep} {q[0]:.3f},{q[1]:.3f}')
    if closed:
        d.append('Z')
    return ''.join(d)


class _Tf:
    def __init__(self, x0, y0, k, H):
        self.x0, self.y0, self.k, self.H = x0, y0, k, H

    def __call__(self, p):
        return (self.x0 + p[0] * self.k, self.y0 + (self.H - p[1]) * self.k)


def _part_els(p, tf, sw=0.2, dash=None):
    els = []
    st = f'fill="none" stroke-width="{sw}"'
    for v in p.polys:
        els.append(f'<path d="{_path(v, True, tf)}" stroke="{CUT}" {st}/>')
    for c, r in p.circles:
        q = tf(c)
        els.append(f'<circle cx="{q[0]:.3f}" cy="{q[1]:.3f}" r="{r * tf.k:.3f}" stroke="{CUT}" {st}/>')
    for v in p.ep:
        els.append(f'<path d="{_path(v, True, tf)}" stroke="{ENGR}" {st}/>')
    for c, r in p.ec:
        q = tf(c)
        els.append(f'<circle cx="{q[0]:.3f}" cy="{q[1]:.3f}" r="{r * tf.k:.3f}" stroke="{ENGR}" {st}/>')
    for s in p.text:
        pts = ' '.join(f'{x:.3f},{y:.3f}' for x, y in (tf(q) for q in s))
        els.append(f'<polyline points="{pts}" stroke="{ENGR}" {st}/>')
    da = dash or f'{3 * tf.k:.2f},{1.5 * tf.k:.2f}'
    for col, ls in ((UP, p.bend_up), (DOWN, p.bend_down)):
        for a, b in ls:
            qa, qb = tf(a), tf(b)
            els.append(f'<line x1="{qa[0]:.3f}" y1="{qa[1]:.3f}" x2="{qb[0]:.3f}" y2="{qb[1]:.3f}" '
                       f'stroke="{col}" {st} stroke-dasharray="{da}"/>')
    return els


def part_svg(p, path, unit='mm'):
    m = 1.0
    W, H = p.L + 2 * m, p.W + 2 * m
    tf = _Tf(m, m, 1.0, p.W)
    body = '\n'.join(_part_els(p, tf, 0.1))
    _write(path, f'<svg xmlns="http://www.w3.org/2000/svg" width="{_sz(W, unit)}" height="{_sz(H, unit)}" '
                 f'viewBox="0 0 {W:.3f} {H:.3f}">\n<title>{escape(p.name)}</title>\n{body}\n</svg>\n')


def _sz(v, unit):
    return f'{v / 25.4:.4f}in' if unit == 'in' else f'{v:.3f}mm'


def _write(path, s):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(s)

