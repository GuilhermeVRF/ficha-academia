<script setup lang="ts">
import { ref } from 'vue'
import { ApiError, request } from '@/lib/api'
import { useRoutineStore } from '@/stores/routine'

const routine = useRoutineStore()
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  busy.value = true
  error.value = ''
  try {
    await request('POST', '/auth/login', { password: password.value })
    routine.unauthorized = false
    await routine.refresh()
    routine.loaded = true
  } catch (failure) {
    error.value = failure instanceof ApiError ? failure.message : 'Sem conexão com o servidor.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="grid min-h-dvh place-items-center px-6">
    <form class="flex w-full max-w-xs flex-col gap-3" @submit.prevent="submit">
      <img src="/icon.svg" alt="" class="mx-auto mb-2 h-16 w-16" />
      <h1 class="text-center font-display text-4xl font-extrabold tracking-wide uppercase">Pino</h1>
      <input
        v-model="password"
        type="password"
        autocomplete="current-password"
        placeholder="Senha"
        class="rounded-xl bg-surface px-4 py-3 outline-none focus:ring-2 focus:ring-accent"
        autofocus
      />
      <p v-if="error" class="text-sm text-danger">{{ error }}</p>
      <button
        :disabled="busy || !password"
        class="rounded-xl bg-accent py-3 font-semibold text-on-accent disabled:opacity-50"
      >
        Entrar
      </button>
    </form>
  </main>
</template>
