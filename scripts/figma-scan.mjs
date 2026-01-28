#!/usr/bin/env node
import fs from 'node:fs/promises'
import path from 'node:path'
import process from 'node:process'

function getArgValue(flag) {
  const index = process.argv.indexOf(flag)
  if (index === -1) return null
  return process.argv[index + 1] || null
}

const token = getArgValue('--token') || process.env.FIGMA_TOKEN
const fileKey = getArgValue('--file') || 'Izgzufe5syG3KcDR7fdPVX'
const nodeId = (getArgValue('--node') || '314:8186').replace(/-/g, ':')
const output = getArgValue('--output') || path.resolve('data/figma-scan.json')

if (!token) {
  console.error('Missing FIGMA_TOKEN. Provide --token or set FIGMA_TOKEN env var.')
  process.exit(1)
}

async function fetchJson(url) {
  const res = await fetch(url, {
    headers: { 'X-Figma-Token': token },
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`Figma API error ${res.status}: ${body}`)
  }
  return res.json()
}

const url = new URL(`https://api.figma.com/v1/nodes/${fileKey}`)
url.searchParams.set('ids', nodeId)

const data = await fetchJson(url.toString())
const root = data?.nodes?.[nodeId]?.document
if (!root) {
  console.error('Could not find node in response.')
  process.exit(1)
}

const vectorTypes = new Set([
  'VECTOR',
  'BOOLEAN_OPERATION',
  'STAR',
  'POLYGON',
  'ELLIPSE',
  'RECTANGLE',
  'LINE',
])

function hasImageFill(node) {
  if (!Array.isArray(node.fills)) return false
  return node.fills.some((fill) => fill?.type === 'IMAGE')
}

function hasVectorSelf(node) {
  return vectorTypes.has(node.type)
}

function hasTextSelf(node) {
  return node.type === 'TEXT'
}

function getSize(node) {
  const box = node.absoluteBoundingBox
  if (!box) return { width: null, height: null }
  return { width: Math.round(box.width), height: Math.round(box.height) }
}

const nodes = []

function traverse(node, parentPath = [], depth = 0) {
  const visible = node.visible !== false
  const name = node.name || ''
  const pathParts = [...parentPath, name]
  const id = node.id

  let childHasImage = false
  let childHasVector = false
  let childHasText = false

  if (Array.isArray(node.children)) {
    for (const child of node.children) {
      const summary = traverse(child, pathParts, depth + 1)
      childHasImage = childHasImage || summary.hasImageFill
      childHasVector = childHasVector || summary.hasVector
      childHasText = childHasText || summary.hasText
    }
  }

  const selfHasImage = hasImageFill(node)
  const selfHasVector = hasVectorSelf(node)
  const selfHasText = hasTextSelf(node)

  const summary = {
    id,
    name,
    type: node.type,
    depth,
    visible,
    isMask: Boolean(node.isMask),
    hasImageFill: selfHasImage || childHasImage,
    hasVector: selfHasVector || childHasVector,
    hasText: selfHasText || childHasText,
    exportSettings: Array.isArray(node.exportSettings) ? node.exportSettings : [],
    size: getSize(node),
    path: pathParts.join(' / '),
    selfHasImage,
    selfHasVector,
    selfHasText,
    childrenCount: Array.isArray(node.children) ? node.children.length : 0,
  }

  nodes.push(summary)
  return summary
}

traverse(root, [], 0)

const outputData = {
  fileKey,
  rootNodeId: nodeId,
  generatedAt: new Date().toISOString(),
  nodeCount: nodes.length,
  nodes,
}

await fs.mkdir(path.dirname(output), { recursive: true })
await fs.writeFile(output, JSON.stringify(outputData, null, 2))

console.log(`Saved scan to ${output} (nodes: ${nodes.length})`)
