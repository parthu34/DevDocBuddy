<template>
  <div class="results-area">
    <div v-if="store.loading">⏳ Loading summary...</div>
    <div v-else-if="store.error" class="error">❌ {{ store.error }}</div>
    <div v-else-if="store.results" v-html="store.results"></div>
    <div v-else>📭 No summary available</div>
  </div>
</template>

<script setup>
import { useDocStore } from '@/stores/docStore'
const store = useDocStore()
</script>

<style scoped>
.results-area {
  border-top: 1px solid #ddd;
  padding-top: 1rem;
  margin-top: 1rem;
  text-align: left;
}
.error { color: red; }
</style>
