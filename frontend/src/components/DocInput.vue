<template>
  <div class="input-area">
    <!-- Summarize & Index typed text -->
    <div class="row">
      <input
        v-model="store.query"
        placeholder="Paste text to summarize & index for Q&A"
        class="input"
      />
      <button @click="store.fetchSummary" :disabled="store.loading || !store.query.trim()">
        {{ store.loading ? 'Working…' : 'Summarize & Index' }}
      </button>
    </div>
    <small class="hint">This replaces the current index with the text above.</small>

    <!-- Load sample doc (frictionless demo) -->
    <div class="row">
      <button @click="loadSample" :disabled="store.loading">Load Sample Doc</button>
      <small class="hint">Instant demo without uploading anything.</small>
    </div>

    <!-- Upload new document (rebuild index) -->
    <div class="row">
      <input type="file" @change="onUpload" />
      <small class="hint">Replaces current index with the selected file.</small>
    </div>

    <!-- Add document (incremental) -->
    <div class="row">
      <input type="file" @change="onAddDoc" />
      <small class="hint">Adds the selected file to the existing index.</small>
    </div>

    <!-- GitHub URL -->
    <div class="row">
      <input v-model="store.url" placeholder="Paste GitHub Doc URL" class="input" />
      <button @click="uploadFromURL" :disabled="store.loading || !store.url.trim()">
        {{ store.loading ? 'Uploading…' : 'Upload URL' }}
      </button>
    </div>

    <!-- Index controls -->
    <div class="row">
      <button @click="store.resetIndex" :disabled="store.loading">Reset Index</button>
      <span class="meta" v-if="store.lastFilename">Last: {{ store.lastFilename }}</span>
    </div>
  </div>
</template>

<script setup>
import { useDocStore } from '@/stores/docStore'
import { track } from '@/analytics'
const store = useDocStore()

const SAMPLE = `# DevDocBuddy Sample
DevDocBuddy summarizes docs and answers questions with sources.
- Upload PDF/Markdown/GitHub URL
- Ask questions in plain English
- See the exact chunks used as citations
`

async function loadSample() {
  store.query = SAMPLE
  track('sample_loaded')
  await store.fetchSummary()
}

async function onUpload(e) {
  const file = e.target.files?.[0]
  if (file) await store.uploadFile(file)
  e.target.value = ''
}
async function onAddDoc(e) {
  const file = e.target.files?.[0]
  if (file) await store.addDoc(file)
  e.target.value = ''
}
async function uploadFromURL() {
  if (store.url) await store.uploadFromURL(store.url)
}
</script>

<style scoped>
.input-area { display: grid; gap: .6rem; margin: 1rem 0; }
.row { display: grid; grid-template-columns: 1fr auto; gap: .5rem; align-items: center; }
.input { padding: .6rem .7rem; border: 1px solid var(--border); border-radius: 8px; }
.hint { color: var(--muted); margin-top: -.3rem; }
.meta { opacity: .75; font-size: .9rem; padding-left: .5rem; }
</style>
