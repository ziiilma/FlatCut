#!/bin/bash
# Development install (macOS): a loader in Fusion AddIns that runs the code from this folder.
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
DST="$HOME/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/FlatCut"
[ -e "$DST" ] || [ -L "$DST" ] && rm -rf "$DST"
mkdir -p "$DST"
cp "$SRC/FlatCut.manifest" "$DST/"
cat > "$DST/FlatCut.py" <<PY
"""FlatCut development loader: code in $SRC (created by install.sh)."""
import importlib.util
import os
import sys

SRC = '$SRC'
NAME = 'flatcut_src'
_mod = None


def run(context):
    global _mod
    for k in [k for k in sys.modules if k == NAME or k.startswith(NAME + '.')]:
        del sys.modules[k]
    spec = importlib.util.spec_from_file_location(NAME, os.path.join(SRC, 'FlatCut.py'),
                                                  submodule_search_locations=[SRC])
    _mod = importlib.util.module_from_spec(spec)
    sys.modules[NAME] = _mod
    spec.loader.exec_module(_mod)
    _mod.run(context)


def stop(context):
    if _mod:
        _mod.stop(context)
PY
touch "$SRC/.dev"
echo "Installed: $DST (code: $SRC)"
echo "In Fusion: Shift+S → Add-Ins → FlatCut → Run"
