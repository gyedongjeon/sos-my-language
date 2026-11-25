import { defineStore } from 'pinia'
import type { RouteLocationRaw } from 'vue-router'
import { api } from '../api'
import { t } from '../i18n'
import type { CorrectionKind, SavedCorrection } from '../types'

/** How the last try at saying a correction's better sentence went. */
export interface Try {
  heard: string
  matched: boolean
  /** Words of the better sentence that were not heard. */
  missing: string[]
}

interface Checked {
  matched: boolean
  missing: string[]
  practiced: number
}

/** Where a correction comes from: its conversation, its pattern, or its sentence in a video;
 * null for a sentence of a video since deleted. */
export function source(c: SavedCorrection): RouteLocationRaw | null {
  if (c.pattern_id !== null) return { name: 'pattern', params: { id: c.pattern_id } }
  if (c.video !== null) return { name: 'video', params: { id: c.video }, query: { line: c.position ?? 0 } }
  if (c.conversation_id !== null) return { name: 'conversation', params: { id: c.conversation_id } }
  return null
}

/** The corrections of all saved conversations, practised by saying the better sentence aloud. */
export const useCorrectionsStore = defineStore('corrections', {
  state: () => ({
    items: [] as SavedCorrection[],
    loading: true,
    error: '',
    // The correction whose recording is being transcribed and checked.
    checking: null as string | null,
    // The last try of this visit, by correction id.
    results: {} as Record<string, Try>,
    // The tab shown: the expressions, or the sentences of videos.
    kind: 'expression' as CorrectionKind,
  }),
  getters: {
    /** The corrections of the tab shown. */
    ofKind: (state) => state.items.filter((c) => c.kind === state.kind),
    /** How many corrections of the tab shown have never been said right. */
    remaining(): number {
      return this.ofKind.filter((c) => c.practiced === 0).length
    },
    /** How many of each kind have never been said right. */
    left: (state): Record<CorrectionKind, number> => {
      const left = { expression: 0, shadowing: 0 }
      for (const c of state.items) if (c.practiced === 0) left[c.kind]++
      return left
    },
  },
  actions: {
    async load() {
      this.loading = true
      this.error = ''
      try {
        this.items = await api<SavedCorrection[]>('/corrections')
        // Open on a tab with something in it.
        const other = this.kind === 'expression' ? 'shadowing' : 'expression'
        if (!this.ofKind.length && this.items.some((c) => c.kind === other)) this.kind = other
      } catch (e) {
        this.error = (e as Error).message
      } finally {
        this.loading = false
      }
    },

    async check(id: string, heard: string, said: string) {
      const checked = await api<Checked>(`/corrections/${id}/attempts`, { method: 'POST', json: { text: said } })
      this.results[id] = { heard, matched: checked.matched, missing: checked.missing }
      const item = this.items.find((c) => c.id === id)
      if (item) item.practiced = checked.practiced
    },

    /** Transcribes a try at the better sentence and checks it. */
    async attempt(id: string, audio: Blob) {
      this.error = ''
      this.checking = id
      try {
        const form = new FormData()
        form.append('file', audio, 'speech.webm')
        const { text } = await api<{ text: string }>('/transcribe', { method: 'POST', body: form })
        if (!text) this.error = t('common.noSpeech')
        else await this.check(id, text, text)
      } catch (e) {
        this.error = (e as Error).message
      } finally {
        this.checking = null
      }
    },

    /** Counts the last try although it was heard differently: speech recognition gets words wrong too. */
    async countAnyway(id: string) {
      const item = this.items.find((c) => c.id === id)
      if (!item) return
      this.error = ''
      try {
        await this.check(id, this.results[id]?.heard ?? '', item.improved)
      } catch (e) {
        this.error = (e as Error).message
      }
    },

    /** Takes a correction off the list. */
    async remove(id: string) {
      this.error = ''
      try {
        await api(`/corrections/${id}`, { method: 'DELETE' })
        this.items = this.items.filter((c) => c.id !== id)
        delete this.results[id]
      } catch (e) {
        this.error = (e as Error).message
      }
    },
  },
})
