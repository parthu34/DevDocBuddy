// vite.config.js
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => {
  // Load .env files so we can read VITE_API_BASE in dev too
  const env = loadEnv(mode, process.cwd(), '')
  const backend = env.VITE_API_BASE || 'http://localhost:8000'

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      port: 5173,
      // Dev-only proxy: when axios baseURL is empty (''), calls to /api/* hit Vite,
      // which forwards to the backend. In prod, axios uses VITE_API_BASE directly.
      proxy: {
        '/api': {
          target: backend,
          changeOrigin: true,
          secure: false,
        },
      },
    },
    // Optional: nicer debugging
    build: {
      sourcemap: mode !== 'production' ? true : false,
      target: 'esnext',
    },
  }
})
