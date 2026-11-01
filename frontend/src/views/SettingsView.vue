<script setup lang="ts">
import { onMounted, ref } from 'vue'
import draggable from 'vuedraggable'
import { useRouter } from 'vue-router'
import { ApiError, request } from '@/lib/api'
import { flush } from '@/lib/outbox'
import { useAuthStore } from '@/stores/auth'
import { useRoutineStore } from '@/stores/routine'
import { useUiStore } from '@/stores/ui'
import type { Invite } from '@/types'

const WEIGHT_STEPS = [0.5, 1, 1.25, 2, 2.5, 5]

const auth = useAuthStore()
const routine = useRoutineStore()
const ui = useUiStore()
const router = useRouter()
const fileInput = ref<HTMLInputElement>()
const invites = ref<Invite[]>([])
const newInviteLink = ref('')
const inviteLinkInput = ref<HTMLInputElement>()

onMounted(() => {
  if (auth.user?.is_admin) void loadInvites()
})

async function loadInvites() {
  invites.value = await request<Invite[]>('GET', '/invites').catch(() => [])
}

function inviteLink(code: string) {
  return `${location.origin}/cadastro?convite=${encodeURIComponent(code)}`
}

async function createInvite() {
  try {
    const invite = await request<Invite>('POST', '/invites')
    newInviteLink.value = inviteLink(invite.code)
    invites.value = [invite, ...invites.value]
  } catch {
    ui.showToast('Não foi possível criar o convite (sem conexão?)')
  }
}

async function shareInvite() {
  const text = `Bora treinar no Pino! Crie sua conta: ${newInviteLink.value}`
  if (navigator.share) {
    await navigator.share({ title: 'Convite para o Pino', text }).catch(() => undefined)
    return
  }
  try {
    await navigator.clipboard.writeText(newInviteLink.value)
    ui.showToast('Link copiado')
  } catch {
    inviteLinkInput.value?.select()
  }
}

function inviteStatus(invite: Invite) {
  if (invite.used_by_name) return `Usado por ${invite.used_by_name}`
  const expires = new Date(invite.expires_at)
  if (expires <= new Date()) return 'Expirado'
  return `Válido até ${expires.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })}`
}

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
  if (!confirm('Restaurar o backup vai SUBSTITUIR todas as suas fichas atuais. Continuar?')) return
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
  if (routine.pending && !confirm(`${routine.pending} alteração(ões) ainda não sincronizada(s) serão perdidas se você sair agora. Sair mesmo assim?`)) {
    return
  }
  await auth.logout()
  await router.replace('/entrar')
}
</script>

<template>
  <div class="pt-safe pb-safe mx-auto max-w-lg px-4">
    <header class="flex items-center gap-2 py-3">
      <button type="button" class="-ml-2 px-2 text-2xl text-muted" aria-label="Voltar" @click="router.back()">‹</button>
      <h1 class="font-display text-2xl font-extrabold tracking-wide uppercase">Ajustes</h1>
    </header>

    <section v-if="auth.user" class="mt-2 flex items-center gap-3 rounded-xl bg-surface px-4 py-3">
      <div class="min-w-0 flex-1">
        <p class="truncate font-semibold">{{ auth.user.name }}</p>
        <p class="truncate text-sm text-subtle">{{ auth.user.email }}</p>
      </div>
      <button type="button" class="rounded-lg px-3 py-2 text-sm text-muted active:bg-raised" @click="logout">Sair</button>
    </section>

    <section v-if="auth.user?.is_admin" class="mt-6 flex flex-col gap-2">
      <h2 class="text-sm font-medium text-muted">Convidar amigos</h2>
      <p class="text-sm text-subtle">Cada link vale para uma pessoa, por 7 dias.</p>
      <button type="button" class="rounded-xl bg-accent py-3 font-semibold text-on-accent" @click="createInvite">
        Gerar link de convite
      </button>
      <div v-if="newInviteLink" class="flex gap-2">
        <input
          id="invite-link"
          ref="inviteLinkInput"
          :value="newInviteLink"
          readonly
          aria-label="Link de convite"
          class="min-w-0 flex-1 rounded-xl bg-surface px-3 py-2 font-mono text-xs text-fg outline-none"
          @focus="($event.target as HTMLInputElement).select()"
        />
        <button type="button" class="rounded-xl bg-raised px-4 text-sm font-semibold" @click="shareInvite">Enviar</button>
      </div>
      <ul v-if="invites.length" class="divide-y divide-line rounded-xl bg-surface text-sm">
        <li v-for="invite in invites" :key="invite.code" class="flex items-center justify-between gap-3 px-4 py-2">
          <span class="font-mono text-xs text-subtle">{{ invite.code }}</span>
          <span :class="invite.used_by_name ? 'text-fg' : 'text-muted'">{{ inviteStatus(invite) }}</span>
        </li>
      </ul>
    </section>

    <section class="mt-6">
      <h2 class="mb-2 text-sm font-medium text-muted">Fichas</h2>
      <draggable
        :list="routine.workouts"
        item-key="id"
        handle=".drag-handle"
        class="flex flex-col gap-2"
        @end="onReorder"
      >
        <template #item="{ element }">
          <div class="flex items-center gap-2 rounded-xl bg-surface px-3 py-1">
            <span class="drag-handle cursor-grab touch-none text-faint select-none">⋮⋮</span>
            <input
              :value="element.name"
              class="min-w-0 flex-1 bg-transparent py-2 outline-none"
              enterkeyhint="done"
              @blur="rename(element.id, $event)"
              @keydown.enter="($event.target as HTMLInputElement).blur()"
            />
            <span class="text-xs text-subtle">{{ element.exercises.length }} ex.</span>
            <button type="button" class="px-2 text-danger" aria-label="Apagar ficha" @click="removeWorkout(element.id, element.name)">
              ✕
            </button>
          </div>
        </template>
      </draggable>
      <p v-if="!routine.workouts.length" class="text-sm text-subtle">Nenhuma ficha.</p>
    </section>

    <section class="mt-6">
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

    <section class="mt-6 flex flex-col gap-2">
      <h2 class="text-sm font-medium text-muted">Dados</h2>
      <RouterLink to="/importar" class="rounded-xl bg-surface px-4 py-3">Colar ficha em texto</RouterLink>
      <button type="button" class="rounded-xl bg-surface px-4 py-3 text-left" @click="exportBackup">
        Exportar backup (JSON)
      </button>
      <button type="button" class="rounded-xl bg-surface px-4 py-3 text-left" @click="fileInput?.click()">
        Restaurar backup…
      </button>
      <input ref="fileInput" type="file" accept="application/json,.json" class="hidden" @change="importBackup" />
    </section>
  </div>
</template>
