<template>
  <div>
    <input v-model="store.query" placeholder="Paste doc URL or text here" />
    <button @click="store.fetchSummary" :disabled="store.loading">Summarize</button>
    <p v-if="store.error" class="error">{{ store.error }}</p>
  </div>
</template>

<script setup>
import { useDocStore } from '../stores/docStore'
const store = useDocStore()
</script>

<style scoped>
.error {
  color: red;
}
</style>
