import { defineStore } from 'pinia'
import { api } from '../api'
import type { LLMSettings, VoiceStatus } from '../types'

/** Languages feedback can be written in: the English name the LLM is told, and its own name. */
export const LANGUAGES = [
  { name: 'English', label: 'English', codes: ['en'] },
  { name: 'Korean', label: '한국어', codes: ['ko'] },
  { name: 'Japanese', label: '日本語', codes: ['ja'] },
  { name: 'Simplified Chinese', label: '简体中文', codes: ['zh'] },
  { name: 'Traditional Chinese', label: '繁體中文', codes: ['zh-tw', 'zh-hk', 'zh-hant'] },
  { name: 'Spanish', label: 'Español', codes: ['es'] },
  { name: 'French', label: 'Français', codes: ['fr'] },
  { name: 'German', label: 'Deutsch', codes: ['de'] },
  { name: 'Italian', label: 'Italiano', codes: ['it'] },
  { name: 'Portuguese', label: 'Português', codes: ['pt'] },
  { name: 'Polish', label: 'Polski', codes: ['pl'] },
  { name: 'Russian', label: 'Русский', codes: ['ru'] },
  { name: 'Ukrainian', label: 'Українська', codes: ['uk'] },
  { name: 'Turkish', label: 'Türkçe', codes: ['tr'] },
  { name: 'Vietnamese', label: 'Tiếng Việt', codes: ['vi'] },
  { name: 'Thai', label: 'ไทย', codes: ['th'] },
  { name: 'Indonesian', label: 'Bahasa Indonesia', codes: ['id'] },
  { name: 'Hindi', label: 'हिन्दी', codes: ['hi'] },
  { name: 'Bengali', label: 'বাংলা', codes: ['bn'] },
] as const

// The listed language matching the browser's language, e.g. "ko-KR" -> Korean.
function browserLanguage(): string {
  const tag = navigator.language.toLowerCase()
  const has = (test: (code: string) => boolean) => LANGUAGES.find((l) => l.codes.some(test))
  // Region-specific codes first ("zh-TW" is Traditional Chinese), then the base language.
  const match = has((code) => code.includes('-') && tag.startsWith(code)) ?? has((code) => code === tag.split('-')[0])
  return match?.name ?? 'English'
}

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    feedbackLanguage: 'English' as string,
    error: null as string | null,
    // null until loaded.
    llm: null as LLMSettings | null,
    // The voices the partner can speak with; empty until loaded.
    voices: [] as VoiceStatus[],
  }),
  getters: {
    voice: (s): string | null => s.voices.find((v) => v.chosen)?.id ?? null,
  },
  actions: {
    async load() {
      try {
        const saved = await api<{ feedback_language: string | null }>('/settings')
        if (saved.feedback_language) this.feedbackLanguage = saved.feedback_language
        // First visit: start from the browser's language; the user can change it any time.
        else await this.setFeedbackLanguage(browserLanguage())
      } catch (e) {
        this.error = (e as Error).message
      }
    },
    async loadLLM() {
      try {
        this.llm = await api<LLMSettings>('/settings/llm')
      } catch (e) {
        this.error = (e as Error).message
      }
    },
    async loadVoices() {
      try {
        this.voices = await api<VoiceStatus[]>('/voices')
      } catch (e) {
        this.error = (e as Error).message
      }
    },
    /** Has the partner speak with another voice; resolves with whether it was saved. */
    async setVoice(voice: string): Promise<boolean> {
      this.error = null
      try {
        this.voices = await api<VoiceStatus[]>('/voice', { method: 'PUT', json: { voice } })
        return true
      } catch (e) {
        this.error = `Could not change the voice: ${(e as Error).message}`
        return false
      }
    },
    async setFeedbackLanguage(language: string) {
      this.error = null
      try {
        await api('/settings', { method: 'PUT', json: { feedback_language: language } })
        this.feedbackLanguage = language
      } catch (e) {
        this.error = `Could not save the language: ${(e as Error).message}`
      }
    },
  },
})
