import { defineStore } from 'pinia'
import { api } from '../api'
import type { SavedVideoLine, Shadowed } from '../types'

/** Shadowing: saying a sentence of a video after hearing it, and seeing which words came through. */
export const useShadowStore = defineStore('shadow', {
  state: () => ({
    // The last try: the sentence it was for, what was heard, and the score word by word.
    result: null as ({ line: number; heard: string } & Pick<Shadowed, 'accuracy' | 'words'>) | null,
    checking: false,
    error: '',
  }),
  actions: {
    /** Transcribes a try at a sentence and scores it against the sentence's words. */
    async attempt(line: SavedVideoLine, audio: Blob) {
      this.error = ''
      this.result = null
      this.checking = true
      try {
        const form = new FormData()
        form.append('file', audio, 'speech.webm')
        const { text } = await api<{ text: string }>('/transcribe', { method: 'POST', body: form })
        if (!text) {
          this.error = 'No speech was recognized. Try saying it again.'
          return
        }
        const scored = await api<Shadowed>(`/video-lines/${line.id}/attempts`, { method: 'POST', json: { text } })
        this.result = { line: line.id, heard: text, accuracy: scored.accuracy, words: scored.words }
        line.shadowed = scored.shadowed
        line.best = scored.best
      } catch (e) {
        this.error = (e as Error).message
      } finally {
        this.checking = false
      }
    },

    clear() {
      this.result = null
      this.error = ''
    },
  },
})
