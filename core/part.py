"""Prepares a part for export: orientation, entities, engraved part number, pre-cut check."""
import math

from . import geom2d as G
from . import font as F


class Part:
    def __init__(self, it, bends_on=True, text_h=10.0):
        self.name, self.pn, self.mat = it['name'], it.get('pn', ''), it.get('mat', '')
        self.t, self.qty, self.note = it['t'], it['qty'], it.get('note', '')
        self.warn = []
        engr_in = it.get('engr') or []
        bends_in = [[['L', b[0], b[1]]] for b in (it.get('bends') or [])] if bends_on else []
        loops, (engr, bl), self.L, self.W = G.normalize(it['loops'], [engr_in, bends_in])
        self.circles, self.polys, curved = G.entities(loops)
        if curved:
            self.warn.append('curve_poly')
        self.ec, self.ep, _ = G.entities(engr) if engr else ([], [], False)
        ups = [b[2] for b in (it.get('bends') or [])] if bends_on else []
        self.bend_up = [(s[0][1], s[0][2]) for s, u in zip(bl, ups) if u]
        self.bend_down = [(s[0][1], s[0][2]) for s, u in zip(bl, ups) if not u]
        self.text, self.text_h = [], 0.0
        txt = (it.get('text') or '').strip()
        if txt:
            bad = F.supported(txt)
            if bad:
                self.warn.append(('font', ''.join(bad)))
            strokes, h = F.place(txt, text_h, self.circles + self.ec, self.polys + self.ep,
                                 self.bend_up + self.bend_down, gap=max(2.0, self.t))
            if strokes:
                self.text, self.text_h = strokes, h
            else:
                self.warn.append(('text_nofit', txt))
        self.warn += check(self)

    @property
    def engraved(self):
        return bool(self.ec or self.ep or self.text)

    def area(self):
        outer, holes = G.rings_of(self.circles, self.polys)
        return (G.area(outer) - sum(G.area(h) for h in holes)) if outer else 0.0

    def draw(self, doc, tf=None):
        f = tf or (lambda p: p)
        for v in self.polys:
            doc.poly([f(p[:2]) + (p[2],) for p in v], True, 'CUT')
        for c, r in self.circles:
            doc.circle(f(c), r, 'CUT')
        for v in self.ep:
            doc.poly([f(p[:2]) + (p[2],) for p in v], True, 'ENGRAVE')
        for c, r in self.ec:
            doc.circle(f(c), r, 'ENGRAVE')
        for s in self.text:
            doc.poly([f(p) for p in s], False, 'ENGRAVE')
        for a, b in self.bend_up:
            doc.line(f(a), f(b), 'BEND_UP')
        for a, b in self.bend_down:
            doc.line(f(a), f(b), 'BEND_DOWN')


def check(p):
    out = []
    t = p.t
    outer, holes = G.rings_of(p.circles, p.polys)
    if not outer:
        return [('no_contour', '')]
    small = sorted({round(2 * r, 2) for c, r in p.circles if 2 * r < t - 1e-6 and G.inside(c, outer)})
    if small:
        out.append(('hole_lt_t', (small, t)))
    web = None
    box = lambda q: (min(x for x, _ in q), min(y for _, y in q), max(x for x, _ in q), max(y for _, y in q))
    far = lambda a, b: a[0] - b[2] >= t or b[0] - a[2] >= t or a[1] - b[3] >= t or b[1] - a[3] >= t
    segs = [(outer[i], outer[i + 1], box(outer[i:i + 2])) for i in range(len(outer) - 1)]

    def near(b):
        return [(a, c) for a, c, sb in segs if not far(b, sb)]

    def to_edge(pts, b):
        ns = near(b)
        return min((G.seg_dist(v, a, c) for v in pts for a, c in ns), default=None)

    cs = [(c, r) for c, r in p.circles if G.inside(c, outer) and 2 * r < 0.99 * max(p.L, p.W)]
    cb = [(c[0] - r, c[1] - r, c[0] + r, c[1] + r) for c, r in cs]
    ds = []
    for (c, r), b in zip(cs, cb):
        d = to_edge([c], b)
        if d is not None:
            ds.append(d - r)
    for i in range(len(cs)):
        for j in range(i + 1, len(cs)):
            if not far(cb[i], cb[j]):
                (a, ra), (b, rb) = cs[i], cs[j]
                ds.append(math.hypot(a[0] - b[0], a[1] - b[1]) - ra - rb)
    ao = G.area(outer)
    sl = [q for q in (G.poly_pts(v) for v in p.polys) if G.area(q) < ao - 1e-9 and G.inside(q[0], outer)]
    bb = [box(q) for q in sl]
    for i, q in enumerate(sl):
        d = to_edge(q[:-1], bb[i])
        if d is not None:
            ds.append(d)
        for (c, r), b in zip(cs, cb):
            if not far(bb[i], b):
                ds.append(G.poly_dist(c, q) - r)
        for j in range(i + 1, len(sl)):
            if not far(bb[i], bb[j]):
                ds += [min(G.poly_dist(v, sl[j]) for v in q[:-1]), min(G.poly_dist(v, q) for v in sl[j][:-1])]
    web = min(ds, default=None)
    if web is not None and web < t - 1e-6:
        out.append(('web_lt_t', (max(web, 0), t)))
    tiny = sum(1 for h in holes if max(max(x for x, _ in h) - min(x for x, _ in h),
                                       max(y for _, y in h) - min(y for _, y in h)) < 1.0)
    if tiny:
        out.append(('tiny', tiny))
    for v in p.polys:
        z = sum(1 for i in range(len(v)) if math.hypot(v[i][0] - v[i - 1][0], v[i][1] - v[i - 1][1]) < 0.01)
        if z:
            out.append(('zero_seg', z))
            break
    return out

