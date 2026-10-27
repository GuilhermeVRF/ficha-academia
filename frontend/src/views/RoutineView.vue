<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import draggable from 'vuedraggable'
import ExerciseCard from '@/components/ExerciseCard.vue'
import { useDoneSets } from '@/composables/useDoneSets'
import { useRoutineStore } from '@/stores/routine'

const LAST_WORKOUT_KEY = 'lastWorkout'

const routine = useRoutineStore()
const { clearWorkout, isDone } = useDoneSets()

const selectedId = ref(readLastWorkout())
const current = computed(
  () => routine.workouts.find((item) => item.id === selectedId.value) ?? routine.workouts[0],
)
const doneCount = computed(
  () =>
    current.value?.exercises.reduce(
      (total, exercise) => total + exercise.sets.filter((_, i) => isDone(exercise.id, i)).length,
      0,
    ) ?? 0,
)

watch(
  () => current.value?.id,
  (id) => {
    if (!id) return
    try {
      localStorage.setItem(LAST_WORKOUT_KEY, id)
    } catch {
      /* storage unavailable */
    }
  },
)

function readLastWorkout() {
  try {
    return localStorage.getItem(LAST_WORKOUT_KEY) ?? ''
  } catch {
    return ''
  }
}

const creatingWorkout = ref(false)
const newWorkoutName = ref('')
const newWorkoutInput = ref<HTMLInputElement>()

async function startWorkoutCreation() {
  const letter = String.fromCharCode(65 + routine.workouts.length)
  newWorkoutName.value = `Treino ${letter}`
  creatingWorkout.value = true
  await nextTick()
  newWorkoutInput.value?.select()
}

function createWorkout() {
  const name = newWorkoutName.value.trim()
  creatingWorkout.value = false
  if (!name) return
  selectedId.value = routine.addWorkout(name).id
}

const newExerciseName = ref('')

function addExercise() {
  const name = newExerciseName.value.trim()
  if (!name || !current.value) return
  routine.addExercise(current.value.id, name)
  newExerciseName.value = ''
}

function onReorder() {
  if (!current.value) return
  routine.reorderExercises(
    current.value.id,
    current.value.exercises.map((item) => item.id),
  )
}
</script>

<template>
  <div class="mx-auto flex min-h-dvh max-w-lg flex-col">
    <header class="pt-safe sticky top-0 z-10 bg-[#0c0c0e]/95 backdrop-blur">
      <div class="flex items-center gap-2 px-4 pt-3">
        <h1 class="flex-1 text-lg font-bold tracking-tight">Ficha</h1>
        <span v-if="routine.pending" class="text-xs text-amber-400" title="Alterações aguardando conexão">
          ● {{ routine.pending }} pendente{{ routine.pending > 1 ? 's' : '' }}
        </span>
        <RouterLink to="/ajustes" class="rounded-lg px-2 py-1 text-xl text-zinc-400" aria-label="Ajustes">⚙</RouterLink>
      </div>
      <nav class="flex gap-2 overflow-x-auto px-4 py-3 [scrollbar-width:none]">
        <button
          v-for="workout in routine.workouts"
          :key="workout.id"
          type="button"
          class="shrink-0 rounded-full px-4 py-2 text-sm font-medium whitespace-nowrap"
          :class="workout.id === current?.id ? 'bg-lime-400 text-zinc-950' : 'bg-zinc-900 text-zinc-300'"
          @click="selectedId = workout.id"
        >
          {{ workout.name }}
        </button>
        <form v-if="creatingWorkout" class="shrink-0" @submit.prevent="createWorkout">
          <input
            ref="newWorkoutInput"
            v-model="newWorkoutName"
            class="w-32 rounded-full bg-zinc-800 px-4 py-2 text-sm outline-none ring-2 ring-lime-400"
            enterkeyhint="done"
            @blur="createWorkout"
          />
        </form>
        <button
          v-else
          type="button"
          class="shrink-0 rounded-full bg-zinc-900 px-4 py-2 text-sm text-zinc-400"
          aria-label="Nova ficha"
          @click="startWorkoutCreation"
        >
          +
        </button>
      </nav>
    </header>

    <main class="pb-safe flex flex-1 flex-col gap-3 px-3">
      <section v-if="!routine.workouts.length" class="mt-16 flex flex-col items-center gap-4 px-6 text-center">
        <p class="text-zinc-400">Nenhuma ficha ainda.</p>
        <RouterLink to="/importar" class="rounded-xl bg-lime-400 px-5 py-3 font-semibold text-zinc-950">
          Colar minha ficha
        </RouterLink>
        <button type="button" class="text-sm text-zinc-400 underline" @click="startWorkoutCreation">
          ou criar do zero
        </button>
      </section>

      <template v-else-if="current">
        <draggable
          :list="current.exercises"
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

        <form class="flex gap-2" @submit.prevent="addExercise">
          <input
            v-model="newExerciseName"
            list="exercise-names"
            placeholder="Adicionar exercício…"
            enterkeyhint="done"
            autocapitalize="sentences"
            class="min-w-0 flex-1 rounded-xl bg-zinc-900 px-4 py-3 outline-none focus:ring-2 focus:ring-lime-400"
          />
          <button
            :disabled="!newExerciseName.trim()"
            class="rounded-xl bg-lime-400 px-4 font-semibold text-zinc-950 disabled:opacity-30"
          >
            +
          </button>
          <datalist id="exercise-names">
            <option v-for="name in routine.exerciseNames" :key="name" :value="name" />
          </datalist>
        </form>

        <div class="flex justify-between px-1 text-sm text-zinc-500">
          <RouterLink to="/importar">Colar vários</RouterLink>
          <button
            v-if="doneCount"
            type="button"
            @click="clearWorkout(current.exercises.map((item) => item.id))"
          >
            Limpar marcações ({{ doneCount }})
          </button>
        </div>
      </template>
    </main>
  </div>
</template>
