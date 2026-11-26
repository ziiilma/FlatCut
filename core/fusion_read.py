"""Reads flat plates and sheet metal parts from a Fusion design."""
import re

import adsk.core
import adsk.fusion

from .i18n import T

T_MAX = 25.0
METAL_DENS = 2000.0
NONMETAL = re.compile(r'поликарб|polycarb|фанер|plywood|дерев|брус|доск|wood|пвх|pvc|акрил|оргстекл|acryl|резин|rubber'
                      r'|hpl|дсп|мдф|mdf|osb|осп|пластик|plastic|foam|cardboard|картон|leather|кож', re.I)
AUTO_PN = re.compile(r'^\d{4}-\d{2}-\d{2}[-T ]\d{2}|^(component|компонент)\s*\d*$', re.I)
HW = re.compile(r'^(bolt|screw|nut|washer|rivet|pin|stud|insert|болт|винт|гайк|шайб|заклёп|заклеп|шуруп|саморез|'
                r'шпильк|анкер|глухар|iso\s?\d|din\s?\d|гост\s?\d)', re.I)


def _frame(face):
    o = face.pointOnFace
    ok, n = face.evaluator.getNormalAtPoint(o)
    ref = adsk.core.Vector3D.create(1, 0, 0) if abs(n.x) < 0.9 else adsk.core.Vector3D.create(0, 1, 0)
    u = n.crossProduct(ref)
    u.normalize()
    v = n.crossProduct(u)
    v.normalize()
    return o, u, v, n


FIT_TOL = 0.05


def _fit(pts, depth=0):
    s = _fit1(pts)
    if s[0] != 'P' or depth >= 4 or len(pts) < 5:
        return [s]
    h = len(pts) // 2
    return _fit(pts[:h + 1], depth + 1) + _fit(pts[h:], depth + 1)


def _fit1(pts):
    a, b = pts[0], pts[-1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    ln = (dx * dx + dy * dy) ** 0.5
    if ln > 1e-6 and max(abs((p[0] - a[0]) * dy - (p[1] - a[1]) * dx) / ln for p in pts) < FIT_TOL:
        return ['L', a, b]
    m = pts[len(pts) // 2]
    d = 2 * (a[0] * (m[1] - b[1]) + m[0] * (b[1] - a[1]) + b[0] * (a[1] - m[1]))
    if abs(d) > 1e-9:
        ux = ((a[0] ** 2 + a[1] ** 2) * (m[1] - b[1]) + (m[0] ** 2 + m[1] ** 2) * (b[1] - a[1])
              + (b[0] ** 2 + b[1] ** 2) * (a[1] - m[1])) / d
        uy = ((a[0] ** 2 + a[1] ** 2) * (b[0] - m[0]) + (m[0] ** 2 + m[1] ** 2) * (a[0] - b[0])
              + (b[0] ** 2 + b[1] ** 2) * (m[0] - a[0])) / d
        r = ((a[0] - ux) ** 2 + (a[1] - uy) ** 2) ** 0.5
        if max(abs(((p[0] - ux) ** 2 + (p[1] - uy) ** 2) ** 0.5 - r) for p in pts) < FIT_TOL:
            return ['A', a, m, b]
    return ['P', pts]


def _loop2d(lp, p2):
    segs = []
    for ce in lp.coEdges:
        e = ce.edge
        g = e.geometry
        ev = e.evaluator
        ok, t0, t1 = ev.getParameterExtents()

        def at(t):
            try:
                ok, p = ev.getPointAtParameter(t)
            except RuntimeError:
                eps = (t1 - t0) * 1e-6
                ok, p = ev.getPointAtParameter(min(max(t, t0 + eps), t1 - eps))
            return p2(p)
        if isinstance(g, adsk.core.Circle3D):
            segs.append(['C', p2(g.center), round(g.radius * 10, 4)])
            continue
        if isinstance(g, adsk.core.Line3D):
            es = [['L', at(t0), at(t1)]]
        elif isinstance(g, adsk.core.Arc3D):
            es = [['A', at(t0), at((t0 + t1) / 2), at(t1)]]
        else:
            k = 64
            es = _fit([at(t0 + (t1 - t0) * i / k) for i in range(k + 1)])
        if ce.isOpposedToEdge:
            es = [[s[0]] + (s[1:][::-1] if s[0] != 'P' else [s[1][::-1]]) for s in es[::-1]]
        segs += es
    return segs


def _p2(face, n=None):
    o, u, v, n0 = _frame(face)
    if n is not None and n.dotProduct(n0) < 0:
        u.scaleBy(-1)

    def p2(p):
        d = o.vectorTo(p)
        return [round(d.dotProduct(u) * 10, 4), round(d.dotProduct(v) * 10, 4)]
    p2.normal = n if n is not None and n.dotProduct(n0) < 0 else n0
    return p2


def _loops(face):
    p2 = _p2(face)
    return [_loop2d(lp, p2) for lp in sorted(face.loops, key=lambda l: not l.isOuter)]


ENGR_TOL = 0.1
ENGR_DEPTH = 1.0


def _box(lp, p2):
    pts = []
    for e in lp.edges:
        ev = e.evaluator
        ok, t0, t1 = ev.getParameterExtents()
        for i in range(9):
            t = t0 + (t1 - t0) * (1e-6 + i / 8 * (1 - 2e-6))
            ok, p = ev.getPointAtParameter(t)
            pts.append(p2(p))
    return (min(x for x, _ in pts), min(y for _, y in pts), max(x for x, _ in pts), max(y for _, y in pts))


def _same(a, b):
    return all(abs(x - y) < ENGR_TOL for x, y in zip(a, b))


def _inside(a, b):
    return a[0] > b[0] - ENGR_TOL and a[1] > b[1] - ENGR_TOL and a[2] < b[2] + ENGR_TOL and a[3] < b[3] + ENGR_TOL


def _cut_engr(body, big, t, center=None):
    n0 = _frame(big)[3]
    o0 = big.pointOnFace
    p0 = _p2(big)
    caps = {1: [], -1: []}
    floors = {1: [], -1: []}
    for f in body.faces:
        if not isinstance(f.geometry, adsk.core.Plane):
            continue
        dot = _frame(f)[3].dotProduct(n0)
        if abs(abs(dot) - 1) > 1e-6:
            continue
        h = o0.vectorTo(f.pointOnFace).dotProduct(n0) * 10
        side = 1 if dot > 0 else -1
        d = -h if side == 1 else h + t
        if abs(d) < 1e-3:
            caps[side].append(f)
        elif 1e-3 < d <= min(ENGR_DEPTH, t / 2):
            floors[side].append(_box(next(l for l in f.loops if l.isOuter), p0))
    if not caps[-1] or not (floors[1] or floors[-1]):
        if not caps[-1] or center is None or o0.vectorTo(center).dotProduct(n0) >= 0:
            p2 = _p2(big)
            return [_loop2d(l, p2) for l in sorted(big.loops, key=lambda l: not l.isOuter)], [], big, p2
        ref = max(caps[-1], key=lambda f: f.area)
        out = n0.copy()
        out.scaleBy(-1)
        p2 = _p2(ref, out)
        return [_loop2d(l, p2) for l in sorted(ref.loops, key=lambda l: not l.isOuter)], [], ref, p2
    cap = {s: max(fs, key=lambda f: f.area) for s, fs in caps.items()}
    inner = {s: [l for l in cap[s].loops if not l.isOuter] for s in cap}
    boxes = {s: [_box(l, p0) for l in inner[s]] for s in cap}
    engr = {}
    for s in cap:
        lone = [(l, b) for l, b in zip(inner[s], boxes[s])
                if not any(_same(b, ob) for ob in boxes[-s]) and any(_inside(fb, b) for fb in floors[s])]
        isl = [l for f in caps[s] if f != cap[s] for l in f.loops if l.isOuter]
        isl = [l for l in isl if any(_inside(_box(l, p0), b) for _, b in lone)]
        engr[s] = [l for l, _ in lone] + isl
    side = 1 if engr[1] or not engr[-1] else -1
    ref = cap[side]
    out = n0.copy()
    out.scaleBy(side)
    p2 = _p2(ref, out)
    cut = [_loop2d(l, p2) for l in sorted(ref.loops, key=lambda l: not l.isOuter) if l not in engr[side]]
    return cut, [_loop2d(l, p2) for l in engr[side]], ref, p2


def _bends(fp, ref, p2):
    n = _frame(ref)[3]
    o = ref.pointOnFace
    view_top = True
    try:
        top = fp.topFace
        view_top = _frame(top)[3].dotProduct(p2.normal) > 0
    except Exception:
        pass
    out = []
    try:
        edges = list(fp.bendLinesBody.edges)
    except Exception:
        return out
    for e in edges:
        g = e.geometry
        if not isinstance(g, adsk.core.Line3D):
            continue
        a, b = g.startPoint, g.endPoint
        if abs(o.vectorTo(a).dotProduct(n)) > 1e-3 or abs(o.vectorTo(b).dotProduct(n)) > 1e-3:
            continue
        up = True
        try:
            bi = fp.getBendInfo(e)
            if bi and bi[0]:
                up = bool(bi[1])
        except Exception:
            pass
        out.append([p2(a), p2(b), up if view_top else not up])
    return out


def _flat(body):
    faces = [f for f in body.faces if isinstance(f.geometry, adsk.core.Plane)]
    if not faces:
        return None
    big = max(faces, key=lambda f: f.area)
    o, u, v, n = _frame(big)
    try:
        obb = adsk.core.Application.get().measureManager.getOrientedBoundingBox(body, u, v)
        t = obb.height * 10
    except Exception:
        return None
    if not 0.2 <= t <= T_MAX:
        return None
    fill = body.volume / (big.area * t / 10)
    if not 0.9 <= fill <= 1.02:
        return None
    if (obb.length * 10) < 3 * t and (obb.width * 10) < 3 * t:
        return None
    return big, t


def _mat(body):
    name = body.material.name if body.material else ''
    try:
        dens = body.material.materialProperties.itemById('structural_Density').value
    except Exception:
        dens = 7850.0
    return name, dens


def _fp_ok(fp):
    try:
        return bool(fp and fp.bodies.count)
    except Exception:
        return False


def _make_flat(comp, body):
    faces = sorted(body.faces, key=lambda f: -f.area)
    err = 'no faces'
    for f in faces[:3]:
        try:
            fp = comp.createFlatPattern(f)
            if _fp_ok(fp):
                return fp, ''
        except Exception as e:
            err = str(e).strip().splitlines()[-1][:120] if str(e).strip() else 'API error'
    return None, err


def _units(design, hidden):
    root = design.rootComponent
    out, seen = [], {}
    if any(b.isSolid and (hidden or b.isVisible) for b in root.bRepBodies):
        seen[root.entityToken] = [root, None, 1]
        out.append(seen[root.entityToken])
    for o in root.allOccurrences:
        if not hidden and not o.isVisible:
            continue
        c = o.component
        if not c.bRepBodies.count:
            continue
        k = c.entityToken
        if k not in seen:
            seen[k] = [c, o, 0]
            out.append(seen[k])
        seen[k][2] += 1
    return out


def _root_center(design):
    bb = design.rootComponent.boundingBox
    return adsk.core.Point3D.create((bb.minPoint.x + bb.maxPoint.x) / 2, (bb.minPoint.y + bb.maxPoint.y) / 2,
                                    (bb.minPoint.z + bb.maxPoint.z) / 2)


def _center(c0, occ):
    c = c0.copy()
    if occ is not None:
        m = occ.transform2.copy()
        m.invert()
        c.transformBy(m)
    return c


def collect(design, hidden=False):
    rows = []
    for c, occ, qty in _units(design, hidden):
        solids = [b for b in c.bRepBodies if b.isSolid and (hidden or b.isVisible)]
        if not solids or HW.match(c.name):
            continue
        fp, broken = None, False
        try:
            fp = c.flatPattern
        except Exception:
            broken = True
        for b in solids:
            is_root = c == design.rootComponent
            name = b.name if is_root else (c.name if len(solids) == 1 else f'{c.name}_{b.name}')
            if HW.match(b.name):
                continue
            mat, dens = _mat(b)
            nonmetal = bool(NONMETAL.search(mat or ''))
            row = dict(comp=c, occ=occ, body=b, name=name, pn='', mat=mat, metal=dens >= METAL_DENS and not nonmetal,
                       qty=qty, kind='flat', note=T('nonmetal') if nonmetal else '', t=0.0)
            row['note0'] = row['note']
            sheet = getattr(b, 'isSheetMetal', False)
            if sheet and not _flat(b):
                one = len(solids) == 1
                fl = _flat(fp.bodies.item(0)) if one and _fp_ok(fp) else None
                if fl:
                    row.update(kind='unfold', t=fl[1], note=', '.join(filter(None, (T('unfold'), row['note']))))
                elif one and _fp_ok(fp):
                    row.update(kind='skip', note=T('fp_notflat'))
                elif one and not broken:
                    mk = 'fix' if fp is not None else 'new'
                    row.update(kind='unfold', make=mk, t=_sm_t(c, b),
                               note=', '.join(filter(None, (T('fp_' + mk), row['note']))))
                else:
                    row.update(kind='skip', note=T('fp_broken') if broken else T('skip_fp'))
                rows.append(row)
                continue
            fl = _flat(b)
            if fl:
                row['t'] = fl[1]
                rows.append(row)
            elif _bent_sheet(b):
                row.update(kind='skip', note=T('not_sm'))
                rows.append(row)
    return rows


def _sm_t(comp, body):
    try:
        th = comp.activeSheetMetalRule.thickness
        v = th.value if hasattr(th, 'value') else float(th)
        if v > 0:
            return round(v * 10, 2)
    except Exception:
        pass
    try:
        return round(2 * body.volume / body.area * 10, 1)
    except Exception:
        return 0.0


def prepare(rows):
    ok, bad = [], []
    for r in rows:
        mk = r.get('make')
        if not mk:
            ok.append(r)
            continue
        c, b = r['comp'], r['body']
        if mk == 'fix':
            try:
                c.flatPattern.deleteMe()
            except Exception:
                pass
        fp, err = _make_flat(c, b)
        fl = _flat(fp.bodies.item(0)) if fp else None
        if not fl:
            bad.append(f"{r['name']}: " + (T('fp_notflat') if fp else T('skip_fp') + (f': {err}' if err else '')))
            continue
        r.update(t=fl[1], make='', note=', '.join(filter(None, (T('made_fp'), r.get('note0', '')))))
        ok.append(r)
    return ok, bad


def _bent_sheet(body):
    try:
        t = 2 * body.volume / body.area
        if not 0.02 <= t <= T_MAX / 10:
            return False
        cyl = []
        for f in body.faces:
            g = f.geometry
            if isinstance(g, adsk.core.Plane) and f.loops.count > 1:
                outer = next(l for l in f.loops if l.isOuter)
                if f.area < 1.5 * t * sum(e.length for e in outer.edges):
                    return False
            elif isinstance(g, adsk.core.Cylinder):
                cyl.append(g)
            elif isinstance(g, adsk.core.Torus):
                return False
        for a in cyl:
            if not any(b is not a and abs(abs(a.radius - b.radius) - t) < 0.2 * t and a.axis.isParallelTo(b.axis)
                       and a.origin.vectorTo(b.origin).crossProduct(a.axis).length < 1e-3 * a.axis.length + 1e-4
                       for b in cyl):
                return False
        big = max(body.faces, key=lambda f: f.area)
        p = big.pointOnFace
        ok, n = big.evaluator.getNormalAtPoint(p)
        In, Out = adsk.fusion.PointContainment.PointInsidePointContainment, \
            adsk.fusion.PointContainment.PointOutsidePointContainment
        for s in (-1, 1):
            q1, q2 = p.copy(), p.copy()
            q1.translateBy(adsk.core.Vector3D.create(n.x * s * t / 2, n.y * s * t / 2, n.z * s * t / 2))
            q2.translateBy(adsk.core.Vector3D.create(n.x * s * t * 1.5, n.y * s * t * 1.5, n.z * s * t * 1.5))
            if body.pointContainment(q1) == In:
                return body.pointContainment(q2) == Out
        return False
    except Exception:
        return False


def fill_pn(rows, progress=None):
    comps = []
    for r in rows:
        if r['comp'] not in comps:
            comps.append(r['comp'])
    got, failed = {}, 0
    for i, c in enumerate(comps):
        if progress and progress(i, len(comps)) is False:
            break
        pn = _pn(c)
        failed += pn is None
        got[c.entityToken] = pn or ''
    for r in rows:
        r['pn'] = got.get(r['comp'].entityToken, '')
    return failed


def _pn(c):
    try:
        pn = c.partNumber or ''
    except Exception:
        return None
    return pn if pn != c.name and not AUTO_PN.match(pn) else ''


def read(rows, zakaz=1, engrave_pn=True):
    items = []
    c0 = None
    for r in rows:
        c = r['comp']
        bends = []
        if r['kind'] == 'unfold':
            fp = c.flatPattern
            body = fp.bodies.item(0)
            fl = _flat(body)
            if not fl:
                continue
            face, t = fl
            cut, engr, ref, p2 = _cut_engr(body, face, t)
            src = r.get('body')
            rolled = src is not None and not isinstance(max(src.faces, key=lambda f: f.area).geometry, adsk.core.Plane)
            bends = [] if rolled else _bends(fp, ref, p2)
        else:
            body = r['body']
            face, t = _flat(body)
            if c0 is None:
                c0 = _root_center(c.parentDesign)
            cut, engr, _, _ = _cut_engr(body, face, t, _center(c0, r.get('occ')))
        text = r['pn'] if engrave_pn and r['metal'] else ''
        items.append(dict(name=r['name'], pn=r['pn'], mat=r['mat'], t=round(t, 2), qty=r['qty'] * zakaz,
                          note=r['note'], loops=cut, engr=engr, bends=bends, text=text))
    return items
