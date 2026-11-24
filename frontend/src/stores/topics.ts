import { defineStore } from 'pinia'
import { api } from '../api'
import type { Topic } from '../types'

/** What the learner types to add a topic; an empty opening line is written by the tutor. */
export interface TopicDraft {
  title: string
  situation: string
  opener: string
}

/** The category the learner's own topics are shown under. */
export const OWN = 'Yours'

/** Whether what was pasted is a web link and nothing else. */
export const isLink = (pasted: string) => /^https?:\/\/\S+$/.test(pasted.trim())

const categoryOf = (topic: Topic) => (topic.custom ? OWN : (topic.category ?? 'Other'))

/** The topics to practise: the built-in ones, then the learner's own. */
export const useTopicsStore = defineStore('topics', {
  state: () => ({
    topics: [] as Topic[],
    loading: true,
    error: '',
    adding: false,
    addError: '',
    // The category chosen on the home page; kept while the app is open.
    category: '',
  }),
  getters: {
    /** The categories that have topics, in the order the backend lists them; the learner's own last. */
    categories: (state): string[] => [...new Set(state.topics.map(categoryOf))],
    /** The category whose topics are shown: the chosen one, or the first while none is or it is gone. */
    active(state): string {
      return this.categories.includes(state.category) ? state.category : (this.categories[0] ?? '')
    },
    shown(state): Topic[] {
      return state.topics.filter((topic) => categoryOf(topic) === this.active)
    },
  },
  actions: {
    async load() {
      this.loading = true
      this.error = ''
      try {
        this.topics = await api<Topic[]>('/topics')
      } catch (e) {
        this.error = (e as Error).message
      } finally {
        this.loading = false
      }
    },

    /** Resolves with whether the topic was added; `addError` says why not. */
    async add(draft: TopicDraft): Promise<boolean> {
      this.adding = true
      this.addError = ''
      try {
        const json = { title: draft.title, situation: draft.situation, opener: draft.opener.trim() || null }
        this.topics.push(await api<Topic>('/topics', { method: 'POST', json }))
        this.category = OWN
        return true
      } catch (e) {
        this.addError = (e as Error).message
        return false
      } finally {
        this.adding = false
      }
    },

    /** Has a topic made from a text such as a news article, or from the page a link leads to; resolves with whether it was added. */
    async addFromText(text: string): Promise<boolean> {
      this.adding = true
      this.addError = ''
      try {
        const pasted = text.trim()
        const json = isLink(pasted) ? { url: pasted } : { text: pasted }
        this.topics.push(await api<Topic>('/topics/from-text', { method: 'POST', json }))
        this.category = OWN
        return true
      } catch (e) {
        this.addError = (e as Error).message
        return false
      } finally {
        this.adding = false
      }
    },

    async remove(id: number) {
      this.error = ''
      try {
        await api(`/topics/${id}`, { method: 'DELETE' })
        this.topics = this.topics.filter((t) => t.id !== id)
      } catch (e) {
        this.error = (e as Error).message
      }
    },
  },
})
