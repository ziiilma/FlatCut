"""FlatCut dialog: part list, options and export."""
import json
import os
import re
import sys
import time
import traceback

import adsk.core
import adsk.fusion

from .core import i18n

_app = None
_ui = None
_cmd_handlers = []
_rows = []
_gen = 0

HERE = os.path.dirname(os.path.abspath(__file__))
DEV = os.path.exists(os.path.join(HERE, '.dev'))
CFG = os.path.join(os.path.expanduser('~'), '.flatcut.json')
FIELDS = ('qty', 'name', 't', 'mat', 'pn', 'none')
N_FIELDS = 4
UNITS = ('mm', 'in')
DEFAULT = dict(fields=['t', 'qty', 'name', 'pn'], bends=True, svg=False, engrave=False, text_h=10.0, open=True, hidden=False,
               folder='')


def init(app, ui):
    global _app, _ui
    _app, _ui = app, ui


def T(*a, **kw):
    return i18n.T(*a, **kw)


def _mods():
    from .core import geom2d, font, dxf, pdf, part, preview, svg, export, fusion_read
    if DEV:
        import importlib
        for m in (i18n, geom2d, font, dxf, pdf, part, preview, svg, export, fusion_read):
            importlib.reload(m)
    _lang()
    return export, fusion_read


def _lang():
    try:
        lang = _app.preferences.generalPreferences.userLanguage
        i18n.LANG = 'ru' if lang == getattr(adsk.core.UserLanguages, 'RussianLanguage', -1) else 'en'
    except Exception:
        i18n.LANG = 'en'


def _cfg():
    c = dict(DEFAULT)
    try:
        with open(CFG, encoding='utf-8') as f:
            c.update(json.load(f))
    except Exception:
        pass
    return c


def _save_cfg(c):
    try:
        with open(CFG, 'w', encoding='utf-8') as f:
            json.dump(c, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def _err():
    if _ui:
        _ui.messageBox(T('error') + '\n' + traceback.format_exc())


def _design():
    p = _app.activeProduct
    if adsk.fusion.FlatPatternProduct.cast(p):
        p = _app.activeDocument.products.itemByProductType('DesignProductType')
    d = adsk.fusion.Design.cast(p)
    if not d:
        _ui.messageBox(T('no_design'))
    return d


def _open(folder):
    try:
        if sys.platform == 'darwin':
            import subprocess
            subprocess.Popen(['open', folder])
        elif sys.platform.startswith('win'):
            os.startfile(folder)
    except Exception:
        pass


def _fields(ci):
    out = []
    for n in range(N_FIELDS):
        dd = ci.itemById(f'f{n}')
        sel = [i for i in range(dd.listItems.count) if dd.listItems.item(i).isSelected]
        k = FIELDS[sel[0]] if sel else 'none'
        if k != 'none':
            out.append(k)
    return out


def _doc_unit(des):
    try:
        u = des.unitsManager.distanceDisplayUnits
        DU = adsk.fusion.DistanceUnits
        return 'in' if u in (DU.InchDistanceUnits, DU.FootDistanceUnits) else 'mm'
    except Exception:
        return 'mm'


def _unit(ci):
    dd = ci.itemById('units')
    sel = [i for i in range(dd.listItems.count) if dd.listItems.item(i).isSelected]
    return UNITS[sel[0]] if sel else 'mm'


def _text_h(ci):
    return ci.itemById('text_h_in').value * i18n.INCH if _unit(ci) == 'in' else ci.itemById('text_h').value


def _id(k, i):
    return f'{k}{_gen}_{i}'


def _fill(t):
    ci = t.commandInputs
    for i, r in enumerate(_rows):
        skip = r['kind'] == 'skip'
        b = ci.addBoolValueInput(_id('on', i), '', True, '', r['metal'] and not skip)
        b.isEnabled = not skip
        t.addCommandInput(b, i, 0)
        t.addCommandInput(ci.addTextBoxCommandInput(_id('nm', i), '', r['name'], 1, True), i, 1)
        t.addCommandInput(ci.addTextBoxCommandInput(_id('mt', i), '', r['note'] if skip else
                                                    r['mat'] + (f' · {r["note"]}' if r['note'] else ''), 1, True), i, 2)
        t.addCommandInput(ci.addTextBoxCommandInput(_id('s', i), '', '' if skip else i18n.thk(r['t']), 1, True), i, 3)
        t.addCommandInput(ci.addTextBoxCommandInput(_id('q', i), '', f'{r["qty"]} {T("pcs")}', 1, True), i, 4)
    n = len(_rows)
    for k in range(3):
        t.addCommandInput(ci.addTextBoxCommandInput(_id('pad', k), '', '', 1, True), n + k, 1)


def _info():
    return T('info', n=sum(1 for r in _rows if r['kind'] != 'skip'))


def _set_hidden(ci, hidden):
    global _rows, _gen
    from .core import fusion_read as R
    des = _design()
    if not des:
        return
    t = ci.itemById('tbl')
    t.clear()
    _gen += 1
    _rows = R.collect(des, hidden)
    _fill(t)
    ci.itemById('info').text = _info()
    ci.itemById('eg').text = _example(_fields(ci))


def _set_unit(ci):
    u = _unit(ci)
    h = ci.itemById('text_h').value if ci.itemById('text_h').isVisible else ci.itemById('text_h_in').value * i18n.INCH
    i18n.UNIT = u
    for i, r in enumerate(_rows):
        s = ci.itemById(_id('s', i))
        if s and r['kind'] != 'skip':
            s.text = i18n.thk(r['t'])
    ci.itemById('text_h').value = h
    ci.itemById('text_h_in').value = h / i18n.INCH
    ci.itemById('text_h').isVisible = u == 'mm'
    ci.itemById('text_h_in').isVisible = u == 'in'
    ci.itemById('eg').text = _example(_fields(ci))


def _example(fields):
    from .core import export
    r = next((x for x in _rows if x['kind'] != 'skip'), None)
    name, t, mat, pn = (r['name'], r['t'], r['mat'], r['pn'] or 'AB-001') if r else ('Bracket', 3, 'Steel', 'AB-001')
    from types import SimpleNamespace
    p = SimpleNamespace(qty=4, name=name, t=t, mat=mat, pn=pn)
    return T('name_eg', export.fname([k for k in fields if k != 'none'], p))


class Created(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            global _rows
            export, R = _mods()
            cmd = args.command
            des = _design()
            if not des:
                try:
                    cmd.doExecute(True)
                except Exception:
                    pass
                return
            c = _cfg()
            cmd.okButtonText = T('ok')
            cmd.setDialogInitialSize(780, 680)
            i18n.UNIT = c.get('units') if c.get('units') in UNITS else _doc_unit(des)
            _rows = R.collect(des, bool(c.get('hidden')))
            st = cmd.commandInputs
            name = re.sub(r'\s+v\d+$', '', des.parentDocument.name)

            tp = st.addTabCommandInput('tp', T('tab_parts')).children
            tp.addTextBoxCommandInput('info', '', _info(), 2, True)
            tp.addStringValueInput('title', T('folder'), f'Laser {name}' if i18n.LANG == 'en' else f'На лазер {name}')
            tp.addIntegerSpinnerCommandInput('zakaz', T('qty_mult'), 1, 10000, 1, 1)
            tp.addBoolValueInput('hidden', T('hidden'), True, '', bool(c.get('hidden')))
            t = tp.addTableCommandInput('tbl', T('tab_parts'), 5, '1:8:4:2:2')
            t.maximumVisibleRows = 10
            t.minimumVisibleRows = 6
            _fill(t)

            to = st.addTabCommandInput('to', T('tab_opts')).children
            dd = to.addDropDownCommandInput('units', T('units'), adsk.core.DropDownStyles.TextListDropDownStyle)
            for u in UNITS:
                dd.listItems.add(T('u_' + u), u == i18n.UNIT)
            fs = (list(c.get('fields') or DEFAULT['fields']) + ['none'] * N_FIELDS)[:N_FIELDS]
            for n in range(N_FIELDS):
                dd = to.addDropDownCommandInput(f'f{n}', T('field', n + 1), adsk.core.DropDownStyles.TextListDropDownStyle)
                for k in FIELDS:
                    dd.listItems.add(T('f_' + k), k == fs[n])
            to.addTextBoxCommandInput('eg', '', _example(fs), 1, True)
            to.addBoolValueInput('bends', T('bends'), True, '', c['bends'])
            to.addBoolValueInput('svg', T('svg'), True, '', c['svg'])
            to.addBoolValueInput('engrave', T('engrave'), True, '', c['engrave'])
            th = to.addFloatSpinnerCommandInput('text_h', T('text_h'), '', 2, 100, 1, c['text_h'])
            th_in = to.addFloatSpinnerCommandInput('text_h_in', T('text_h_in'), '', 0.08, 4, 0.05,
                                                   round(c['text_h'] / i18n.INCH, 3))
            th.isVisible, th_in.isVisible = i18n.UNIT == 'mm', i18n.UNIT == 'in'
            to.addBoolValueInput('open', T('open'), True, '', c['open'])

            _cmd_handlers.clear()
            h = Changed()
            cmd.inputChanged.add(h)
            _cmd_handlers.append(h)
            h = Execute()
            cmd.execute.add(h)
            _cmd_handlers.append(h)
        except Exception:
            _err()


class Changed(adsk.core.InputChangedEventHandler):
    def notify(self, args):
        try:
            ci = args.input.parentCommand.commandInputs
            if args.input.id == 'hidden':
                _set_hidden(ci, args.input.value)
            elif args.input.id == 'units':
                _set_unit(ci)
            elif args.input.id in {f'f{n}' for n in range(N_FIELDS)}:
                ci.itemById('eg').text = _example(_fields(ci))
        except Exception:
            _err()


class Execute(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            export, R = _mods()
            inp = args.command.commandInputs
            v = lambda k: inp.itemById(k).value
            rows = [r for i, r in enumerate(_rows) if r['kind'] != 'skip' and v(_id('on', i))]
            if not rows:
                _ui.messageBox(T('none'))
                return
            c = _cfg()
            i18n.UNIT = _unit(inp)
            c.update(fields=_fields(inp), bends=v('bends'), svg=v('svg'), engrave=v('engrave'), text_h=_text_h(inp),
                     units=i18n.UNIT, hidden=v('hidden'),
                     open=v('open'))
            title = re.sub(r'[\\/:*?"<>|]', '_', v('title')).strip() or 'Laser'
            fd = _ui.createFolderDialog()
            fd.title = T('pick', t=title)
            if c.get('folder') and os.path.isdir(c['folder']):
                fd.initialDirectory = c['folder']
            if fd.showDialog() != adsk.core.DialogResults.DialogOK:
                return
            c['folder'] = fd.folder
            _save_cfg(c)
            folder = os.path.join(fd.folder, title)
            fix = [r for r in rows if r.get('make') == 'fix']
            if fix and _ui.messageBox(T('fix_ask', n=len(fix), names='\n'.join(r['name'] for r in fix[:10])), 'FlatCut',
                                      adsk.core.MessageBoxButtonTypes.YesNoButtonType) != adsk.core.DialogResults.DialogYes:
                rows = [r for r in rows if r.get('make') != 'fix']
                fixed_no = [f"{r['name']}: {T('fp_broken')}" for r in fix]
            else:
                fixed_no = []
            tm, t0 = {}, time.perf_counter()
            rows, bad = R.prepare(rows)
            tm['fp'], t0 = time.perf_counter() - t0, time.perf_counter()
            no_pn = _read_pn(R, rows) if rows and (c['engrave'] or 'pn' in c['fields']) else 0
            tm['pn'], t0 = time.perf_counter() - t0, time.perf_counter()
            items = R.read(rows, v('zakaz'), c['engrave'])
            tm['read'] = time.perf_counter() - t0
            skipped = [f"{x['name']}: {x['note']}" for x in _rows if x['kind'] == 'skip'] + fixed_no + bad
            try:
                rep = export.run(items, folder, dict(c, title=title), skipped)
            except export.Busy as e:
                _ui.messageBox(T('busy', f=str(e)))
                return
            if c['open']:
                _open(folder)
            if no_pn:
                rep = [T('pn_offline', n=no_pn), ''] + rep
            if DEV:
                tm.update(export.TIMES)
                nfp = sum(1 for r in rows if 'made_fp' in str(r.get('note')))
                ncomp = len({r['comp'].entityToken for r in rows})
                rep = [f"time: flat patterns {tm['fp']:.1f} s ({nfp}), part numbers {tm['pn']:.1f} s ({ncomp} comp.), "
                       f"contours {tm['read']:.1f} s, DXF/SVG {tm.get('files', 0):.1f} s, "
                       f"preview {tm.get('preview', 0):.1f} s", ''] + rep
            msg = '\n'.join(rep)
            if len(msg) > 2500:
                msg = msg[:2500] + '\n…'
            _ui.messageBox('FlatCut\n' + msg)
        except Exception:
            _err()


def _read_pn(R, rows):
    pd = _ui.createProgressDialog()
    pd.isCancelButtonShown = True
    pd.cancelButtonText = T('cancel')
    pd.show('FlatCut', T('pn_progress'), 0, max(len(rows), 1), 0)

    def step(i, n):
        pd.maximumValue = max(n, 1)
        pd.progressValue = i
        adsk.doEvents()
        return not pd.wasCancelled
    try:
        return R.fill_pn(rows, step)
    finally:
        pd.hide()


def stop():
    _cmd_handlers.clear()
