// src/api/index.js
import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE || (import.meta.env.DEV ? '' : undefined)
if (!baseURL && !import.meta.env.DEV) {
  throw new Error('VITE_API_BASE is not set. Add it in Vercel → Settings → Environment Variables and redeploy.')
}

const api = axios.create({
  baseURL,
  timeout: 120000,
})

// Helpful error extractor
function asMessage(err) {
  const d = err?.response?.data
  if (d?.detail) return typeof d.detail === 'string' ? d.detail : JSON.stringify(d.detail)
  if (typeof d === 'string') return d
  return err?.message || 'Request failed'
}

export async function summarize({ query, index = true, mode = 'replace', title = 'Manual Text' }) {
  const { data } = await api.post('/api/summarize', { query, index, mode, title })
  return data
}

export async function uploadFile(file) {
  const fd = new FormData()
  fd.append('file', file)
  try {
    const { data } = await api.post('/api/upload', fd)
    return data
  } catch (e) {
    throw new Error(asMessage(e))
  }
}

export async function addDocument(file) {
  const fd = new FormData()
  fd.append('file', file)
  try {
    const { data } = await api.post('/api/add-doc', fd)
    return data
  } catch (e) {
    throw new Error(asMessage(e))
  }
}

export async function uploadFromURL(url) {
  const fd = new FormData()
  fd.append('url', url)
  try {
    const { data } = await api.post('/api/upload-url', fd)
    return data
  } catch (e) {
    throw new Error(asMessage(e))
  }
}

export async function resetEmbeddings() {
  try {
    const { data } = await api.post('/api/reset')
    return data
  } catch (e) {
    throw new Error(asMessage(e))
  }
}

export async function getIndexStatus() {
  const { data } = await api.get('/api/index-status')
  return data
}

export async function askQA({ question, top_k = 8 }) {
  const fd = new FormData()
  fd.append('question', question)
  fd.append('top_k', String(top_k))
  try {
    const { data } = await api.post('/api/ask', fd)
    return data
  } catch (e) {
    throw new Error(asMessage(e))
  }
}

export default api
