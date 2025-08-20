<template>
  <div class="qa-widget">
    <h3>Ask AI about your docs</h3>

    <div class="chat-window" ref="chatWindow">
      <div v-if="!messages.length" class="empty">
        <template v-if="!store.hasIndex">
          <strong>Upload a PDF/URL or paste text first.</strong>
          <div style="margin-top:6px;opacity:.85">Q&A unlocks after indexing.</div>
        </template>
        <template v-else>
          Start by asking about your uploaded docs. Examples:
          <ul>
            <li>Which are Python data types?</li>
            <li>What is a variable?</li>
            <li>Show the rules for variable names.</li>
          </ul>
        </template>
      </div>

      <div
        v-for="(msg, index) in messages"
        :key="index"
        :class="['message', msg.from]"
      >
        <div class="who">{{ msg.from === 'user' ? 'You' : 'AI' }}</div>
        <pre class="bubble answer">{{ msg.text }}</pre>

        <div v-if="msg.sources?.length" class="sources">
          <button class="toggle" @click="toggleSources(index)">
            {{ msg.showSources ? 'Hide Sources' : 'Show Sources' }}
          </button>
          <ul v-show="msg.showSources">
            <li v-for="(s, i) in msg.sources" :key="i">
              <span class="title">{{ sourceTitle(s) }}</span>
              <span class="meta">
                <template v-if="s.page">— p. {{ s.page }}</template>
                <template v-if="isNumber(s.similarity)">, sim {{ s.similarity.toFixed(3) }}</template>
              </span>
            </li>
          </ul>
        </div>
      </div>

      <div v-if="loading" class="loading">Thinking…</div>
    </div>

    <form @submit.prevent="sendQuestion" class="ask">
      <input v-model="question" placeholder="Type your question here…" :disabled="!store.hasIndex" />
      <button :disabled="loading || !question.trim() || !store.hasIndex">Ask</button>
      <button type="button" class="secondary" :disabled="loading || !messages.length" @click="clearChat">
        Clear
      </button>
    </form>

    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { askQA } from '@/api'
import { useDocStore } from '@/stores/docStore'

const store = useDocStore()
const question = ref('')
const messages = ref([])
const loading = ref(false)
const error = ref(null)
const chatWindow = ref(null)

onMounted(() => {
  // On first load, learn whether an index already exists (e.g., after refresh)
  store.initIndexStatus()
})

function isNumber(x) {
  return typeof x === 'number' && !Number.isNaN(x)
}
function sourceTitle(s) {
  if (!s) return 'Document'
  if (typeof s === 'string') return s
  return s.title || 'Document'
}
function toggleSources(index) {
  messages.value[index].showSources = !messages.value[index].showSources
}
function clearChat() {
  messages.value = []
}

async function sendQuestion() {
  if (!store.hasIndex) {
    error.value = 'Please upload a PDF/URL or paste text before asking questions.'
    return
  }
  if (!question.value.trim()) return
  error.value = null
  loading.value = true

  messages.value.push({ from: 'user', text: question.value })

  try {
    const data = await askQA({ question: question.value })
    const answer = (data.answer || 'No answer received.').trim()
    const raw = Array.isArray(data.sources) ? data.sources : []
    const normalized = raw.map((s) => {
      if (typeof s === 'string') return { title: s }
      if (s.text && !s.title) s.title = 'Document'
      return {
        title: s.title || s.source_title || 'Document',
        page: s.page ?? null,
        similarity: typeof s.similarity === 'number' ? s.similarity : null
      }
    })
    messages.value.push({ from: 'ai', text: answer, sources: normalized, showSources: false })
  } catch (err) {
    // Show the exact backend message (400/413/429/503)
    error.value = err?.message || 'Failed to get answer.'
  } finally {
    loading.value = false
    question.value = ''
    await nextTick()
    if (chatWindow.value) chatWindow.value.scrollTop = chatWindow.value.scrollHeight
  }
}
</script>

<style scoped>
.qa-widget { max-width: 760px; margin: 1rem auto; border: 1px solid var(--border); border-radius: 12px; padding: 1rem; background: var(--panel-bg); color: var(--panel-text); }
.chat-window { height: 360px; overflow-y: auto; border: 1px solid var(--border); padding: .75rem; margin-bottom: 1rem; background: var(--panel-bg); color: var(--panel-text); border-radius: 8px; }
.empty { opacity: .9; font-size: .95rem; }
.message { margin-bottom: 1rem; display: grid; gap: .25rem; }
.message .who { font-weight: 600; font-size: .9rem; opacity: .85; }
.message.user .who { color: #3b82f6; }
.message.ai .who { color: #16a34a; }
.bubble.answer { white-space: pre-wrap; text-align: left; padding: .6rem .8rem; border-radius: 8px; background: #ffffff; color: #111827; border: 1px solid var(--border); }
@media (prefers-color-scheme: dark) { .bubble.answer { background: #0f131a; color: #e5e7eb; } }
.sources { margin-top: .4rem; font-size: .9rem; background: #eef6ff; color: #0b3a6f; padding: .5rem .6rem; border-radius: 6px; text-align: left; border: 1px solid #dbeafe; }
@media (prefers-color-scheme: dark) { .sources { background: #0b1f33; color: #c9e5ff; border-color: #173a5c; } }
.toggle { background: none; border: none; color: #2563eb; cursor: pointer; text-decoration: underline; padding: 0; margin-bottom: .25rem; font-size: .9rem; }
.sources ul { margin: 0; padding-left: 1.2rem; }
.ask { display: grid; grid-template-columns: 1fr auto auto; gap: .5rem; }
.ask input { padding: .6rem .7rem; }
.ask button { padding: .6rem 1rem; border-radius: 8px; }
.ask .secondary { background: var(--panel-bg); }
.loading { text-align: center; opacity: .8; }
.error { color: #ef4444; margin-top: .5rem; }
</style>
