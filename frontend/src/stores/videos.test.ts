import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Video, VideoSuggestion, VideoSummary } from '../types'
import { useVideosStore } from './videos'

const SAVED: VideoSummary = {
  id: 1,
  video_id: 'UF8uR6Z6KLc',
  title: 'Commencement address',
  channel: 'Stanford',
  language: 'en',
  generated: false,
  added_at: '2026-11-21T10:00:00Z',
  sentences: 150,
  level: 'B2',
}
const ADDED: Video = {
  id: 2,
  video_id: 'arj7oStGLkU',
  title: 'A talk',
  channel: 'TED',
  language: 'en',
  generated: true,
  added_at: '2026-11-21T11:00:00Z',
  level: null,
  lines: [
    { id: 11, start: 1, end: 2, text: 'One.', shadowed: 0, best: null },
    { id: 12, start: 2, end: 3, text: 'Two.', shadowed: 0, best: null },
  ],
}
const SUGGESTED: VideoSuggestion = {
  video_id: 'arj7oStGLkU',
  title: 'A talk',
  channel: 'TED',
  duration: 600,
  level: 'B2',
  generated: false,
}

// Answers each "METHOD path" with the prepared [status, body], and records the requests and their JSON.
function fakeBackend(replies: Record<string, [number, unknown]>) {
  const sent: Record<string, unknown> = {}
  const asked: string[] = []
  vi.stubGlobal('fetch', async (url: string, init?: RequestInit) => {
    const call = `${init?.method ?? 'GET'} ${url.replace('/api', '')}`
    if (typeof init?.body === 'string') sent[call] = JSON.parse(init.body)
    const [status, body] = replies[call.split('?')[0]]
    asked.push(call)
    return new Response(status === 204 ? null : JSON.stringify(body), { status })
  })
  return { sent, asked }
}

beforeEach(() => setActivePinia(createPinia()))
afterEach(() => vi.unstubAllGlobals())

describe('videos', () => {
  it('loads the saved videos', async () => {
    fakeBackend({ 'GET /videos': [200, [SAVED]] })
    const store = useVideosStore()
    await store.load()
    expect(store.videos).toEqual([SAVED])
    expect(store.loading).toBe(false)
  })

  it('adds a video from its link and puts it first in the list', async () => {
    const backend = fakeBackend({ 'GET /videos': [200, [SAVED]], 'POST /videos': [201, ADDED] })
    const store = useVideosStore()
    await store.load()
    expect(await store.add(' https://youtu.be/arj7oStGLkU ')).toEqual(ADDED)
    expect(backend.sent['POST /videos']).toEqual({ url: 'https://youtu.be/arj7oStGLkU' })
    expect(store.videos.map((v) => [v.id, v.sentences])).toEqual([
      [2, 2],
      [1, 150],
    ])
    expect(store.adding).toBe(false)
  })

  it('does not list a video twice when it was saved before', async () => {
    fakeBackend({ 'GET /videos': [200, [SAVED]], 'POST /videos': [200, { ...ADDED, id: 1 }] })
    const store = useVideosStore()
    await store.load()
    await store.add('https://youtu.be/UF8uR6Z6KLc')
    expect(store.videos).toHaveLength(1)
  })

  it('says why a video could not be added', async () => {
    fakeBackend({ 'GET /videos': [200, []], 'POST /videos': [422, { detail: 'This video has no English subtitles.' }] })
    const store = useVideosStore()
    await store.load()
    expect(await store.add('https://youtu.be/arj7oStGLkU')).toBeNull()
    expect(store.addError).toContain('no English subtitles')
    expect(store.videos).toEqual([])
  })

  it('removes a video, and keeps it when that fails', async () => {
    const replies: Record<string, [number, unknown]> = { 'GET /videos': [200, [SAVED]], 'DELETE /videos/1': [500, { detail: 'The disk is full.' }] }
    fakeBackend(replies)
    const store = useVideosStore()
    await store.load()
    await store.remove(1)
    expect(store.error).toContain('The disk is full.')
    expect(store.videos).toEqual([SAVED])
    replies['DELETE /videos/1'] = [204, null]
    await store.remove(1)
    expect(store.videos).toEqual([])
  })

  const HIT = { id: 12, video: 2, video_id: 'arj7oStGLkU', title: 'A talk', position: 1, start: 2, text: 'Two.' }

  it('searches the saved subtitles for a phrase', async () => {
    const backend = fakeBackend({ 'GET /video-lines': [200, [HIT]] })
    const store = useVideosStore()
    await store.search('  two & more ')
    expect(backend.asked).toEqual(['GET /video-lines?q=two%20%26%20more'])
    expect(store.hits).toEqual([HIT])
    expect(store.searched).toBe('two & more')
    expect(store.searching).toBe(false)
  })

  it('clears the results when the search box is emptied, without asking', async () => {
    const backend = fakeBackend({ 'GET /video-lines': [200, [HIT]] })
    const store = useVideosStore()
    await store.search('two')
    await store.search('  ')
    expect(store.hits).toEqual([])
    expect(store.searched).toBe('')
    expect(backend.asked).toHaveLength(1)
  })

  it('reports a search that failed', async () => {
    fakeBackend({ 'GET /video-lines': [500, { detail: 'The disk is gone.' }] })
    const store = useVideosStore()
    await store.search('two')
    expect(store.error).toContain('The disk is gone.')
    expect(store.hits).toEqual([])
  })

  const TALK: VideoSummary = { ...SAVED, id: 3, level: 'C1' }
  const PLAIN: VideoSummary = { ...SAVED, id: 4, level: null }

  it('shows the videos of one level, or those without one, or all', async () => {
    fakeBackend({ 'GET /videos': [200, [PLAIN, TALK, SAVED]] })
    const store = useVideosStore()
    await store.load()
    // In the order of the levels, whatever order the videos come in.
    expect(store.levels).toEqual(['B2', 'C1', 'No level'])
    expect(store.shown).toHaveLength(3)
    store.level = 'C1'
    expect(store.shown).toEqual([TALK])
    store.level = 'No level'
    expect(store.shown).toEqual([PLAIN])
  })

  it('goes back to all videos when the chosen level has none left', async () => {
    fakeBackend({ 'GET /videos': [200, [TALK, SAVED]], 'DELETE /videos/3': [204, null] })
    const store = useVideosStore()
    await store.load()
    store.level = 'C1'
    await store.remove(3)
    expect(store.active).toBe('All')
    expect(store.shown).toEqual([SAVED])
  })

  it('sets a level by hand and has one estimated, keeping the list up to date', async () => {
    const backend = fakeBackend({
      'GET /videos': [200, [SAVED]],
      'PUT /videos/1/level': [200, { ...ADDED, id: 1, level: 'A2' }],
      'POST /videos/1/level': [200, { ...ADDED, id: 1, level: 'B1' }],
    })
    const store = useVideosStore()
    await store.load()
    expect((await store.setLevel(1, 'A2'))?.level).toBe('A2')
    expect(backend.sent['PUT /videos/1/level']).toEqual({ level: 'A2' })
    expect(store.videos[0].level).toBe('A2')
    expect((await store.estimateLevel(1))?.level).toBe('B1')
    expect(store.videos[0].level).toBe('B1')
  })

  it('reports a level that could not be estimated', async () => {
    fakeBackend({ 'GET /videos': [200, [SAVED]], 'POST /videos/1/level': [502, { detail: 'No model is configured.' }] })
    const store = useVideosStore()
    await store.load()
    expect(await store.estimateLevel(1)).toBeNull()
    expect(store.error).toContain('No model is configured.')
    expect(store.videos[0].level).toBe('B2')
  })
})

describe('suggested videos', () => {
  it('suggests videos like a saved one', async () => {
    const backend = fakeBackend({ 'POST /videos/1/suggestions': [200, [SUGGESTED]] })
    const store = useVideosStore()
    await store.suggest(1)
    expect(backend.asked).toEqual(['POST /videos/1/suggestions'])
    expect(store.suggestions).toEqual([SUGGESTED])
    expect(store.suggestedFor).toBe(1)
    expect(store.suggesting).toBe(false)
  })

  it('says why no videos could be suggested', async () => {
    fakeBackend({ 'POST /videos/1/suggestions': [502, { detail: 'YouTube could not be searched: offline' }] })
    const store = useVideosStore()
    await store.suggest(1)
    expect(store.suggestions).toEqual([])
    expect(store.suggestError).toContain('YouTube could not be searched')
  })

  it('ignores suggestions that come after another video asked for its own', async () => {
    fakeBackend({ 'POST /videos/1/suggestions': [200, [SUGGESTED]], 'POST /videos/2/suggestions': [200, []] })
    const store = useVideosStore()
    const first = store.suggest(1)
    await store.suggest(2)
    await first
    expect(store.suggestedFor).toBe(2)
    expect(store.suggestions).toEqual([])
  })

  it('no longer suggests a video once it is added', async () => {
    fakeBackend({ 'POST /videos/1/suggestions': [200, [SUGGESTED]], 'POST /videos': [201, ADDED] })
    const store = useVideosStore()
    await store.suggest(1)
    await store.add('https://youtu.be/arj7oStGLkU')
    expect(store.suggestions).toEqual([])
  })
})

describe('translations', () => {
  const TRANSLATED = { language: 'Korean', lines: [{ line: 11, text: '하나.' }, { line: 12, text: '둘.' }] }

  it('translates the sentences of a video, by line', async () => {
    const backend = fakeBackend({ 'POST /videos/2/translations': [200, TRANSLATED] })
    const store = useVideosStore()
    const pending = store.translate(2)
    expect(store.translating).toBe(true)
    await pending
    expect(store.translations).toEqual({ 11: '하나.', 12: '둘.' })
    expect(store.translatedFor).toBe(2)
    expect(store.translating).toBe(false)
    expect(backend.asked).toEqual(['POST /videos/2/translations'])
  })

  it('says why a video could not be translated', async () => {
    fakeBackend({ 'POST /videos/2/translations': [502, { detail: 'Could not translate the sentences: timeout' }] })
    const store = useVideosStore()
    await store.translate(2)
    expect(store.translateError).toContain('timeout')
    expect(store.translations).toEqual({})
    expect(store.translating).toBe(false)
  })

  it('counts the sentences left without a translation, and keeps the others shown while asking again', async () => {
    fakeBackend({ 'POST /videos/2/translations': [200, { ...TRANSLATED, lines: TRANSLATED.lines.slice(0, 1), missing: 1 }] })
    const store = useVideosStore()
    await store.translate(2)
    expect(store.untranslated).toBe(1)
    fakeBackend({ 'POST /videos/2/translations': [200, { ...TRANSLATED, missing: 0 }] })
    const again = store.translate(2)
    expect(store.translations).toEqual({ 11: '하나.' })
    await again
    expect(store.translations).toEqual({ 11: '하나.', 12: '둘.' })
    expect(store.untranslated).toBe(0)
  })

  it('ignores a translation that comes after another video asked for its own', async () => {
    fakeBackend({
      'POST /videos/2/translations': [200, TRANSLATED],
      'POST /videos/3/translations': [200, { language: 'Korean', lines: [{ line: 21, text: '셋.' }] }],
    })
    const store = useVideosStore()
    const first = store.translate(2)
    await store.translate(3)
    await first
    expect(store.translatedFor).toBe(3)
    expect(store.translations).toEqual({ 21: '셋.' })
  })
})
