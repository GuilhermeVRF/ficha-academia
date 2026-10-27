import { ref, watch } from 'vue'

/**
 * "Follow-along" checkmarks for today's session. Purely local and ephemeral:
 * they reset on the next day and are never sent to the server.
 */
const STORAGE_KEY = 'doneSets'
const today = () => new Date().toLocaleDateString('sv-SE')

const done = ref<Set<string>>(load())

watch(
  done,
  (value) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ day: today(), keys: [...value] }))
    } catch {
      /* storage unavailable */
    }
  },
  { deep: true },
)

function load(): Set<string> {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null')
    return saved?.day === today() ? new Set(saved.keys) : new Set()
  } catch {
    return new Set()
  }
}

export function useDoneSets() {
  const key = (exerciseId: string, index: number) => `${exerciseId}:${index}`

  function isDone(exerciseId: string, index: number) {
    return done.value.has(key(exerciseId, index))
  }

  function toggle(exerciseId: string, index: number) {
    const item = key(exerciseId, index)
    if (done.value.has(item)) done.value.delete(item)
    else done.value.add(item)
  }

  function clearWorkout(exerciseIds: string[]) {
    for (const item of [...done.value]) if (exerciseIds.some((id) => item.startsWith(`${id}:`))) done.value.delete(item)
  }

  return { isDone, toggle, clearWorkout }
}
