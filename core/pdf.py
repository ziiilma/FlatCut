"""Minimal PDF writer with an embedded TrueType font."""
import os
import struct
import zlib

K = 72 / 25.4

FONT_PATHS = [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           'resources', 'fonts', 'LiberationSans-Regular.ttf')]


class TTF:
    def __init__(self, path):
        self.data = d = open(path, 'rb').read()
        n = struct.unpack('>H', d[4:6])[0]
        tab = {}
        for i in range(n):
            tag, _, off, ln = struct.unpack('>4sIII', d[12 + 16 * i:28 + 16 * i])
            tab[tag.decode('latin-1')] = (off, ln)
        self.upem = struct.unpack('>H', d[tab['head'][0] + 18:tab['head'][0] + 20])[0]
        hh = tab['hhea'][0]
        self.ascent, self.descent = struct.unpack('>hh', d[hh + 4:hh + 8])
        nh = struct.unpack('>H', d[hh + 34:hh + 36])[0]
        hm = tab['hmtx'][0]
        self.adv = [struct.unpack('>H', d[hm + 4 * i:hm + 4 * i + 2])[0] for i in range(nh)]
        self.cmap = self._cmap(d, tab['cmap'][0])
        self.name = os.path.splitext(os.path.basename(path))[0].replace(' ', '')

    @staticmethod
    def _cmap(d, base):
        n = struct.unpack('>H', d[base + 2:base + 4])[0]
        sub = None
        for i in range(n):
            pid, eid, off = struct.unpack('>HHI', d[base + 4 + 8 * i:base + 12 + 8 * i])
            if pid == 3 and eid in (1, 0) or pid == 0 and sub is None:
                if struct.unpack('>H', d[base + off:base + off + 2])[0] == 4:
                    sub = base + off
        m = {}
        if sub is None:
            return m
        seg = struct.unpack('>H', d[sub + 6:sub + 8])[0] // 2
        ends = struct.unpack(f'>{seg}H', d[sub + 14:sub + 14 + 2 * seg])
        p = sub + 16 + 2 * seg
        starts = struct.unpack(f'>{seg}H', d[p:p + 2 * seg])
        deltas = struct.unpack(f'>{seg}h', d[p + 2 * seg:p + 4 * seg])
        ro_at = p + 4 * seg
        ros = struct.unpack(f'>{seg}H', d[ro_at:ro_at + 2 * seg])
        for i in range(seg):
            for c in range(starts[i], ends[i] + 1):
                if c == 0xFFFF:
                    continue
                if ros[i] == 0:
                    g = (c + deltas[i]) & 0xFFFF
                else:
                    a = ro_at + 2 * i + ros[i] + 2 * (c - starts[i])
                    g = struct.unpack('>H', d[a:a + 2])[0]
                    if g:
                        g = (g + deltas[i]) & 0xFFFF
                if g:
                    m[c] = g
        return m

    def gid(self, ch):
        return self.cmap.get(ord(ch), 0)

    def w(self, g):
        return self.adv[g] if g < len(self.adv) else self.adv[-1]

    def width(self, s, size):
        return sum(self.w(self.gid(c)) for c in s) / self.upem * size


def _font():
    for p in FONT_PATHS:
        if os.path.exists(p):
            try:
                f = TTF(p)
                if f.gid('A') and f.gid('Ж'):
                    return f
            except Exception:
                pass
    return None


def _n(v):
    s = f'{v:.3f}'.rstrip('0').rstrip('.')
    return '0' if s in ('', '-0') else s


class PDF:
    def __init__(self, w_mm, h_mm):
        self.w, self.h = w_mm, h_mm
        self.pages = []
        self.font = _font()
        self.used = set()

    def page(self):
        self.pages.append([])
        self.c = self.pages[-1]

    def _st(self, color, lw, dash):
        r, g, b = color
        self.c.append(f'{_n(r)} {_n(g)} {_n(b)} RG {_n(lw * K)} w ' +
                      (f'[{" ".join(_n(x * K) for x in dash)}] 0 d' if dash else '[] 0 d'))

    def lines(self, pts, color=(0, 0, 0), lw=0.25, closed=False, dash=None, fill=None):
        if len(pts) < 2:
            return
        self._st(color, lw, dash)
        ops = [f'{_n(pts[0][0] * K)} {_n(pts[0][1] * K)} m'] + [f'{_n(x * K)} {_n(y * K)} l' for x, y in pts[1:]]
        if fill:
            r, g, b = fill
            self.c.append(f'{_n(r)} {_n(g)} {_n(b)} rg')
            self.c.append(' '.join(ops) + ' h f')
        else:
            self.c.append(' '.join(ops) + (' h S' if closed else ' S'))

    def rect(self, x, y, w, h, color=(0.8, 0.8, 0.8), lw=0.3):
        self.lines([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], color, lw, True)

    def circle(self, c, r, color=(0, 0, 0), lw=0.25):
        k = 0.5523 * r
        x, y = c
        self._st(color, lw, None)
        p = lambda a, b: f'{_n(a * K)} {_n(b * K)}'
        self.c.append(f'{p(x + r, y)} m {p(x + r, y + k)} {p(x + k, y + r)} {p(x, y + r)} c '
                      f'{p(x - k, y + r)} {p(x - r, y + k)} {p(x - r, y)} c '
                      f'{p(x - r, y - k)} {p(x - k, y - r)} {p(x, y - r)} c '
                      f'{p(x + k, y - r)} {p(x + r, y - k)} {p(x + r, y)} c S')

    def text_w(self, s, size):
        if self.font:
            return self.font.width(s, size)
        from . import font as F
        return F.strokes(s, size * 0.7)[1]

    def text(self, x, y, s, size=3.2, color=(0, 0, 0), anchor='start', rot=0):
        w = self.text_w(s, size)
        dx = {'start': 0, 'middle': -w / 2, 'end': -w}[anchor]
        if not self.font:
            from . import font as F
            import math
            ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
            for st in F.strokes(s, size * 0.7)[0]:
                self.lines([(x + (px + dx) * ca - py * sa, y + (px + dx) * sa + py * ca) for px, py in st], color, size * 0.07)
            return
        gs = [self.font.gid(c) for c in s]
        self.used.update(zip(gs, s))
        r, g, b = color
        import math
        ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        tx, ty = x + dx * ca, y + dx * sa
        hexs = ''.join(f'{v:04X}' for v in gs)
        self.c.append(f'BT {_n(r)} {_n(g)} {_n(b)} rg /F1 {_n(size * K)} Tf '
                      f'{_n(ca)} {_n(sa)} {_n(-sa)} {_n(ca)} {_n(tx * K)} {_n(ty * K)} Tm <{hexs}> Tj ET')

    def save(self, path):
        objs = []

        def add(b):
            objs.append(b if isinstance(b, bytes) else b.encode('latin-1'))
            return len(objs)

        def stream(data, extra=''):
            z = zlib.compress(data)
            return f'<< /Length {len(z)} /Filter /FlateDecode {extra}>>\nstream\n'.encode('latin-1') + z + b'\nendstream'
        cat = add('')
        pages = add('')
        font_ref = None
        if self.font:
            f = self.font
            ff = add(stream(f.data, f'/Length1 {len(f.data)} '))
            sc = 1000 / f.upem
            desc = add(f'<< /Type /FontDescriptor /FontName /{f.name} /Flags 32 /FontBBox [-665 -325 2000 1006] '
                       f'/ItalicAngle 0 /Ascent {int(f.ascent * sc)} /Descent {int(f.descent * sc)} /CapHeight 716 '
                       f'/StemV 80 /FontFile2 {ff} 0 R >>')
            ws = ' '.join(f'{g} [{int(f.w(g) * sc)}]' for g, _ in sorted(self.used))
            cid = add(f'<< /Type /Font /Subtype /CIDFontType2 /BaseFont /{f.name} /CIDSystemInfo << /Registry (Adobe) '
                      f'/Ordering (Identity) /Supplement 0 >> /FontDescriptor {desc} 0 R /W [{ws}] '
                      f'/CIDToGIDMap /Identity >>')
            cmap = ('/CIDInit /ProcSet findresource begin 12 dict begin begincmap /CIDSystemInfo << /Registry (Adobe) '
                    '/Ordering (UCS) /Supplement 0 >> def /CMapName /Adobe-Identity-UCS def /CMapType 2 def '
                    '1 begincodespacerange <0000> <FFFF> endcodespacerange\n')
            items = sorted(self.used)
            for i in range(0, len(items), 100):
                ch = items[i:i + 100]
                cmap += f'{len(ch)} beginbfchar\n' + '\n'.join(f'<{g:04X}> <{ord(c):04X}>' for g, c in ch) + '\nendbfchar\n'
            cmap += 'endcmap CMapName currentdict /CMap defineresource pop end end'
            tu = add(stream(cmap.encode('latin-1')))
            font_ref = add(f'<< /Type /Font /Subtype /Type0 /BaseFont /{f.name} /Encoding /Identity-H '
                           f'/DescendantFonts [{cid} 0 R] /ToUnicode {tu} 0 R >>')
        kids = []
        res = f'<< /Font << /F1 {font_ref} 0 R >> >>' if font_ref else '<< >>'
        for p in self.pages:
            cs = add(stream('\n'.join(['1 J 1 j'] + p).encode('latin-1')))
            kids.append(add(f'<< /Type /Page /Parent {pages} 0 R /MediaBox [0 0 {_n(self.w * K)} {_n(self.h * K)}] '
                            f'/Contents {cs} 0 R /Resources {res} >>'))
        objs[cat - 1] = f'<< /Type /Catalog /Pages {pages} 0 R >>'.encode('latin-1')
        objs[pages - 1] = (f'<< /Type /Pages /Kids [{" ".join(f"{k} 0 R" for k in kids)}] '
                           f'/Count {len(kids)} >>').encode('latin-1')
        out = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
        offs = []
        for i, b in enumerate(objs, 1):
            offs.append(len(out))
            out += f'{i} 0 obj\n'.encode('latin-1') + b + b'\nendobj\n'
        xref = len(out)
        out += f'xref\n0 {len(objs) + 1}\n0000000000 65535 f \n'.encode('latin-1')
        out += b''.join(f'{o:010d} 00000 n \n'.encode('latin-1') for o in offs)
        out += f'trailer\n<< /Size {len(objs) + 1} /Root {cat} 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode('latin-1')
        with open(path, 'wb') as fh:
            fh.write(out)
