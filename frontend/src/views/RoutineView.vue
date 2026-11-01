<script setup lang="ts">
import { computed, ref } from 'vue'
import draggable from 'vuedraggable'
import { useRouter } from 'vue-router'
import ExerciseCard from '@/components/ExerciseCard.vue'
import { PLATE_LABELS, nextPlateColor, plateBg } from '@/lib/plates'
import { useRoutineStore } from '@/stores/routine'
import { useSessionStore } from '@/stores/session'

const props = defineProps<{ id: string }>()

const routine = useRoutineStore()
const session = useSessionStore()
const router = useRouter()

const workout = computed(() => routine.workouts.find((item) => item.id === props.id))
const otherActive = computed(() => session.active && session.active.workout_id !== props.id)

const newExerciseName = ref('')

function rename(event: Event) {
  const name = (event.target as HTMLInputElement).value.trim()
  if (workout.value && name && name !== workout.value.name) routine.renameWorkout(workout.value.id, name)
}

function addExercise() {
  const name = newExerciseName.value.trim()
  if (!name || !workout.value) return
  routine.addExercise(workout.value.id, name)
  newExerciseName.value = ''
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
          :aria-label="`Cor: ${PLATE_LABELS[workout.color]}. Toque para trocar`"
          @click="routine.setWorkoutColor(workout.id, nextPlateColor(workout.color))"
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

      <form class="flex gap-2" @submit.prevent="addExercise">
        <input
          v-model="newExerciseName"
          list="exercise-names"
          placeholder="Adicionar exercício…"
          aria-label="Nome do novo exercício"
          enterkeyhint="done"
          autocapitalize="sentences"
          class="min-w-0 flex-1 rounded-xl bg-surface px-4 py-3 outline-none focus:ring-2 focus:ring-accent"
        />
        <button
          :disabled="!newExerciseName.trim()"
          class="rounded-xl bg-accent px-4 font-semibold text-on-accent disabled:opacity-30"
          aria-label="Adicionar exercício"
        >
          +
        </button>
        <datalist id="exercise-names">
          <option v-for="name in routine.exerciseNames" :key="name" :value="name" />
        </datalist>
      </form>

      <div class="flex justify-between px-1 text-sm text-subtle">
        <RouterLink :to="{ path: '/importar', query: { ficha: workout.id } }">Colar vários</RouterLink>
        <button type="button" class="text-danger" @click="remove">Apagar ficha</button>
      </div>
    </main>

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
