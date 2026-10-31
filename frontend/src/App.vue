<script setup lang="ts">
import { onMounted } from 'vue'
import LoginView from './views/LoginView.vue'
import AppToast from './components/AppToast.vue'
import { useRoutineStore } from './stores/routine'

const routine = useRoutineStore()

onMounted(() => void routine.init())
</script>

<template>
  <LoginView v-if="routine.unauthorized" />
  <template v-else>
    <RouterView v-if="routine.loaded" />
    <div v-else class="grid min-h-dvh place-items-center text-subtle">Carregando…</div>
  </template>
  <AppToast />
</template>
