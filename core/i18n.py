"""UI and report strings in English and Russian; units."""

LANG = 'en'
UNIT = 'mm'
INCH = 25.4

S = {
    'panel': ('FlatCut', 'FlatCut'),
    'cmd': ('Export to Laser', 'На лазер'),
    'tip': ('DXF/SVG of all flat and sheet metal parts in one click: flat patterns (incl. rolled shells), '
            'engraving layer, bend lines and a pre-cut check',
            'DXF/SVG всех плоских и листовых деталей в один клик: развёртки, слой гравировки, линии гиба, '
            'проверка до резки'),
    'ok': ('Export', 'Выгрузить'),
    'info': ('Flat parts: {n}. Bent sheet metal is unfolded automatically.',
             'Плоских деталей: {n}. Гнутым развёртка создаётся сама.'),
    'tab_parts': ('Parts', 'Детали'),
    'tab_opts': ('Options', 'Настройки'),
    'folder': ('Folder name', 'Папка'),
    'qty_mult': ('Assemblies in order', 'Изделий в заказе'),
    'field': ('File name, field {0}', 'Имя файла, поле {0}'),
    'f_qty': ('Quantity (4x)', 'Количество (4шт)'),
    'f_name': ('Part name', 'Наименование'),
    'f_t': ('Thickness (s3)', 'Толщина (s3)'),
    'f_mat': ('Material', 'Материал'),
    'f_pn': ('Part number', 'Обозначение'),
    'f_none': ('—', '—'),
    'name_eg': ('Example: {0}.dxf', 'Пример: {0}.dxf'),
    'qty_suf': ('x', 'шт'),
    'bends': ('Bend lines (layers BEND_UP / BEND_DOWN)', 'Линии гиба (слои BEND_UP / BEND_DOWN)'),
    'svg': ('Also save SVG (Glowforge, xTool, LightBurn)', 'Ещё и SVG (Glowforge, xTool, LightBurn)'),
    'engrave': ('Engrave part number (online only)', 'Гравировать обозначение (только онлайн)'),
    'text_h': ('Text height, mm', 'Высота текста, мм'),
    'text_h_in': ('Text height, in', 'Высота текста, дюймы'),
    'units': ('Units', 'Единицы'),
    'u_mm': ('mm', 'мм'),
    'u_in': ('in', 'дюймы'),
    'u_in_s': ('in', '″'),
    'open': ('Open folder', 'Открыть папку'),
    'hidden': ('Include hidden parts', 'Скрытые детали тоже'),
    'col_part': ('Part', 'Деталь'),
    'col_mat': ('Material', 'Материал'),
    'none': ('No parts selected.', 'Не отмечено ни одной детали.'),
    'pick': ('Where to create folder "{t}"', 'Где создать папку «{t}»'),
    'no_design': ('Open a design.', 'Откройте модель (Design).'),
    'error': ('FlatCut error', 'FlatCut: ошибка'),
    'nonmetal': ('non-metal', 'не металл'),
    'unfold': ('flat pattern', 'развёртка'),
    'made_fp': ('flat pattern created', 'развёртка создана'),
    'fp_broken': ('broken flat pattern in model — delete it in the browser and run again',
                  'битая развёртка в модели — удалите её в браузере и запустите снова'),
    'fp_notflat': ('flat pattern is not flat — check the part and recreate the flat pattern',
                   'развёртка не плоская — проверьте деталь и пересоздайте развёртку'),
    'fp_new': ('flat pattern will be created on export', 'развёртка создастся при выгрузке'),
    'fp_fix': ('broken flat pattern — will be recreated on export (asks first)',
               'битая развёртка — пересоздастся при выгрузке (спросит)'),
    'fix_ask': ('{n} part(s) have a broken flat pattern. Delete it and create a new one?\n\n{names}',
                'У деталей ({n}) битая развёртка. Удалить её и создать заново?\n\n{names}'),
    'not_sm': ('bent, not Sheet Metal — convert to Sheet Metal', 'гнутая, не листовой металл — переведите в Sheet Metal'),
    'skip_fp': ('bent, flat pattern failed', 'гнутая, развёртка не создалась'),
    'done': ('{n} DXF -> {f}', '{n} DXF -> {f}'),
    'done_svg': ('{n} SVG', '{n} SVG'),
    'check': ('Pre-cut check:', 'Проверка до резки:'),
    'check_ok': ('Pre-cut check: no issues.', 'Проверка до резки: замечаний нет.'),
    'skipped': ('Skipped:', 'Пропущены:'),
    'hole_lt_t': ('hole Ø{0} smaller than thickness {1} — may not cut clean, drill instead',
                  'отверстие Ø{0} меньше толщины {1} — лазер может не прорезать, лучше сверлить'),
    'web_lt_t': ('web {0} between holes / edge is thinner than thickness {1} — may burn through or warp',
                 'перемычка {0} между отверстиями / краем тоньше толщины {1} — может прогореть или повести'),
    'tiny': ('{0} contour(s) smaller than {1}', 'контуров меньше {1}: {0}'),
    'zero_seg': ('{0} zero-length segment(s) in contour', 'нулевых отрезков в контуре: {0}'),
    'no_contour': ('no closed contour', 'нет замкнутого контура'),
    'curve_poly': ('ellipse/spline replaced by polyline', 'эллипс/сплайн заменён ломаной'),
    'text_nofit': ('text "{0}" does not fit — engrave manually', 'текст «{0}» не помещается — гравировку вручную'),
    'text_small': ('text reduced to {0} to fit', 'текст уменьшен до {0}'),
    'font': ('characters not in engraving font: {0}', 'знаков нет в шрифте гравировки: {0}'),
    'pcs': ('pcs', 'шт'),
    'pn_progress': ('Exporting %v / %m', 'Выгрузка %v / %m'),
    'pn_offline': ('No engraving: Fusion is offline?', 'Нет гравировки: Fusion офлайн?'),
    'grav_pref': ('Gr_', 'Гр_'),
    'cancel': ('Cancel', 'Отмена'),
    'busy': ('File is open in another program — close it and export again:\n{f}',
             'Файл открыт в другой программе — закройте его и выгрузите снова:\n{f}'),
}


def T(key, *a, **kw):
    s = S.get(key, (key, key))
    s = s[1] if LANG == 'ru' else s[0]
    return s.format(*a, **kw) if (a or kw) else s


def num(mm, comma=False):
    s = f'{round(mm / INCH, 3):g}' if UNIT == 'in' else f'{round(mm, 2):g}'
    return s.replace('.', ',') if comma and LANG == 'ru' else s


def unit():
    return T('u_in_s') if UNIT == 'in' else T('u_mm')


def L(mm):
    return num(mm) + ('' if unit() == '″' else ' ') + unit()


def thk(t):
    return f'{num(t)}in' if UNIT == 'in' else f's{num(t)}'


def W(w):
    if isinstance(w, str):
        return T(w)
    k, v = w
    if k == 'hole_lt_t':
        return T(k, ', '.join(num(d) for d in v[0]), L(v[1]))
    if k == 'web_lt_t':
        return T(k, L(v[0]), L(v[1]))
    if k == 'tiny':
        return T(k, v, L(1.0))
    if k == 'text_small':
        return T(k, L(v))
    if isinstance(v, tuple):
        return T(k, *v)
    return T(k, v)
