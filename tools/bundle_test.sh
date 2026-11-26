#!/bin/bash
# Test the release bundle on macOS.
#   ./tools/bundle_test.sh install  build the bundle, replace the dev add-in with it
#   ./tools/bundle_test.sh remove   remove the bundle, restore the dev add-in
set -e
SRC="$(cd "$(dirname "$0")/.." && pwd)"
PLUG="$HOME/Library/Application Support/Autodesk/Application Plugins"
DEVDIR="$HOME/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/FlatCut"
case "$1" in
  install)
    "$SRC/tools/make_store_package.sh" >/dev/null
    rm -rf "$DEVDIR"
    mkdir -p "$PLUG"
    rm -rf "$PLUG/FlatCut.bundle"
    cp -R "$SRC/dist/FlatCut.bundle" "$PLUG/"
    echo "Installed: $PLUG/FlatCut.bundle. Restart Fusion.";;
  remove)
    rm -rf "$PLUG/FlatCut.bundle"
    "$SRC/install.sh"
    echo "Bundle removed, dev add-in restored. Restart Fusion.";;
  *) echo "usage: $0 install|remove"; exit 1;;
esac
