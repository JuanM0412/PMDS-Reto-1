<script setup lang="ts">
const props = defineProps<{
  title: string
  code: string
}>()

function sanitizeFileName(name: string): string {
  return name.replace(/[^\w\s.-]/gi, '_').replace(/\s+/g, '_') || 'pseudocode'
}

function downloadPseudocode() {
  const blob = new Blob([props.code], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${sanitizeFileName(props.title)}.txt`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <div class="pseudocode-preview">
    <div class="pseudocode-header">
      <p class="pseudocode-title">{{ title }}</p>
      <button type="button" class="btn-download-code" @click="downloadPseudocode">
        Descargar TXT
      </button>
    </div>
    <pre class="pseudocode-source">{{ code }}</pre>
  </div>
</template>

<style scoped>
.pseudocode-preview {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(0, 0, 0, 0.25);
}

.pseudocode-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.pseudocode-title {
  margin: 0;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text-primary);
}

.btn-download-code {
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  border: 1px solid rgba(16, 185, 129, 0.45);
  background: rgba(16, 185, 129, 0.22);
  color: #d1fae5;
  font-size: 0.6875rem;
  cursor: pointer;
}

.btn-download-code:hover {
  background: rgba(16, 185, 129, 0.32);
}

.pseudocode-source {
  margin: 0;
  padding: 0.6rem;
  border-radius: 0.375rem;
  background: rgba(255, 255, 255, 0.06);
  font-size: 0.6875rem;
  line-height: 1.35;
  color: #cbd5e1;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 360px;
  overflow: auto;
}
</style>
