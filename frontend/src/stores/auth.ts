import { defineStore } from 'pinia'
import { del, get, set } from 'idb-keyval'
import { ref } from 'vue'
import { NetworkError, request } from '@/lib/api'
import { clearLocalData } from '@/lib/localData'
import { flush } from '@/lib/outbox'
import type { User } from '@/types'

/** Last signed-in user; doubles as the owner of the data cached on this device. */
const USER_KEY = 'user'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  let ready: Promise<void> | undefined

  /** Resolve who is signed in, once. Offline, the cached user keeps the app usable. */
  function init() {
    ready ??= load()
    return ready
  }

  async function load() {
    const cached = await get<User>(USER_KEY).catch(() => undefined)
    try {
      const current = await request<User>('GET', '/auth/me')
      // The cookie may now belong to someone else (e.g. signed in from another tab).
      if (cached && cached.id !== current.id) await clearLocalData()
      remember(current)
    } catch (error) {
      user.value = error instanceof NetworkError ? (cached ?? null) : null
    }
  }

  /** Log in or sign up; wipes local data first if it belonged to another account. */
  async function signIn(path: '/auth/login' | '/auth/signup', body: Record<string, unknown>) {
    const next = await request<User>('POST', path, body)
    const previous = await get<User>(USER_KEY).catch(() => undefined)
    if (previous && previous.id !== next.id) await clearLocalData()
    remember(next)
  }

  /** The server stopped accepting our session. Local data stays, in case the same person signs back in. */
  function expire() {
    user.value = null
  }

  /** Sync what we can, end the session and forget this account's data on the device. */
  async function logout() {
    await flush().catch(() => false)
    await request('POST', '/auth/logout').catch(() => undefined)
    await clearLocalData()
    await del(USER_KEY).catch(() => undefined)
    user.value = null
  }

  function remember(next: User) {
    user.value = next
    void set(USER_KEY, { ...next }).catch(() => undefined)
  }

  return { user, init, signIn, expire, logout }
})
