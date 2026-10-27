import { get, set } from 'idb-keyval'
import { ApiError, NetworkError, request } from './api'

/**
 * Persistent queue of pending mutations. The UI applies changes optimistically
 * and the outbox replays them in order whenever the server is reachable.
 * Every endpoint it calls is idempotent, so retries are safe.
 */
interface Entry {
  key: string
  method: string
  path: string
  body?: unknown
}

const STORAGE_KEY = 'outbox'
const FLUSH_DELAY_MS = 600
const RETRY_DELAY_MS = 5000

let entries: Entry[] = []
let flushing = false
// The entry currently being sent must not absorb newer edits, or they'd be lost when it is shifted.
let inFlight: Entry | undefined
let timer: ReturnType<typeof setTimeout> | undefined
let onUnauthorized: () => void = () => {}
let onChange: (pending: number) => void = () => {}

export async function initOutbox(handlers: { onUnauthorized: () => void; onChange: (pending: number) => void }) {
  onUnauthorized = handlers.onUnauthorized
  onChange = handlers.onChange
  entries = (await get<Entry[]>(STORAGE_KEY).catch(() => undefined)) ?? []
  onChange(entries.length)
  window.addEventListener('online', () => void flush())
}

export function pendingCount() {
  return entries.length
}

/**
 * Queue a mutation. PUT/PATCH to the same path coalesce into one entry so a
 * burst of "+" taps becomes a single request.
 */
export function enqueue(method: string, path: string, body?: unknown) {
  const coalescable = method === 'PUT' || method === 'PATCH'
  const key = coalescable ? `${method} ${path}` : `${method} ${path} ${crypto.randomUUID()}`
  const existing = coalescable ? entries.find((entry) => entry.key === key && entry !== inFlight) : undefined
  if (existing) {
    existing.body = method === 'PATCH' ? { ...(existing.body as object), ...(body as object) } : body
  } else {
    entries.push({ key, method, path, body })
  }
  void persist()
  schedule(FLUSH_DELAY_MS)
}

export async function flush(): Promise<boolean> {
  if (flushing) return false
  flushing = true
  clearTimeout(timer)
  try {
    while (entries.length) {
      const entry = entries[0]
      inFlight = entry
      try {
        await request(entry.method, entry.path, entry.body)
      } catch (error) {
        if (error instanceof NetworkError || (error instanceof ApiError && error.status >= 500)) {
          schedule(RETRY_DELAY_MS)
          return false
        }
        if (error instanceof ApiError && error.status === 401) {
          onUnauthorized()
          return false
        }
        console.warn('Dropping rejected change', entry, error)
      }
      entries.shift()
      await persist()
    }
    return true
  } finally {
    inFlight = undefined
    flushing = false
  }
}

function schedule(delay: number) {
  clearTimeout(timer)
  timer = setTimeout(() => void flush(), delay)
}

async function persist() {
  onChange(entries.length)
  await set(STORAGE_KEY, JSON.parse(JSON.stringify(entries))).catch(() => undefined)
}
