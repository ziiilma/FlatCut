#!/bin/bash
# Build the installable package.
#   dist/FlatCut.bundle/      PackageContents.xml + Contents/ (ApplicationPlugins)
#   dist/FlatCut/             plain add-in folder (API/AddIns)
#   dist/FlatCut_<ver>.zip    both folders zipped (GitHub release asset)
#   FlatCut_<ver>.zip         the same zip in the repository root
set -e
SRC="$(cd "$(dirname "$0")/.." && pwd)"
VER=$(python3 -c "import json;print(json.load(open('$SRC/FlatCut.manifest'))['version'])")
DESC=$(python3 -c "import json;print(json.load(open('$SRC/FlatCut.manifest'))['description'][''])")
OUT="$SRC/dist"
PRODUCT_CODE='{41633450-3EB8-43FA-9DFC-4A1288431DFA}'
UPGRADE_CODE='{2F1CB8F3-EF3E-48B8-A750-FE29FD5C2269}'

rm -rf "$OUT/FlatCut" "$OUT/FlatCut.bundle" "$OUT"/FlatCut_[0-9]*.zip
mkdir -p "$OUT/FlatCut/core" "$OUT/FlatCut/resources"
cp "$SRC/FlatCut.py" "$SRC/flatcut_ui.py" "$SRC/FlatCut.manifest" "$OUT/FlatCut/"
cp "$SRC"/core/*.py "$OUT/FlatCut/core/"
cp -R "$SRC/resources/laser" "$SRC/resources/fonts" "$OUT/FlatCut/resources/"
cp "$SRC/store/help.html" "$OUT/FlatCut/"

B="$OUT/FlatCut.bundle"
mkdir -p "$B"
cp -R "$OUT/FlatCut" "$B/Contents"
cat > "$B/PackageContents.xml" <<XML
<?xml version="1.0" encoding="utf-8"?>
<ApplicationPackage SchemaVersion="1.0" AutodeskProduct="Fusion" ProductType="Application"
    Name="FlatCut" AppVersion="$VER" FriendlyVersion="$VER"
    Description="$DESC"
    Author="LZA" ProductCode="$PRODUCT_CODE" UpgradeCode="$UPGRADE_CODE"
    HelpFile="./Contents/help.html" SupportedLocales="Enu|Rus">
  <CompanyDetails Name="LZA" />
  <Components Description="FlatCut add-in">
    <RuntimeRequirements OS="Win64|Mac" Platform="Fusion" />
    <ComponentEntry AppName="FlatCut" Version="$VER" ModuleName="./Contents/FlatCut.py"
        AppDescription="$DESC" />
  </Components>
</ApplicationPackage>
XML
python3 -c "import xml.dom.minidom,sys;xml.dom.minidom.parse(sys.argv[1])" "$B/PackageContents.xml"

find "$OUT/FlatCut" "$B" \( -name '__pycache__' -o -name '.DS_Store' -o -name '.dev' \) -prune -exec rm -rf {} +
xattr -cr "$OUT/FlatCut" "$B" 2>/dev/null || true
(cd "$OUT" && COPYFILE_DISABLE=1 zip -qrX "FlatCut_$VER.zip" FlatCut.bundle FlatCut)
rm -f "$SRC"/FlatCut_[0-9]*.zip
cp "$OUT/FlatCut_$VER.zip" "$SRC/"
echo "Done: $OUT/FlatCut_$VER.zip, $SRC/FlatCut_$VER.zip"
unzip -l "$OUT/FlatCut_$VER.zip" | tail -n +4 | sed '$d' | sed '$d' | awk '{print "  " $4}'
