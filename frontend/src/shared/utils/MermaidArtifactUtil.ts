export interface MermaidBlockInterface {
  key: string
  title: string
  code: string
}

export interface PseudocodeBlockInterface {
  key: string
  title: string
  code: string
}

const MERMAID_PREFIXES = [
  'graph ',
  'flowchart',
  'sequenceDiagram',
  'classDiagram',
  'stateDiagram',
  'stateDiagram-v2',
  'erDiagram',
  'journey',
  'gantt',
  'pie',
  'mindmap',
  'timeline',
  'quadrantChart',
  'requirementDiagram',
  'gitGraph',
  'C4Context',
  'C4Container',
  'C4Component',
  'C4Dynamic',
  'C4Deployment',
] as const

const PSEUDOCODE_MARKERS = [
  'procedure ',
  'function ',
  'entradas',
  'salidas',
  'inputs',
  'outputs',
  'pasos',
  'algoritmo',
] as const

function stripCodeFence(value: string): string {
  const text = value.trim()
  if (!text.startsWith('```')) return text

  const lines = text.split('\n')
  if (!lines.length) return text

  const firstLineRaw = lines.length > 0 ? lines[0] : undefined
  const firstLine = firstLineRaw?.trim().toLowerCase()
  if (!firstLine) return text
  if (firstLine !== '```' && firstLine !== '```mermaid') return text

  const contentLines = [...lines.slice(1)]
  const lastLineRaw = contentLines.length > 0 ? contentLines[contentLines.length - 1] : undefined
  const lastLine = lastLineRaw?.trim()
  if (lastLine === '```') {
    contentLines.pop()
  }
  return contentLines.join('\n').trim()
}

export function normalizeMermaidCode(value: string): string {
  let text = value
    .trim()
    .replace(/\\r\\n/g, '\n')
    .replace(/\\n/g, '\n')

  text = stripCodeFence(text)
  if (text.toLowerCase().startsWith('mermaid\n')) {
    text = text.slice('mermaid\n'.length)
  }

  return text
    .split('\n')
    .map((line) => line.replace(/\t/g, '    ').replace(/\s+$/g, ''))
    .join('\n')
    .trim()
}

export function normalizePseudocodeCode(value: string): string {
  const text = stripCodeFence(
    value
      .trim()
      .replace(/\\r\\n/g, '\n')
      .replace(/\\n/g, '\n')
  )

  return text
    .split('\n')
    .map((line) => line.replace(/\t/g, '    ').replace(/\s+$/g, ''))
    .join('\n')
    .trim()
}

export function isLikelyMermaid(value: string): boolean {
  const text = normalizeMermaidCode(value)
  if (!text) return false
  return MERMAID_PREFIXES.some((prefix) => text.startsWith(prefix))
}

export function isLikelyPseudocode(value: string): boolean {
  const text = normalizePseudocodeCode(value)
  if (!text) return false
  if (isLikelyMermaid(text)) return false
  const lowered = text.toLowerCase()
  return PSEUDOCODE_MARKERS.some((marker) => lowered.includes(marker))
}

function humanizeKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

export function extractMermaidBlocks(payload: unknown): MermaidBlockInterface[] {
  const blocks: MermaidBlockInterface[] = []
  const seen = new Set<string>()

  function walk(value: unknown, path: string[]) {
    if (typeof value === 'string') {
      const key = path[path.length - 1] ?? 'diagram'
      const hinted = key.toLowerCase().includes('mermaid') || key.toLowerCase().includes('diagram')
      const normalized = normalizeMermaidCode(value)
      if (!normalized) return
      if (!hinted && !isLikelyMermaid(normalized)) return
      if (seen.has(normalized)) return
      seen.add(normalized)
      blocks.push({
        key: path.join('.'),
        title: humanizeKey(key),
        code: normalized,
      })
      return
    }

    if (Array.isArray(value)) {
      value.forEach((item, index) => walk(item, [...path, String(index)]))
      return
    }

    if (value && typeof value === 'object') {
      Object.entries(value as Record<string, unknown>).forEach(([k, v]) => walk(v, [...path, k]))
    }
  }

  walk(payload, [])
  return blocks
}

export function extractPseudocodeBlocks(payload: unknown): PseudocodeBlockInterface[] {
  const blocks: PseudocodeBlockInterface[] = []
  const seen = new Set<string>()

  function walk(value: unknown, path: string[]) {
    if (typeof value === 'string') {
      const key = path[path.length - 1] ?? 'pseudocode'
      const keyLower = key.toLowerCase()
      const hinted = keyLower.includes('pseudocode') || keyLower.includes('pseudo')
      const normalized = normalizePseudocodeCode(value)
      if (!normalized) return
      if (isLikelyMermaid(normalized)) return
      if (!hinted && !isLikelyPseudocode(normalized)) return
      if (seen.has(normalized)) return
      seen.add(normalized)
      blocks.push({
        key: path.join('.'),
        title: humanizeKey(key),
        code: normalized,
      })
      return
    }

    if (Array.isArray(value)) {
      value.forEach((item, index) => walk(item, [...path, String(index)]))
      return
    }

    if (value && typeof value === 'object') {
      Object.entries(value as Record<string, unknown>).forEach(([k, v]) => walk(v, [...path, k]))
    }
  }

  walk(payload, [])
  return blocks
}

export function toArtifactPreviewText(payload: unknown): string {
  if (typeof payload === 'string') {
    const text = payload.trim()
    if (!text) return ''
    try {
      return JSON.stringify(JSON.parse(text), null, 2)
    } catch {
      return payload
    }
  }

  if (payload === undefined) {
    return ''
  }

  try {
    return JSON.stringify(payload, null, 2)
  } catch {
    return String(payload)
  }
}
