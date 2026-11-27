import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api'
import type { SavedWord, WordLookup } from '../types'

/** Where on the screen the tapped word is, to show its explanation next to it. */
export interface Place {
  left: number
  top: number
  bottom: number
}

export interface Tapped {
  word: string
  sentence: string
  at: Place
  // Which of the sentence's words it is, where the same word is in it twice.
  piece?: number
}

// The word the learner tapped last and its explanation. One is shown at a time.
export const useLookupStore = defineStore('lookup', () => {
  const tapped = ref<Tapped | null>(null)
  const found = ref<WordLookup | null>(null)
  const loading = ref(false)
  const error = ref('')
  const saving = ref(false)
  const saveError = ref('')
  // Bumped each time a word is saved or taken off, so a page listing them shows them again.
  const savedChanges = ref(0)
  // Bumped on every tap and on close, so an answer to an earlier tap is not shown.
  let request = 0

  async function lookUp(word: string, sentence: string, at: Place, piece?: number) {
    const mine = ++request
    tapped.value = { word, sentence, at, piece }
    found.value = null
    error.value = ''
    saveError.value = ''
    loading.value = true
    try {
      const answer = await api<WordLookup>('/lookup', { method: 'POST', json: { word, sentence } })
      if (mine === request) found.value = answer
    } catch (e) {
      if (mine === request) error.value = (e as Error).message
    } finally {
      if (mine === request) loading.value = false
    }
  }

  /** Saves the word shown to the learner's list of words, or takes it off when it is there. */
  async function toggleSaved() {
    const word = found.value
    const at = tapped.value
    if (!word || !at || saving.value) return
    saving.value = true
    saveError.value = ''
    try {
      if (word.saved === null) {
        const saved = await api<SavedWord>('/words', { method: 'POST', json: { word: at.word, sentence: at.sentence } })
        word.saved = saved.id
      } else {
        await api(`/words/${word.saved}`, { method: 'DELETE' })
        word.saved = null
      }
      savedChanges.value++
    } catch (e) {
      saveError.value = (e as Error).message
    } finally {
      saving.value = false
    }
  }

  function close() {
    request++
    tapped.value = null
    found.value = null
    error.value = ''
    saveError.value = ''
    loading.value = false
  }

  return { tapped, found, loading, error, saving, saveError, savedChanges, lookUp, toggleSaved, close }
})
