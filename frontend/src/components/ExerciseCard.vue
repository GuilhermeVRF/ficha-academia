<script setup lang="ts">
import { computed, ref } from 'vue'
import SetRow from './SetRow.vue'
import { formatWeight } from '@/lib/format'
import { useDoneSets } from '@/composables/useDoneSets'
import { useRoutineStore } from '@/stores/routine'
import { useUiStore } from '@/stores/ui'
import type { Exercise, SetData } from '@/types'

const props = defineProps<{ exercise: Exercise }>()

const routine = useRoutineStore()
const ui = useUiStore()
const { isDone, toggle } = useDoneSets()

/** Index of the last edited set, offered as the source for "apply to all". */
const lastEdited = ref<number | null>(null)

const allDone = computed(() => props.exercise.sets.length > 0 && props.exercise.sets.every((_, i) => isDone(props.exercise.id, i)))
const applySource = computed(() => {
  if (lastEdited.value === null) return null
  const source = props.exercise.sets[lastEdited.value]
  if (!source) return null
  const differs = props.exercise.sets.some((item) => item.weight_kg !== source.weight_kg || item.reps !== source.reps)
  return differs ? source : null
})

function updateSet(index: number, value: SetData) {
  const sets = props.exercise.sets.map((item, i) => (i === index ? value : item))
  lastEdited.value = index
  routine.setSets(props.exercise.id, sets)
}

function addSet() {
  const last = props.exercise.sets.at(-1) ?? { weight_kg: 0, reps: 10 }
  routine.setSets(props.exercise.id, [...props.exercise.sets, { ...last }])
}

function removeSet(index: number) {
  const previous = props.exercise.sets
  lastEdited.value = null
  routine.setSets(
    props.exercise.id,
    previous.filter((_, i) => i !== index),
  )
  ui.showToast(`Série ${index + 1} removida`, 'Desfazer', () => routine.setSets(props.exercise.id, previous))
}

function applyToAll() {
  const source = applySource.value
  if (!source) return
  routine.setSets(
    props.exercise.id,
    props.exercise.sets.map(() => ({ ...source })),
  )
  lastEdited.value = null
}
</script>

<template>
  <article class="rounded-2xl bg-zinc-900 p-3" :class="{ 'ring-1 ring-lime-400/40': allDone }">
    <header class="mb-2 flex items-center gap-2">
      <span class="drag-handle -ml-1 cursor-grab touch-none px-1 text-zinc-600 select-none" aria-label="Arrastar">⋮⋮</span>
      <RouterLink :to="`/exercicio/${exercise.id}`" class="min-w-0 flex-1 truncate font-semibold text-zinc-100">
        {{ exercise.name }}
      </RouterLink>
      <span v-if="exercise.rest_seconds" class="text-xs text-zinc-500">⏱ {{ exercise.rest_seconds }}s</span>
      <RouterLink :to="`/exercicio/${exercise.id}`" class="px-1 text-zinc-500" aria-label="Detalhes">›</RouterLink>
    </header>
    <p v-if="exercise.notes" class="mb-2 text-xs text-zinc-500">{{ exercise.notes }}</p>

    <div class="flex flex-col gap-1.5">
      <SetRow
        v-for="(item, index) in exercise.sets"
        :key="index"
        :set="item"
        :index="index"
        :done="isDone(exercise.id, index)"
        :weight-step="ui.weightStep"
        @update="updateSet(index, $event)"
        @remove="removeSet(index)"
        @toggle="toggle(exercise.id, index)"
      />
    </div>

    <div class="mt-2 flex flex-wrap gap-2">
      <button type="button" class="rounded-lg px-3 py-1.5 text-sm text-zinc-400 active:bg-zinc-800" @click="addSet">
        + série
      </button>
      <button
        v-if="applySource"
        type="button"
        class="rounded-lg bg-lime-400/10 px-3 py-1.5 text-sm text-lime-300 active:bg-lime-400/20"
        @click="applyToAll"
      >
        Aplicar {{ formatWeight(applySource.weight_kg) }}kg × {{ applySource.reps }} a todas
      </button>
    </div>
  </article>
</template>
