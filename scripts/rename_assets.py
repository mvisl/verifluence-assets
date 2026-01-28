#!/usr/bin/env python3
import json
import hashlib
from pathlib import Path
from PIL import Image
import re

# Manual naming map for known assets (keyed by original filename)
NAME_MAP = {
    # SVG
    'bg-3531-31387.svg': {
        'name': 'Landing background overlay',
        'slug': 'landing-background-overlay',
        'section': 'page',
        'usage': 'Background overlay with bottom transparency (over solid color)',
    },
    'bg-3531-31399.svg': {
        'name': 'Landing background layer A',
        'slug': 'landing-background-layer-a',
        'section': 'page',
        'usage': 'Background gradient layer (upper area)',
    },
    'bg-3531-31422.svg': {
        'name': 'Landing background layer B',
        'slug': 'landing-background-layer-b',
        'section': 'page',
        'usage': 'Background gradient layer (mid area)',
    },
    'bg-I314-8231;308-8765.svg': {
        'name': 'Team section background',
        'slug': 'team-section-background',
        'section': 'team',
        'usage': 'Background for Team section',
    },
    'page-3-314-8204.svg': {
        'name': 'Landing base background',
        'slug': 'landing-base-background',
        'section': 'page',
        'usage': 'Base full-width background rectangle',
    },
    'bg-I314-8221;236-6695;236-6687.svg': {
        'name': 'Benefits list icon blob 01',
        'slug': 'benefits-list-icon-blob-01',
        'section': 'benefits',
        'usage': 'Blob under benefits list icon (variant 1)',
    },
    'bg-I314-8221;236-6706;236-6687.svg': {
        'name': 'Benefits list icon blob 02',
        'slug': 'benefits-list-icon-blob-02',
        'section': 'benefits',
        'usage': 'Blob under benefits list icon (variant 2)',
    },
    'bg-I314-8228;236-7604;236-7597.svg': {
        'name': 'Benefits feature icon blob',
        'slug': 'benefits-feature-icon-blob',
        'section': 'benefits',
        'usage': 'Blob under benefits feature icon',
    },
    'bg-I314-8231;308-8730;306-8294;301-7732;246-6645;246-6634.svg': {
        'name': 'Team bullet icon blob',
        'slug': 'team-bullet-icon-blob',
        'section': 'team',
        'usage': 'Blob behind team bullet icon',
    },
    'ellipse-2-314-8197.svg': {
        'name': 'Hero illustration glow',
        'slug': 'hero-illustration-glow',
        'section': 'hero',
        'usage': 'Glow behind hero illustration',
    },
    'ellipse-2-I314-8205;236-7498.svg': {
        'name': 'Market illustration glow',
        'slug': 'market-illustration-glow',
        'section': 'market',
        'usage': 'Glow behind market size illustration',
    },
    'logo-v3-I314-8233;4-342;3-44.svg': {
        'name': 'Logo mark',
        'slug': 'logo-mark',
        'section': 'nav',
        'usage': 'Header logo mark',
    },
    'martin-light-I314-8231;308-8730;312-4540.svg': {
        'name': 'Team portrait glow',
        'slug': 'team-portrait-glow',
        'section': 'team',
        'usage': 'Glow behind Martin portrait',
    },
    'rectangle-38-I314-8221;236-6601.svg': {
        'name': 'Benefits card background',
        'slug': 'benefits-card-background',
        'section': 'benefits',
        'usage': 'Main card background for benefits panel',
    },
    'shapes-I314-8221;236-7479.svg': {
        'name': 'Benefits card shapes',
        'slug': 'benefits-card-shapes',
        'section': 'benefits',
        'usage': 'Decorative shapes for benefits card',
    },
    'shapes-I314-8222;246-6975.svg': {
        'name': 'Contact card shapes',
        'slug': 'contact-card-shapes',
        'section': 'contact',
        'usage': 'Decorative shapes for contact card',
    },
    'vector-15-I314-8231;308-8730;308-8603;312-4557;306-8341.svg': {
        'name': 'Team portrait outline small',
        'slug': 'team-portrait-outline-small',
        'section': 'team',
        'usage': 'Small outline overlay on Martin portrait',
    },
    'vector-16-I314-8231;308-8730;308-8603;312-4557;306-8342.svg': {
        'name': 'Team portrait outline large',
        'slug': 'team-portrait-outline-large',
        'section': 'team',
        'usage': 'Large outline overlay on Martin portrait',
    },
    'vector-17-I314-8221;236-6603.svg': {
        'name': 'Card blob small',
        'slug': 'card-blob-small',
        'section': 'shared',
        'usage': 'Small decorative blob (benefits/contact cards)',
    },
    'vector-18-I314-8221;236-6604.svg': {
        'name': 'Card blob large 01',
        'slug': 'card-blob-large-01',
        'section': 'shared',
        'usage': 'Large decorative blob (variant 1) for benefits/contact cards',
    },
    'vector-18-I314-8222;246-6965.svg': {
        'name': 'Card blob large 02',
        'slug': 'card-blob-large-02',
        'section': 'shared',
        'usage': 'Large decorative blob (variant 2) for benefits/contact cards',
    },
    'vector-42-I314-8194;94-3045.svg': {
        'name': 'Hero logo accent 01',
        'slug': 'hero-logo-accent-01',
        'section': 'hero',
        'usage': 'Accent vector in hero logo illustration',
    },
    'vector-43-I314-8194;94-3044.svg': {
        'name': 'Hero logo accent 02',
        'slug': 'hero-logo-accent-02',
        'section': 'hero',
        'usage': 'Accent vector in hero logo illustration',
    },
    'vector-44-314-8195.svg': {
        'name': 'Hero logo accent 03',
        'slug': 'hero-logo-accent-03',
        'section': 'hero',
        'usage': 'Accent vector in hero logo illustration',
    },
    'vector-45-314-8196.svg': {
        'name': 'Hero logo accent 04',
        'slug': 'hero-logo-accent-04',
        'section': 'hero',
        'usage': 'Accent vector in hero logo illustration',
    },
    # PNG
    'image-175-314-8207.png': {
        'name': 'City skyline small 01',
        'slug': 'city-skyline-small-01',
        'section': 'page',
        'usage': 'Bottom skyline silhouette (small)',
    },
    'image-176-314-8210.png': {
        'name': 'City skyline small 02',
        'slug': 'city-skyline-small-02',
        'section': 'page',
        'usage': 'Bottom skyline silhouette (small)',
    },
    'image-177-314-8212.png': {
        'name': 'City skyline small 03',
        'slug': 'city-skyline-small-03',
        'section': 'page',
        'usage': 'Bottom skyline silhouette (small)',
    },
    'image-183-314-8216.png': {
        'name': 'City skyline wide 01',
        'slug': 'city-skyline-wide-01',
        'section': 'page',
        'usage': 'Bottom skyline silhouette (wide)',
    },
    'image-184-314-8208.png': {
        'name': 'City skyline wide 02',
        'slug': 'city-skyline-wide-02',
        'section': 'page',
        'usage': 'Bottom skyline silhouette (wide)',
    },
    'image-185-I314-8228;236-7604;236-7644.png': {
        'name': 'Benefits icon orb',
        'slug': 'benefits-icon-orb',
        'section': 'benefits',
        'usage': 'Orb inside benefits feature icon',
    },
    'image-195-I314-8222;246-7073.png': {
        'name': 'Contact illustration handshake',
        'slug': 'contact-illustration-handshake',
        'section': 'contact',
        'usage': 'Handshake illustration in contact section',
    },
    'image-197-I314-8231;308-8730;308-8603;312-4557;345-6702.png': {
        'name': 'Team portrait Martin',
        'slug': 'team-portrait-martin',
        'section': 'team',
        'usage': 'Portrait image in team section',
    },
    'image-48-I314-8205;236-7497.png': {
        'name': 'Market illustration coins',
        'slug': 'market-illustration-coins',
        'section': 'market',
        'usage': 'Coins layer under market illustration',
    },
    'image-49-I314-8205;236-7495.png': {
        'name': 'Market illustration controller',
        'slug': 'market-illustration-controller',
        'section': 'market',
        'usage': 'Main controller illustration in market section',
    },
    'image-50-I314-8205;236-7496.png': {
        'name': 'Market illustration controller glow',
        'slug': 'market-illustration-controller-glow',
        'section': 'market',
        'usage': 'Glow layer behind controller illustration',
    },
    'image-62-I314-8194;94-3036.png': {
        'name': 'Hero logo illustration base',
        'slug': 'hero-logo-illustration-base',
        'section': 'hero',
        'usage': 'Base layer of hero 3D logo illustration',
    },
    'image-63-I314-8194;94-3046.png': {
        'name': 'Hero logo illustration core',
        'slug': 'hero-logo-illustration-core',
        'section': 'hero',
        'usage': 'Core layer of hero 3D logo illustration',
    },
    'image-65-I314-8221;236-6578.png': {
        'name': 'Benefits illustration slot machine',
        'slug': 'benefits-illustration-slot-machine',
        'section': 'benefits',
        'usage': 'Slot machine illustration in benefits section',
    },
    'image-78-I314-8231;308-8730;306-8294;301-7732;246-6645;246-6641.png': {
        'name': 'Team bullet icon',
        'slug': 'team-bullet-icon',
        'section': 'team',
        'usage': 'Icon used in team bullet list',
    },
    'image-78-I314-8232;314-5597.png': {
        'name': 'Hero orb icon',
        'slug': 'hero-orb-icon',
        'section': 'hero',
        'usage': 'Small orb icon in hero area',
    },
}


def slugify(text: str):
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s_-]+', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    return text.strip('-') or 'asset'


def main():
    base = Path(__file__).resolve().parents[1]
    assets_path = base / 'data' / 'assets.json'
    assets_dir = base / 'assets'

    assets_data = json.loads(assets_path.read_text())
    assets = assets_data['assets']

    # Deduplicate by file hash
    hash_groups = {}
    for asset in assets:
        file_path = assets_dir / asset['filename']
        if not file_path.exists():
            continue
        h = hashlib.sha256(file_path.read_bytes()).hexdigest()
        hash_groups.setdefault(h, []).append(asset)

    canonical_assets = []
    for items in hash_groups.values():
        mapped = [a for a in items if a['filename'] in NAME_MAP]
        canonical_assets.append(mapped[0] if mapped else items[0])

    canonical_assets.sort(key=lambda a: a['filename'])

    used_filenames = set()
    new_records = []

    for asset in canonical_assets:
        original_filename = asset['filename']
        meta = NAME_MAP.get(original_filename)
        if not meta:
            base_name = asset.get('name') or 'asset'
            meta = {
                'name': base_name,
                'slug': slugify(base_name),
                'section': 'misc',
                'usage': asset.get('usage') or 'Asset',
            }

        ext = asset['type']
        filename = f"{meta['slug']}.{ext}"
        counter = 2
        while filename in used_filenames:
            filename = f"{meta['slug']}-{counter}.{ext}"
            counter += 1
        used_filenames.add(filename)

        src_path = assets_dir / original_filename
        dest_path = assets_dir / filename
        if src_path.exists() and src_path != dest_path:
            if dest_path.exists():
                raise SystemExit(f'Name collision for {dest_path}')
            src_path.rename(dest_path)

        size = asset.get('size') or {}
        if ext == 'png':
            with Image.open(dest_path) as img:
                size = {'width': img.size[0], 'height': img.size[1]}

        new_records.append({
            'id': asset['id'],
            'name': meta['name'],
            'type': ext,
            'filename': filename,
            'path': f"assets/{filename}",
            'size': size,
            'usage': meta['usage'],
            'section': meta['section'],
            'sourceNodeId': asset['id'],
            'status': 'ready',
        })

    keep = {r['filename'] for r in new_records}
    for file_path in assets_dir.iterdir():
        if file_path.is_file() and file_path.name not in keep:
            file_path.unlink()

    assets_path.write_text(json.dumps({'count': len(new_records), 'assets': sorted(new_records, key=lambda r: r['filename'])}, indent=2, ensure_ascii=False))
    print(f'Updated assets: {len(new_records)}')


if __name__ == '__main__':
    main()
