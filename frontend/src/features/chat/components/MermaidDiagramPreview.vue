<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import mermaid from 'mermaid'

const props = defineProps<{
  title: string
  code: string
}>()

const diagramHost = ref<HTMLElement | null>(null)
const renderError = ref('')
const renderedSvg = ref('')

mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  securityLevel: 'loose',
  suppressErrorRendering: true, // evita que Mermaid inyecte el mensaje "Syntax error in text" en el DOM
})

async function renderDiagram() {
  if (!diagramHost.value) return
  const source = props.code.trim()
  if (!source) {
    diagramHost.value.innerHTML = ''
    renderError.value = ''
    renderedSvg.value = ''
    return
  }

  try {
    renderError.value = ''
    const renderId = `mermaid-${Math.random().toString(36).slice(2)}`
    const { svg } = await mermaid.render(renderId, source)
    if (!diagramHost.value) return
    renderedSvg.value = svg
    diagramHost.value.innerHTML = svg
  } catch (_err) {
    if (diagramHost.value) diagramHost.value.innerHTML = ''
    document.querySelectorAll('.mermaid-error-icon, [data-mermaid-error]').forEach((el) => el.remove())
    renderError.value = 'No se pudo renderizar este diagrama Mermaid (revisa la sintaxis del código).'
    renderedSvg.value = ''
  }
}

function sanitizeFileName(name: string): string {
  return name.replace(/[^\w\s.-]/gi, '_').replace(/\s+/g, '_') || 'mermaid_diagram'
}

function downloadSvg() {
  if (!renderedSvg.value) return
  const blob = new Blob([renderedSvg.value], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${sanitizeFileName(props.title)}.svg`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(renderDiagram)
watch(() => props.code, renderDiagram)
</script>

<template>
  <div class="mermaid-preview">
    <div class="mermaid-header">
      <p class="mermaid-title">{{ title }}</p>
      <button
        v-if="!renderError && renderedSvg"
        type="button"
        class="btn-download-svg"
        @click="downloadSvg"
      >
        Descargar SVG
      </button>
    </div>
    <div v-if="renderError" class="mermaid-error">{{ renderError }}</div>
    <div v-else ref="diagramHost" class="mermaid-host" />
    <pre class="mermaid-source">{{ code }}</pre>
  </div>
</template>

<style scoped>
.mermaid-preview {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(0, 0, 0, 0.25);
}

.mermaid-title {
  margin: 0;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text-primary);
}

.mermaid-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.btn-download-svg {
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  border: 1px solid rgba(59, 130, 246, 0.45);
  background: rgba(59, 130, 246, 0.2);
  color: #dbeafe;
  font-size: 0.6875rem;
  cursor: pointer;
}

.btn-download-svg:hover {
  background: rgba(59, 130, 246, 0.3);
}

.mermaid-error {
  margin: 0;
  font-size: 0.75rem;
  color: #fca5a5;
}

.mermaid-host {
  overflow-x: auto;
}

.mermaid-host :deep(svg) {
  max-width: 100%;
  height: auto;
}

.mermaid-source {
  margin: 0;
  padding: 0.6rem;
  border-radius: 0.375rem;
  background: rgba(255, 255, 255, 0.06);
  font-size: 0.6875rem;
  line-height: 1.35;
  color: #cbd5e1;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
