// src/stores/docStore.js
import { defineStore } from 'pinia'
import { summarize, uploadFile, uploadFromURL, addDocument, resetEmbeddings, getIndexStatus } from '@/api'
import { track } from '@/analytics'

export const useDocStore = defineStore('docStore', {
  state: () => ({
    query: '',
    url: '',
    results: null,
    loading: false,
    error: null,
    lastFilename: null,
    hasIndex: false,   // gate for Q&A
  }),
  actions: {
    async initIndexStatus() {
      try {
        const st = await getIndexStatus()
        this.hasIndex = !!st?.ready
      } catch {
        this.hasIndex = false
      }
    },

    async fetchSummary() {
      this.loading = true
      this.error = null
      try {
        const data = await summarize({
          query: this.query,
          index: true,
          mode: 'replace',
          title: 'Manual Text'
        })
        this.results = data.summary || null
        this.lastFilename = data.title || 'Manual Text'
        this.hasIndex = true
        track('summary_uploaded', { kind: 'text', chars: (this.query || '').length })
      } catch (e) {
        this.error = e?.message || 'Failed to summarize'
        track('upload_failed', { kind: 'text', message: this.error })
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
        this.hasIndex = true
        track('summary_uploaded', { kind: 'file', size: file?.size || 0, name: this.lastFilename })
      } catch (e) {
        this.error = e?.message || 'File upload failed'
        track('upload_failed', { kind: 'file', message: this.error })
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
        this.hasIndex = true
        track('summary_uploaded', { kind: 'add-doc', size: file?.size || 0, name: this.lastFilename })
      } catch (e) {
        this.error = e?.message || 'Add-doc failed'
        track('upload_failed', { kind: 'add-doc', message: this.error })
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
        this.hasIndex = true
        track('url_uploaded', { url })
      } catch (e) {
        this.error = e?.message || 'URL upload failed'
        track('upload_failed', { kind: 'url', message: this.error })
      } finally {
        this.loading = false
      }
    },

    async resetIndex() {
      this.loading = true
      this.error = null
      try {
        await resetEmbeddings()
        this.results = null
        this.lastFilename = null
        this.query = ''
        this.url = ''
        this.hasIndex = false
        track('reset_index')
      } catch (e) {
        this.error = e?.message || 'Reset failed'
        track('upload_failed', { kind: 'reset', message: this.error })
      } finally {
        this.loading = false
      }
    }
  }
})
