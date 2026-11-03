<script setup lang="ts">
import { computed, ref } from 'vue'
import draggable from 'vuedraggable'
import { useRouter } from 'vue-router'
import ExerciseCard from '@/components/ExerciseCard.vue'
import ColorPanel from '@/components/ColorPanel.vue'
import ExercisePicker from '@/components/ExercisePicker.vue'
import { PLATE_LABELS, plateBg } from '@/lib/plates'
import { useRoutineStore } from '@/stores/routine'
import { useSessionStore } from '@/stores/session'
import { useUiStore } from '@/stores/ui'
import type { CatalogItem } from '@/types'

const props = defineProps<{ id: string }>()

const routine = useRoutineStore()
const session = useSessionStore()
const ui = useUiStore()
const router = useRouter()

const workout = computed(() => routine.workouts.find((item) => item.id === props.id))
const otherActive = computed(() => session.active && session.active.workout_id !== props.id)

const picking = ref(false)
const choosingColor = ref(false)

function rename(event: Event) {
  const name = (event.target as HTMLInputElement).value.trim()
  if (workout.value && name && name !== workout.value.name) routine.renameWorkout(workout.value.id, name)
}

function addFromLibrary(items: CatalogItem[]) {
  picking.value = false
  if (!workout.value) return
  for (const item of items) routine.addExercise(workout.value.id, item.name, item)
}

function addByName(name: string) {
  picking.value = false
  if (workout.value) routine.addExercise(workout.value.id, name)
}

function duplicate() {
  if (!workout.value) return
  const copy = routine.duplicateWorkout(workout.value.id)
  if (!copy) return
  ui.showToast(`"${copy.name}" criada`)
  void router.push(`/treino/${copy.id}`)
}

function onReorder() {
  if (!workout.value) return
  routine.reorderExercises(
    workout.value.id,
    workout.value.exercises.map((item) => item.id),
  )
}

function start() {
  if (!workout.value) return
  if (session.active?.workout_id !== workout.value.id) session.start(workout.value)
  void router.push(`/treino/${workout.value.id}/sessao`)
}

function remove() {
  if (!workout.value) return
  if (!confirm(`Apagar a ficha "${workout.value.name}" com todos os exercícios e histórico de cargas? Os treinos já feitos continuam no calendário.`)) return
  routine.deleteWorkout(workout.value.id)
  void router.replace('/fichas')
}
</script>

<template>
  <div class="pt-safe mx-auto flex min-h-dvh max-w-lg flex-col">
    <header class="sticky top-0 z-10 flex items-center gap-2 bg-bg/95 px-2 py-2 backdrop-blur">
      <RouterLink to="/fichas" class="px-2 text-2xl text-muted" aria-label="Voltar para as fichas">‹</RouterLink>
      <template v-if="workout">
        <button
          type="button"
          class="h-7 w-7 shrink-0 rounded-full ring-4 ring-bg"
          :class="plateBg(workout.color)"
          :aria-label="`Cor: ${PLATE_LABELS[workout.color]}. Escolher cor`"
          :aria-expanded="choosingColor"
          @click="choosingColor = !choosingColor"
        />
        <input
          :key="workout.id"
          :value="workout.name"
          aria-label="Nome da ficha"
          class="min-w-0 flex-1 bg-transparent font-display text-2xl font-extrabold tracking-wide uppercase outline-none"
          enterkeyhint="done"
          @blur="rename"
          @keydown.enter="($event.target as HTMLInputElement).blur()"
        />
      </template>
    </header>

    <p v-if="!workout" class="mt-16 text-center text-subtle">Ficha não encontrada.</p>

    <main v-else class="flex flex-1 flex-col gap-3 px-3 pb-28">
      <button
        v-if="!choosingColor"
        type="button"
        class="flex items-center gap-2 self-start rounded-full bg-surface py-1.5 pr-3 pl-1.5 text-sm text-muted"
        @click="choosingColor = true"
      >
        <span class="h-5 w-5 rounded-full" :class="plateBg(workout.color)" aria-hidden="true" />
        Cor: {{ PLATE_LABELS[workout.color] }}
      </button>
      <div v-else class="flex flex-col gap-2">
        <ColorPanel
          :workout-id="workout.id"
          :model-value="workout.color"
          @update:model-value="routine.setWorkoutColor(workout.id, $event)"
        />
        <button type="button" class="self-end px-2 text-sm text-subtle" @click="choosingColor = false">Fechar</button>
      </div>

      <draggable
        :list="workout.exercises"
        item-key="id"
        handle=".drag-handle"
        :animation="150"
        class="flex flex-col gap-3"
        @end="onReorder"
      >
        <template #item="{ element }">
          <ExerciseCard :exercise="element" />
        </template>
      </draggable>

      <button
        type="button"
        class="rounded-2xl border border-dashed border-line py-4 font-semibold text-accent-ink"
        @click="picking = true"
      >
        + Adicionar exercícios
      </button>
      <p v-if="!workout.exercises.length" class="px-4 text-center text-sm text-subtle">
        Escolha na biblioteca, com foto de cada exercício, ou crie os seus.
      </p>

      <div class="flex justify-between px-1 text-sm text-subtle">
        <button type="button" @click="duplicate">Duplicar ficha</button>
        <button type="button" class="text-danger" @click="remove">Apagar ficha</button>
      </div>
    </main>

    <ExercisePicker v-if="picking" @pick="addFromLibrary" @pick-name="addByName" @close="picking = false" />

    <div v-if="workout" class="fixed inset-x-0 bottom-0 z-10 bg-gradient-to-t from-bg via-bg/95 to-transparent px-4 pt-6 pb-[calc(env(safe-area-inset-bottom)+1rem)]">
      <div class="mx-auto max-w-lg">
        <RouterLink
          v-if="otherActive"
          :to="`/treino/${session.active!.workout_id}/sessao`"
          class="block rounded-xl bg-raised py-3 text-center text-sm text-fg"
        >
          {{ session.active!.workout_name }} está em andamento · abrir
        </RouterLink>
        <button
          v-else
          type="button"
          class="w-full rounded-xl bg-accent py-4 font-display text-xl font-extrabold tracking-wide text-on-accent uppercase disabled:opacity-40"
          :disabled="!workout.exercises.length"
          @click="start"
        >
          {{ session.active ? 'Continuar treino' : 'Iniciar treino' }}
        </button>
      </div>
    </div>
  </div>
</template>
