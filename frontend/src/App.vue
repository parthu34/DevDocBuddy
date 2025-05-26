<template>
  <div id="app" class="app-container">
    <header>
      <nav>
        <router-link to="/" class="nav-link" exact-active-class="active">Home</router-link>
        <router-link to="/docs" class="nav-link" exact-active-class="active">Docs</router-link>
      </nav>
    </header>

    <main>
      <router-view />
    </main>

    <footer>
      <small>© 2025 DevDocBuddy</small>
    </footer>
  </div>
</template>

<script setup>
// No extra script logic here as router & pinia are initialized in main.js
</script>

<style scoped>
.app-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

header {
  margin-bottom: 1.5rem;
}

nav {
  display: flex;
  gap: 1.5rem;
  font-weight: bold;
}

.nav-link {
  text-decoration: none;
  color: #555;
}

.nav-link.active {
  color: #42b983; /* Vue green */
  border-bottom: 2px solid #42b983;
  padding-bottom: 2px;
}

main {
  flex-grow: 1;
}

footer {
  text-align: center;
  margin-top: 3rem;
  color: #888;
  font-size: 0.9rem;
}
</style>
