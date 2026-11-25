import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useSettingsStore } from './settings'

// A tiny backend: remembers the feedback language and the theme like the real `/api/settings`,
// which saves only the settings it is sent.
function fakeBackend(saved: string | null, browserLanguage: string, failSaving = false, theme = '') {
  const state = { saved, theme, puts: 0 }
  vi.stubGlobal('navigator', { language: browserLanguage })
  vi.stubGlobal('fetch', async (_url: string, init?: RequestInit) => {
    if (init?.method === 'PUT') {
      state.puts++
      if (failSaving) return new Response(JSON.stringify({ detail: 'disk full' }), { status: 500 })
      const sent = JSON.parse(init.body as string)
      if ('feedback_language' in sent) state.saved = sent.feedback_language
      if ('theme' in sent) state.theme = sent.theme
    }
    return new Response(JSON.stringify({ feedback_language: state.saved, theme: state.theme }), { status: 200 })
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
    // Said in the learner's language, which is Korean here.
    expect(store.error).toBe('언어를 저장하지 못했습니다: disk full')
  })
})

describe('theme', () => {
  it('follows the system until one is chosen', async () => {
    fakeBackend('Korean', 'ko-KR')
    const store = useSettingsStore()
    await store.load()
    expect(store.theme).toBe('')
  })

  it('is the saved one', async () => {
    fakeBackend('Korean', 'ko-KR', false, 'sos-night')
    const store = useSettingsStore()
    await store.load()
    expect(store.theme).toBe('sos-night')
  })

  it('is saved on its own when chosen', async () => {
    const backend = fakeBackend('Korean', 'ko-KR')
    const store = useSettingsStore()
    await store.load()
    await store.setTheme('sos')
    expect(store.theme).toBe('sos')
    expect(backend).toMatchObject({ theme: 'sos', saved: 'Korean' })
  })

  it('keeps the previous theme and reports an error when saving fails', async () => {
    fakeBackend('Korean', 'ko-KR', true)
    const store = useSettingsStore()
    await store.load()
    await store.setTheme('sos-night')
    expect(store.theme).toBe('')
    expect(store.error).toBe('화면 테마를 저장하지 못했습니다: disk full')
  })
})

describe('partner voice', () => {
  const VOICES = [
    { id: 'af_heart', label: 'Heart · American · female', size: 353746785, downloaded: true, chosen: true },
    { id: 'bm_george', label: 'George · British · male', size: 353746785, downloaded: true, chosen: false },
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

describe('language to practise', () => {
  const LANGUAGES = [
    { code: 'en', name: 'English', native: 'English', locale: 'en-US', sample: 'Hi!', chosen: false },
    { code: 'de', name: 'German', native: 'Deutsch', locale: 'de-DE', sample: 'Hallo!', chosen: false },
  ]
  const GERMAN_VOICES = [{ id: 'de_DE-thorsten-high', label: 'Thorsten', size: 113900076, downloaded: false, chosen: true }]

  // Remembers the chosen language like the real `/api/languages` and `/api/language`.
  function languageBackend(chosen: string | null, fail = false) {
    const state = { chosen, asked: [] as string[] }
    vi.stubGlobal('fetch', async (url: string, init?: RequestInit) => {
      state.asked.push(`${init?.method ?? 'GET'} ${url}`)
      if (url === '/api/language') {
        if (fail) return new Response(JSON.stringify({ detail: 'Unknown language: tlh' }), { status: 422 })
        state.chosen = JSON.parse(init?.body as string).language
      }
      if (url.startsWith('/api/language')) {
        return new Response(JSON.stringify(LANGUAGES.map((l) => ({ ...l, chosen: l.code === state.chosen }))), { status: 200 })
      }
      if (url === '/api/voices') return new Response(JSON.stringify(GERMAN_VOICES), { status: 200 })
      return new Response(JSON.stringify([]), { status: 200 })
    })
    return state
  }

  it('has none chosen on the first start', async () => {
    languageBackend(null)
    const store = useSettingsStore()
    expect(store.languages).toBeNull()
    await store.loadLanguages()
    expect(store.languages?.map((l) => l.code)).toEqual(['en', 'de'])
    expect(store.learning).toBeNull()
    expect(store.learningName).toBe('the language')
  })

  it('knows the one chosen before', async () => {
    languageBackend('de')
    const store = useSettingsStore()
    await store.loadLanguages()
    expect(store.learning?.code).toBe('de')
    expect(store.learningName).toBe('German')
  })

  it('chooses a language and starts downloading its speech models', async () => {
    const backend = languageBackend(null)
    const store = useSettingsStore()
    await store.loadLanguages()
    expect(await store.chooseLanguage('de')).toBe(true)
    expect(store.learning?.native).toBe('Deutsch')
    await vi.waitFor(() => expect(backend.asked).toContain('POST /api/models/download'))
  })

  it('lists the voices of the new language when the voices were shown', async () => {
    languageBackend('en')
    const store = useSettingsStore()
    await store.loadLanguages()
    store.voices = [{ id: 'af_heart', label: 'Heart', size: 1, downloaded: true, chosen: true }]
    await store.chooseLanguage('de')
    expect(store.voice).toBe('de_DE-thorsten-high')
  })

  it('goes over to the language of what was opened, unless it is practised already', async () => {
    const backend = languageBackend('en')
    const store = useSettingsStore()
    await store.loadLanguages()
    expect(await store.practise('en')).toBe(true)
    expect(backend.asked).not.toContain('PUT /api/language')
    expect(await store.practise('de')).toBe(true)
    expect(backend.asked).toContain('PUT /api/language')
    expect(store.learning?.code).toBe('de')
  })

  it('keeps the language and says why when choosing fails', async () => {
    languageBackend('en')
    const store = useSettingsStore()
    await store.loadLanguages()
    languageBackend('en', true)
    expect(await store.chooseLanguage('tlh')).toBe(false)
    expect(store.learning?.code).toBe('en')
    expect(store.error).toBe('Could not change the language: Unknown language: tlh')
  })
})
