import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useSettingsStore } from './settings'

// A tiny backend: remembers the feedback language like the real `/api/settings`.
function fakeBackend(saved: string | null, browserLanguage: string, failSaving = false) {
  const state = { saved, puts: 0 }
  vi.stubGlobal('navigator', { language: browserLanguage })
  vi.stubGlobal('fetch', async (_url: string, init?: RequestInit) => {
    if (init?.method === 'PUT') {
      state.puts++
      if (failSaving) return new Response(JSON.stringify({ detail: 'disk full' }), { status: 500 })
      state.saved = JSON.parse(init.body as string).feedback_language
    }
    return new Response(JSON.stringify({ feedback_language: state.saved }), { status: 200 })
  })
  return state
}

beforeEach(() => setActivePinia(createPinia()))
afterEach(() => vi.unstubAllGlobals())

describe('feedback language', () => {
  it('uses the saved choice and leaves it alone', async () => {
    const backend = fakeBackend('Japanese', 'ko-KR')
    const store = useSettingsStore()
    await store.load()
    expect(store.feedbackLanguage).toBe('Japanese')
    expect(backend.puts).toBe(0)
  })

  it.each([
    ['ko-KR', 'Korean'],
    ['zh-TW', 'Traditional Chinese'],
    ['zh-CN', 'Simplified Chinese'],
    ['pt-BR', 'Portuguese'],
    ['ru-RU', 'Russian'],
    ['tr-TR', 'Turkish'],
    ['it-IT', 'Italian'],
    ['th-TH', 'Thai'],
    ['pl-PL', 'Polish'],
    ['uk-UA', 'Ukrainian'],
    ['bn-BD', 'Bengali'],
    ['sv-SE', 'English'],
  ])('starts from the browser language on the first visit: %s -> %s', async (browser, expected) => {
    const backend = fakeBackend(null, browser)
    const store = useSettingsStore()
    await store.load()
    expect(store.feedbackLanguage).toBe(expected)
    expect(backend.saved).toBe(expected)
  })

  it('keeps the previous language and reports an error when saving fails', async () => {
    fakeBackend('Korean', 'ko-KR', true)
    const store = useSettingsStore()
    await store.load()
    await store.setFeedbackLanguage('French')
    expect(store.feedbackLanguage).toBe('Korean')
    expect(store.error).toBe('Could not save the language: disk full')
  })
})

describe('partner voice', () => {
  const VOICES = [
    { id: 'af_heart', label: 'Heart · American · female', chosen: true },
    { id: 'bm_george', label: 'George · British · male', chosen: false },
  ]

  function voiceBackend(fail = false) {
    const asked: string[] = []
    vi.stubGlobal('fetch', async (url: string, init?: RequestInit) => {
      asked.push(`${init?.method ?? 'GET'} ${url}`)
      if (fail) return new Response(JSON.stringify({ detail: 'Unknown voice' }), { status: 422 })
      if (init?.method === 'PUT') {
        const wanted = JSON.parse(init.body as string).voice
        return new Response(JSON.stringify(VOICES.map((v) => ({ ...v, chosen: v.id === wanted }))), { status: 200 })
      }
      return new Response(JSON.stringify(VOICES), { status: 200 })
    })
    return asked
  }

  it('lists the voices and which one is chosen', async () => {
    voiceBackend()
    const store = useSettingsStore()
    await store.loadVoices()
    expect(store.voices.map((v) => v.id)).toEqual(['af_heart', 'bm_george'])
    expect(store.voice).toBe('af_heart')
  })

  it('chooses another voice', async () => {
    const asked = voiceBackend()
    const store = useSettingsStore()
    await store.loadVoices()
    expect(await store.setVoice('bm_george')).toBe(true)
    expect(store.voice).toBe('bm_george')
    expect(asked).toContain('PUT /api/voice')
  })

  it('keeps the voice and says why when choosing fails', async () => {
    voiceBackend()
    const store = useSettingsStore()
    await store.loadVoices()
    voiceBackend(true)
    expect(await store.setVoice('bm_george')).toBe(false)
    expect(store.voice).toBe('af_heart')
    expect(store.error).toContain('Could not change the voice')
  })
})
