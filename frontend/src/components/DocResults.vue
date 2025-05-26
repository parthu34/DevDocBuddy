<template>
  <div>
    <p v-if="store.loading">Loading...</p>
    <div v-if="store.results" v-html="store.results"></div>
  </div>
</template>

<script setup>
import { useDocStore } from '../stores/docStore'
const store = useDocStore()
</script>
