# FlatCut — DXF for Laser Cutting

Autodesk Fusion add-in. Exports every flat plate and sheet metal part of a design to DXF/SVG for laser cutting in one click. Windows and macOS, English and Russian interface.

## Features

- Flat patterns are created automatically, including rolled shells (cylinders and cones).
- One DXF R2000 per part: closed contours, arcs instead of splines — opens in LightBurn, CypCut, SigmaNEST, Lantek, RDWorks. In CypCut engraving and bend lines land on layer 2, cut lines on the default layer.
- Layers: `CUT`, `ENGRAVE` (shallow pockets and the part number as single-line text), `BEND_UP` / `BEND_DOWN`.
- Optional SVG for Glowforge, xTool, LightBurn.
- mm or inches: DXF, SVG, file names and preview follow the Units option.
- `preview.pdf` on A3 (Tabloid 11×17 in inches): each part with overall size and dimensions to bend lines.
- File names from quantity, name, thickness, material and part number in any order.
- Pre-cut check: holes smaller than thickness, thin webs, tiny contours.
- No external Python or libraries.

## Install

**[⬇ Download FlatCut_1.0.0.zip](https://github.com/ziiilma/FlatCut/releases/latest/download/FlatCut_1.0.0.zip)**. The same file is in the repository root, so it also comes with **Code → Download ZIP**.

The zip has two folders: `FlatCut.bundle` and `FlatCut`. Use one way, not both.

**Way 1 — ApplicationPlugins**
1. Copy `FlatCut.bundle` to:
   - Windows: `%APPDATA%\Autodesk\ApplicationPlugins\`
   - macOS: `~/Library/Application Support/Autodesk/Application Plugins/`
2. Restart Fusion.

**Way 2 — AddIns** (if Way 1 shows no button)
1. Copy the `FlatCut` folder to:
   - Windows: `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\`
   - macOS: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/`
2. Restart Fusion. If there is no button: Shift+S → Add-Ins → FlatCut → Run.

The button: Design → Utilities → ADD-INS → **Export to Laser**.

**From source (macOS, development):** `./install.sh`, then in Fusion: Shift+S → Add-Ins → FlatCut → Run.

**Build the package:** `./tools/make_store_package.sh` → `dist/FlatCut_<version>.zip`.

## Usage

Design workspace → Utilities → Add-Ins → **Export to Laser**. Full help: [store/help.html](store/help.html).

## Layout

| Path | Purpose |
|---|---|
| `FlatCut.py` | Button only (startup < 5 ms) |
| `flatcut_ui.py` | Dialog, loaded on first click |
| `core/fusion_read.py` | Reads parts and flat patterns from Fusion |
| `core/dxf.py`, `core/svg.py` | DXF R2000 and SVG writers |
| `core/preview.py`, `core/pdf.py` | PDF preview with dimensions |
| `core/font.py` | Single-line engraving font |
| `core/part.py` | Pre-cut check |
| `core/i18n.py` | EN/RU strings, units |

## Privacy

FlatCut works locally and sends no design data anywhere.

## License

MIT — see [LICENSE](LICENSE). Liberation Sans — SIL OFL 1.1.

---

# FlatCut (RU)

Аддон для Autodesk Fusion: все плоские и листовые детали модели — в DXF/SVG на лазер в один клик. Развёртка гнутым создаётся сама, слои CUT / ENGRAVE / BEND, превью PDF с размерами, проверка до резки. Без внешнего Python, Windows и macOS, интерфейс EN/RU.

**Установка:** скачайте [FlatCut_1.0.0.zip](https://github.com/ziiilma/FlatCut/releases/latest/download/FlatCut_1.0.0.zip) (он же лежит в корне репозитория) и распакуйте. Выберите один способ.

Способ 1 — скопируйте папку `FlatCut.bundle`:
- Windows: `%APPDATA%\Autodesk\ApplicationPlugins\`
- macOS: `~/Library/Application Support/Autodesk/Application Plugins/`

Перезапустите Fusion.

Способ 2 (если кнопки нет) — скопируйте папку `FlatCut`:
- Windows: `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\`
- macOS: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/`

Перезапустите Fusion. Если кнопки нет: Shift+S → Add-Ins → FlatCut → Run.

Кнопка: Design → Утилиты → ADD-INS → **На лазер**.
