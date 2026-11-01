<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const email = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

/** Only follow in-app paths, never a link someone crafted to leave the app. */
function safeBack(value: unknown) {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') ? value : '/'
}

async function submit() {
  busy.value = true
  error.value = ''
  try {
    await auth.signIn('/auth/login', { email: email.value, password: password.value })
    await router.replace(safeBack(route.query.voltar))
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
      <div class="flex flex-col items-center gap-3">
        <img src="/icon.svg" alt="" class="h-16 w-16 rounded-2xl" />
        <h1 class="font-display text-4xl font-extrabold tracking-wide uppercase">Pino</h1>
      </div>

      <form class="flex flex-col gap-3" @submit.prevent="submit">
        <label class="flex flex-col gap-1 text-sm text-muted" for="login-email">
          E-mail
          <input
            id="login-email"
            v-model="email"
            type="email"
            autocomplete="username"
            required
            class="rounded-xl bg-surface px-4 py-3 text-base text-fg outline-none focus:ring-2 focus:ring-accent"
          />
        </label>
        <label class="flex flex-col gap-1 text-sm text-muted" for="login-password">
          Senha
          <input
            id="login-password"
            v-model="password"
            type="password"
            autocomplete="current-password"
            required
            class="rounded-xl bg-surface px-4 py-3 text-base text-fg outline-none focus:ring-2 focus:ring-accent"
          />
        </label>
        <p v-if="error" class="text-sm text-danger" role="alert">{{ error }}</p>
        <button
          :disabled="busy"
          class="mt-1 rounded-xl bg-accent py-3 font-semibold text-on-accent disabled:opacity-50"
        >
          Entrar
        </button>
      </form>

      <p class="text-center text-sm text-subtle">
        Recebeu um convite?
        <RouterLink to="/cadastro" class="text-accent-ink underline">Criar conta</RouterLink>
      </p>
    </div>
  </main>
</template>
