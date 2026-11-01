<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError, request } from '@/lib/api'
import { formatSets } from '@/lib/format'
import { flush } from '@/lib/outbox'
import { useRoutineStore } from '@/stores/routine'
import { useUiStore } from '@/stores/ui'
import type { ImportPreview } from '@/types'

const PLACEHOLDER = `Treino A
Supino reto 4x10 40kg
Crucifixo 3x12 14kg
Tríceps corda 12,10,8 25kg

Treino B
Agachamento 4x8 60kg
Leg press 3x12`

const routine = useRoutineStore()
const ui = useUiStore()
const route = useRoute()
const router = useRouter()

const text = ref('')
const preview = ref<ImportPreview | null>(null)
const error = ref('')
const busy = ref(false)

/** Lines before any "Treino X" header go to the workout this screen was opened from. */
function currentWorkoutId() {
  return typeof route.query.ficha === 'string' ? route.query.ficha : routine.workouts[0]?.id
}

async function send(dryRun: boolean) {
  busy.value = true
  error.value = ''
  try {
    if (!(await flush())) throw new Error('Sincronize as alterações pendentes antes de importar (sem conexão?).')
    const result = await request<ImportPreview>('POST', `/import-text?dry_run=${dryRun}`, {
      text: text.value,
      workout_id: currentWorkoutId() ?? null,
    })
    if (dryRun) {
      preview.value = result
      return
    }
    await routine.refresh()
    const total = result.workouts.reduce((sum, workout) => sum + workout.exercises.length, 0)
    ui.showToast(`${total} exercício${total === 1 ? '' : 's'} importado${total === 1 ? '' : 's'}`)
    router.replace(typeof route.query.ficha === 'string' ? `/treino/${route.query.ficha}` : '/fichas')
  } catch (failure) {
    error.value = failure instanceof ApiError ? failure.message : (failure as Error).message || 'Sem conexão.'
  } finally {
    busy.value = false
  }
}

</script>

<template>
  <div class="pt-safe pb-safe mx-auto flex min-h-dvh max-w-lg flex-col px-4">
    <header class="flex items-center gap-2 py-3">
      <button type="button" class="-ml-2 px-2 text-2xl text-muted" aria-label="Voltar" @click="router.back()">‹</button>
      <h1 class="font-display text-2xl font-extrabold tracking-wide uppercase">Colar ficha</h1>
    </header>

    <template v-if="!preview">
      <p class="mb-3 text-sm text-muted">
        Cole a ficha como texto, um exercício por linha. Linhas como “Treino A” criam (ou reaproveitam) uma ficha.
      </p>
      <textarea
        v-model="text"
        :placeholder="PLACEHOLDER"
        rows="14"
        class="w-full flex-1 rounded-2xl bg-surface p-4 font-mono text-sm outline-none focus:ring-2 focus:ring-accent"
      />
      <p v-if="error" class="mt-2 text-sm text-danger">{{ error }}</p>
      <button
        type="button"
        :disabled="busy || !text.trim()"
        class="mt-3 rounded-xl bg-accent py-3 font-semibold text-on-accent disabled:opacity-40"
        @click="send(true)"
      >
        Pré-visualizar
      </button>
    </template>

    <template v-else>
      <section v-for="workout in preview.workouts" :key="workout.name" class="mb-4">
        <h2 class="mb-2 flex items-center gap-2 font-semibold">
          {{ workout.name }}
          <span class="text-xs font-normal text-subtle">{{ workout.existing_id ? 'ficha existente' : 'nova ficha' }}</span>
        </h2>
        <ul class="divide-y divide-line rounded-2xl bg-surface px-4">
          <li v-for="(exercise, index) in workout.exercises" :key="index" class="py-2.5">
            <div class="flex justify-between gap-3 text-sm">
              <span>{{ exercise.name }}</span>
              <span class="shrink-0 tabular-nums text-muted">{{ formatSets(exercise.sets) }}</span>
            </div>
            <p v-if="exercise.warning" class="text-xs text-warn">{{ exercise.warning }}</p>
          </li>
        </ul>
      </section>
      <p v-if="!preview.workouts.length" class="py-10 text-center text-subtle">Nenhum exercício reconhecido.</p>
      <p v-if="error" class="text-sm text-danger">{{ error }}</p>
      <div class="mt-auto flex gap-2 pt-3">
        <button type="button" class="flex-1 rounded-xl bg-surface py-3" @click="preview = null">Editar texto</button>
        <button
          type="button"
          :disabled="busy || !preview.workouts.length"
          class="flex-1 rounded-xl bg-accent py-3 font-semibold text-on-accent disabled:opacity-40"
          @click="send(false)"
        >
          Importar
        </button>
      </div>
    </template>
  </div>
</template>
