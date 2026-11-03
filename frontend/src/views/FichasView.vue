<script setup lang="ts">
import { nextTick, ref } from 'vue'
import draggable from 'vuedraggable'
import { useRouter } from 'vue-router'
import { relativeDays } from '@/lib/dates'
import { PLATE_LABELS, nextPlateColor, plateBg } from '@/lib/plates'
import { useHistoryStore } from '@/stores/history'
import { useRoutineStore } from '@/stores/routine'
import type { Workout } from '@/types'

const routine = useRoutineStore()
const history = useHistoryStore()
const router = useRouter()

const creating = ref(false)
const newName = ref('')
const newNameInput = ref<HTMLInputElement>()

async function startCreation() {
  newName.value = `Treino ${String.fromCharCode(65 + routine.workouts.length)}`
  creating.value = true
  await nextTick()
  newNameInput.value?.select()
}

function create() {
  const name = newName.value.trim()
  creating.value = false
  if (!name) return
  void router.push(`/treino/${routine.addWorkout(name).id}`)
}

function lastTrained(workoutId: string) {
  const found = history.sessions.find((item) => item.workout_id === workoutId)
  return found ? relativeDays(new Date(found.started_at)) : 'nunca treinado'
}

function cycleColor(workout: Workout) {
  routine.setWorkoutColor(workout.id, nextPlateColor(workout.color))
}

function onReorder() {
  routine.reorderWorkouts(routine.workouts.map((item) => item.id))
}
</script>

<template>
  <div class="pt-safe pb-nav mx-auto flex max-w-lg flex-col gap-4 px-4">
    <header class="flex items-center gap-2 pt-4">
      <h1 class="flex-1 font-display text-3xl font-extrabold tracking-wide uppercase">Fichas</h1>
      <span v-if="routine.pending" class="text-xs text-warn" title="Alterações aguardando conexão">
        ● {{ routine.pending }} pendente{{ routine.pending > 1 ? 's' : '' }}
      </span>
    </header>

    <section v-if="!routine.workouts.length && !creating" class="mt-10 flex flex-col items-center gap-4 px-6 text-center">
      <p class="text-muted">Nenhuma ficha ainda.</p>
      <button type="button" class="rounded-xl bg-accent px-5 py-3 font-semibold text-on-accent" @click="startCreation">
        Criar minha primeira ficha
      </button>
      <RouterLink to="/importar" class="text-sm text-muted underline">ou colar uma ficha em texto</RouterLink>
    </section>

    <draggable
      v-else
      :list="routine.workouts"
      item-key="id"
      handle=".drag-handle"
      :animation="150"
      class="flex flex-col gap-2"
      @end="onReorder"
    >
      <template #item="{ element }">
        <div class="flex items-center gap-3 rounded-2xl bg-surface py-2 pr-3 pl-2">
          <span class="drag-handle cursor-grab touch-none px-1 text-faint select-none" aria-label="Arrastar para reordenar">⋮⋮</span>
          <button
            type="button"
            class="h-9 w-9 shrink-0 rounded-full ring-4 ring-bg"
            :class="plateBg(element.color)"
            :aria-label="`Cor: ${PLATE_LABELS[element.color as Workout['color']]}. Toque para trocar`"
            @click="cycleColor(element)"
          />
          <RouterLink :to="`/treino/${element.id}`" class="flex min-w-0 flex-1 items-center gap-2 py-1">
            <span class="min-w-0 flex-1">
              <span class="block truncate font-display text-xl font-bold tracking-wide uppercase">{{ element.name }}</span>
              <span class="block text-xs text-subtle">
                {{ element.exercises.length }} exercícios · {{ lastTrained(element.id) }}
              </span>
            </span>
            <span class="text-subtle" aria-hidden="true">›</span>
          </RouterLink>
        </div>
      </template>
    </draggable>

    <form v-if="creating" class="flex gap-2" @submit.prevent="create">
      <input
        id="new-workout-name"
        ref="newNameInput"
        v-model="newName"
        aria-label="Nome da nova ficha"
        class="min-w-0 flex-1 rounded-xl bg-surface px-4 py-3 outline-none ring-2 ring-accent"
        enterkeyhint="done"
        @blur="create"
      />
    </form>
    <button
      v-else-if="routine.workouts.length"
      type="button"
      class="rounded-2xl border border-dashed border-line py-3 text-sm text-muted"
      @click="startCreation"
    >
      + Nova ficha
    </button>
    <p v-if="routine.workouts.length" class="text-center text-xs text-subtle">Toque na bolinha para trocar a cor da ficha.</p>
  </div>
</template>
