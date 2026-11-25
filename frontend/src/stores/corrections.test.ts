import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { CorrectionKind, SavedCorrection } from '../types'
import { source, useCorrectionsStore } from './corrections'

const saved = (id: string, improved: string, practiced = 0, kind: CorrectionKind = 'expression'): SavedCorrection => ({
  id,
  kind,
  conversation_id: 1,
  pattern_id: null,
  video: null,
  position: null,
  title: 'Small talk',
  prompt: null,
  original: 'I go to the beach',
  improved,
  explanation: 'Past tense.',
  practiced,
  practiced_at: practiced ? '2026-11-21T09:00:00Z' : null,
})
const LIST = [saved('m5', "I'm excited."), saved('p2', 'I went to the beach.', 1)]
const AUDIO = new Blob(['audio'])

// Answers each path with the prepared [status, body], and records the requests and their JSON.
function fakeBackend(replies: Record<string, [number, unknown]>) {
  const sent: Record<string, unknown> = {}
  const calls: string[] = []
  vi.stubGlobal('fetch', async (url: string, init?: RequestInit) => {
    const path = url.replace('/api', '')
    calls.push(path)
    if (typeof init?.body === 'string') sent[path] = JSON.parse(init.body)
    const [status, body] = replies[path]
    return new Response(status === 204 ? null : JSON.stringify(body), { status })
  })
  return { sent, calls }
}

beforeEach(() => setActivePinia(createPinia()))
afterEach(() => vi.unstubAllGlobals())

describe('corrections', () => {
  it('loads the saved corrections and counts those not practised yet', async () => {
    fakeBackend({ '/corrections': [200, LIST] })
    const store = useCorrectionsStore()
    await store.load()
    expect(store.items).toEqual(LIST)
    expect(store.remaining).toBe(1)
    expect(store.loading).toBe(false)
  })

  it('keeps the expressions and the sentences of videos apart', async () => {
    const shadowed = saved('s3', 'This makes you realize where you still have gaps.', 0, 'shadowing')
    fakeBackend({ '/corrections': [200, [...LIST, shadowed]] })
    const store = useCorrectionsStore()
    await store.load()
    expect(store.kind).toBe('expression')
    expect(store.ofKind).toEqual(LIST)
    expect(store.remaining).toBe(1)
    // What is left to practise in each, for the tabs.
    expect(store.left).toEqual({ expression: 1, shadowing: 1 })
    store.kind = 'shadowing'
    expect(store.ofKind).toEqual([shadowed])
    expect(store.remaining).toBe(1)
  })

  it('opens on the sentences of videos when there are no expressions', async () => {
    const shadowed = saved('s3', 'This makes you realize where you still have gaps.', 0, 'shadowing')
    fakeBackend({ '/corrections': [200, [shadowed]] })
    const store = useCorrectionsStore()
    await store.load()
    expect(store.kind).toBe('shadowing')
  })

  it('reports that the corrections could not be loaded', async () => {
    fakeBackend({ '/corrections': [500, { detail: 'The disk is gone.' }] })
    const store = useCorrectionsStore()
    await store.load()
    expect(store.error).toContain('The disk is gone.')
  })

  it('counts a sentence that was said right', async () => {
    const backend = fakeBackend({
      '/corrections': [200, LIST],
      '/transcribe': [200, { text: 'I am excited.' }],
      '/corrections/m5/attempts': [200, { matched: true, missing: [], practiced: 1 }],
    })
    const store = useCorrectionsStore()
    await store.load()
    await store.attempt('m5', AUDIO)
    expect(backend.sent['/corrections/m5/attempts']).toEqual({ text: 'I am excited.' })
    expect(store.results['m5']).toEqual({ heard: 'I am excited.', matched: true, missing: [] })
    expect(store.items[0].practiced).toBe(1)
    expect(store.remaining).toBe(0)
    expect(store.checking).toBeNull()
  })

  it('shows what was heard and which words were missing when it was not said right', async () => {
    fakeBackend({
      '/corrections': [200, LIST],
      '/transcribe': [200, { text: 'I am exciting.' }],
      '/corrections/m5/attempts': [200, { matched: false, missing: ['excited'], practiced: 0 }],
    })
    const store = useCorrectionsStore()
    await store.load()
    await store.attempt('m5', AUDIO)
    expect(store.results['m5']).toEqual({ heard: 'I am exciting.', matched: false, missing: ['excited'] })
    expect(store.remaining).toBe(1)
  })

  it('asks to try again when no speech was recognized', async () => {
    const backend = fakeBackend({ '/corrections': [200, LIST], '/transcribe': [200, { text: '' }] })
    const store = useCorrectionsStore()
    await store.load()
    await store.attempt('m5', AUDIO)
    expect(backend.calls).toEqual(['/corrections', '/transcribe'])
    expect(store.error).toContain('No speech was recognized')
    expect(store.results['m5']).toBeUndefined()
  })

  it('reports a try that could not be checked', async () => {
    fakeBackend({ '/corrections': [200, LIST], '/transcribe': [500, { detail: 'The model is missing.' }] })
    const store = useCorrectionsStore()
    await store.load()
    await store.attempt('m5', AUDIO)
    expect(store.error).toContain('The model is missing.')
    expect(store.checking).toBeNull()
  })

  it('lets the learner count a try that speech recognition misheard', async () => {
    const backend = fakeBackend({
      '/corrections': [200, LIST],
      '/corrections/m5/attempts': [200, { matched: true, missing: [], practiced: 1 }],
    })
    const store = useCorrectionsStore()
    await store.load()
    store.results['m5'] = { heard: 'I am excite it.', matched: false, missing: ['excited'] }
    await store.countAnyway('m5')
    // The better sentence itself is sent, which always matches.
    expect(backend.sent['/corrections/m5/attempts']).toEqual({ text: "I'm excited." })
    expect(store.results['m5']).toEqual({ heard: 'I am excite it.', matched: true, missing: [] })
    expect(store.items[0].practiced).toBe(1)
  })

  it('takes a correction off the list, and keeps it when that fails', async () => {
    const replies: Record<string, [number, unknown]> = { '/corrections': [200, LIST], '/corrections/p2': [500, { detail: 'The disk is full.' }] }
    fakeBackend(replies)
    const store = useCorrectionsStore()
    await store.load()
    await store.remove('p2')
    expect(store.error).toContain('The disk is full.')
    expect(store.items).toHaveLength(2)
    replies['/corrections/p2'] = [204, null]
    await store.remove('p2')
    expect(store.items.map((c) => c.id)).toEqual(['m5'])
  })
})

describe('the source of a correction', () => {
  it('is the conversation, the pattern, or the sentence of the video it comes from', () => {
    expect(source(saved('m5', 'x'))).toEqual({ name: 'conversation', params: { id: 1 } })
    expect(source({ ...saved('p2', 'x'), conversation_id: null, pattern_id: 'should-have' })).toEqual({
      name: 'pattern',
      params: { id: 'should-have' },
    })
    expect(source({ ...saved('s3', 'x'), conversation_id: null, video: 4, position: 7 })).toEqual({
      name: 'video',
      params: { id: 4 },
      query: { line: 7 },
    })
  })

  it('is none for a sentence of a video since deleted', () => {
    expect(source({ ...saved('s3', 'x'), conversation_id: null })).toBeNull()
  })
})
