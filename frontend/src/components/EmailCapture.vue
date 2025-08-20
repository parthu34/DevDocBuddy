<template>
  <form
    class="email-capture"
    :action="endpoint"
    method="post"
    target="_blank"
    rel="noopener"
  >
    <label class="title">Get updates & Pro beta invites</label>
    <div class="row">
      <input
        name="email"
        type="email"
        required
        placeholder="you@company.com"
        aria-label="Email address"
      />
      <button type="submit">Subscribe</button>
    </div>
    <small class="hint">No spam. Unsubscribe any time.</small>
  </form>
</template>

<script setup>
import { computed } from 'vue'

// Replace "YOUR_BUTTONDOWN_USERNAME" with your actual Buttondown username.
// Create one here: https://buttondown.email/
const endpoint = computed(() =>
  'https://buttondown.email/api/emails/embed-subscribe/YOUR_BUTTONDOWN_USERNAME'
)
</script>

<style scoped>
.email-capture {
  margin: 1.25rem auto;
  padding: 1rem;
  border: 1px solid var(--border);
  border-radius: 12px;
  max-width: 760px;
  background: var(--panel-bg);
  color: var(--panel-text);
}
.title { font-weight: 600; display: block; margin-bottom: .5rem; }
.row { display: grid; grid-template-columns: 1fr auto; gap: .5rem; align-items: center; }
input { padding: .6rem .7rem; border: 1px solid var(--border); border-radius: 8px; }
button { padding: .6rem 1rem; border-radius: 8px; }
.hint { color: var(--muted); }
</style>
