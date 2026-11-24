import { defineStore } from 'pinia'
import { api } from '../api'
import type { PatternStatus } from '../types'

/** The sentence patterns, grouped by CEFR level, with the learner's progress on each. */
export const usePatternsStore = defineStore('patterns', {
  state: () => ({
    patterns: [] as PatternStatus[],
    loading: true,
    // Whether the whole list came from the backend; a pattern just made from a video may be all that is known.
    loaded: false,
    error: '',
    // The level chosen on the patterns page; kept while the app is open.
    level: '',
    // Making a pattern from a sentence of a video.
    making: false,
    makeError: '',
  }),
  getters: {
    /** The levels that have patterns, in the order the backend lists them. */
    levels: (state): string[] => [...new Set(state.patterns.map((p) => p.level))],
    active(state): string {
      return this.levels.includes(state.level) ? state.level : (this.levels[0] ?? '')
    },
    shown(state): PatternStatus[] {
      return state.patterns.filter((p) => p.level === this.active)
    },
    byId: (state) => (id: string): PatternStatus | null => state.patterns.find((p) => p.id === id) ?? null,
  },
  actions: {
    async load() {
      this.loading = true
      this.error = ''
      try {
        this.patterns = await api<PatternStatus[]>('/patterns')
        this.loaded = true
      } catch (e) {
        this.error = (e as Error).message
      } finally {
        this.loading = false
      }
    },

    /** Loads the list unless it was loaded already. */
    async ensureLoaded() {
      if (!this.loaded) await this.load()
    },

    /** Has a pattern made from the marked part of a video's sentence; null with `makeError` set when it fails. */
    async make(line: number, phrase: string): Promise<PatternStatus | null> {
      this.making = true
      this.makeError = ''
      try {
        const made = await api<PatternStatus>('/patterns', { method: 'POST', json: { line, phrase: phrase.trim() } })
        if (!this.patterns.some((p) => p.id === made.id)) this.patterns.push(made)
        return made
      } catch (e) {
        this.makeError = (e as Error).message
        return null
      } finally {
        this.making = false
      }
    },

    /** Removes a pattern of the learner's own. */
    async remove(id: string) {
      this.error = ''
      try {
        await api(`/patterns/${id}`, { method: 'DELETE' })
        this.patterns = this.patterns.filter((p) => p.id !== id)
      } catch (e) {
        this.error = (e as Error).message
      }
    },

    /** Takes over a pattern's progress after a round, so the list need not be loaded again. */
    update(status: PatternStatus) {
      const at = this.patterns.findIndex((p) => p.id === status.id)
      if (at >= 0) this.patterns[at] = status
    },
  },
})
