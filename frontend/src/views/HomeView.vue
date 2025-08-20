<template>
  <section>
    <h1>Welcome to DevDocBuddy</h1>
    <DocInput />
    <DocResults />
    <QAWidget />
  </section>
</template>

<script setup>
import { onMounted } from 'vue'
import { useDocStore } from '@/stores/docStore'
import DocInput from '../components/DocInput.vue'
import DocResults from '../components/DocResults.vue'
import QAWidget from '../components/QAWidget.vue'

const store = useDocStore()
onMounted(() => store.initIndexStatus())
</script>
