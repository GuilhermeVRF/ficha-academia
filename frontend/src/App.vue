<script setup lang="ts">
import { watch } from 'vue'
import { useRouter } from 'vue-router'
import AppToast from './components/AppToast.vue'
import { useAuthStore } from './stores/auth'
import { useRoutineStore } from './stores/routine'

const auth = useAuthStore()
const routine = useRoutineStore()
const router = useRouter()

watch(
  () => auth.user?.id,
  (id) => {
    if (id) {
      routine.unauthorized = false
      void routine.init()
    } else {
      routine.reset()
    }
  },
  { immediate: true },
)

// Any API call answering 401 means the session ended: ask to sign in again and come back here.
watch(
  () => routine.unauthorized,
  (expired) => {
    if (!expired || !auth.user) return
    auth.expire()
    const back = router.currentRoute.value.fullPath
    void router.replace({ path: '/entrar', query: back === '/' ? {} : { voltar: back } })
  },
)
</script>

<template>
  <RouterView v-if="!auth.user || routine.loaded" />
  <div v-else class="grid min-h-dvh place-items-center text-subtle">Carregando…</div>
  <AppToast />
</template>
