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
// No changes needed here
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
  background-color: #f9f9f9; /* Soft background */
}

header {
  margin-bottom: 1.5rem;
  border-bottom: 1px solid #ddd;
  padding-bottom: 0.5rem;
}

nav {
  display: flex;
  gap: 1.5rem;
  font-weight: bold;
}

.nav-link {
  text-decoration: none;
  color: #333;
  padding-bottom: 2px;
  transition: all 0.2s ease;
}

.nav-link:hover {
  color: #42b983;
  border-bottom: 2px solid #42b983;
}

.nav-link.active {
  color: #42b983;
  border-bottom: 2px solid #42b983;
}

main {
  flex-grow: 1;
}

footer {
  text-align: center;
  margin-top: auto;
  padding-top: 2rem;
  color: #888;
  font-size: 0.9rem;
}
</style>
