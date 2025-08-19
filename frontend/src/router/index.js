import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import DocsView from '@/views/DocsView.vue'

const routes = [
  { path: '/', name: 'Home', component: HomeView },
  { path: '/docs', name: 'Docs', component: DocsView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
