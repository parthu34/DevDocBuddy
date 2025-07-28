<template>
  <section class="home">
    <header class="intro">
      <h1>Welcome to DevDocBuddy</h1>
      <p class="tagline">Summarize docs, ask questions, and explore API insights — all in one place.</p>
    </header>

    <div class="section">
      <h2>Upload Documentation</h2>
      <DocInput />
      <DocResults />
    </div>

    <div class="section">
      <h2>Ask Questions</h2>
      <QAWidget />
    </div>
  </section>
</template>

<script setup>
import DocInput from '../components/DocInput.vue'
import DocResults from '../components/DocResults.vue'
import QAWidget from '../components/QAWidget.vue'
</script>

<style scoped>
.home {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.intro {
  text-align: center;
}

.intro h1 {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.tagline {
  font-size: 1.1rem;
  color: #666;
}

.section {
  background: #fff;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}
</style>
