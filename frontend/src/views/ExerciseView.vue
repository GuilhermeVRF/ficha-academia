<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import HistoryChart from '@/components/HistoryChart.vue'
import { request } from '@/lib/api'
import { formatLongDate } from '@/lib/dates'
import { formatSets } from '@/lib/format'
import { useRoutineStore } from '@/stores/routine'
import { useUiStore } from '@/stores/ui'
import type { ExerciseSessionPoint, HistoryPoint } from '@/types'

const props = defineProps<{ id: string }>()

const routine = useRoutineStore()
const ui = useUiStore()
const router = useRouter()

const found = computed(() => routine.findExercise(props.id))
const history = ref<HistoryPoint[] | null>(null)
const historyError = ref(false)
const sessions = ref<ExerciseSessionPoint[]>([])

onMounted(async () => {
  try {
    history.value = await request<HistoryPoint[]>('GET', `/exercises/${props.id}/history`)
    sessions.value = await request<ExerciseSessionPoint[]>('GET', `/exercises/${props.id}/sessions`)
  } catch {
    historyError.value = true
  }
})

function saveText(field: 'name' | 'notes', event: Event) {
  const value = (event.target as HTMLInputElement).value.trim()
  if (!found.value || value === found.value.exercise[field]) return
  if (field === 'name' && !value) return
  routine.updateExercise(props.id, { [field]: value })
}

function saveRest(event: Event) {
  const raw = (event.target as HTMLInputElement).value
  const value = raw ? Math.max(0, Math.round(Number(raw))) : null
  if (!found.value || value === found.value.exercise.rest_seconds || Number.isNaN(value)) return
  routine.updateExercise(props.id, { rest_seconds: value })
}

function move(event: Event) {
  routine.moveExercise(props.id, (event.target as HTMLSelectElement).value)
}

function remove() {
  const name = found.value?.exercise.name
  const workoutId = found.value?.workout.id
  const undo = routine.deleteExercise(props.id)
  ui.showToast(`"${name}" removido`, 'Desfazer', undo)
  router.replace(workoutId ? `/treino/${workoutId}` : '/fichas')
}


function formatDate(isoDate: string) {
  return new Date(`${isoDate}T12:00:00`).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' })
}
</script>

<template>
  <div class="pt-safe pb-safe mx-auto max-w-lg px-4">
    <header class="flex items-center gap-2 py-3">
      <button type="button" class="-ml-2 px-2 text-2xl text-muted" aria-label="Voltar" @click="router.back()">‹</button>
      <h1 class="text-sm text-subtle">Exercício</h1>
    </header>

    <p v-if="!found" class="mt-10 text-center text-subtle">Exercício não encontrado.</p>

    <template v-else>
      <input
        :value="found.exercise.name"
        class="w-full bg-transparent text-2xl font-bold outline-none"
        enterkeyhint="done"
        @blur="saveText('name', $event)"
        @keydown.enter="($event.target as HTMLInputElement).blur()"
      />

      <section class="mt-6">
        <h2 class="mb-2 text-sm font-medium text-muted">Evolução da carga máxima</h2>
        <div class="rounded-2xl bg-surface p-3">
          <p v-if="historyError" class="py-8 text-center text-sm text-subtle">Histórico indisponível offline.</p>
          <p v-else-if="!history" class="py-8 text-center text-sm text-subtle">Carregando…</p>
          <p v-else-if="history.length < 2" class="py-8 text-center text-sm text-subtle">
            O gráfico aparece quando você alterar a carga em dias diferentes.
          </p>
          <HistoryChart v-else :points="history" />
        </div>
        <ul v-if="history?.length" class="mt-3 divide-y divide-line text-sm">
          <li v-for="point in [...history].reverse()" :key="point.date" class="flex justify-between gap-4 py-2">
            <span class="text-muted">{{ formatDate(point.date) }}</span>
            <span class="text-right tabular-nums text-fg">{{ formatSets(point.sets) }}</span>
          </li>
        </ul>
      </section>

      <section v-if="sessions.length" class="mt-6">
        <h2 class="mb-2 text-sm font-medium text-muted">Últimos treinos</h2>
        <ul class="divide-y divide-line text-sm">
          <li v-for="point in sessions" :key="point.session_id">
            <RouterLink :to="`/sessao/${point.session_id}`" class="flex justify-between gap-4 py-2">
              <span class="text-muted first-letter:uppercase">{{ formatLongDate(new Date(point.started_at)) }}</span>
              <span class="text-right tabular-nums text-fg">{{ formatSets(point.sets) }}</span>
            </RouterLink>
          </li>
        </ul>
      </section>

      <section class="mt-6 flex flex-col gap-3">
        <label class="flex flex-col gap-1 text-sm text-muted">
          Observações
          <textarea
            :value="found.exercise.notes"
            rows="2"
            placeholder="Ex.: banco no 3º furo, pegada fechada"
            class="rounded-xl bg-surface px-3 py-2 text-fg outline-none focus:ring-2 focus:ring-accent"
            @blur="saveText('notes', $event)"
          />
        </label>
        <label class="flex items-center justify-between gap-3 text-sm text-muted">
          Descanso (segundos)
          <input
            :value="found.exercise.rest_seconds ?? ''"
            inputmode="numeric"
            placeholder="—"
            class="w-24 rounded-xl bg-surface px-3 py-2 text-right text-fg outline-none focus:ring-2 focus:ring-accent"
            @blur="saveRest"
          />
        </label>
        <label class="flex items-center justify-between gap-3 text-sm text-muted">
          Ficha
          <select
            :value="found.workout.id"
            class="rounded-xl bg-surface px-3 py-2 text-fg outline-none"
            @change="move"
          >
            <option v-for="workout in routine.workouts" :key="workout.id" :value="workout.id">{{ workout.name }}</option>
          </select>
        </label>
      </section>

      <button type="button" class="mt-10 w-full rounded-xl bg-danger/15 py-3 text-danger" @click="remove">
        Remover exercício
      </button>
    </template>
  </div>
</template>
