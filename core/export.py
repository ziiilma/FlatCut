"""Export of parts to DXF/SVG files and preview.pdf."""
import os
import re
import time

from . import dxf as D
from . import part as P
from . import preview as PV
from . import svg as S
from . import i18n
from .i18n import T, W

TIMES = {}
BAD = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


class Busy(Exception):
    pass


def _rm(path):
    try:
        os.remove(path)
    except OSError:
        raise Busy(path)


def g(v):
    return f'{round(v, 2):g}'


FIELDS = ('qty', 'name', 't', 'mat', 'pn')


def field(k, qty, name, t, mat, pn):
    return {'qty': f'{qty}{T("qty_suf")}', 'name': name, 't': i18n.thk(t), 'mat': mat, 'pn': pn}.get(k, '')


def fname(fields, p):
    s = '_'.join(x for x in (field(k, p.qty, p.name, p.t, p.mat, p.pn) for k in fields) if x)
    s = BAD.sub('_', s).strip(' ._') or BAD.sub('_', p.name) or 'part'
    return re.sub(r'_+', '_', s)[:150]


def _clean(folder, sub, ext):
    d = os.path.join(folder, sub)
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.lower().endswith(ext):
                _rm(os.path.join(d, f))
    os.makedirs(d, exist_ok=True)
    return d


SEP = '._- /'


def short_codes(codes):
    cs = [c for c in dict.fromkeys(codes) if c]
    if not cs:
        return {}
    if len(cs) == 1:
        p = cs[0]
        cut = [i for i, ch in enumerate(p) if ch in SEP]
        k = cut[-2] + 1 if len(cut) >= 2 else 0
        return {p: p[k:]}
    n = 0
    while all(len(c) > n for c in cs) and len({c[n] for c in cs}) == 1:
        n += 1
    while n > 0 and cs[0][n - 1] not in SEP:
        n -= 1
    return {c: c[n:] or c for c in cs}


def run(items, folder, opts, skipped=()):
    os.makedirs(folder, exist_ok=True)
    for f in os.listdir(folder):
        if f.startswith('preview') and f.endswith(('.svg', '.pdf')):
            _rm(os.path.join(folder, f))
    dxf_dir = _clean(folder, 'DXF', '.dxf')
    svg_dir = _clean(folder, 'SVG', '.svg') if opts.get('svg') else None
    parts, names, warn = [], set(), []
    t0 = time.perf_counter()
    short = short_codes([it.get('text') for it in items])
    for it in items:
        if it.get('text'):
            it = dict(it, text=short.get(it['text'], it['text']))
        if not opts.get('engrave', True):
            it = dict(it, text='')
        p = P.Part(it, opts.get('bends', True), opts.get('text_h', 10.0))
        base = fname(opts.get('fields') or ('t', 'qty', 'name', 'pn'), p)
        if p.engraved:
            base = T('grav_pref') + base
        b, i = base, 2
        while b.lower() in names:
            b, i = f'{base}_{i}', i + 1
        names.add(b.lower())
        p.file = b
        doc = D.Doc(i18n.UNIT)
        p.draw(doc)
        doc.save(os.path.join(dxf_dir, b + '.dxf'))
        if svg_dir:
            S.part_svg(p, os.path.join(svg_dir, b + '.svg'), i18n.UNIT)
        parts.append(p)
        warn += [f'{p.name}: {W(w)}' for w in p.warn]
    TIMES['files'] = time.perf_counter() - t0
    rep = [T('done', n=len(parts), f=dxf_dir)]
    if svg_dir:
        rep.append(T('done_svg', n=len(parts)))
    labels = [[p.file, f'{i18n.thk(p.t)} · {p.mat} · {p.qty} {T("pcs")}' + (f' · {p.note}' if p.note else '')]
              for p in parts]
    t0 = time.perf_counter()
    if parts:
        PV.build(parts, labels, opts.get('title', ''), os.path.join(folder, 'preview.pdf'))
    TIMES['preview'] = time.perf_counter() - t0
    rep.append('')
    rep += ([T('check')] + ['  ' + w for w in warn]) if warn else [T('check_ok')]
    if skipped:
        rep += ['', T('skipped')] + ['  ' + s for s in skipped]
    old = os.path.join(folder, 'report.txt')
    if os.path.exists(old):
        _rm(old)
    return rep

