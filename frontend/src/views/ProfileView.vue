<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { request } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import { useRoutineStore } from '@/stores/routine'
import { useUiStore } from '@/stores/ui'
import type { Invite } from '@/types'

const auth = useAuthStore()
const routine = useRoutineStore()
const ui = useUiStore()
const router = useRouter()

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

async function logout() {
  if (routine.pending && !confirm(`${routine.pending} alteração(ões) ainda não sincronizada(s) serão perdidas se você sair agora. Sair mesmo assim?`)) {
    return
  }
  await auth.logout()
  await router.replace('/entrar')
}
</script>

<template>
  <div class="pt-safe pb-nav mx-auto flex max-w-lg flex-col gap-6 px-4">
    <h1 class="pt-4 font-display text-3xl font-extrabold tracking-wide uppercase">Perfil</h1>

    <section v-if="auth.user" class="flex items-center gap-4 rounded-2xl bg-surface p-4">
      <span class="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-raised font-display text-2xl font-extrabold uppercase" aria-hidden="true">
        {{ auth.user.name.slice(0, 1) }}
      </span>
      <div class="min-w-0 flex-1">
        <p class="truncate text-lg font-semibold">{{ auth.user.name }}</p>
        <p class="truncate text-sm text-subtle">{{ auth.user.email }}</p>
        <p v-if="auth.user.is_admin" class="mt-1 text-xs font-semibold tracking-widest text-accent-ink uppercase">Administrador</p>
      </div>
    </section>

    <section v-if="auth.user?.is_admin" class="flex flex-col gap-2">
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

    <button type="button" class="rounded-xl bg-danger/15 py-3 font-semibold text-danger" @click="logout">Sair da conta</button>
  </div>
</template>
