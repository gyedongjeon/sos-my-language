import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { WordLookup } from '../types'
import { useLookupStore } from './lookup'

const CORTEX: WordLookup = {
  word: 'cortex',
  lemma: 'cortex',
  phrase: '',
  part_of_speech: '명사',
  meaning: '피질',
  in_context: '뇌의 바깥층',
}
const SENTENCE = 'It involves all four lobes of the cortex.'
const AT = { left: 10, top: 20, bottom: 40 }

beforeEach(() => setActivePinia(createPinia()))
afterEach(() => vi.unstubAllGlobals())

describe('lookup', () => {
  it('asks for a tapped word with its sentence and shows the explanation', async () => {
    const fetch = vi.fn(async () => new Response(JSON.stringify(CORTEX)))
    vi.stubGlobal('fetch', fetch)
    const store = useLookupStore()
    const done = store.lookUp('cortex', SENTENCE, AT)
    expect(store.tapped).toEqual({ word: 'cortex', sentence: SENTENCE, at: AT })
    expect(store.loading).toBe(true)
    await done
    expect(fetch).toHaveBeenCalledWith('/api/lookup', expect.objectContaining({ method: 'POST' }))
    expect(JSON.parse((fetch.mock.calls[0] as unknown as [string, RequestInit])[1].body as string)).toEqual({
      word: 'cortex',
      sentence: SENTENCE,
    })
    expect(store.found).toEqual(CORTEX)
    expect(store.loading).toBe(false)
  })

  it('shows why a word could not be looked up', async () => {
    vi.stubGlobal('fetch', async () => new Response(JSON.stringify({ detail: 'Could not look up the word.' }), { status: 502 }))
    const store = useLookupStore()
    await store.lookUp('cortex', SENTENCE, AT)
    expect(store.error).toBe('Could not look up the word.')
    expect(store.found).toBeNull()
  })

  it('shows the word tapped last when an earlier answer comes after it', async () => {
    let answerFirst: (r: Response) => void = () => {}
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockImplementationOnce(() => new Promise<Response>((resolve) => (answerFirst = resolve)))
        .mockImplementationOnce(async () => new Response(JSON.stringify({ ...CORTEX, word: 'lobes', lemma: 'lobe' }))),
    )
    const store = useLookupStore()
    const first = store.lookUp('cortex', SENTENCE, AT)
    await store.lookUp('lobes', SENTENCE, AT)
    answerFirst(new Response(JSON.stringify(CORTEX)))
    await first
    expect(store.found?.lemma).toBe('lobe')
    expect(store.tapped?.word).toBe('lobes')
  })

  it('forgets the word when closed, and an answer that comes later is not shown', async () => {
    let answer: (r: Response) => void = () => {}
    vi.stubGlobal('fetch', () => new Promise<Response>((resolve) => (answer = resolve)))
    const store = useLookupStore()
    const done = store.lookUp('cortex', SENTENCE, AT)
    store.close()
    answer(new Response(JSON.stringify(CORTEX)))
    await done
    expect(store.tapped).toBeNull()
    expect(store.found).toBeNull()
    expect(store.loading).toBe(false)
  })
})
