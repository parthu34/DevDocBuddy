import { defineStore } from 'pinia'
import { summarize, uploadFile, uploadFromURL, addDocument, resetEmbeddings } from '@/api'

export const useDocStore = defineStore('docStore', {
  state: () => ({
    query: '',         // pasted text
    url: '',           // GitHub URL (moved from local component state)
    results: null,
    loading: false,
    error: null,
    lastFilename: null,
  }),
  actions: {
    async fetchSummary() {
      this.loading = true
      this.error = null
      try {
        const data = await summarize({
          query: this.query,
          index: true,            // Summarize & Index (replace)
          mode: 'replace',
          title: 'Manual Text'
        })
        this.results = data.summary || null
        this.lastFilename = data.title || 'Manual Text'
      } catch (e) {
        this.error = e?.message || 'Failed to summarize'
      } finally {
        this.loading = false
      }
    },

    async uploadFile(file) {
      this.loading = true
      this.error = null
      this.lastFilename = file?.name || null
      try {
        const data = await uploadFile(file)
        this.results = data.summary || null
      } catch (e) {
        this.error = e?.message || 'File upload failed'
      } finally {
        this.loading = false
      }
    },

    async addDoc(file) {
      this.loading = true
      this.error = null
      this.lastFilename = file?.name || null
      try {
        const data = await addDocument(file)
        this.results = data.summary || null
      } catch (e) {
        this.error = e?.message || 'Add-doc failed'
      } finally {
        this.loading = false
      }
    },

    async uploadFromURL(url) {
      this.loading = true
      this.error = null
      this.lastFilename = url
      try {
        const data = await uploadFromURL(url)
        this.results = data.summary || null
      } catch (e) {
        this.error = e?.message || 'URL upload failed'
      } finally {
        this.loading = false
      }
    },

    async resetIndex() {
      this.loading = true
      this.error = null
      try {
        await resetEmbeddings()
        // Also clear user inputs & UI state
        this.results = null
        this.lastFilename = null
        this.query = ''    // clear pasted text
        this.url = ''      // clear GitHub URL input
      } catch (e) {
        this.error = e?.message || 'Reset failed'
      } finally {
        this.loading = false
      }
    }
  }
})
