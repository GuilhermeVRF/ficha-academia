import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { UNDO_WINDOW_MS } from './routine'

interface Toast {
  id: number
  message: string
  actionLabel?: string
  action?: () => void
}

const STEP_KEY = 'weightStep'

export const useUiStore = defineStore('ui', () => {
  const toast = ref<Toast | null>(null)
  const weightStep = ref(readNumber(STEP_KEY, 2.5))
  let timer: ReturnType<typeof setTimeout> | undefined

  watch(weightStep, (value) => {
    try {
      localStorage.setItem(STEP_KEY, String(value))
    } catch {
      /* storage unavailable: keep the value for this session only */
    }
  })

  function showToast(message: string, actionLabel?: string, action?: () => void) {
    clearTimeout(timer)
    toast.value = { id: Date.now(), message, actionLabel, action }
    timer = setTimeout(() => (toast.value = null), UNDO_WINDOW_MS)
  }

  function runToastAction() {
    toast.value?.action?.()
    toast.value = null
  }

  return { toast, weightStep, showToast, runToastAction }
})

function readNumber(key: string, fallback: number) {
  try {
    const value = Number(localStorage.getItem(key))
    return value > 0 ? value : fallback
  } catch {
    return fallback
  }
}
