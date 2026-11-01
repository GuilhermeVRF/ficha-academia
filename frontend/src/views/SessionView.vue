<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import ExerciseCard from '@/components/ExerciseCard.vue'
import { formatDuration } from '@/lib/dates'
import { useRoutineStore } from '@/stores/routine'
import { useSessionStore } from '@/stores/session'

const props = defineProps<{ id: string }>()

const REST_STEP_SECONDS = 30

const routine = useRoutineStore()
const session = useSessionStore()
const router = useRouter()

const workout = computed(() => routine.workouts.find((item) => item.id === props.id))
const active = computed(() => (session.active?.workout_id === props.id ? session.active : null))

const totalSets = computed(() => workout.value?.exercises.reduce((total, item) => total + item.sets.length, 0) ?? 0)
const doneSets = computed(() => active.value?.done.length ?? 0)

const now = ref(Date.now())
let ticker: ReturnType<typeof setInterval> | undefined
let wakeLock: { release: () => Promise<void> } | null = null

onMounted(async () => {
  if (!active.value) {
    // Opened by URL with no workout running here: go to the one running, or back to the workout.
    void router.replace(session.active ? `/treino/${session.active.workout_id}/sessao` : `/treino/${props.id}`)
    return
  }
  ticker = setInterval(() => (now.value = Date.now()), 250)
  // Keep the screen on while training; refused silently where unsupported.
  const nav = navigator as Navigator & { wakeLock?: { request: (type: 'screen') => Promise<{ release: () => Promise<void> }> } }
  wakeLock = (await nav.wakeLock?.request('screen').catch(() => null)) ?? null
})

onUnmounted(() => {
  clearInterval(ticker)
  void wakeLock?.release().catch(() => undefined)
})

const elapsed = computed(() => (active.value ? formatDuration(now.value - new Date(active.value.started_at).getTime()) : ''))
const restLeft = computed(() => {
  const ends = active.value?.rest_ends_at
  return ends ? Math.max(0, ends - now.value) : 0
})

// Buzz once when the rest is over, then hide the bar.
watch(restLeft, (left, previous) => {
  if (left === 0 && previous > 0) {
    navigator.vibrate?.([200, 100, 200])
    session.skipRest()
  }
})

function finish() {
  if (!workout.value || !active.value) return
  if (!doneSets.value && !confirm('Nenhuma série marcada. Finalizar mesmo assim?')) return
  const sessionId = session.finish(workout.value)
  void router.replace({ path: `/sessao/${sessionId}`, query: { novo: '1' } })
}

function discard() {
  if (!confirm('Descartar este treino? Ele não vai aparecer no calendário.')) return
  session.discard()
  void router.replace(workout.value ? `/treino/${props.id}` : '/')
}
</script>

<template>
  <div v-if="active" class="pt-safe mx-auto flex min-h-dvh max-w-lg flex-col">
    <header class="sticky top-0 z-10 flex items-center gap-3 bg-bg/95 px-4 py-3 backdrop-blur">
      <div class="min-w-0 flex-1">
        <p class="text-xs font-semibold tracking-widest text-accent-ink uppercase">Em andamento · {{ doneSets }}/{{ totalSets }} séries</p>
        <p class="truncate font-display text-2xl leading-tight font-extrabold tracking-wide uppercase">{{ active.workout_name }}</p>
      </div>
      <p class="font-display text-3xl font-bold tabular-nums" aria-label="Tempo de treino">{{ elapsed }}</p>
    </header>
    <div class="h-1 bg-raised" aria-hidden="true">
      <div class="h-full bg-accent transition-[width]" :style="{ width: `${totalSets ? (doneSets / totalSets) * 100 : 0}%` }" />
    </div>

    <p v-if="!workout" class="mx-4 mt-6 rounded-xl bg-surface p-4 text-sm text-muted">
      A ficha deste treino foi apagada. Você pode descartar o treino abaixo.
    </p>

    <main v-else class="flex flex-1 flex-col gap-3 px-3 pt-3 pb-44">
      <ExerciseCard v-for="exercise in workout.exercises" :key="exercise.id" :exercise="exercise" tracking />
      <p class="px-1 text-center text-xs text-subtle">Toque no número da série para marcar como feita. Ajustar carga aqui também atualiza a ficha.</p>
    </main>

    <div class="fixed inset-x-0 bottom-0 z-10 bg-gradient-to-t from-bg via-bg/95 to-transparent px-4 pt-6 pb-[calc(env(safe-area-inset-bottom)+1rem)]">
      <div class="mx-auto flex max-w-lg flex-col gap-2">
        <div v-if="restLeft > 0" class="flex items-center gap-3 rounded-xl bg-raised px-4 py-2" role="timer" aria-live="off">
          <span class="text-xs font-semibold tracking-widest text-subtle uppercase">Descanso</span>
          <span class="flex-1 font-display text-3xl font-bold tabular-nums">{{ formatDuration(restLeft + 999) }}</span>
          <button type="button" class="rounded-lg bg-surface px-3 py-2 text-sm font-semibold" @click="session.extendRest(REST_STEP_SECONDS)">
            +{{ REST_STEP_SECONDS }}s
          </button>
          <button type="button" class="rounded-lg px-3 py-2 text-sm text-muted" @click="session.skipRest()">Pular</button>
        </div>
        <button
          v-if="workout"
          type="button"
          class="w-full rounded-xl bg-accent py-4 font-display text-xl font-extrabold tracking-wide text-on-accent uppercase"
          @click="finish"
        >
          Finalizar treino
        </button>
        <button type="button" class="py-1 text-sm text-subtle" @click="discard">Descartar treino</button>
      </div>
    </div>
  </div>
</template>
