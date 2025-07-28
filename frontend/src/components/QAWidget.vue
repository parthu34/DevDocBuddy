<template>
  <div class="qa-widget">
    <h3>Ask AI about your docs</h3>

    <div class="chat-window" ref="chatWindow">
      <div
        v-for="(msg, index) in messages"
        :key="index"
        :class="['message', msg.from]"
      >
        <strong>{{ msg.from === 'user' ? 'You' : 'AI' }}:</strong>
        <p>{{ msg.text }}</p>

        <!-- Collapsible sources -->
        <div v-if="msg.sources && msg.sources.length" class="sources">
          <button 
            @click="toggleSources(index)"
            class="toggle-sources-btn"
          >
            {{ msg.showSources ? 'Hide Sources' : 'Show Sources' }}
          </button>
          <ul v-show="msg.showSources">
            <li v-for="(src, i) in msg.sources" :key="i">{{ src }}</li>
          </ul>
        </div>
      </div>
    </div>

    <form @submit.prevent="sendQuestion">
      <input v-model="question" placeholder="Type your question here..." />
      <button :disabled="loading || !question.trim()">Ask</button>
    </form>

    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import axios from 'axios'

const question = ref('')
const messages = ref([]) // {from, text, sources?, showSources?}
const loading = ref(false)
const error = ref(null)
const chatWindow = ref(null)

function toggleSources(index) {
  messages.value[index].showSources = !messages.value[index].showSources
}

async function sendQuestion() {
  if (!question.value.trim()) return
  error.value = null
  loading.value = true

  // Add user message
  messages.value.push({ from: 'user', text: question.value })

  try {
    const formData = new FormData()
    formData.append('question', question.value)

    const res = await axios.post('http://localhost:8000/api/ask', formData)
    const answer = res.data.answer || 'No answer received.'
    const sources = res.data.sources || []

    messages.value.push({
      from: 'ai',
      text: answer,
      sources: sources,
      showSources: false // default collapsed
    })
  } catch (err) {
    error.value = 'Failed to get answer. Please try again.'
  } finally {
    loading.value = false
    question.value = ''

    // Scroll chat window to bottom
    await nextTick()
    if (chatWindow.value) {
      chatWindow.value.scrollTop = chatWindow.value.scrollHeight
    }
  }
}
</script>

<style scoped>
.qa-widget {
  max-width: 600px;
  margin: 1rem auto;
  border: 1px solid #ccc;
  border-radius: 8px;
  padding: 1rem;
}
.chat-window {
  height: 300px;
  overflow-y: auto;
  border: 1px solid #ddd;
  padding: 0.5rem;
  margin-bottom: 1rem;
  background: #f9f9f9;
}
.message {
  margin-bottom: 1rem;
}
.message.user {
  text-align: right;
  color: #007bff;
}
.message.ai {
  text-align: left;
  color: #333;
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
.error {
  color: red;
  margin-top: 0.5rem;
}
form {
  display: flex;
  gap: 0.5rem;
}
input {
  flex-grow: 1;
  padding: 0.5rem;
}
button {
  padding: 0.5rem 1rem;
}
button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
