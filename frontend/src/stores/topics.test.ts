import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Topic } from '../types'
import { useTopicsStore } from './topics'

const BUILT_IN: Topic = { id: 1, title: 'Small talk', situation: 'A relaxed chat.', opener: 'How are you?', custom: false, category: 'Everyday', background: null }
const OWN: Topic = { id: 7, title: 'Renting a car', situation: 'At the rental desk.', opener: 'Hello!', custom: true, category: null, background: null }

// Answers each "METHOD path" with the prepared [status, body], and records the requests and their JSON.
function fakeBackend(replies: Record<string, [number, unknown]>) {
  const sent: Record<string, unknown> = {}
  const calls: string[] = []
  vi.stubGlobal('fetch', async (url: string, init?: RequestInit) => {
    const call = `${init?.method ?? 'GET'} ${url.replace('/api', '')}`
    calls.push(call)
    if (typeof init?.body === 'string') sent[call] = JSON.parse(init.body)
    const [status, body] = replies[call]
    return new Response(status === 204 ? null : JSON.stringify(body), { status })
  })
  return { sent, calls }
}

beforeEach(() => setActivePinia(createPinia()))
afterEach(() => vi.unstubAllGlobals())

describe('topics', () => {
  it('loads the topics', async () => {
    fakeBackend({ 'GET /topics': [200, [BUILT_IN, OWN]] })
    const store = useTopicsStore()
    await store.load()
    expect(store.topics).toEqual([BUILT_IN, OWN])
    expect(store.loading).toBe(false)
  })

  it('reports that the topics could not be loaded', async () => {
    fakeBackend({ 'GET /topics': [500, { detail: 'The disk is gone.' }] })
    const store = useTopicsStore()
    await store.load()
    expect(store.error).toContain('The disk is gone.')
  })

  it('adds a topic of the learner’s own to the end of the list', async () => {
    const backend = fakeBackend({ 'GET /topics': [200, [BUILT_IN]], 'POST /topics': [201, OWN] })
    const store = useTopicsStore()
    await store.load()
    expect(await store.add({ title: 'Renting a car', situation: 'At the rental desk.', opener: '' })).toBe(true)
    // An empty opening line is left for the tutor to write.
    expect(backend.sent['POST /topics']).toEqual({ title: 'Renting a car', situation: 'At the rental desk.', opener: null })
    expect(store.topics).toEqual([BUILT_IN, OWN])
    expect(store.adding).toBe(false)
  })

  it('says why a topic could not be added and keeps the list as it was', async () => {
    fakeBackend({ 'GET /topics': [200, [BUILT_IN]], 'POST /topics': [409, { detail: 'There is already a topic with this title.' }] })
    const store = useTopicsStore()
    await store.load()
    expect(await store.add({ title: 'Small talk', situation: 'A chat.', opener: 'Hi!' })).toBe(false)
    expect(store.addError).toContain('already a topic')
    expect(store.topics).toEqual([BUILT_IN])
  })

  it('removes a topic of the learner’s own', async () => {
    const backend = fakeBackend({ 'GET /topics': [200, [BUILT_IN, OWN]], 'DELETE /topics/7': [204, null] })
    const store = useTopicsStore()
    await store.load()
    await store.remove(7)
    expect(backend.calls).toContain('DELETE /topics/7')
    expect(store.topics).toEqual([BUILT_IN])
  })

  it('keeps a topic that could not be removed', async () => {
    fakeBackend({ 'GET /topics': [200, [BUILT_IN, OWN]], 'DELETE /topics/7': [500, { detail: 'The disk is full.' }] })
    const store = useTopicsStore()
    await store.load()
    await store.remove(7)
    expect(store.error).toContain('The disk is full.')
    expect(store.topics).toEqual([BUILT_IN, OWN])
  })

  const CAFE: Topic = { id: 3, title: 'At a café', situation: 'Ordering.', opener: 'Hi!', custom: false, category: 'Food', background: null }
  const WEATHER: Topic = { id: 9, title: 'The weather', situation: 'A chat.', opener: 'Hi!', custom: false, category: 'Everyday', background: null }

  it('groups the topics by category, in the order they come, with the learner’s own last', async () => {
    fakeBackend({ 'GET /topics': [200, [BUILT_IN, WEATHER, CAFE, OWN]] })
    const store = useTopicsStore()
    await store.load()
    expect(store.categories).toEqual(['Everyday', 'Food', 'Yours'])
    // The first category is open to begin with.
    expect(store.active).toBe('Everyday')
    expect(store.shown).toEqual([BUILT_IN, WEATHER])
    store.category = 'Food'
    expect(store.shown).toEqual([CAFE])
    store.category = 'Yours'
    expect(store.shown).toEqual([OWN])
  })

  it('has no category for the learner’s own topics until there is one', async () => {
    fakeBackend({ 'GET /topics': [200, [BUILT_IN, CAFE]] })
    const store = useTopicsStore()
    await store.load()
    expect(store.categories).toEqual(['Everyday', 'Food'])
  })

  it('opens the learner’s own topics after one was added', async () => {
    fakeBackend({ 'GET /topics': [200, [BUILT_IN, CAFE]], 'POST /topics': [201, OWN] })
    const store = useTopicsStore()
    await store.load()
    await store.add({ title: 'Renting a car', situation: 'At the rental desk.', opener: '' })
    expect(store.active).toBe('Yours')
    expect(store.shown).toEqual([OWN])
  })

  it('goes back to the first category when the last own topic was removed', async () => {
    fakeBackend({ 'GET /topics': [200, [BUILT_IN, CAFE, OWN]], 'DELETE /topics/7': [204, null] })
    const store = useTopicsStore()
    await store.load()
    store.category = 'Yours'
    await store.remove(7)
    expect(store.categories).toEqual(['Everyday', 'Food'])
    expect(store.active).toBe('Everyday')
    expect(store.shown).toEqual([BUILT_IN])
  })

  const ARTICLE: Topic = {
    id: 8,
    title: 'A car-free main street',
    situation: 'A discussion of an article.',
    opener: 'What do you think?',
    custom: true,
    category: null,
    background: 'The street closes to cars on weekends.',
  }

  it('makes a topic from a pasted text and opens the learner’s own topics', async () => {
    const backend = fakeBackend({ 'GET /topics': [200, [BUILT_IN]], 'POST /topics/from-text': [201, ARTICLE] })
    const store = useTopicsStore()
    await store.load()
    expect(await store.addFromText('  The city council voted…  ')).toBe(true)
    expect(backend.sent['POST /topics/from-text']).toEqual({ text: 'The city council voted…' })
    expect(store.topics).toEqual([BUILT_IN, ARTICLE])
    expect(store.active).toBe('Yours')
    expect(store.adding).toBe(false)
  })

  it('says why a topic could not be made from a text', async () => {
    fakeBackend({ 'GET /topics': [200, [BUILT_IN]], 'POST /topics/from-text': [502, { detail: 'No model is configured.' }] })
    const store = useTopicsStore()
    await store.load()
    expect(await store.addFromText('The city council voted…')).toBe(false)
    expect(store.addError).toContain('No model is configured.')
    expect(store.topics).toEqual([BUILT_IN])
  })

  it('sends a pasted link as a link, so the backend reads the page', async () => {
    const backend = fakeBackend({ 'GET /topics': [200, [BUILT_IN]], 'POST /topics/from-text': [201, ARTICLE] })
    const store = useTopicsStore()
    await store.load()
    expect(await store.addFromText(' https://news.example/street?id=1 ')).toBe(true)
    expect(backend.sent['POST /topics/from-text']).toEqual({ url: 'https://news.example/street?id=1' })
    // A text that merely starts with a link is still a text.
    await store.addFromText('https://news.example/street says the council voted…')
    expect(backend.sent['POST /topics/from-text']).toEqual({ text: 'https://news.example/street says the council voted…' })
  })
})
