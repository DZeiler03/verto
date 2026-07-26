# Verto

**Verto** (from Latin *verto* — “I turn / transform”) is a **desktop file converter that works completely offline**. No cloud, no accounts, no telemetry.

Verto’s conversion engine, **Morphix**, handles all format detection and conversion work under the hood. The interface is themed as **FileForge** — a blacksmith’s forge (anvil input slot, hammer-strike animation, output slot, inventory-style forge queue).

| Platform | Support |
|----------|---------|
| **Linux** | **Primary** — first-class install, CI builds, packaging |
| **macOS** | Secondary — run from source; packaging stretch |
| **Windows** | Optional — run from source; packaging not prioritized |

## Features

### Morphix conversions

- **Images:** JPG ⇄ PNG ⇄ BMP ⇄ WEBP ⇄ TIFF ⇄ GIF, images → PDF  
- **PDF:** PDF → PNG/JPG (per page), PDF → TXT, TXT → PDF  
- **PDF tools:** merge, split (one file per page), compress  
- **OCR (optional):** scanned PDF / image → text via local **Tesseract**  
- **Spreadsheets:** XLSX ⇄ CSV  
- **Office (LibreOffice):** DOCX ⇄ PDF/ODT, XLSX ⇄ ODS, PPTX ⇄ PDF/ODP  

### FileForge UI

- Anvil drop zone, hammer animation while forging, output slot + Download  
- Forge queue with per-item status  
- **Forge** (dark) / **Daylight smithy** (light) themes  

### Staging & Download

Results land in a private cache first; **Download ⬇️** copies them to Downloads (or your chosen destination). Staging is cleared on exit; leftovers older than 24h are purged on startup.

## Hard constraints

- No internet or cloud API calls in the app  
- No telemetry / analytics / tracking  
- No paid proprietary SDKs  

## Requirements (Linux)

- **Python 3.11+**
- **Qt/PySide6** stack (installed via pip)
- **LibreOffice** (optional) — Office ⇄ PDF/ODF  
- **Tesseract** (optional) — offline OCR  

```bash
# Fedora / RHEL
sudo dnf install python3 python3-pip libreoffice tesseract

# Debian / Ubuntu
sudo apt install python3 python3-venv python3-pip libreoffice tesseract-ocr

# Arch
sudo pacman -S python python-pip libreoffice-still tesseract
```

### macOS (secondary)

```bash
brew install python libreoffice tesseract
```

### Windows (optional)

Install [Python 3.11+](https://www.python.org/downloads/), optionally [LibreOffice](https://www.libreoffice.org/) and [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki). Then use the same `pip` / `venv` flow as below.

## Install & run (from source)

```bash
git clone https://github.com/DZeiler03/verto.git
cd verto
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

PYTHONPATH=src python src/main.py
```

## Build standalone Linux binary

```bash
bash scripts/build-linux.sh
# → dist/verto
./dist/verto
```

Optional desktop entry:

```bash
cp packaging/verto.desktop ~/.local/share/applications/
# install the binary as `verto` on your PATH
```

Tagged releases (`v*`) trigger a GitHub Actions Linux build (see `.github/workflows/`).

## Supported conversions

| Category | Formats |
|----------|---------|
| Documents | PDF ⇄ DOCX*, PDF ⇄ TXT, PDF → images, DOCX ⇄ ODT*, DOCX → PDF* |
| PDF tools | Merge, split, compress; OCR-TXT† |
| Images | JPG, PNG, BMP, WEBP, TIFF, GIF; images → PDF; OCR-TXT† |
| Spreadsheets | XLSX ⇄ CSV, XLSX ⇄ ODS* |
| Presentations | PPTX ⇄ PDF*, PPTX ⇄ ODP* |

\* Requires local LibreOffice (`soffice --headless`).  
† Requires local Tesseract.

### Google Workspace files

Native `.gdoc` / `.gsheet` / `.gslides` files are **not documents** — they are link files. Export from Google Drive first, then convert in Verto.

## Project layout

```
verto/
├── src/
│   ├── main.py
│   ├── ui/                 # FileForge GUI + PDF tools dialog
│   ├── morphix/            # Morphix engine, converters, PDF tools, OCR
│   ├── core/               # detector, queue, storage, settings
│   └── utils/
├── packaging/              # PyInstaller spec, .desktop
├── scripts/build-linux.sh
├── tests/
└── README.md
```

## Development

```bash
pip install -r requirements.txt
PYTHONPATH=src QT_QPA_PLATFORM=offscreen pytest
```

## Architecture

- **Morphix** — format detection, conversion, PDF tools, optional OCR  
- **Core** — queue, staging/download storage, local settings  
- **FileForge** — PySide6 forge UI; conversions on a worker thread  

## License

MIT — see [LICENSE](LICENSE).

## Roadmap

1. ~~Phase 1: Morphix + functional GUI~~  
2. ~~Phase 2: staging cache, Download destinations~~  
3. ~~Phase 3: FileForge theme~~  
4. ~~Phase 4: PDF tools, OCR, Linux packaging & release CI~~  
