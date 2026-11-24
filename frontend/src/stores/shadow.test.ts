import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { SavedVideoLine } from '../types'
import { useShadowStore } from './shadow'

const AUDIO = new Blob(['audio'])
const RESULT = {
  accuracy: 67,
  words: [
    { text: 'Truth', heard: true },
    { text: 'be', heard: true },
    { text: 'told.', heard: false },
  ],
  shadowed: 2,
  best: 100,
}
const line = (): SavedVideoLine => ({ id: 11, start: 1, end: 2, text: 'Truth be told.', shadowed: 1, best: 100 })

function fakeBackend(replies: Record<string, [number, unknown]>) {
  const sent: Record<string, unknown> = {}
  const calls: string[] = []
  vi.stubGlobal('fetch', async (url: string, init?: RequestInit) => {
    const path = url.replace('/api', '')
    calls.push(path)
    if (typeof init?.body === 'string') sent[path] = JSON.parse(init.body)
    const [status, body] = replies[path]
    return new Response(JSON.stringify(body), { status })
  })
  return { sent, calls }
}

beforeEach(() => setActivePinia(createPinia()))
afterEach(() => vi.unstubAllGlobals())

describe('shadow', () => {
  it('has a try at a sentence transcribed and scored, and keeps the sentence up to date', async () => {
    const backend = fakeBackend({ '/transcribe': [200, { text: 'Truth be' }], '/video-lines/11/attempts': [200, RESULT] })
    const store = useShadowStore()
    const shadowed = line()
    await store.attempt(shadowed, AUDIO)
    expect(backend.sent['/video-lines/11/attempts']).toEqual({ text: 'Truth be' })
    expect(store.result).toEqual({ line: 11, heard: 'Truth be', accuracy: 67, words: RESULT.words })
    expect([shadowed.shadowed, shadowed.best]).toEqual([2, 100])
    expect(store.checking).toBe(false)
  })

  it('asks to try again when no speech was recognized', async () => {
    const backend = fakeBackend({ '/transcribe': [200, { text: '' }] })
    const store = useShadowStore()
    await store.attempt(line(), AUDIO)
    expect(store.error).toContain('No speech was recognized')
    expect(store.result).toBeNull()
    expect(backend.calls).toEqual(['/transcribe'])
  })

  it('reports a try that could not be scored', async () => {
    fakeBackend({ '/transcribe': [200, { text: 'Truth be' }], '/video-lines/11/attempts': [500, { detail: 'The disk is full.' }] })
    const store = useShadowStore()
    await store.attempt(line(), AUDIO)
    expect(store.error).toContain('The disk is full.')
    expect(store.checking).toBe(false)
  })

  it('forgets the last result when another sentence is chosen', async () => {
    fakeBackend({ '/transcribe': [200, { text: 'Truth be' }], '/video-lines/11/attempts': [200, RESULT] })
    const store = useShadowStore()
    await store.attempt(line(), AUDIO)
    store.clear()
    expect(store.result).toBeNull()
    expect(store.error).toBe('')
  })
})
