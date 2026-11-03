<script setup lang="ts">
import { ref } from 'vue'
import { ApiError, request } from '@/lib/api'
import { flush } from '@/lib/outbox'
import { useHistoryStore } from '@/stores/history'
import { useRoutineStore } from '@/stores/routine'
import { useUiStore } from '@/stores/ui'

const WEIGHT_STEPS = [0.5, 1, 1.25, 2, 2.5, 5]

const history = useHistoryStore()
const routine = useRoutineStore()
const ui = useUiStore()
const fileInput = ref<HTMLInputElement>()

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
  if (!confirm('Restaurar o backup vai SUBSTITUIR suas fichas e treinos atuais. Continuar?')) return
  try {
    await request('POST', '/import-json', JSON.parse(await file.text()))
    await routine.refresh()
    history.reset()
    await history.init()
    ui.showToast('Backup restaurado')
  } catch (failure) {
    ui.showToast(failure instanceof ApiError ? failure.message : 'Arquivo inválido ou sem conexão')
  } finally {
    if (fileInput.value) fileInput.value.value = ''
  }
}
</script>

<template>
  <div class="pt-safe pb-nav mx-auto flex max-w-lg flex-col gap-6 px-4">
    <h1 class="pt-4 font-display text-3xl font-extrabold tracking-wide uppercase">Ajustes</h1>

    <section>
      <h2 class="mb-2 text-sm font-medium text-muted">Passo do botão de carga</h2>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="step in WEIGHT_STEPS"
          :key="step"
          type="button"
          class="rounded-full px-4 py-2 text-sm"
          :class="ui.weightStep === step ? 'bg-accent text-on-accent' : 'bg-surface text-fg'"
          @click="ui.weightStep = step"
        >
          {{ String(step).replace('.', ',') }} kg
        </button>
      </div>
    </section>

    <section class="flex flex-col gap-2">
      <h2 class="text-sm font-medium text-muted">Dados</h2>
      <RouterLink to="/importar" class="rounded-xl bg-surface px-4 py-3">Colar ficha em texto</RouterLink>
      <button type="button" class="rounded-xl bg-surface px-4 py-3 text-left" @click="exportBackup">
        Exportar backup (JSON)
      </button>
      <button type="button" class="rounded-xl bg-surface px-4 py-3 text-left" @click="fileInput?.click()">
        Restaurar backup…
      </button>
      <input ref="fileInput" type="file" accept="application/json,.json" class="hidden" @change="importBackup" />
      <p class="text-xs text-subtle">O backup inclui suas fichas, o histórico de cargas e os treinos do calendário.</p>
    </section>
  </div>
</template>
