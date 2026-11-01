<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'

const MIN_PASSWORD_LENGTH = 8

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const name = ref('')
const email = ref('')
const password = ref('')
const inviteCode = ref(typeof route.query.convite === 'string' ? route.query.convite : '')
const error = ref('')
const busy = ref(false)

async function submit() {
  busy.value = true
  error.value = ''
  try {
    await auth.signIn('/auth/signup', {
      name: name.value,
      email: email.value,
      password: password.value,
      invite_code: inviteCode.value,
    })
    await router.replace('/')
  } catch (failure) {
    error.value = failure instanceof ApiError ? failure.message : 'Sem conexão com o servidor.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="pt-safe pb-safe grid min-h-dvh place-items-center px-6">
    <div class="flex w-full max-w-xs flex-col gap-6">
      <div class="flex flex-col items-center gap-3 text-center">
        <img src="/icon.svg" alt="" class="h-16 w-16 rounded-2xl" />
        <h1 class="font-display text-4xl font-extrabold tracking-wide uppercase">Criar conta</h1>
        <p class="text-sm text-muted">O Pino é só para convidados. Use o link ou o código que você recebeu.</p>
      </div>

      <form class="flex flex-col gap-3" @submit.prevent="submit">
        <label class="flex flex-col gap-1 text-sm text-muted" for="signup-name">
          Nome
          <input
            id="signup-name"
            v-model="name"
            autocomplete="given-name"
            required
            maxlength="80"
            class="rounded-xl bg-surface px-4 py-3 text-base text-fg outline-none focus:ring-2 focus:ring-accent"
          />
        </label>
        <label class="flex flex-col gap-1 text-sm text-muted" for="signup-email">
          E-mail
          <input
            id="signup-email"
            v-model="email"
            type="email"
            autocomplete="username"
            required
            class="rounded-xl bg-surface px-4 py-3 text-base text-fg outline-none focus:ring-2 focus:ring-accent"
          />
        </label>
        <label class="flex flex-col gap-1 text-sm text-muted" for="signup-password">
          Senha
          <input
            id="signup-password"
            v-model="password"
            type="password"
            autocomplete="new-password"
            required
            :minlength="MIN_PASSWORD_LENGTH"
            class="rounded-xl bg-surface px-4 py-3 text-base text-fg outline-none focus:ring-2 focus:ring-accent"
          />
          <span class="text-xs text-subtle">Pelo menos {{ MIN_PASSWORD_LENGTH }} caracteres.</span>
        </label>
        <label class="flex flex-col gap-1 text-sm text-muted" for="signup-invite">
          Código do convite
          <input
            id="signup-invite"
            v-model="inviteCode"
            autocomplete="off"
            autocapitalize="off"
            required
            class="rounded-xl bg-surface px-4 py-3 font-mono text-base text-fg outline-none focus:ring-2 focus:ring-accent"
          />
        </label>
        <p v-if="error" class="text-sm text-danger" role="alert">{{ error }}</p>
        <button
          :disabled="busy"
          class="mt-1 rounded-xl bg-accent py-3 font-semibold text-on-accent disabled:opacity-50"
        >
          Criar conta e entrar
        </button>
      </form>

      <p class="text-center text-sm text-subtle">
        Já tem conta?
        <RouterLink to="/entrar" class="text-accent-ink underline">Entrar</RouterLink>
      </p>
    </div>
  </main>
</template>
