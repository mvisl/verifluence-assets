#!/usr/bin/env python3
import argparse
import json
import os
import re
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen

VECTOR_TYPES = {
    'VECTOR',
    'BOOLEAN_OPERATION',
    'STAR',
    'POLYGON',
    'ELLIPSE',
    'RECTANGLE',
    'LINE',
}

CONTAINER_TYPES = {
    'GROUP',
    'FRAME',
    'COMPONENT',
    'COMPONENT_SET',
    'INSTANCE',
    'SECTION',
}

VECTOR_KEYWORDS = [
    'bg',
    'background',
    'blob',
    'shape',
    'icon',
    'badge',
    'chip',
    'logo',
    'gradient',
    'wave',
    'skyline',
    'outline',
    'card',
    'pill',
    'circle',
    'ring',
    'spark',
    'glow',
    'highlight',
    'decor',
    'pattern',
]


def fetch_json(url: str, token: str):
    req = Request(url, headers={'X-Figma-Token': token})
    with urlopen(req) as res:
        data = res.read()
    return json.loads(data.decode('utf-8'))


def fetch_binary(url: str):
    with urlopen(url) as res:
        return res.read()


def has_image_fill(node):
    fills = node.get('fills')
    if not isinstance(fills, list):
        return False
    return any(fill.get('type') == 'IMAGE' for fill in fills if isinstance(fill, dict))


def get_size(node):
    box = node.get('absoluteBoundingBox') or {}
    width = box.get('width')
    height = box.get('height')
    if width is None or height is None:
        return {'width': None, 'height': None}
    return {'width': int(round(width)), 'height': int(round(height))}


def slugify(text: str):
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s_-]+', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    return text.strip('-')


def build_tree(node, parent_id=None, depth=0, nodes=None):
    if nodes is None:
        nodes = {}
    node_id = node.get('id')
    name = node.get('name') or ''

    child_ids = []
    for child in node.get('children') or []:
        child_id = child.get('id')
        if child_id:
            child_ids.append(child_id)
        build_tree(child, node_id, depth + 1, nodes)

    nodes[node_id] = {
        'id': node_id,
        'name': name,
        'type': node.get('type'),
        'depth': depth,
        'visible': node.get('visible', True),
        'isMask': bool(node.get('isMask')),
        'fills': node.get('fills') or [],
        'size': get_size(node),
        'children': child_ids,
        'parent': parent_id,
        'exportSettings': node.get('exportSettings') or [],
    }
    return nodes


def compute_flags(nodes):
    def dfs(node_id):
        node = nodes[node_id]
        child_has_image = False
        child_has_vector = False
        child_has_text = False

        for child_id in node['children']:
            child_flags = dfs(child_id)
            child_has_image = child_has_image or child_flags['has_image']
            child_has_vector = child_has_vector or child_flags['has_vector']
            child_has_text = child_has_text or child_flags['has_text']

        self_has_image = has_image_fill(node)
        self_has_vector = node['type'] in VECTOR_TYPES
        self_has_text = node['type'] == 'TEXT'

        node['flags'] = {
            'self_has_image': self_has_image,
            'self_has_vector': self_has_vector,
            'self_has_text': self_has_text,
            'has_image': self_has_image or child_has_image,
            'has_vector': self_has_vector or child_has_vector,
            'has_text': self_has_text or child_has_text,
        }
        return node['flags']

    root_ids = [nid for nid, n in nodes.items() if n.get('parent') is None]
    for root_id in root_ids:
        dfs(root_id)


def ancestor_ids(nodes, node_id):
    ids = []
    current = nodes[node_id].get('parent')
    while current:
        ids.append(current)
        current = nodes[current].get('parent')
    return ids


def is_vector_candidate(node, flags):
    if not node['visible']:
        return False
    if node['type'] == 'TEXT':
        return False
    if flags['has_image']:
        return False
    if not flags['has_vector']:
        return False
    if flags['has_text']:
        return False

    size = node['size']
    width = size.get('width') or 0
    height = size.get('height') or 0
    if width < 24 or height < 24:
        return False
    if width > 3000 or height > 3000:
        return False

    name = (node['name'] or '').lower()
    has_keyword = any(keyword in name for keyword in VECTOR_KEYWORDS)

    if node['type'] in VECTOR_TYPES:
        return True

    if node['type'] in CONTAINER_TYPES:
        if has_keyword:
            return True
        if max(width, height) <= 360:
            return True
    return False


def is_raster_candidate(node, flags):
    if not node['visible']:
        return False
    if not flags['self_has_image']:
        return False
    size = node['size']
    width = size.get('width') or 0
    height = size.get('height') or 0
    if width < 16 or height < 16:
        return False
    return True


def select_candidates(nodes):
    raster = []
    vector = []

    for node_id, node in nodes.items():
        flags = node.get('flags') or {}
        if is_raster_candidate(node, flags):
            raster.append(node_id)
        elif is_vector_candidate(node, flags):
            vector.append(node_id)

    vector_set = set(vector)
    filtered_vector = []
    for node_id in vector:
        ancestors = ancestor_ids(nodes, node_id)
        skip = False
        for ancestor_id in ancestors:
            if ancestor_id in vector_set:
                ancestor = nodes[ancestor_id]
                if ancestor['type'] in CONTAINER_TYPES:
                    skip = True
                    break
        if not skip:
            filtered_vector.append(node_id)

    return raster, filtered_vector


def build_asset_records(nodes, raster_ids, vector_ids, file_key, output_dir):
    records = []
    used_filenames = set()

    def filename_for(node_id, name, ext):
        base = slugify(name) or 'asset'
        short_id = node_id.replace(':', '-')
        candidate = f"{base}-{short_id}.{ext}"
        if candidate not in used_filenames:
            used_filenames.add(candidate)
            return candidate
        index = 2
        while True:
            candidate = f"{base}-{short_id}-{index}.{ext}"
            if candidate not in used_filenames:
                used_filenames.add(candidate)
                return candidate
            index += 1

    for node_id in raster_ids:
        node = nodes[node_id]
        size = node['size']
        name = node['name'] or 'Raster asset'
        filename = filename_for(node_id, name, 'png')
        records.append({
            'id': node_id,
            'name': name,
            'type': 'png',
            'filename': filename,
            'path': f"assets/{filename}",
            'size': size,
            'usage': 'Raster asset (image fill)',
            'sourceNodeId': node_id,
            'status': 'ready',
        })

    for node_id in vector_ids:
        node = nodes[node_id]
        size = node['size']
        name = node['name'] or 'Vector asset'
        filename = filename_for(node_id, name, 'svg')
        records.append({
            'id': node_id,
            'name': name,
            'type': 'svg',
            'filename': filename,
            'path': f"assets/{filename}",
            'size': size,
            'usage': 'Vector asset',
            'sourceNodeId': node_id,
            'status': 'ready',
        })

    return records


def download_assets(file_key, token, records, output_dir):
    by_format = {}
    for record in records:
        by_format.setdefault(record['type'], []).append(record)

    downloaded = set()

    for fmt, items in by_format.items():
        ids = [item['id'] for item in items]
        query = {
            'ids': ','.join(ids),
            'format': fmt,
            'scale': 1,
        }
        if fmt == 'svg':
            query['svg_include_id'] = 'true'
        url = f"https://api.figma.com/v1/images/{file_key}?{urlencode(query)}"
        data = fetch_json(url, token)
        images = data.get('images') or {}

        for record in items:
            image_url = images.get(record['id'])
            if not image_url:
                continue
            content = fetch_binary(image_url)
            output_path = os.path.join(output_dir, record['filename'])
            with open(output_path, 'wb') as f:
                f.write(content)
            downloaded.add(record['id'])

    return downloaded


def fetch_node_tree(file_key, token, node_ids):
    ids_param = ','.join(node_ids)
    url = f"https://api.figma.com/v1/files/{file_key}/nodes?{urlencode({'ids': ids_param})}"
    data = fetch_json(url, token)
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token', default=os.getenv('FIGMA_TOKEN'))
    parser.add_argument('--file', default='Izgzufe5syG3KcDR7fdPVX')
    parser.add_argument('--root', default='314:8186')
    parser.add_argument('--extra', default='3531:31387')
    parser.add_argument('--output-dir', default='assets')
    parser.add_argument('--data', default='data/assets.json')
    parser.add_argument('--scan', default='data/figma-scan.json')
    args = parser.parse_args()

    if not args.token:
        raise SystemExit('Missing FIGMA_TOKEN. Provide --token or set FIGMA_TOKEN env var.')

    root_id = args.root.replace('-', ':')
    extra_id = args.extra.replace('-', ':') if args.extra else None

    data = fetch_node_tree(args.file, args.token, [root_id])
    root = data.get('nodes', {}).get(root_id, {}).get('document')
    if not root:
        raise SystemExit('Root node not found in response.')

    nodes = build_tree(root)
    compute_flags(nodes)

    raster_ids, vector_ids = select_candidates(nodes)

    if extra_id:
        extra_data = fetch_node_tree(args.file, args.token, [extra_id])
        extra_node = extra_data.get('nodes', {}).get(extra_id, {}).get('document')
        if extra_node:
            extra_nodes = build_tree(extra_node)
            compute_flags(extra_nodes)
            if extra_id not in vector_ids:
                vector_ids.append(extra_id)
            nodes.update(extra_nodes)

    records = build_asset_records(nodes, raster_ids, vector_ids, args.file, args.output_dir)

    os.makedirs(args.output_dir, exist_ok=True)
    downloaded = download_assets(args.file, args.token, records, args.output_dir)

    records = [record for record in records if record['id'] in downloaded]

    output = {
        'fileKey': args.file,
        'rootNodeId': root_id,
        'generatedAt': datetime.utcnow().isoformat() + 'Z',
        'count': len(records),
        'assets': sorted(records, key=lambda r: r['filename']),
    }

    os.makedirs(os.path.dirname(args.data), exist_ok=True)
    with open(args.data, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    with open(args.scan, 'w', encoding='utf-8') as f:
        json.dump({
            'fileKey': args.file,
            'rootNodeId': root_id,
            'generatedAt': datetime.utcnow().isoformat() + 'Z',
            'nodes': list(nodes.values()),
        }, f, ensure_ascii=False, indent=2)

    print(f"Exported {len(records)} assets to {args.output_dir}")


if __name__ == '__main__':
    main()
