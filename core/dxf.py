"""DXF R2000 writer: layers, LWPOLYLINE with bulge arcs, CIRCLE, LINE; CypCut layer via XDATA."""

LAYERS = {
    'CUT': 3,
    'ENGRAVE': 1,
    'BEND_UP': 1,
    'BEND_DOWN': 1,
}
CH_INNER = 2
CHANNEL = {'ENGRAVE': CH_INNER, 'BEND_UP': CH_INNER, 'BEND_DOWN': CH_INNER}

LEN_CODES = {10, 20, 30, 11, 21, 31, 40}
INT_CODES = {62, 66, 70, 71, 72, 73, 90, 370, 1070}
MS = '1F'


def _f(v):
    s = f'{v:.4f}'.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def _xdata(ch):
    return ((1001, 'FS_CYPCUT'), (1000, 'Channel'), (1070, ch),
            (1000, 'LeadIn'), (1002, '{'), (1070, 0), (1040, 0.0), (1040, 0.0), (1040, 0.0), (1040, 0.0),
            (1070, 0), (1040, 0.0), (1070, 0), (1002, '}'),
            (1000, 'LeadOut'), (1002, '{'), (1070, 0), (1040, 0.0), (1040, 0.0), (1040, 0.0), (1070, 0), (1002, '}'),
            (1000, 'IsFill'), (1070, 0), (1000, 'PathStart'), (1040, 0.0),
            (1000, 'ToolCompensation'), (1002, '{'), (1070, 0), (1040, 0.0), (1070, 0), (1002, '}'))


class Doc:
    def __init__(self, unit='mm'):
        self.unit = unit
        self.ents = []
        self.used = set()

    def _add(self, kind, layer, sub, geom, ch):
        self.used.add(layer)
        ch = CHANNEL.get(layer) if ch is None else ch
        self.ents.append((kind, ((8, layer), (62, LAYERS.get(layer, 7))), sub, geom, _xdata(ch) if ch else ()))

    def line(self, a, b, layer='CUT', ch=None):
        self._add('LINE', layer, 'AcDbLine', ((10, a[0]), (20, a[1]), (30, 0), (11, b[0]), (21, b[1]), (31, 0)), ch)

    def circle(self, c, r, layer='CUT', ch=None):
        self._add('CIRCLE', layer, 'AcDbCircle', ((10, c[0]), (20, c[1]), (30, 0), (40, r)), ch)

    def poly(self, verts, closed=True, layer='CUT', ch=None):
        if len(verts) < 2:
            return
        g = [(90, len(verts)), (70, 1 if closed else 0), (43, 0.0)]
        for v in verts:
            g += [(10, v[0]), (20, v[1])]
            if len(v) > 2 and abs(v[2]) > 1e-9:
                g.append((42, v[2]))
        self._add('LWPOLYLINE', layer, 'AcDbPolyline', tuple(g), ch)

    def text(self):
        out = []
        k = 1 / 25.4 if self.unit == 'in' else 1.0
        inch = self.unit == 'in'
        h = [0x100]

        def nh():
            h[0] += 1
            return f'{h[0]:X}'

        def put(*pairs):
            for code, val in pairs:
                if code in LEN_CODES:
                    val = float(val) * k
                elif isinstance(val, (int, float)) and code not in INT_CODES:
                    val = float(val)
                out.append(f'{code:>3}')
                out.append(_f(val) if isinstance(val, float) else str(val))
        xs, ys = [], []
        for e in self.ents:
            for code, val in e[3]:
                if code in (10, 11):
                    xs.append(val)
                elif code in (20, 21):
                    ys.append(val)
        lo = (min(xs), min(ys)) if xs else (0.0, 0.0)
        hi = (max(xs), max(ys)) if xs else (0.0, 0.0)
        put((0, 'SECTION'), (2, 'HEADER'), (9, '$ACADVER'), (1, 'AC1015'), (9, '$HANDSEED'), (5, 'FFFF'),
            (9, '$INSUNITS'), (70, 1 if inch else 4), (9, '$MEASUREMENT'), (70, 0 if inch else 1),
            (9, '$EXTMIN'), (10, lo[0]), (20, lo[1]), (30, 0), (9, '$EXTMAX'), (10, hi[0]), (20, hi[1]), (30, 0),
            (0, 'ENDSEC'), (0, 'SECTION'), (2, 'CLASSES'), (0, 'ENDSEC'), (0, 'SECTION'), (2, 'TABLES'))

        def table(name, hnd, n):
            put((0, 'TABLE'), (2, name), (5, hnd), (330, '0'), (100, 'AcDbSymbolTable'), (70, n))

        def rec(kind, owner, sub, *pairs):
            put((0, kind), (5, nh()), (330, owner), (100, 'AcDbSymbolTableRecord'), (100, sub), *pairs)
        table('LTYPE', '5', 3)
        for n in ('ByBlock', 'ByLayer', 'Continuous'):
            rec('LTYPE', '5', 'AcDbLinetypeTableRecord', (2, n), (70, 0),
                (3, 'Solid line' if n == 'Continuous' else ''), (72, 65), (73, 0), (40, 0.0))
        put((0, 'ENDTAB'))
        layers = ['0'] + [n for n in LAYERS if n in self.used]
        table('LAYER', '2', len(layers))
        for n in layers:
            rec('LAYER', '2', 'AcDbLayerTableRecord', (2, n), (70, 0), (62, LAYERS.get(n, 7)), (6, 'Continuous'),
                (370, -3), (390, 'F'))
        put((0, 'ENDTAB'))
        table('STYLE', '3', 1)
        rec('STYLE', '3', 'AcDbTextStyleTableRecord', (2, 'Standard'), (70, 0), (40, 0.0), (41, 1.0), (50, 0.0),
            (71, 0), (42, 2.5), (3, 'txt'), (4, ''))
        put((0, 'ENDTAB'))
        for name, hnd in (('VIEW', '6'), ('UCS', '7'), ('VPORT', '8')):
            table(name, hnd, 0)
            put((0, 'ENDTAB'))
        table('DIMSTYLE', 'A', 0)
        put((100, 'AcDbDimStyleTable'), (0, 'ENDTAB'))
        table('APPID', '9', 2)
        for a in ('ACAD', 'FS_CYPCUT'):
            rec('APPID', '9', 'AcDbRegAppTableRecord', (2, a), (70, 0))
        put((0, 'ENDTAB'))
        table('BLOCK_RECORD', '1', 2)
        for n, hnd in (('*Model_Space', MS), ('*Paper_Space', '1B')):
            put((0, 'BLOCK_RECORD'), (5, hnd), (330, '1'), (100, 'AcDbSymbolTableRecord'),
                (100, 'AcDbBlockTableRecord'), (2, n))
        put((0, 'ENDTAB'), (0, 'ENDSEC'), (0, 'SECTION'), (2, 'BLOCKS'))
        for n, hnd, b, e in (('*Model_Space', MS, '20', '21'), ('*Paper_Space', '1B', '1C', '1D')):
            put((0, 'BLOCK'), (5, b), (330, hnd), (100, 'AcDbEntity'), (8, '0'), (100, 'AcDbBlockBegin'), (2, n),
                (70, 0), (10, 0), (20, 0), (30, 0), (3, n), (1, ''),
                (0, 'ENDBLK'), (5, e), (330, hnd), (100, 'AcDbEntity'), (8, '0'), (100, 'AcDbBlockEnd'))
        put((0, 'ENDSEC'), (0, 'SECTION'), (2, 'ENTITIES'))
        for kind, lay, sub, geom, xd in self.ents:
            put((0, kind), (5, nh()), (330, MS), (100, 'AcDbEntity'), *lay, (100, sub), *geom, *xd)
        put((0, 'ENDSEC'), (0, 'SECTION'), (2, 'OBJECTS'),
            (0, 'DICTIONARY'), (5, 'C'), (330, '0'), (100, 'AcDbDictionary'), (281, 1), (3, 'ACAD_GROUP'), (350, 'D'),
            (0, 'DICTIONARY'), (5, 'D'), (330, 'C'), (100, 'AcDbDictionary'), (281, 1), (0, 'ENDSEC'), (0, 'EOF'))
        return '\n'.join(out) + '\n'

    def save(self, path):
        with open(path, 'w', encoding='utf-8', newline='\r\n') as f:
            f.write(self.text())
