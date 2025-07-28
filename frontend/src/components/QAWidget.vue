<template>
  <section class="qa-widget">
    <h2>Ask Questions</h2>

    <div class="chat-window" ref="chatWindow">
      <div v-if="messages.length === 0" class="empty-state">
        <p>Start by asking a question about your uploaded documentation.</p>
      </div>

      <div
        v-for="(msg, index) in messages"
        :key="index"
        :class="['message', msg.from]"
      >
        <strong v-if="msg.from === 'user'">You:</strong>
        <strong v-else>AI:</strong>
        <span>{{ msg.text }}</span>

        <!-- Sources collapsible section -->
        <div v-if="msg.sources && msg.sources.length" class="sources">
          <button @click="toggleSources(index)" class="toggle-sources-btn">
            {{ msg.showSources ? 'Hide Sources' : 'Show Sources' }}
          </button>
          <ul v-show="msg.showSources">
            <li v-for="(src, i) in msg.sources" :key="i">{{ src }}</li>
          </ul>
        </div>
      </div>

      <div v-if="loading" class="message ai loading">
        <span class="dot"></span><span class="dot"></span><span class="dot"></span>
      </div>
    </div>

    <form @submit.prevent="askQuestion" class="qa-form">
      <input v-model="question" type="text" placeholder="Ask a question..." />
      <button :disabled="loading || !question.trim()" type="submit">Ask</button>
    </form>
  </section>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import axios from 'axios'

const question = ref('')
const messages = ref([]) // messages now can have sources and showSources props
const loading = ref(false)
const chatWindow = ref(null)

function toggleSources(index) {
  messages.value[index].showSources = !messages.value[index].showSources
}

async function askQuestion() {
  if (!question.value.trim()) return

  messages.value.push({ from: 'user', text: question.value })
  const asked = question.value
  question.value = ''
  loading.value = true

  try {
    const formData = new FormData()
    formData.append('question', asked)

    const res = await axios.post('/api/ask', formData)
    const answer = res.data.answer || 'No answer received.'
    const sources = res.data.sources || []

    messages.value.push({
      from: 'ai',
      text: answer,
      sources: sources,
      showSources: false, // collapsed by default
    })
  } catch (err) {
    messages.value.push({ from: 'ai', text: 'Error: Failed to fetch answer.' })
  } finally {
    loading.value = false
  }
}

watch(messages, async () => {
  await nextTick()
  if (chatWindow.value) {
    chatWindow.value.scrollTop = chatWindow.value.scrollHeight
  }
})
</script>

<style scoped>
.qa-widget {
  margin-top: 2rem;
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 8px;
}

.chat-window {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #ccc;
  padding: 0.75rem;
  margin-bottom: 1rem;
  border-radius: 4px;
  background: #f9f9f9;
}

.message {
  margin-bottom: 0.5rem;
}

.message.user {
  color: #333;
}

.message.ai {
  color: #2c7;
}

.sources {
  margin-top: 0.5rem;
  font-size: 0.9rem;
  background: #eef;
  padding: 0.5rem;
  border-radius: 6px;
}

.toggle-sources-btn {
  background: none;
  border: none;
  color: #007bff;
  cursor: pointer;
  text-decoration: underline;
  padding: 0;
  margin-bottom: 0.3rem;
  font-size: 0.9rem;
}

.sources ul {
  padding-left: 1.2rem;
  margin: 0;
}

.qa-form {
  display: flex;
  gap: 0.5rem;
}

.qa-form input {
  flex-grow: 1;
  padding: 0.5rem;
}

.qa-form button {
  padding: 0.5rem 1rem;
}

.message.ai.loading {
  display: flex;
  gap: 0.3rem;
  align-items: center;
}

.dot {
  width: 8px;
  height: 8px;
  background: #42b983;
  border-radius: 50%;
  animation: blink 1s infinite alternate;
}

.dot:nth-child(2) {
  animation-delay: 0.2s;
}

.dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes blink {
  0% {
    opacity: 0.3;
  }
  100% {
    opacity: 1;
  }
}

.empty-state {
  text-align: center;
  color: #888;
  font-style: italic;
  margin-top: 2rem;
}
</style>
