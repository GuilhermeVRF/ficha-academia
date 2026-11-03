<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import ExercisePicker from '@/components/ExercisePicker.vue'
import HistoryChart from '@/components/HistoryChart.vue'
import Stepper from '@/components/Stepper.vue'
import { request } from '@/lib/api'
import { formatLongDate } from '@/lib/dates'
import { formatSets } from '@/lib/format'
import { DEFAULT_REST_SECONDS } from '@/stores/session'
import { useRoutineStore } from '@/stores/routine'
import { useUiStore } from '@/stores/ui'
import type { CatalogItem, ExerciseSessionPoint, HistoryPoint, SetData } from '@/types'

const props = defineProps<{ id: string }>()

const REST_PRESETS = [30, 60, 90, 120, 180]
const MAX_SETS = 20

const routine = useRoutineStore()
const ui = useUiStore()
const router = useRouter()

const found = computed(() => routine.findExercise(props.id))
const tab = ref<'editar' | 'evolucao'>('editar')
const history = ref<HistoryPoint[] | null>(null)
const historyError = ref(false)
const sessions = ref<ExerciseSessionPoint[]>([])
const linking = ref(false)
const customRest = ref(false)

const rest = computed(() => found.value?.exercise.rest_seconds ?? null)
const restIsPreset = computed(() => rest.value === null || REST_PRESETS.includes(rest.value))

onMounted(async () => {
  customRest.value = !restIsPreset.value
  try {
    history.value = await request<HistoryPoint[]>('GET', `/exercises/${props.id}/history`)
    sessions.value = await request<ExerciseSessionPoint[]>('GET', `/exercises/${props.id}/sessions`)
  } catch {
    historyError.value = true
  }
})

function backToWorkout() {
  void router.replace(found.value ? `/treino/${found.value.workout.id}` : '/fichas')
}

function saveText(field: 'name' | 'notes', event: Event) {
  const value = (event.target as HTMLInputElement).value.trim()
  if (!found.value || value === found.value.exercise[field]) return
  if (field === 'name' && !value) return
  routine.updateExercise(props.id, { [field]: value })
}

function setRest(seconds: number | null) {
  customRest.value = false
  if (found.value && seconds !== rest.value) routine.updateExercise(props.id, { rest_seconds: seconds })
}

function saveCustomRest(event: Event) {
  const raw = (event.target as HTMLInputElement).value
  const value = raw ? Math.max(0, Math.round(Number(raw))) : null
  if (!found.value || Number.isNaN(value) || value === rest.value) return
  routine.updateExercise(props.id, { rest_seconds: value })
}

function updateSet(index: number, value: SetData) {
  if (!found.value) return
  routine.setSets(
    props.id,
    found.value.exercise.sets.map((item, i) => (i === index ? value : item)),
  )
}

function addSet() {
  if (!found.value) return
  const sets = found.value.exercise.sets
  routine.setSets(props.id, [...sets, { ...(sets.at(-1) ?? { weight_kg: 0, reps: 10 }) }])
}

function removeSet(index: number) {
  if (!found.value) return
  const previous = found.value.exercise.sets
  routine.setSets(
    props.id,
    previous.filter((_, i) => i !== index),
  )
  ui.showToast(`Série ${index + 1} removida`, 'Desfazer', () => routine.setSets(props.id, previous))
}

function applyFirstToAll() {
  if (!found.value) return
  const [first] = found.value.exercise.sets
  if (first) routine.setSets(props.id, found.value.exercise.sets.map(() => ({ ...first })))
}

const setsDiffer = computed(() => {
  const sets = found.value?.exercise.sets ?? []
  return sets.some((item) => item.weight_kg !== sets[0].weight_kg || item.reps !== sets[0].reps)
})

function link(items: CatalogItem[]) {
  linking.value = false
  const [item] = items
  if (item) routine.linkExercise(props.id, item)
}

function move(event: Event) {
  routine.moveExercise(props.id, (event.target as HTMLSelectElement).value)
}

function remove() {
  const name = found.value?.exercise.name
  const workoutId = found.value?.workout.id
  const undo = routine.deleteExercise(props.id)
  ui.showToast(`"${name}" removido`, 'Desfazer', undo)
  void router.replace(workoutId ? `/treino/${workoutId}` : '/fichas')
}

function formatDate(isoDate: string) {
  return new Date(`${isoDate}T12:00:00`).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' })
}

function restLabel(seconds: number) {
  return seconds < 120 ? `${seconds} s` : `${seconds / 60} min`
}
</script>

<template>
  <div class="pt-safe pb-safe mx-auto max-w-lg px-4">
    <header class="flex items-center gap-2 py-3">
      <button type="button" class="-ml-2 px-2 text-2xl text-muted" aria-label="Voltar para a ficha" @click="backToWorkout">‹</button>
      <p class="min-w-0 flex-1 truncate text-sm text-subtle">{{ found?.workout.name ?? 'Exercício' }}</p>
    </header>

    <p v-if="!found" class="mt-10 text-center text-subtle">Exercício não encontrado.</p>

    <template v-else>
      <figure
        v-if="found.exercise.images.length"
        class="photos relative mb-4 aspect-[4/3] max-w-full overflow-hidden rounded-2xl bg-white"
      >
        <img
          v-for="(src, index) in found.exercise.images"
          :key="src"
          :src="src"
          :alt="index === 0 ? `Posição inicial de ${found.exercise.name}` : `Posição final de ${found.exercise.name}`"
          class="absolute inset-0 h-full w-full object-contain"
          :class="index === 1 ? 'photo-end' : ''"
        />
      </figure>
      <button
        v-else
        type="button"
        class="mb-4 grid aspect-[3/1] w-full place-items-center rounded-2xl border border-dashed border-line text-sm text-muted"
        @click="linking = true"
      >
        + Adicionar foto da biblioteca
      </button>

      <input
        :value="found.exercise.name"
        aria-label="Nome do exercício"
        class="w-full bg-transparent font-display text-3xl leading-tight font-extrabold tracking-wide uppercase outline-none"
        enterkeyhint="done"
        @blur="saveText('name', $event)"
        @keydown.enter="($event.target as HTMLInputElement).blur()"
      />

      <div class="mt-4 grid grid-cols-2 rounded-xl bg-surface p-1" role="tablist" aria-label="Seções do exercício">
        <button
          id="tab-editar"
          type="button"
          role="tab"
          class="rounded-lg py-2 text-sm font-semibold"
          :class="tab === 'editar' ? 'bg-raised text-fg' : 'text-muted'"
          :aria-selected="tab === 'editar'"
          aria-controls="panel-editar"
          @click="tab = 'editar'"
        >
          Editar
        </button>
        <button
          id="tab-evolucao"
          type="button"
          role="tab"
          class="rounded-lg py-2 text-sm font-semibold"
          :class="tab === 'evolucao' ? 'bg-raised text-fg' : 'text-muted'"
          :aria-selected="tab === 'evolucao'"
          aria-controls="panel-evolucao"
          @click="tab = 'evolucao'"
        >
          Evolução
        </button>
      </div>

      <div v-show="tab === 'editar'" id="panel-editar" role="tabpanel" aria-labelledby="tab-editar" class="mt-5 flex flex-col gap-6">
        <section>
          <div class="mb-2 flex items-baseline justify-between">
            <h2 class="text-sm font-medium text-muted">Séries</h2>
            <button v-if="setsDiffer" type="button" class="text-sm text-accent-ink" @click="applyFirstToAll">
              Igualar à 1ª série
            </button>
          </div>
          <ol class="flex flex-col gap-2">
            <li v-for="(item, index) in found.exercise.sets" :key="index" class="flex items-center gap-2">
              <span class="w-5 shrink-0 text-center font-display text-lg font-bold text-subtle">{{ index + 1 }}</span>
              <Stepper
                class="flex-[1.15]"
                :model-value="item.weight_kg"
                :step="ui.weightStep"
                unit="kg"
                decimal
                @update:model-value="updateSet(index, { ...item, weight_kg: $event })"
              />
              <Stepper
                class="flex-1"
                :model-value="item.reps"
                :step="1"
                unit="rep"
                @update:model-value="updateSet(index, { ...item, reps: $event })"
              />
              <button
                type="button"
                class="grid h-11 w-8 shrink-0 place-items-center rounded-lg text-faint active:text-danger"
                :aria-label="`Remover série ${index + 1}`"
                @click="removeSet(index)"
              >
                ✕
              </button>
            </li>
          </ol>
          <button
            v-if="found.exercise.sets.length < MAX_SETS"
            type="button"
            class="mt-2 w-full rounded-xl border border-dashed border-line py-2.5 text-sm font-semibold text-accent-ink"
            @click="addSet"
          >
            + Série
          </button>
        </section>

        <section>
          <h2 class="mb-2 text-sm font-medium text-muted">Descanso entre séries</h2>
          <div class="flex flex-wrap gap-2" role="radiogroup" aria-label="Descanso entre séries">
            <button
              v-for="seconds in REST_PRESETS"
              :key="seconds"
              type="button"
              role="radio"
              class="rounded-full px-4 py-2 text-sm"
              :class="rest === seconds && !customRest ? 'bg-accent font-semibold text-on-accent' : 'bg-surface text-fg'"
              :aria-checked="rest === seconds && !customRest"
              @click="setRest(seconds)"
            >
              {{ restLabel(seconds) }}
            </button>
            <button
              type="button"
              role="radio"
              class="rounded-full px-4 py-2 text-sm"
              :class="customRest ? 'bg-accent font-semibold text-on-accent' : 'bg-surface text-fg'"
              :aria-checked="customRest"
              @click="customRest = true"
            >
              Outro
            </button>
          </div>
          <label v-if="customRest" class="mt-2 flex items-center gap-2 text-sm text-muted" for="custom-rest">
            <input
              id="custom-rest"
              :value="rest ?? ''"
              inputmode="numeric"
              placeholder="seg."
              class="w-24 rounded-xl bg-surface px-3 py-2 text-right text-fg outline-none focus:ring-2 focus:ring-accent"
              @blur="saveCustomRest"
              @keydown.enter="($event.target as HTMLInputElement).blur()"
            />
            segundos
          </label>
          <p v-if="rest === null && !customRest" class="mt-2 text-xs text-subtle">
            Sem descanso definido: o treino usa {{ DEFAULT_REST_SECONDS }} s.
          </p>
        </section>

        <section>
          <label class="flex flex-col gap-2 text-sm font-medium text-muted" for="exercise-notes">
            Observações
            <textarea
              id="exercise-notes"
              :value="found.exercise.notes"
              rows="2"
              placeholder="Ex.: banco no 3º furo, pegada fechada"
              class="rounded-xl bg-surface px-3 py-2 font-normal text-fg outline-none focus:ring-2 focus:ring-accent"
              @blur="saveText('notes', $event)"
            />
          </label>
        </section>

        <section class="flex flex-col gap-2">
          <h2 class="text-sm font-medium text-muted">Organizar</h2>
          <label class="flex items-center justify-between gap-3 rounded-xl bg-surface px-4 py-2 text-sm" for="exercise-workout">
            Ficha
            <select
              id="exercise-workout"
              :value="found.workout.id"
              class="max-w-[60%] rounded-lg bg-raised px-3 py-2 text-fg outline-none"
              @change="move"
            >
              <option v-for="workout in routine.workouts" :key="workout.id" :value="workout.id">{{ workout.name }}</option>
            </select>
          </label>
          <button type="button" class="rounded-xl bg-surface px-4 py-3 text-left text-sm" @click="linking = true">
            {{ found.exercise.catalog_id ? 'Trocar foto (escolher outro da biblioteca)' : 'Adicionar foto (escolher na biblioteca)' }}
          </button>
          <button
            v-if="found.exercise.catalog_id"
            type="button"
            class="rounded-xl px-4 py-2 text-left text-sm text-subtle"
            @click="routine.linkExercise(props.id, null)"
          >
            Remover foto
          </button>
        </section>

        <button type="button" class="w-full rounded-xl bg-danger/15 py-3 text-danger" @click="remove">Remover exercício</button>
      </div>

      <div v-show="tab === 'evolucao'" id="panel-evolucao" role="tabpanel" aria-labelledby="tab-evolucao" class="mt-5 flex flex-col gap-6">
        <section>
          <h2 class="mb-2 text-sm font-medium text-muted">Carga máxima</h2>
          <div class="rounded-2xl bg-surface p-3">
            <p v-if="historyError" class="py-8 text-center text-sm text-subtle">Evolução indisponível sem conexão.</p>
            <p v-else-if="!history" class="py-8 text-center text-sm text-subtle">Carregando…</p>
            <p v-else-if="history.length < 2" class="py-8 text-center text-sm text-subtle">
              O gráfico aparece quando você alterar a carga em dias diferentes.
            </p>
            <HistoryChart v-else-if="tab === 'evolucao'" :points="history" />
          </div>
          <ul v-if="history?.length" class="mt-3 divide-y divide-line text-sm">
            <li v-for="point in [...history].reverse()" :key="point.date" class="flex justify-between gap-4 py-2">
              <span class="text-muted">{{ formatDate(point.date) }}</span>
              <span class="text-right tabular-nums text-fg">{{ formatSets(point.sets) }}</span>
            </li>
          </ul>
        </section>

        <section>
          <h2 class="mb-2 text-sm font-medium text-muted">Últimos treinos</h2>
          <p v-if="!sessions.length" class="text-sm text-subtle">Nenhum treino com este exercício ainda.</p>
          <ul v-else class="divide-y divide-line text-sm">
            <li v-for="point in sessions" :key="point.session_id">
              <RouterLink :to="`/sessao/${point.session_id}`" class="flex justify-between gap-4 py-2">
                <span class="text-muted first-letter:uppercase">{{ formatLongDate(new Date(point.started_at)) }}</span>
                <span class="text-right tabular-nums text-fg">{{ formatSets(point.sets) }}</span>
              </RouterLink>
            </li>
          </ul>
        </section>
      </div>
    </template>

    <ExercisePicker
      v-if="linking"
      title="Escolher na biblioteca"
      :multiple="false"
      @pick="link"
      @pick-name="linking = false"
      @close="linking = false"
    />
  </div>
</template>

<style scoped>
/* Start and end positions alternate, like a two-frame animation. */
@media (prefers-reduced-motion: no-preference) {
  .photo-end {
    animation: alternate-photo 2.4s steps(1) infinite;
  }
}
@media (prefers-reduced-motion: reduce) {
  .photo-end {
    display: none;
  }
}
@keyframes alternate-photo {
  0% {
    opacity: 0;
  }
  50% {
    opacity: 1;
  }
}
</style>
