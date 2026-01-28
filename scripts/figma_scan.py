#!/usr/bin/env python3
import argparse
import json
import os
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from datetime import datetime

VECTOR_TYPES = {
    'VECTOR',
    'BOOLEAN_OPERATION',
    'STAR',
    'POLYGON',
    'ELLIPSE',
    'RECTANGLE',
    'LINE',
}


def fetch_json(url: str, token: str):
    req = Request(url, headers={'X-Figma-Token': token})
    with urlopen(req) as res:
        data = res.read()
    return json.loads(data.decode('utf-8'))


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


def traverse(node, parent_path, depth, nodes):
    name = node.get('name') or ''
    path_parts = parent_path + [name]
    node_id = node.get('id')

    child_has_image = False
    child_has_vector = False
    child_has_text = False

    for child in node.get('children') or []:
        summary = traverse(child, path_parts, depth + 1, nodes)
        child_has_image = child_has_image or summary['hasImageFill']
        child_has_vector = child_has_vector or summary['hasVector']
        child_has_text = child_has_text or summary['hasText']

    self_has_image = has_image_fill(node)
    self_has_vector = node.get('type') in VECTOR_TYPES
    self_has_text = node.get('type') == 'TEXT'

    summary = {
        'id': node_id,
        'name': name,
        'type': node.get('type'),
        'depth': depth,
        'visible': node.get('visible', True),
        'isMask': bool(node.get('isMask')),
        'hasImageFill': self_has_image or child_has_image,
        'hasVector': self_has_vector or child_has_vector,
        'hasText': self_has_text or child_has_text,
        'exportSettings': node.get('exportSettings') or [],
        'size': get_size(node),
        'path': ' / '.join(path_parts),
        'selfHasImage': self_has_image,
        'selfHasVector': self_has_vector,
        'selfHasText': self_has_text,
        'childrenCount': len(node.get('children') or []),
        'parentPath': ' / '.join(parent_path) if parent_path else None,
    }

    nodes.append(summary)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token', default=os.getenv('FIGMA_TOKEN'))
    parser.add_argument('--file', default='Izgzufe5syG3KcDR7fdPVX')
    parser.add_argument('--node', default='314:8186')
    parser.add_argument('--output', default='data/figma-scan.json')
    args = parser.parse_args()

    if not args.token:
        raise SystemExit('Missing FIGMA_TOKEN. Provide --token or set FIGMA_TOKEN env var.')

    node_id = args.node.replace('-', ':')
    query = urlencode({'ids': node_id})
    url = f'https://api.figma.com/v1/files/{args.file}/nodes?{query}'
    data = fetch_json(url, args.token)
    root = data.get('nodes', {}).get(node_id, {}).get('document')
    if not root:
        raise SystemExit('Could not find node in response.')

    nodes = []
    traverse(root, [], 0, nodes)

    output_data = {
        'fileKey': args.file,
        'rootNodeId': node_id,
        'generatedAt': datetime.utcnow().isoformat() + 'Z',
        'nodeCount': len(nodes),
        'nodes': nodes,
    }

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f'Saved scan to {args.output} (nodes: {len(nodes)})')


if __name__ == '__main__':
    main()
