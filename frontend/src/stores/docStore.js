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
        this.results = response.data
      } catch (e) {
        this.error = e.message || 'Failed to fetch summary'
      } finally {
        this.loading = false
      }
    }
  }
})
