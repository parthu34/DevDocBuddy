<template>
  <div class="input-area">
    <input
      v-model="store.query"
      placeholder="Type or paste your doc content"
      class="input"
    />
    <button @click="store.fetchSummary" :disabled="store.loading">
      {{ store.loading ? 'Fetching...' : 'Fetch' }}
    </button>
  </div>
</template>

<script setup>
import { useDocStore } from '../stores/docStore'
const store = useDocStore()
</script>

<style scoped>
.input-area {
  display: flex;
  gap: 1rem;
  margin: 1rem 0;
}
.input {
  flex-grow: 1;
  padding: 0.5rem;
}
</style>
