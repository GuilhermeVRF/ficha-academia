import { defineStore } from 'pinia'
import { del, get, set } from 'idb-keyval'
import { ref, watch } from 'vue'
import { enqueue } from '@/lib/outbox'
import type { SessionDetail, SessionSet, Workout } from '@/types'
import { useHistoryStore } from './history'

export const ACTIVE_SESSION_KEY = 'activeSession'
/** Rest used when the exercise has no rest time set. */
export const DEFAULT_REST_SECONDS = 90

interface ActiveSession {
  id: string
  workout_id: string
  workout_name: string
  started_at: string
  /** Keys "exerciseId:setIndex" of the sets marked as done. */
  done: string[]
  /** Epoch ms when the current rest ends, if resting. */
  rest_ends_at: number | null
}

/**
 * The workout being trained right now. It lives on the device (survives
 * reloads and offline) until "Finalizar" turns it into a session sent
 * through the outbox.
 */
export const useSessionStore = defineStore('session', () => {
  const active = ref<ActiveSession | null>(null)
  /** The last session finished on this device, so its summary shows even before it syncs. */
  const lastFinished = ref<SessionDetail | null>(null)
  let persisting = false

  async function init() {
    active.value = (await get<ActiveSession>(ACTIVE_SESSION_KEY).catch(() => undefined)) ?? null
    if (!persisting) {
      watch(active, persist, { deep: true })
      persisting = true
    }
  }

  function start(workout: Workout) {
    active.value = {
      id: crypto.randomUUID(),
      workout_id: workout.id,
      workout_name: workout.name,
      started_at: new Date().toISOString(),
      done: [],
      rest_ends_at: null,
    }
    return active.value
  }

  function isDone(exerciseId: string, index: number) {
    return active.value?.done.includes(key(exerciseId, index)) ?? false
  }

  /** Mark or unmark a set; marking it done starts the rest countdown. */
  function toggle(exerciseId: string, index: number, restSeconds: number | null) {
    if (!active.value) return
    const item = key(exerciseId, index)
    if (active.value.done.includes(item)) {
      active.value.done = active.value.done.filter((other) => other !== item)
      return
    }
    active.value.done.push(item)
    active.value.rest_ends_at = Date.now() + (restSeconds ?? DEFAULT_REST_SECONDS) * 1000
  }

  function extendRest(seconds: number) {
    if (active.value?.rest_ends_at) active.value.rest_ends_at += seconds * 1000
  }

  function skipRest() {
    if (active.value) active.value.rest_ends_at = null
  }

  /**
   * Record the session with the workout's current loads and the done marks,
   * queue it for the server and show it in the calendar immediately.
   */
  function finish(workout: Workout) {
    const current = active.value
    if (!current) return null
    const sets: SessionSet[] = workout.exercises.flatMap((exercise, position) =>
      exercise.sets.map((item, index) => ({
        exercise_id: exercise.id,
        exercise_name: exercise.name,
        exercise_position: position,
        set_index: index,
        weight_kg: item.weight_kg,
        reps: item.reps,
        done: current.done.includes(key(exercise.id, index)),
      })),
    )
    const payload = {
      workout_id: current.workout_id,
      workout_name: workout.name,
      started_at: current.started_at,
      finished_at: new Date().toISOString(),
      notes: '',
      sets,
    }
    enqueue('PUT', `/sessions/${current.id}`, payload)

    const done = sets.filter((item) => item.done)
    const detail: SessionDetail = {
      ...payload,
      id: current.id,
      workout_color: workout.color,
      sets_done: done.length,
      volume_kg: done.reduce((total, item) => total + item.weight_kg * item.reps, 0),
    }
    useHistoryStore().addLocal(detail)
    lastFinished.value = detail
    active.value = null
    return detail.id
  }

  function discard() {
    active.value = null
  }

  function reset() {
    active.value = null
    lastFinished.value = null
  }

  function persist() {
    const value = active.value
    void (value ? set(ACTIVE_SESSION_KEY, JSON.parse(JSON.stringify(value))) : del(ACTIVE_SESSION_KEY)).catch(
      () => undefined,
    )
  }

  return { active, lastFinished, init, start, isDone, toggle, extendRest, skipRest, finish, discard, reset }
})

function key(exerciseId: string, index: number) {
  return `${exerciseId}:${index}`
}
