import { del } from 'idb-keyval'
import { resetDoneSets } from '@/composables/useDoneSets'
import { TREE_KEY } from '@/stores/routine'
import { clearOutbox } from './outbox'

const LOCAL_STORAGE_KEYS = ['lastWorkout']

/**
 * Forget everything this device cached for the previous account: pending
 * changes, the offline copy of the workouts and today's checkmarks. Without
 * this, the next person to sign in on the same phone would see (or replay)
 * someone else's data.
 */
export async function clearLocalData() {
  await clearOutbox()
  await del(TREE_KEY).catch(() => undefined)
  resetDoneSets()
  for (const key of LOCAL_STORAGE_KEYS) {
    try {
      localStorage.removeItem(key)
    } catch {
      /* storage unavailable */
    }
  }
}
