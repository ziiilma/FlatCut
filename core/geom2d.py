"""2D geometry of parts: orientation, DXF/SVG entities, contour points, checks."""
import math


def rot(p, a):
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c)


def bulge(a, m, b):
    cx, cy = b[0] - a[0], b[1] - a[1]
    ch = math.hypot(cx, cy)
    if ch < 1e-9:
        return 0.0
    s = (cx * (m[1] - a[1]) - cy * (m[0] - a[0])) / ch
    return -2 * s / ch


def circle3(a, m, b):
    d = 2 * (a[0] * (m[1] - b[1]) + m[0] * (b[1] - a[1]) + b[0] * (a[1] - m[1]))
    if abs(d) < 1e-9:
        return None
    ux = ((a[0] ** 2 + a[1] ** 2) * (m[1] - b[1]) + (m[0] ** 2 + m[1] ** 2) * (b[1] - a[1])
          + (b[0] ** 2 + b[1] ** 2) * (a[1] - m[1])) / d
    uy = ((a[0] ** 2 + a[1] ** 2) * (b[0] - m[0]) + (m[0] ** 2 + m[1] ** 2) * (a[0] - b[0])
          + (b[0] ** 2 + b[1] ** 2) * (m[0] - a[0])) / d
    return (ux, uy), math.hypot(a[0] - ux, a[1] - uy)


def arc_pts(a, b, bul, n=24):
    if abs(bul) < 1e-9:
        return [tuple(a), tuple(b)]
    th = 4 * math.atan(bul)
    ch = math.hypot(b[0] - a[0], b[1] - a[1])
    if ch < 1e-12:
        return [tuple(a), tuple(b)]
    r = ch / (2 * math.sin(th / 2))
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    ux, uy = (b[0] - a[0]) / ch, (b[1] - a[1]) / ch
    d = r * math.cos(th / 2)
    cx, cy = mx - uy * d, my + ux * d
    a0 = math.atan2(a[1] - cy, a[0] - cx)
    k = max(4, int(abs(th) / (2 * math.pi) * n * 4))
    return [(cx + abs(r) * math.cos(a0 + th * i / k), cy + abs(r) * math.sin(a0 + th * i / k)) for i in range(k + 1)]


def arc_center(a, b, bul):
    th = 4 * math.atan(bul)
    ch = math.hypot(b[0] - a[0], b[1] - a[1])
    r = ch / (2 * math.sin(th / 2))
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    ux, uy = (b[0] - a[0]) / ch, (b[1] - a[1]) / ch
    d = r * math.cos(th / 2)
    return (mx - uy * d, my + ux * d), abs(r), th


def poly_pts(v, closed=True):
    pts = []
    n = len(v) if closed else len(v) - 1
    for i in range(n):
        a, b = v[i], v[(i + 1) % len(v)]
        pts += arc_pts((a[0], a[1]), (b[0], b[1]), a[2])[:-1]
    if closed:
        return pts + pts[:1]
    return pts + [(v[-1][0], v[-1][1])]


def ring(c, r, k=72):
    return [(c[0] + r * math.cos(2 * math.pi * i / k), c[1] + r * math.sin(2 * math.pi * i / k)) for i in range(k + 1)]


def sample(loops):
    pts = []
    for segs in loops:
        for s in segs:
            if s[0] == 'C':
                c, r = s[1], s[2]
                pts += [(c[0] + r * math.cos(k * math.pi / 18), c[1] + r * math.sin(k * math.pi / 18)) for k in range(36)]
            elif s[0] == 'P':
                pts += [tuple(p) for p in s[1]]
            elif s[0] == 'A':
                pts += arc_pts(s[1], s[3], bulge(s[1], s[2], s[3]), 12)
            else:
                pts += [tuple(s[1]), tuple(s[2])]
    return pts


def hull(pts):
    p = sorted(set((round(x, 6), round(y, 6)) for x, y in pts))
    if len(p) < 3:
        return p

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for q in p:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], q) <= 0:
            lo.pop()
        lo.append(q)
    for q in reversed(p):
        while len(up) >= 2 and cross(up[-2], up[-1], q) <= 0:
            up.pop()
        up.append(q)
    return lo[:-1] + up[:-1]


def best_angle(pts):
    h = hull(pts)
    if len(h) < 3:
        return 0.0
    angles = {0.0}
    for i in range(len(h)):
        a, b = h[i], h[(i + 1) % len(h)]
        angles.add(round(-math.atan2(b[1] - a[1], b[0] - a[0]) % (math.pi / 2), 9))
    best = None
    for a in sorted(angles):
        q = [rot(p, a) for p in h]
        w = max(x for x, _ in q) - min(x for x, _ in q)
        ht = max(y for _, y in q) - min(y for _, y in q)
        key = round(w * ht, 3)
        if best is None or key < best[0] - 1e-6 or (abs(key - best[0]) < 1e-6 and abs(a) < abs(best[1])):
            best = (key, a, w, ht)
    a = best[1]
    if best[3] > best[2] + 1e-6:
        a += math.pi / 2
    return a


def _tr_seg(s, f):
    if s[0] == 'C':
        return ['C', f(s[1]), s[2]]
    if s[0] == 'P':
        return ['P', [f(p) for p in s[1]]]
    return [s[0]] + [f(p) for p in s[1:]]


def normalize(loops, extra=()):
    a = best_angle(sample(loops))
    groups = [list(loops)] + [list(g) for g in extra]
    groups = [[[_tr_seg(s, lambda p: rot(p, a)) for s in segs] for segs in g] for g in groups]
    pts = sample(groups[0])
    x0, y0 = min(x for x, _ in pts), min(y for _, y in pts)
    L, W = max(x for x, _ in pts) - x0, max(y for _, y in pts) - y0

    def sh(p):
        return (round(p[0] - x0, 4), round(p[1] - y0, 4))
    groups = [[[_tr_seg(s, sh) for s in segs] for segs in g] for g in groups]
    return groups[0], groups[1:], L, W


def entities(loops):
    circles, polys, curved = [], [], False
    for segs in loops:
        if len(segs) == 1 and segs[0][0] == 'C':
            circles.append((tuple(segs[0][1]), segs[0][2]))
            continue
        arcs = [circle3(s[1], s[2], s[3]) for s in segs if s[0] == 'A']
        if arcs and len(arcs) == len(segs) and all(arcs):
            (cx, cy), r = arcs[0]
            if all(math.hypot(c[0] - cx, c[1] - cy) < 0.01 and abs(rr - r) < 0.01 for c, rr in arcs):
                circles.append(((cx, cy), r))
                continue
        v = []
        for s in segs:
            if s[0] == 'L':
                v.append((s[1][0], s[1][1], 0.0))
            elif s[0] == 'A':
                v.append((s[1][0], s[1][1], bulge(s[1], s[2], s[3])))
            elif s[0] == 'P':
                curved = True
                v += [(p[0], p[1], 0.0) for p in s[1][:-1]]
            elif s[0] == 'C':
                circles.append((tuple(s[1]), s[2]))
        if len(v) >= 2:
            polys.append(v)
    return circles, polys, curved


def area(q):
    return abs(sum(q[i][0] * q[i - 1][1] - q[i - 1][0] * q[i][1] for i in range(len(q)))) / 2


def inside(pt, poly):
    x, y = pt
    n = len(poly)
    c = False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-300) + xi:
            c = not c
        j = i
    return c


def seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 < 1e-18 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def poly_dist(p, pts):
    return min(seg_dist(p, pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def seg_x(a, b, c, d):
    def o(p, q, r):
        v = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        return (v > 1e-12) - (v < -1e-12)
    return o(a, b, c) != o(a, b, d) and o(c, d, a) != o(c, d, b)


def rings_of(circles, polys):
    rs = [poly_pts(v) for v in polys] + [ring(c, r) for c, r in circles]
    if not rs:
        return None, []
    outer = max(rs, key=area)
    return outer, [r for r in rs if r is not outer]


def cut_length(circles, polys):
    n = sum(2 * math.pi * r for _, r in circles)
    for v in polys:
        q = poly_pts(v)
        n += sum(math.hypot(q[i + 1][0] - q[i][0], q[i + 1][1] - q[i][1]) for i in range(len(q) - 1))
    return n
