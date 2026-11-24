import { defineStore } from 'pinia'
import { api } from '../api'
import { t } from '../i18n'
import type { Exercise, PatternStatus } from '../types'
import { usePatternsStore } from './patterns'

/** How the last try at the current sentence went. */
export interface DrillTry {
  /** What was heard; empty when the answer was asked for instead. */
  heard: string
  correct: boolean
  improved: string
  explanation: string | null
}

type DrillPhase = 'loading' | 'idle' | 'transcribing' | 'checking' | 'done'

/** One round of a sentence pattern: a few sentences shown in the learner's language, said in the language practised. */
export const useDrillStore = defineStore('drill', {
  state: () => ({
    pattern: null as PatternStatus | null,
    note: '',
    items: [] as Exercise[],
    index: 0,
    // Whether each sentence was right at the first try; null while it was not tried.
    firstTries: [] as (boolean | null)[],
    last: null as DrillTry | null,
    phase: 'idle' as DrillPhase,
    error: '',
    // Bumped by start(), so a slow answer of an abandoned round is ignored.
    round: 0,
  }),
  getters: {
    current: (state): Exercise | null => state.items[state.index] ?? null,
    score: (state): number => state.firstTries.filter(Boolean).length,
  },
  actions: {
    /** Gets new sentences for the pattern and starts at the first. */
    async start(pattern: PatternStatus) {
      const round = ++this.round
      Object.assign(this, { pattern, note: '', items: [], index: 0, firstTries: [], last: null, error: '' })
      this.phase = 'loading'
      try {
        const written = await api<{ note: string; items: Exercise[] }>(`/patterns/${pattern.id}/exercises`, { method: 'POST' })
        if (round !== this.round) return
        this.note = written.note
        this.items = written.items
        this.firstTries = written.items.map(() => null)
      } catch (e) {
        if (round === this.round) this.error = (e as Error).message
      } finally {
        if (round === this.round) this.phase = 'idle'
      }
    },

    settle(result: DrillTry) {
      this.last = result
      if (this.firstTries[this.index] === null) this.firstTries[this.index] = result.correct
    },

    /** Transcribes a try at the current sentence and has it judged. */
    async attempt(audio: Blob) {
      const shown = this.current
      if (!this.pattern || !shown) return
      const round = this.round
      this.error = ''
      this.phase = 'transcribing'
      try {
        const form = new FormData()
        form.append('file', audio, 'speech.webm')
        const { text } = await api<{ text: string }>('/transcribe', { method: 'POST', body: form })
        if (round !== this.round) return
        if (!text) {
          this.error = t('common.noSpeech')
          return
        }
        this.phase = 'checking'
        const verdict = await api<Omit<DrillTry, 'heard'>>(`/patterns/${this.pattern.id}/check`, {
          method: 'POST',
          json: { ...shown, said: text },
        })
        if (round !== this.round) return
        this.settle({ heard: text, ...verdict })
      } catch (e) {
        if (round === this.round) this.error = (e as Error).message
      } finally {
        if (round === this.round) this.phase = 'idle'
      }
    },

    /** Shows the answer without a try, which counts as not knowing it. */
    reveal() {
      if (this.current) this.settle({ heard: '', correct: false, improved: this.current.answer, explanation: null })
    },

    /** Goes to the next sentence; after the last one the round is recorded. */
    async next() {
      this.last = null
      this.error = ''
      if (this.index + 1 < this.items.length) {
        this.index++
        return
      }
      this.phase = 'done'
      if (!this.pattern) return
      try {
        const saved = await api<PatternStatus>(`/patterns/${this.pattern.id}/results`, {
          method: 'POST',
          json: { correct: this.score, total: this.items.length },
        })
        usePatternsStore().update(saved)
      } catch (e) {
        this.error = t('drill.notSaved', { error: (e as Error).message })
      }
    },
  },
})
