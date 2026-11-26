"""preview.pdf: every part with overall size and dimensions to bend lines."""
import math

from . import geom2d as G
from . import i18n
from .pdf import PDF

A3 = (420.0, 297.0)
TABLOID = (431.8, 279.4)
FONT = 3.2
HEAD = 12.0
MARGIN = 8.0
CELL_MIN = (70.0, 55.0)
DIM = 2.6 * FONT
ARR = 1.6
BLACK, RED, BLUE = (0, 0, 0), (0.9, 0, 0), (0.12, 0.31, 0.6)
GREEN = (0, 0.6, 0)


def g(v):
    if i18n.UNIT == 'in':
        return i18n.num(v, True)
    s = f'{round(v, 1):g}'
    return s.replace('.', ',') if i18n.LANG == 'ru' else s


def bend_chains(p, tol=0.3):
    xs, ys = [], []
    for a, b in p.bend_up + p.bend_down:
        if abs(a[0] - b[0]) < tol:
            xs.append((a[0] + b[0]) / 2)
        elif abs(a[1] - b[1]) < tol:
            ys.append((a[1] + b[1]) / 2)
    return sorted(set(round(x, 2) for x in xs)), sorted(set(round(y, 2) for y in ys))


def _short(d, cuts, total, k):
    if not cuts:
        return False
    ch = [0.0] + cuts + [total]
    return any(d.text_w(g(b - a), FONT) + 1.0 >= (b - a) * k for a, b in zip(ch, ch[1:]))


def _arrow(d, tip, ux, uy, col):
    px, py = -uy, ux
    b = (tip[0] - ux * ARR, tip[1] - uy * ARR)
    d.lines([tip, (b[0] + px * ARR * 0.3, b[1] + py * ARR * 0.3), (b[0] - px * ARR * 0.3, b[1] - py * ARR * 0.3)],
            col, 0.1, fill=col)


NO_AFTER = (-1e9, -1e9)


def _row(x0, after):
    if x0 >= after[0] + 0.8:
        return 0
    if x0 >= after[1] + 0.8:
        return 1
    return 0 if after[0] <= after[1] else 1


def dim_h(d, xa, xb, y, ye, txt, after=NO_AFTER):
    s = 1 if y > ye else -1
    for x in (xa, xb):
        d.lines([(x, ye + s * 0.5), (x, y + s * 1.0)], BLUE, 0.15)
    d.lines([(xa, y), (xb, y)], BLUE, 0.15)
    if xb - xa > 2.2 * ARR:
        _arrow(d, (xa, y), -1, 0, BLUE)
        _arrow(d, (xb, y), 1, 0, BLUE)
    w = d.text_w(txt, FONT)
    if w + 1.0 < xb - xa:
        x, al = (xa + xb) / 2, 'middle'
        x0 = x - w / 2
    else:
        d.lines([(xb, y), (xb + 1.2, y)], BLUE, 0.15)
        x, al = xb + 1.5, 'start'
        x0 = x
    r = _row(x0, after)
    x, x0 = x + max(0.0, after[r] + 0.8 - x0), max(x0, after[r] + 0.8)
    d.text(x, y + 0.8 + (FONT * 1.15 if r else 0.0), txt, FONT, BLUE, al)
    return (after[0], x0 + w) if r else (x0 + w, after[1])


def dim_v(d, ya, yb, x, xe, txt, after=NO_AFTER):
    s = 1 if x > xe else -1
    for y in (ya, yb):
        d.lines([(xe + s * 0.5, y), (x + s * 1.0, y)], BLUE, 0.15)
    d.lines([(x, ya), (x, yb)], BLUE, 0.15)
    if yb - ya > 2.2 * ARR:
        _arrow(d, (x, ya), 0, -1, BLUE)
        _arrow(d, (x, yb), 0, 1, BLUE)
    w = d.text_w(txt, FONT)
    if w + 1.0 < yb - ya:
        y, al = (ya + yb) / 2, 'middle'
        y0 = y - w / 2
    else:
        d.lines([(x, yb), (x, yb + 1.2)], BLUE, 0.15)
        y, al = yb + 1.5, 'start'
        y0 = y
    r = _row(y0, after) if s > 0 else 0
    if s > 0:
        y, y0 = y + max(0.0, after[r] + 0.8 - y0), max(y0, after[r] + 0.8)
    d.text(x + 0.8 + FONT if r else x - 0.8, y, txt, FONT, BLUE, al, 90)
    return (after[0], y0 + w) if r else (y0 + w, after[1])


def _wrap(d, text, width):
    out, cur = [], ''
    for w in text.split(' '):
        t = (cur + ' ' + w).strip()
        if cur and d.text_w(t, FONT) > width:
            out.append(cur)
            cur = w
        else:
            cur = t
    return out + ([cur] if cur else [])


def _draw_part(d, p, tf, k):
    for v in p.polys:
        d.lines([tf(q) for q in G.poly_pts(v)], GREEN, 0.25)
    for c, r in p.circles:
        d.circle(tf(c), r * k, GREEN, 0.25)
    for v in p.ep:
        d.lines([tf(q) for q in G.poly_pts(v)], RED, 0.18)
    for c, r in p.ec:
        d.circle(tf(c), r * k, RED, 0.18)
    for s in p.text:
        d.lines([tf(q) for q in s], RED, 0.18)
    for a, b in p.bend_up + p.bend_down:
        d.lines([tf(a), tf(b)], RED, 0.18)


def build(parts, labels, title, path):
    W, H = TABLOID if i18n.UNIT == 'in' else A3
    aw, ah = W - 2 * MARGIN, H - HEAD - MARGIN
    n = len(parts)
    best = None
    for cols in range(1, 8):
        for rows in range(1, 8):
            cw, ch = aw / cols, ah / rows
            if (cw < CELL_MIN[0] or ch < CELL_MIN[1]) and (cols, rows) != (1, 1):
                continue
            per = cols * rows
            if per > n and per - cols >= n:
                continue
            fit = sum(min((cw - 2 * DIM) / max(p.L, 1e-6), (ch - 2 * DIM - 3 * FONT) / max(p.W, 1e-6)) ** 2 * p.L * p.W
                      for p in parts[:per])
            key = (math.ceil(n / per), -fit)
            if best is None or key < best[0]:
                best = (key, cols, rows)
    _, cols, rows = best
    per = cols * rows
    cw, ch = aw / cols, ah / rows
    chunks = [list(range(i, min(i + per, n))) for i in range(0, n, per)]
    d = PDF(W, H)
    lh = FONT * 1.25
    for pi, idx in enumerate(chunks, 1):
        d.page()
        d.text(MARGIN, H - HEAD + 4, title + (f'   {pi}/{len(chunks)}' if len(chunks) > 1 else ''), FONT * 1.3)
        for k_, i in enumerate(idx):
            p = parts[i]
            r, c = k_ // cols, k_ % cols
            x0, ytop = MARGIN + c * cw, H - HEAD - r * ch
            y0 = ytop - ch
            d.rect(x0, y0 + 2, cw - 2, ch - 2)
            lines = [w for t in labels[i] for w in _wrap(d, t, cw - 6)]
            lab_h = len(lines) * lh + 1
            bx, by = bend_chains(p)
            top0, right0 = (DIM if bx else 1.5), (DIM if by else 1.5)
            top, right = top0, right0
            for _ in range(2):
                sw = cw - 2 - 4 - DIM - right
                sh = ch - 2 - 4 - DIM - top - lab_h
                k = max(min(sw / max(p.L, 1e-6), sh / max(p.W, 1e-6)), 1e-6)
                top = top0 + (FONT * 1.2 if _short(d, bx, p.L, k) else 0)
                right = right0 + (FONT * 1.2 if _short(d, by, p.W, k) else 0)
            px = x0 + 2 + DIM + (sw - p.L * k) / 2
            py = y0 + 2 + 2 + lab_h + DIM + (sh - p.W * k) / 2
            tf = lambda q, px=px, py=py, k=k: (px + q[0] * k, py + q[1] * k)
            _draw_part(d, p, tf, k)
            X1, Y1 = px + p.L * k, py + p.W * k
            dim_h(d, px, X1, py - DIM * 0.7, py, g(p.L))
            dim_v(d, py, Y1, px - DIM * 0.7, px, g(p.W))
            if bx:
                ch_ = [0.0] + bx + [p.L]
                e = NO_AFTER
                for a, b in zip(ch_, ch_[1:]):
                    e = dim_h(d, px + a * k, px + b * k, Y1 + DIM * 0.6, Y1, g(b - a), e)
            if by:
                ch_ = [0.0] + by + [p.W]
                e = NO_AFTER
                for a, b in zip(ch_, ch_[1:]):
                    e = dim_v(d, py + a * k, py + b * k, X1 + DIM * 0.75, X1, g(b - a), e)
            for j, t in enumerate(lines):
                d.text(x0 + 3, y0 + 4 + (len(lines) - 1 - j) * lh, t, FONT)
    d.save(path)
    return path
