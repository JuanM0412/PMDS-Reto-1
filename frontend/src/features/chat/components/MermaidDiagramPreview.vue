<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import mermaid from 'mermaid'

const props = defineProps<{
  title: string
  code: string
}>()

const diagramHost = ref<HTMLElement | null>(null)
const renderError = ref('')

mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  securityLevel: 'loose',
})

async function renderDiagram() {
  if (!diagramHost.value) return
  const source = props.code.trim()
  if (!source) {
    diagramHost.value.innerHTML = ''
    renderError.value = ''
    return
  }

  try {
    renderError.value = ''
    const renderId = `mermaid-${Math.random().toString(36).slice(2)}`
    const { svg } = await mermaid.render(renderId, source)
    if (!diagramHost.value) return
    diagramHost.value.innerHTML = svg
  } catch {
    if (diagramHost.value) diagramHost.value.innerHTML = ''
    renderError.value = 'No se pudo renderizar este diagrama Mermaid.'
  }
}

onMounted(renderDiagram)
watch(() => props.code, renderDiagram)
</script>

<template>
  <div class="mermaid-preview">
    <p class="mermaid-title">{{ title }}</p>
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
