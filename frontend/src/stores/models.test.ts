import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ModelStatus } from '../types'
import { megabytes, percent, POLL_MS, useModelsStore } from './models'

const model = (overrides: Partial<ModelStatus> = {}): ModelStatus => ({
  id: 'speech-to-text',
  label: 'Speech recognition',
  state: 'downloading',
  downloaded: 0,
  total: 480_000_000,
  error: null,
  ...overrides,
})

// A backend that answers each request with the next prepared list of models.
function fakeBackend(...replies: ModelStatus[][]) {
  const requests: string[] = []
  vi.stubGlobal('fetch', async (url: string, init?: RequestInit) => {
    requests.push(`${init?.method ?? 'GET'} ${url}`)
    const reply = replies.length > 1 ? replies.shift()! : replies[0]
    return new Response(JSON.stringify(reply), { status: 200 })
  })
  return requests
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.useFakeTimers()
})
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('percent', () => {
  it('is the share of the expected size, as a whole number', () => {
    expect(percent(model({ downloaded: 120_000_000 }))).toBe(25)
    expect(percent(model({ downloaded: 0 }))).toBe(0)
  })

  it('never goes above 100 when the expected size was an estimate', () => {
    expect(percent(model({ downloaded: 500_000_000 }))).toBe(100)
  })

  it('is unknown while the expected size is', () => {
    expect(percent(model({ total: null, downloaded: 5 }))).toBeNull()
  })
})

describe('megabytes', () => {
  it('rounds bytes to megabytes', () => {
    expect(megabytes(483_545_366)).toBe(484)
  })
})

describe('models store', () => {
  it('asks for the downloads when the app opens, then follows them until they finish', async () => {
    const requests = fakeBackend(
      [model({ downloaded: 0 })],
      [model({ downloaded: 240_000_000 })],
      [model({ state: 'ready', downloaded: 480_000_000 })],
    )
    const store = useModelsStore()
    await store.start()
    expect(requests).toEqual(['POST /api/models/download'])
    expect(store.active.map((m) => m.id)).toEqual(['speech-to-text'])

    await vi.advanceTimersByTimeAsync(POLL_MS)
    expect(percent(store.models[0])).toBe(50)
    await vi.advanceTimersByTimeAsync(POLL_MS)
    expect(store.active).toEqual([])

    // Nothing is downloading any more, so the page stops asking.
    await vi.advanceTimersByTimeAsync(POLL_MS * 5)
    expect(requests).toEqual(['POST /api/models/download', 'GET /api/models', 'GET /api/models'])
  })

  it('does not keep asking when everything is already there', async () => {
    const requests = fakeBackend([model({ state: 'ready' })])
    await useModelsStore().start()
    await vi.advanceTimersByTimeAsync(POLL_MS * 3)
    expect(requests).toEqual(['POST /api/models/download'])
  })

  it('lists failed downloads, so the page can offer to try again', async () => {
    fakeBackend([model({ state: 'error', error: 'disk full' }), model({ id: 'voice', state: 'ready' })])
    const store = useModelsStore()
    await store.start()
    expect(store.failed.map((m) => [m.id, m.error])).toEqual([['speech-to-text', 'disk full']])
    expect(store.byId('voice')?.state).toBe('ready')
  })

  it('notices a download that started later, such as one the first recording set off', async () => {
    const requests = fakeBackend([model({ state: 'missing' })], [model({ downloaded: 1 })], [model({ state: 'ready' })])
    const store = useModelsStore()
    await store.start()
    await store.check()
    expect(store.active).toHaveLength(1)
    await vi.advanceTimersByTimeAsync(POLL_MS)
    expect(store.active).toEqual([])
    expect(requests).toHaveLength(3)
  })

  it('keeps following the downloads when one request for their state fails', async () => {
    let calls = 0
    vi.stubGlobal('fetch', async () => {
      calls++
      if (calls === 2) throw new Error('network down')
      return new Response(JSON.stringify([model({ state: calls > 2 ? 'ready' : 'downloading' })]), { status: 200 })
    })
    const store = useModelsStore()
    await store.start()
    await vi.advanceTimersByTimeAsync(POLL_MS * 2)
    expect(store.active).toEqual([])
  })
})
