import { del } from 'idb-keyval'
import { SESSIONS_KEY } from '@/stores/history'
import { TREE_KEY } from '@/stores/routine'
import { ACTIVE_SESSION_KEY } from '@/stores/session'
import { clearOutbox } from './outbox'

const LOCAL_STORAGE_KEYS = ['lastWorkout', 'doneSets']

/**
 * Forget everything this device cached for the previous account: pending
 * changes, the offline copy of workouts and sessions, and any workout in progress. Without
 * this, the next person to sign in on the same phone would see (or replay)
 * someone else's data.
 */
export async function clearLocalData() {
  await clearOutbox()
  for (const key of [TREE_KEY, SESSIONS_KEY, ACTIVE_SESSION_KEY]) await del(key).catch(() => undefined)
  for (const key of LOCAL_STORAGE_KEYS) {
    try {
      localStorage.removeItem(key)
    } catch {
      /* storage unavailable */
    }
  }
}
