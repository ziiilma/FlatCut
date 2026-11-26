"""FlatCut: Autodesk Fusion add-in that exports flat and sheet metal parts to DXF/SVG for laser cutting.

This module only adds the button. The dialog (flatcut_ui.py) and core/ load on the first click.
"""
import os

import adsk.core

_app = None
_ui = None
_handlers = []
_mod = None

PANEL_ID = 'SolidScriptsAddinsPanel'
OLD_PANEL_ID = 'FlatCutPanel'
CMD_ID = 'FlatCutExport'
HERE = os.path.dirname(os.path.abspath(__file__))
DEV = os.path.exists(os.path.join(HERE, '.dev'))
CMD = ('Export to Laser', 'На лазер')
TIP = ('DXF/SVG of all flat and sheet metal parts in one click: flat patterns (incl. rolled shells), '
       'engraving layer, bend lines and a pre-cut check',
       'DXF/SVG всех плоских и листовых деталей в один клик: развёртки, слой гравировки, линии гиба, '
       'проверка до резки')


def _ru():
    try:
        return _app.preferences.generalPreferences.userLanguage == adsk.core.UserLanguages.RussianLanguage
    except Exception:
        return False


def _err():
    import traceback
    if _ui:
        _ui.messageBox('FlatCut\n' + traceback.format_exc())


def _ui_mod():
    global _mod
    if _mod is None or DEV:
        from . import flatcut_ui
        if DEV and _mod is not None:
            import importlib
            importlib.reload(flatcut_ui)
        flatcut_ui.init(_app, _ui)
        _mod = flatcut_ui
    return _mod


class Created(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            _ui_mod().Created().notify(args)
        except Exception:
            _err()


def run(context):
    global _app, _ui
    try:
        _app = adsk.core.Application.get()
        _ui = _app.userInterface
        ru = _ru()
        old = _ui.allToolbarPanels.itemById(OLD_PANEL_ID)
        if old:
            old.deleteMe()
        panel = _ui.allToolbarPanels.itemById(PANEL_ID)
        if not panel:
            ws = _ui.workspaces.itemById('FusionSolidEnvironment')
            tab = ws.toolbarTabs.itemById('ToolsTab') or ws.toolbarTabs.item(0)
            panel = tab.toolbarPanels.add(OLD_PANEL_ID, 'FlatCut')
        ctl = panel.controls.itemById(CMD_ID)
        if ctl:
            ctl.deleteMe()
        cd = _ui.commandDefinitions.itemById(CMD_ID)
        if cd:
            cd.deleteMe()
        cd = _ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD[ru], TIP[ru], os.path.join(HERE, 'resources', 'laser'))
        h = Created()
        cd.commandCreated.add(h)
        _handlers.append(h)
        ctl = panel.controls.addCommand(cd)
        ctl.isPromoted = True
        ctl.isPromotedByDefault = True
    except Exception:
        _err()


def stop(context):
    try:
        panel = _ui.allToolbarPanels.itemById(PANEL_ID)
        ctl = panel.controls.itemById(CMD_ID) if panel else None
        if ctl:
            ctl.deleteMe()
        old = _ui.allToolbarPanels.itemById(OLD_PANEL_ID)
        if old:
            old.deleteMe()
        cd = _ui.commandDefinitions.itemById(CMD_ID)
        if cd:
            cd.deleteMe()
    except Exception:
        pass
    if _mod:
        _mod.stop()
    _handlers.clear()
