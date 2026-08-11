# Contributing to Verto

Thanks for your interest in improving Verto.

## Principles

1. **Offline first** — no network calls, telemetry, analytics, or auto-update pings.
2. **Morphix** owns conversion logic under `src/morphix/`.
3. **FileForge** owns UI theming under `src/ui/fileforge/` (theme is cosmetic; UX must stay usable without it).
4. Reliability beats visual polish.

## Development setup

```bash
cd verto
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest
python -m main              # from repo root with PYTHONPATH=src, or:
PYTHONPATH=src python src/main.py
```

## Pull requests

- Keep changes focused and tested.
- Add or update unit tests for Morphix converters when changing conversion behavior.
- Do not add HTTP clients or cloud SDKs.

## License

By contributing, you agree that your contributions are licensed under the MIT License.
