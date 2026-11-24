// Calls the backend and returns the parsed JSON body (undefined for 204 No Content).
// A failed request throws an Error carrying the backend's `detail` message.
export async function api<T = void>(path: string, init?: RequestInit & { json?: unknown }): Promise<T> {
  const { json, ...rest } = init ?? {}
  const res = await fetch(`/api${path}`, {
    ...rest,
    ...(json !== undefined && {
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(json),
    }),
  })
  if (res.status === 204) return undefined as T
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    const detail = data?.detail
    throw new Error(typeof detail === 'string' ? detail : `HTTP ${res.status}`)
  }
  return data as T
}
