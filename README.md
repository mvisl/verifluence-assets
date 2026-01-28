# Verifluence Assets

Asset exports and documentation for the Verifluence landing page.

## Export assets from Figma

Set `FIGMA_TOKEN` and run:

```bash
python3 scripts/figma_export.py \
  --file Izgzufe5syG3KcDR7fdPVX \
  --root 314:8186 \
  --extra 3531:31387
```

This writes:
- `assets/` — exported SVG/PNG assets
- `data/assets.json` — registry used by the docs page
- `data/figma-scan.json` — scan snapshot for debugging

## Apply friendly names + remove duplicates

```bash
python3 scripts/rename_assets.py
```

## Optimize PNGs (lossless)

```bash
python3 scripts/optimize_pngs.py --dir assets
```

## View docs locally

```bash
python3 -m http.server 8000
```

Open `http://localhost:8000`.
