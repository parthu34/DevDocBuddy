<template>
  <div class="input-area">
    <!-- Existing Text Input -->
    <input
      v-model="store.query"
      placeholder="Type or paste your doc content"
      class="input"
    />
    <button @click="store.fetchSummary" :disabled="store.loading">
      {{ store.loading ? 'Fetching...' : 'Fetch' }}
    </button>

    <!-- File Upload -->
    <input type="file" @change="handleFileUpload" />

    <!-- GitHub URL -->
    <input
      v-model="urlInput"
      placeholder="Paste GitHub Doc URL"
      class="input"
    />
    <button @click="uploadFromURL" :disabled="store.loading">
      {{ store.loading ? 'Uploading...' : 'Upload URL' }}
    </button>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useDocStore } from '../stores/docStore'

const store = useDocStore()
const urlInput = ref('')

const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (file) {
    await store.uploadFile(file)
  }
}

const uploadFromURL = async () => {
  if (urlInput.value) {
    await store.uploadFromURL(urlInput.value)
  }
}
</script>

<style scoped>
.input-area {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin: 1rem 0;
}
.input {
  padding: 0.5rem;
}
</style>
