import { defineStore } from 'pinia'
import { get, set } from 'idb-keyval'
import { computed, ref, watch } from 'vue'
import { ApiError, NetworkError, request } from '@/lib/api'
import { enqueue, flush, initOutbox } from '@/lib/outbox'
import { unusedPlateColor } from '@/lib/plates'
import type { Exercise, PlateColor, SetData, Workout } from '@/types'

export const TREE_KEY = 'tree'
const DEFAULT_SETS: SetData[] = [
  { weight_kg: 0, reps: 10 },
  { weight_kg: 0, reps: 10 },
  { weight_kg: 0, reps: 10 },
]
/** How long a delete can be undone before it is sent to the server. */
export const UNDO_WINDOW_MS = 5000

export const useRoutineStore = defineStore('routine', () => {
  const workouts = ref<Workout[]>([])
  const loaded = ref(false)
  const pending = ref(0)
  const unauthorized = ref(false)

  const exerciseNames = computed(() => {
    const names = new Set<string>()
    for (const workout of workouts.value) for (const exercise of workout.exercises) names.add(exercise.name)
    return [...names].sort((a, b) => a.localeCompare(b, 'pt-BR'))
  })

  let watchingCache = false

  async function init() {
    await initOutbox({
      onUnauthorized: () => (unauthorized.value = true),
      onChange: (count) => (pending.value = count),
    })
    const cached = await get<Workout[]>(TREE_KEY).catch(() => undefined)
    if (cached) {
      workouts.value = cached
      loaded.value = true
    }
    await refresh()
    loaded.value = true
    if (!watchingCache) {
      watch(workouts, saveCache, { deep: true })
      watchingCache = true
    }
  }

  /** Forget the in-memory tree when signing out; the cache is cleared separately. */
  function reset() {
    workouts.value = []
    loaded.value = false
    unauthorized.value = false
  }

  /** Pull the server tree, but only once local changes are synced so they aren't overwritten. */
  async function refresh() {
    if (!(await flush())) return
    try {
      workouts.value = await request<Workout[]>('GET', '/workouts')
      unauthorized.value = false
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) unauthorized.value = true
      else if (!(error instanceof NetworkError)) throw error
    }
  }

  function saveCache() {
    void set(TREE_KEY, clone(workouts.value)).catch(() => undefined)
  }

  function findExercise(exerciseId: string) {
    for (const workout of workouts.value) {
      const exercise = workout.exercises.find((item) => item.id === exerciseId)
      if (exercise) return { workout, exercise }
    }
    return undefined
  }

  function addWorkout(name: string) {
    const color = unusedPlateColor(workouts.value.map((item) => item.color))
    const workout: Workout = { id: crypto.randomUUID(), name, position: workouts.value.length, color, exercises: [] }
    workouts.value.push(workout)
    enqueue('POST', '/workouts', { id: workout.id, name, color })
    return workout
  }

  function setWorkoutColor(workoutId: string, color: PlateColor) {
    const workout = workouts.value.find((item) => item.id === workoutId)
    if (!workout) return
    workout.color = color
    enqueue('PATCH', `/workouts/${workoutId}`, { color })
  }

  function renameWorkout(workoutId: string, name: string) {
    const workout = workouts.value.find((item) => item.id === workoutId)
    if (!workout) return
    workout.name = name
    enqueue('PATCH', `/workouts/${workoutId}`, { name })
  }

  function deleteWorkout(workoutId: string) {
    workouts.value = workouts.value.filter((item) => item.id !== workoutId)
    enqueue('DELETE', `/workouts/${workoutId}`)
  }

  function reorderWorkouts(ids: string[]) {
    workouts.value.sort((a, b) => ids.indexOf(a.id) - ids.indexOf(b.id))
    enqueue('PUT', '/workouts/order', { ids })
  }

  /** Add an exercise, reusing the sets of an existing exercise with the same name. */
  function addExercise(workoutId: string, name: string) {
    const workout = workouts.value.find((item) => item.id === workoutId)
    if (!workout) return
    const template = workouts.value
      .flatMap((item) => item.exercises)
      .find((item) => item.name.toLowerCase() === name.toLowerCase())
    const exercise: Exercise = {
      id: crypto.randomUUID(),
      name,
      position: workout.exercises.length,
      notes: '',
      rest_seconds: null,
      sets: clone(template?.sets ?? DEFAULT_SETS),
    }
    workout.exercises.push(exercise)
    enqueue('POST', `/workouts/${workoutId}/exercises`, {
      id: exercise.id,
      name,
      sets: exercise.sets,
    })
    return exercise
  }

  function updateExercise(exerciseId: string, patch: Partial<Pick<Exercise, 'name' | 'notes' | 'rest_seconds'>>) {
    const found = findExercise(exerciseId)
    if (!found) return
    Object.assign(found.exercise, patch)
    enqueue('PATCH', `/exercises/${exerciseId}`, patch)
  }

  function moveExercise(exerciseId: string, targetWorkoutId: string) {
    const found = findExercise(exerciseId)
    const target = workouts.value.find((item) => item.id === targetWorkoutId)
    if (!found || !target || found.workout === target) return
    found.workout.exercises = found.workout.exercises.filter((item) => item.id !== exerciseId)
    target.exercises.push(found.exercise)
    enqueue('PATCH', `/exercises/${exerciseId}`, { workout_id: targetWorkoutId })
  }

  function setSets(exerciseId: string, sets: SetData[]) {
    const found = findExercise(exerciseId)
    if (!found) return
    found.exercise.sets = sets
    enqueue('PUT', `/exercises/${exerciseId}/sets`, { sets })
  }

  /**
   * Remove an exercise locally right away and send the delete only after the
   * undo window, since deleting on the server also wipes its history.
   * Returns a function that restores it.
   */
  function deleteExercise(exerciseId: string) {
    const found = findExercise(exerciseId)
    if (!found) return () => {}
    const { workout, exercise } = found
    const index = workout.exercises.indexOf(exercise)
    workout.exercises.splice(index, 1)
    const timer = setTimeout(() => enqueue('DELETE', `/exercises/${exerciseId}`), UNDO_WINDOW_MS)
    return () => {
      clearTimeout(timer)
      workout.exercises.splice(index, 0, exercise)
    }
  }

  function reorderExercises(workoutId: string, ids: string[]) {
    enqueue('PUT', `/workouts/${workoutId}/order`, { ids })
  }

  return {
    workouts,
    loaded,
    pending,
    unauthorized,
    exerciseNames,
    init,
    reset,
    refresh,
    findExercise,
    addWorkout,
    renameWorkout,
    setWorkoutColor,
    deleteWorkout,
    reorderWorkouts,
    addExercise,
    updateExercise,
    moveExercise,
    setSets,
    deleteExercise,
    reorderExercises,
  }
})

/** Plain deep copy, stripping Vue proxies (IndexedDB and outbox need plain data). */
function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value))
}
