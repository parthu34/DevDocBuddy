import { defineStore } from 'pinia'
import axios from 'axios'

export const useDocStore = defineStore('docStore', {
  state: () => ({
    query: '',
    results: null,
    loading: false,
    error: null,
  }),
  actions: {
    async fetchSummary() {
      this.loading = true
      this.error = null
      try {
        const response = await axios.post('/api/summarize', { query: this.query })
        this.results = response.data.summary
      } catch (e) {
        this.error = e.message || 'Failed to fetch summary'
      } finally {
        this.loading = false
      }
    },

    async uploadFile(file) {
      this.loading = true
      this.error = null
      try {
        const formData = new FormData()
        formData.append('file', file)

        const response = await axios.post('/api/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        this.results = response.data.summary
      } catch (e) {
        this.error = e.message || 'File upload failed'
      } finally {
        this.loading = false
      }
    },

    async uploadFromURL(url) {
    this.loading = true
    this.error = null
    try {
        const formData = new FormData()
        formData.append('url', url)

        const response = await axios.post('/api/upload-url', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        })
        this.results = response.data.summary
    } catch (e) {
        this.error = e.message || 'URL upload failed'
    } finally {
        this.loading = false
    }
    }
  }
})
