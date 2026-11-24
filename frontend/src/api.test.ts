import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from './api'

function respondWith(status: number, body?: unknown) {
  const text = body === undefined ? null : typeof body === 'string' ? body : JSON.stringify(body)
  const fetchMock = vi.fn(async (..._args: Parameters<typeof fetch>) => new Response(text, { status }))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

afterEach(() => vi.unstubAllGlobals())

describe('api', () => {
  it('returns the parsed body of a successful request', async () => {
    const fetchMock = respondWith(200, [{ id: 1 }])
    expect(await api('/topics')).toEqual([{ id: 1 }])
    expect(fetchMock.mock.calls[0][0]).toBe('/api/topics')
  })

  it('sends `json` as a JSON body', async () => {
    const fetchMock = respondWith(200, {})
    await api('/settings', { method: 'PUT', json: { feedback_language: 'Korean' } })
    const init = fetchMock.mock.calls[0][1]!
    expect(init.method).toBe('PUT')
    expect(init.headers).toEqual({ 'Content-Type': 'application/json' })
    expect(init.body).toBe('{"feedback_language":"Korean"}')
  })

  it('returns nothing for 204 No Content', async () => {
    respondWith(204)
    expect(await api('/settings/llm/test', { method: 'POST' })).toBeUndefined()
  })

  it("throws the backend's message when a request fails", async () => {
    respondWith(502, { detail: 'No model is configured.' })
    await expect(api('/reply')).rejects.toThrow('No model is configured.')
  })

  it('throws the status when the failure has no readable message', async () => {
    respondWith(500, 'Internal Server Error')
    await expect(api('/reply')).rejects.toThrow('HTTP 500')
    respondWith(422, { detail: [{ msg: 'field required' }] })
    await expect(api('/reply')).rejects.toThrow('HTTP 422')
  })
})
