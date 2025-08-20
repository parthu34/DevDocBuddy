<template>
  <span :style="styleObj" title="Backend health">
    ● {{ ok ? 'Online' : 'Offline' }}
  </span>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api'

const ok = ref(false)
const styleObj = computed(() => ({
  display: 'inline-block',
  padding: '2px 8px',
  borderRadius: '999px',
  fontSize: '12px',
  background: ok.value ? '#DCFCE7' : '#FEE2E2',
  color: ok.value ? '#166534' : '#991B1B',
  border: `1px solid ${ok.value ? '#86EFAC' : '#FCA5A5'}`
}))

onMounted(async () => {
  try {
    const { data } = await api.get('/healthz')
    ok.value = data?.status === 'ok'
  } catch {
    ok.value = false
  }
})
</script>
