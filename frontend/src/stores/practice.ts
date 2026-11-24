import { defineStore } from 'pinia'
import { api } from '../api'
import type { Correction, Message, Phase, Review, Topic } from '../types'

interface Transcript {
  text: string
  clarity: number | null
  unclear_words: string[]
  words_per_minute: number | null
}

/** The conversation in progress with the tutor. */
export const usePracticeStore = defineStore('practice', {
  state: () => ({
    topic: null as Topic | null,
    messages: [] as Message[],
    phase: 'idle' as Phase,
    error: '',
    // Bumped by begin(), so a slow request of an abandoned conversation is ignored.
    session: 0,
    // The saved conversation these lines go into; it is started with the first thing said.
    conversationId: null as number | null,
    // The learner's last line has not reached the saved conversation yet.
    unsaved: false,
    // How the conversation went, once the learner has wrapped it up.
    review: null as Review | null,
  }),
  getters: {
    /** The learner spoke last: the tutor's reply is missing (it failed) or on its way. */
    awaitingReply: (state) => state.messages[state.messages.length - 1]?.role === 'learner',
    /** Something was said and answered, and it has not been reviewed yet. */
    canWrapUp(state): boolean {
      return state.conversationId !== null && !this.awaitingReply && !state.review
    },
  },
  actions: {
    begin(topic: Topic) {
      this.session++
      this.topic = topic
      this.messages = [{ role: 'tutor', text: topic.opener }]
      this.phase = 'idle'
      this.error = ''
      this.conversationId = null
      this.unsaved = false
      this.review = null
    },

    /** Transcribes what the learner said and gets the tutor's reply; resolves with the reply to read aloud. */
    async say(audio: Blob): Promise<string | null> {
      const session = this.session
      this.error = ''
      this.phase = 'transcribing'
      let heard: Transcript
      try {
        const form = new FormData()
        form.append('file', audio, 'speech.webm')
        heard = await api<Transcript>('/transcribe', { method: 'POST', body: form })
      } catch (e) {
        if (session === this.session) {
          this.error = (e as Error).message
          this.phase = 'idle'
        }
        return null
      }
      if (session !== this.session) return null
      if (!heard.text) {
        this.error = 'No speech was recognized. Try saying it again.'
        this.phase = 'idle'
        return null
      }
      this.messages.push({
        role: 'learner',
        text: heard.text,
        correction: null,
        delivery:
          heard.clarity === null
            ? null
            : { clarity: heard.clarity, unclearWords: heard.unclear_words, wordsPerMinute: heard.words_per_minute },
      })
      this.unsaved = true
      // A review covers the conversation as it was; the backend drops it too.
      this.review = null
      return this.requestReply()
    },

    /** Gets the tutor's reply to the learner's last line; also used to ask again after a failure. */
    async requestReply(): Promise<string | null> {
      if (!this.topic || !this.awaitingReply) return null
      const session = this.session
      this.error = ''
      this.phase = 'thinking'
      try {
        if (this.conversationId === null) {
          const started = await api<{ id: number }>('/conversations', { method: 'POST', json: { topic_id: this.topic.id } })
          if (session !== this.session) return null
          this.conversationId = started.id
        }
        const saved = `/conversations/${this.conversationId}`
        if (this.unsaved) {
          const { text, delivery } = this.messages[this.messages.length - 1]
          const spoken = delivery && {
            clarity: delivery.clarity,
            unclear_words: delivery.unclearWords,
            words_per_minute: delivery.wordsPerMinute,
          }
          await api(`${saved}/messages`, { method: 'POST', json: { text, delivery: spoken ?? null } })
          if (session !== this.session) return null
          this.unsaved = false
        }
        const data = await api<{ reply: string; correction: Correction | null }>(`${saved}/reply`, { method: 'POST' })
        if (session !== this.session) return null
        this.messages[this.messages.length - 1].correction = data.correction
        this.messages.push({ role: 'tutor', text: data.reply })
        this.phase = 'idle'
        return data.reply
      } catch (e) {
        if (session === this.session) {
          this.error = `Could not get a reply: ${(e as Error).message}`
          this.phase = 'idle'
        }
        return null
      }
    },

    /** Ends the conversation with a review of it, which is saved with the conversation. */
    async wrapUp() {
      if (!this.canWrapUp) return
      const session = this.session
      this.error = ''
      this.phase = 'reviewing'
      try {
        const review = await api<Review>(`/conversations/${this.conversationId}/review`, { method: 'POST' })
        if (session !== this.session) return
        this.review = review
      } catch (e) {
        if (session === this.session) this.error = `Could not write the summary: ${(e as Error).message}`
      } finally {
        if (session === this.session) this.phase = 'idle'
      }
    },
  },
})
