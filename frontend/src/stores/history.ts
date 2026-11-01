import { defineStore } from 'pinia'
import { get, set } from 'idb-keyval'
import { computed, ref } from 'vue'
import { NetworkError, request } from '@/lib/api'
import { addDays, dayKey, startOfDay } from '@/lib/dates'
import { enqueue, flush } from '@/lib/outbox'
import type { SessionSummary } from '@/types'

export const SESSIONS_KEY = 'sessions'
/** How far back the first load goes; older months are fetched when the calendar opens them. */
const INITIAL_DAYS = 180

/** Finished sessions, kept offline so the calendar works without a connection. */
export const useHistoryStore = defineStore('history', () => {
  const sessions = ref<SessionSummary[]>([])
  const loadedMonths = new Set<string>()

  const byDay = computed(() => {
    const days = new Map<string, SessionSummary[]>()
    for (const item of sessions.value) {
      const key = dayKey(new Date(item.started_at))
      days.set(key, [...(days.get(key) ?? []), item])
    }
    return days
  })

  /** Newest first. */
  const latest = computed(() => sessions.value[0])

  async function init() {
    const cached = await get<SessionSummary[]>(SESSIONS_KEY).catch(() => undefined)
    if (cached) sessions.value = cached
    await fetchRange(addDays(startOfDay(new Date()), -INITIAL_DAYS), addDays(startOfDay(new Date()), 1))
  }

  /** Make sure a calendar month is loaded (no-op when it already is or when offline). */
  async function ensureMonth(year: number, month: number) {
    const key = `${year}-${month}`
    if (loadedMonths.has(key)) return
    if (await fetchRange(new Date(year, month, 1), new Date(year, month + 1, 1))) loadedMonths.add(key)
  }

  /** Replace what we know about [start, end) with the server's view, once local changes are synced. */
  async function fetchRange(start: Date, end: Date) {
    if (!(await flush())) return false
    try {
      const fresh = await request<SessionSummary[]>(
        'GET',
        `/sessions?start=${encodeURIComponent(start.toISOString())}&end=${encodeURIComponent(end.toISOString())}`,
      )
      const outside = sessions.value.filter((item) => {
        const started = new Date(item.started_at)
        return started < start || started >= end
      })
      replace([...outside, ...fresh])
      return true
    } catch (error) {
      if (error instanceof NetworkError) return false
      throw error
    }
  }

  /** Show a just-finished session right away, before (or without) the server answering. */
  function addLocal(summary: SessionSummary) {
    replace([summary, ...sessions.value.filter((item) => item.id !== summary.id)])
  }

  function remove(sessionId: string) {
    replace(sessions.value.filter((item) => item.id !== sessionId))
    enqueue('DELETE', `/sessions/${sessionId}`)
  }

  function reset() {
    sessions.value = []
    loadedMonths.clear()
  }

  function replace(next: SessionSummary[]) {
    sessions.value = next.sort((a, b) => b.started_at.localeCompare(a.started_at))
    void set(SESSIONS_KEY, JSON.parse(JSON.stringify(sessions.value))).catch(() => undefined)
  }

  return { sessions, byDay, latest, init, ensureMonth, addLocal, remove, reset }
})
