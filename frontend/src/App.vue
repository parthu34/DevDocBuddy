<template>
  <div id="app" class="app-container">
    <header class="hdr">
      <nav class="nav">
        <router-link to="/" class="nav-link" exact-active-class="active">Demo</router-link>

        <!-- Soft CTA in header (only shows when env vars are set) -->
        <a
          v-if="showCTA && checkoutUrl"
          :href="checkoutUrl"
          target="_blank"
          rel="noopener nofollow"
          class="cta-btn"
          @click="onClickCTA"
        >
          Get the self-host bundle
        </a>
      </nav>
    </header>

    <main>
      <router-view />
    </main>

    <!-- Keep a simple footer; no CTA here -->
    <footer class="ftr">
      <small>© 2025 DevDocBuddy</small>
    </footer>
  </div>
</template>

<script setup>
import { track } from '@/analytics'

// Controlled via env vars from Vercel
const showCTA = (import.meta.env.VITE_SHOW_CTA || '').toString().toLowerCase() === 'true'
const checkoutUrl = import.meta.env.VITE_CHECKOUT_SELFHOST_URL || ''

function onClickCTA() {
  try { track('checkout_click', { place: 'header' }) } catch {}
}
</script>

<style scoped>
.app-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem;
  font-family: system-ui, -apple-system, Segoe UI, Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.hdr { margin-bottom: 1.2rem; }
.nav {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  flex-wrap: wrap;
}
.nav-link {
  text-decoration: none;
  color: #555;
  font-weight: 600;
  padding: .4rem .6rem;
  border-radius: 8px;
}
.nav-link.active {
  color: #42b983;
  border: 2px solid #42b983;
}
.cta-btn {
  margin-left: auto; /* push button to the right */
  display: inline-flex;
  align-items: center;
  gap: .4rem;
  background: #2563eb;
  color: white;
  padding: .5rem .8rem;
  border-radius: 10px;
  text-decoration: none;
  font-weight: 600;
  border: 1px solid rgba(0,0,0,0.05);
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25);
}
.cta-btn:hover { filter: brightness(1.05); }
.cta-btn:active { transform: translateY(1px); }

main { flex-grow: 1; }
.ftr { text-align: center; margin-top: 2rem; color: #888; font-size: 0.9rem; }

@media (max-width: 560px) {
  .cta-btn { width: 100%; margin-left: 0; justify-content: center; }
}
</style>
