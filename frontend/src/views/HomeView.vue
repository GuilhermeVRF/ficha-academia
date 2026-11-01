<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import MonthCalendar from '@/components/MonthCalendar.vue'
import { dayKey, formatDuration, formatLongDate, relativeDays, startOfWeek, weekStreak } from '@/lib/dates'
import { formatWeight } from '@/lib/format'
import { plateBg } from '@/lib/plates'
import { useAuthStore } from '@/stores/auth'
import { useHistoryStore } from '@/stores/history'
import { useRoutineStore } from '@/stores/routine'
import { useSessionStore } from '@/stores/session'
import type { Workout } from '@/types'

const auth = useAuthStore()
const history = useHistoryStore()
const routine = useRoutineStore()
const session = useSessionStore()
const router = useRouter()

const now = ref(new Date())
let ticker: ReturnType<typeof setInterval> | undefined
onMounted(() => (ticker = setInterval(() => (now.value = new Date()), 1000)))
onUnmounted(() => clearInterval(ticker))

const greeting = computed(() => {
  const hour = now.value.getHours()
  const part = hour < 12 ? 'Bom dia' : hour < 18 ? 'Boa tarde' : 'Boa noite'
  const firstName = auth.user?.name.split(' ')[0]
  return firstName ? `${part}, ${firstName}` : part
})

const activeWorkout = computed(() => routine.workouts.find((item) => item.id === session.active?.workout_id))

/** The workout after the last one trained, following the list order (A → B → C → A). */
const nextWorkout = computed<Workout | undefined>(() => {
  const workouts = routine.workouts.filter((item) => item.exercises.length)
  if (!workouts.length) return routine.workouts[0]
  const lastIndex = workouts.findIndex((item) => item.id === history.latest?.workout_id)
  return workouts[(lastIndex + 1) % workouts.length]
})

function lastTrained(workoutId: string) {
  const found = history.sessions.find((item) => item.workout_id === workoutId)
  return found ? relativeDays(new Date(found.started_at), now.value) : 'nunca treinado'
}

const thisWeek = computed(() => {
  const start = startOfWeek(now.value)
  return history.sessions.filter((item) => new Date(item.started_at) >= start).length
})
const streak = computed(() => weekStreak(history.sessions.map((item) => new Date(item.started_at)), now.value))

const shownYear = ref(now.value.getFullYear())
const shownMonth = ref(now.value.getMonth())
const selectedDay = ref(dayKey(now.value))
const selectedSessions = computed(() => history.byDay.get(selectedDay.value) ?? [])
const selectedLabel = computed(() => {
  const [year, month, day] = selectedDay.value.split('-').map(Number)
  return selectedDay.value === dayKey(now.value) ? 'Hoje' : formatLongDate(new Date(year, month - 1, day))
})

watch([shownYear, shownMonth], ([year, month]) => void history.ensureMonth(year, month))

function moveMonth(delta: number) {
  const target = new Date(shownYear.value, shownMonth.value + delta, 1)
  shownYear.value = target.getFullYear()
  shownMonth.value = target.getMonth()
}

function start(workout: Workout) {
  session.start(workout)
  void router.push(`/treino/${workout.id}/sessao`)
}

function duration(item: { started_at: string; finished_at: string }) {
  return formatDuration(new Date(item.finished_at).getTime() - new Date(item.started_at).getTime())
}
</script>

<template>
  <div class="pt-safe pb-safe mx-auto flex max-w-lg flex-col gap-4 px-4">
    <header class="flex items-start gap-2 pt-4">
      <div class="min-w-0 flex-1">
        <p class="text-sm text-subtle first-letter:uppercase">{{ formatLongDate(now) }}</p>
        <h1 class="font-display text-3xl font-extrabold tracking-wide uppercase">{{ greeting }}</h1>
      </div>
      <RouterLink to="/fichas" class="rounded-lg bg-surface px-3 py-2 text-sm font-semibold">Fichas</RouterLink>
      <RouterLink to="/ajustes" class="rounded-lg px-2 py-1 text-xl text-muted" aria-label="Ajustes">⚙</RouterLink>
    </header>

    <section v-if="session.active" class="flex flex-col gap-3 rounded-2xl bg-accent p-4 text-on-accent">
      <p class="text-xs font-semibold tracking-widest uppercase opacity-70">Treino em andamento</p>
      <div class="flex items-end justify-between gap-3">
        <p class="font-display text-3xl leading-none font-extrabold uppercase">{{ session.active.workout_name }}</p>
        <p class="font-display text-3xl leading-none font-bold tabular-nums">
          {{ formatDuration(now.getTime() - new Date(session.active.started_at).getTime()) }}
        </p>
      </div>
      <RouterLink
        :to="`/treino/${session.active.workout_id}/sessao`"
        class="rounded-xl bg-on-accent py-3 text-center font-semibold text-accent"
      >
        Continuar treino
      </RouterLink>
      <p v-if="!activeWorkout" class="text-sm">Esta ficha foi apagada. Descarte o treino na tela dele.</p>
    </section>

    <section v-else-if="nextWorkout" class="flex flex-col gap-3 rounded-2xl bg-surface p-4">
      <p class="text-xs font-semibold tracking-widest text-subtle uppercase">Próximo treino</p>
      <div class="flex items-center gap-3">
        <span class="h-8 w-8 shrink-0 rounded-full ring-4 ring-bg" :class="plateBg(nextWorkout.color)" aria-hidden="true" />
        <div class="min-w-0">
          <p class="truncate font-display text-3xl leading-none font-extrabold uppercase">{{ nextWorkout.name }}</p>
          <p class="text-sm text-subtle">
            {{ nextWorkout.exercises.length }} exercícios · {{ lastTrained(nextWorkout.id) }}
          </p>
        </div>
      </div>
      <button
        type="button"
        class="rounded-xl bg-accent py-3 font-semibold text-on-accent disabled:opacity-40"
        :disabled="!nextWorkout.exercises.length"
        @click="start(nextWorkout)"
      >
        Iniciar treino
      </button>
    </section>

    <section v-else class="flex flex-col items-center gap-3 rounded-2xl bg-surface p-6 text-center">
      <p class="text-muted">Você ainda não tem fichas.</p>
      <RouterLink to="/fichas" class="rounded-xl bg-accent px-5 py-3 font-semibold text-on-accent">Criar minha ficha</RouterLink>
    </section>

    <section class="grid grid-cols-2 gap-3">
      <div class="rounded-2xl bg-surface p-4">
        <p class="text-xs text-subtle">Treinos nesta semana</p>
        <p class="font-display text-4xl font-extrabold tabular-nums">{{ thisWeek }}</p>
      </div>
      <div class="rounded-2xl bg-surface p-4">
        <p class="text-xs text-subtle">Semanas seguidas</p>
        <p class="font-display text-4xl font-extrabold tabular-nums">{{ streak }}</p>
      </div>
    </section>

    <MonthCalendar
      :year="shownYear"
      :month="shownMonth"
      :by-day="history.byDay"
      :selected="selectedDay"
      @select="selectedDay = $event"
      @move="moveMonth"
    />

    <section class="flex flex-col gap-2" aria-live="polite">
      <h2 class="text-sm font-medium text-muted first-letter:uppercase">{{ selectedLabel }}</h2>
      <p v-if="!selectedSessions.length" class="text-sm text-subtle">Nenhum treino neste dia.</p>
      <RouterLink
        v-for="item in selectedSessions"
        :key="item.id"
        :to="`/sessao/${item.id}`"
        class="flex items-center gap-3 rounded-xl bg-surface px-4 py-3"
      >
        <span class="h-3 w-3 shrink-0 rounded-full" :class="plateBg(item.workout_color)" aria-hidden="true" />
        <span class="min-w-0 flex-1">
          <span class="block truncate font-semibold">{{ item.workout_name }}</span>
          <span class="block text-xs text-subtle">
            {{ new Date(item.started_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) }}
            · {{ duration(item) }} · {{ item.sets_done }} séries · {{ formatWeight(Math.round(item.volume_kg)) }} kg
          </span>
        </span>
        <span class="text-subtle" aria-hidden="true">›</span>
      </RouterLink>
    </section>
  </div>
</template>
