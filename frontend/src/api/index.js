import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '',
  timeout: 30000,
})

export async function summarize({ query, index = true, mode = 'replace', title = 'Manual Text' }) {
  const { data } = await api.post('/api/summarize', { query, index, mode, title })
  return data
}

export async function uploadFile(file) {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await api.post('/api/upload', fd)
  return data
}

export async function addDocument(file) {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await api.post('/api/add-doc', fd)
  return data
}

export async function uploadFromURL(url) {
  const fd = new FormData()
  fd.append('url', url)
  const { data } = await api.post('/api/upload-url', fd)
  return data
}

export async function resetEmbeddings() {
  const { data } = await api.post('/api/reset')
  return data
}

export async function askQA({ question, top_k = 8 }) {
  const fd = new FormData()
  fd.append('question', question)
  fd.append('top_k', String(top_k))
  const { data } = await api.post('/api/ask', fd)
  return data
}

export default api
