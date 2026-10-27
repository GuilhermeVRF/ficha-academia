<script setup lang="ts">
import { ref } from 'vue'
import draggable from 'vuedraggable'
import { useRouter } from 'vue-router'
import { ApiError, request } from '@/lib/api'
import { flush } from '@/lib/outbox'
import { useRoutineStore } from '@/stores/routine'
import { useUiStore } from '@/stores/ui'

const WEIGHT_STEPS = [0.5, 1, 1.25, 2, 2.5, 5]

const routine = useRoutineStore()
const ui = useUiStore()
const router = useRouter()
const fileInput = ref<HTMLInputElement>()

function rename(workoutId: string, event: Event) {
  const name = (event.target as HTMLInputElement).value.trim()
  if (name) routine.renameWorkout(workoutId, name)
}

function removeWorkout(workoutId: string, name: string) {
  if (confirm(`Apagar a ficha "${name}" com todos os exercícios e histórico?`)) routine.deleteWorkout(workoutId)
}

function onReorder() {
  routine.reorderWorkouts(routine.workouts.map((item) => item.id))
}

async function exportBackup() {
  try {
    await flush()
    const backup = await request('GET', '/export')
    const blob = new Blob([JSON.stringify(backup, null, 2)], { type: 'application/json' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `ficha-${new Date().toLocaleDateString('sv-SE')}.json`
    link.click()
    URL.revokeObjectURL(link.href)
  } catch {
    ui.showToast('Não foi possível exportar (sem conexão?)')
  }
}

async function importBackup(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (!confirm('Restaurar o backup vai SUBSTITUIR todos os dados atuais. Continuar?')) return
  try {
    await request('POST', '/import-json', JSON.parse(await file.text()))
    await routine.refresh()
    ui.showToast('Backup restaurado')
  } catch (failure) {
    ui.showToast(failure instanceof ApiError ? failure.message : 'Arquivo inválido ou sem conexão')
  } finally {
    if (fileInput.value) fileInput.value.value = ''
  }
}

async function logout() {
  await request('POST', '/auth/logout').catch(() => undefined)
  routine.unauthorized = true
}
</script>

<template>
  <div class="pt-safe pb-safe mx-auto max-w-lg px-4">
    <header class="flex items-center gap-2 py-3">
      <button type="button" class="-ml-2 px-2 text-2xl text-zinc-400" aria-label="Voltar" @click="router.back()">‹</button>
      <h1 class="font-semibold">Ajustes</h1>
    </header>

    <section class="mt-2">
      <h2 class="mb-2 text-sm font-medium text-zinc-400">Fichas</h2>
      <draggable
        :list="routine.workouts"
        item-key="id"
        handle=".drag-handle"
        class="flex flex-col gap-2"
        @end="onReorder"
      >
        <template #item="{ element }">
          <div class="flex items-center gap-2 rounded-xl bg-zinc-900 px-3 py-1">
            <span class="drag-handle cursor-grab touch-none text-zinc-600 select-none">⋮⋮</span>
            <input
              :value="element.name"
              class="min-w-0 flex-1 bg-transparent py-2 outline-none"
              enterkeyhint="done"
              @blur="rename(element.id, $event)"
              @keydown.enter="($event.target as HTMLInputElement).blur()"
            />
            <span class="text-xs text-zinc-500">{{ element.exercises.length }} ex.</span>
            <button type="button" class="px-2 text-red-400" aria-label="Apagar ficha" @click="removeWorkout(element.id, element.name)">
              ✕
            </button>
          </div>
        </template>
      </draggable>
      <p v-if="!routine.workouts.length" class="text-sm text-zinc-500">Nenhuma ficha.</p>
    </section>

    <section class="mt-6">
      <h2 class="mb-2 text-sm font-medium text-zinc-400">Passo do botão de carga</h2>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="step in WEIGHT_STEPS"
          :key="step"
          type="button"
          class="rounded-full px-4 py-2 text-sm"
          :class="ui.weightStep === step ? 'bg-lime-400 text-zinc-950' : 'bg-zinc-900 text-zinc-300'"
          @click="ui.weightStep = step"
        >
          {{ String(step).replace('.', ',') }} kg
        </button>
      </div>
    </section>

    <section class="mt-6 flex flex-col gap-2">
      <h2 class="text-sm font-medium text-zinc-400">Dados</h2>
      <RouterLink to="/importar" class="rounded-xl bg-zinc-900 px-4 py-3">Colar ficha em texto</RouterLink>
      <button type="button" class="rounded-xl bg-zinc-900 px-4 py-3 text-left" @click="exportBackup">
        Exportar backup (JSON)
      </button>
      <button type="button" class="rounded-xl bg-zinc-900 px-4 py-3 text-left" @click="fileInput?.click()">
        Restaurar backup…
      </button>
      <input ref="fileInput" type="file" accept="application/json,.json" class="hidden" @change="importBackup" />
      <button type="button" class="mt-4 rounded-xl px-4 py-3 text-left text-zinc-400" @click="logout">Sair</button>
    </section>
  </div>
</template>
