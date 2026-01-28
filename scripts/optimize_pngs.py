#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
from PIL import Image


def optimize_png(path: Path):
    with Image.open(path) as img:
        img.save(path, optimize=True, compress_level=9)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', default='assets')
    args = parser.parse_args()

    base = Path(args.dir)
    if not base.exists():
        raise SystemExit(f'Assets dir not found: {base}')

    png_files = list(base.rglob('*.png'))
    for file_path in png_files:
        optimize_png(file_path)

    print(f'Optimized {len(png_files)} PNG files in {base}')


if __name__ == '__main__':
    main()
