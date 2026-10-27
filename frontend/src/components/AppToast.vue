<script setup lang="ts">
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
</script>

<template>
  <Transition
    enter-from-class="translate-y-4 opacity-0"
    leave-to-class="translate-y-4 opacity-0"
    enter-active-class="transition"
    leave-active-class="transition"
  >
    <div
      v-if="ui.toast"
      :key="ui.toast.id"
      class="fixed inset-x-4 bottom-[calc(env(safe-area-inset-bottom)+1rem)] z-50 mx-auto flex max-w-md items-center gap-3 rounded-xl bg-zinc-100 px-4 py-3 text-sm text-zinc-900 shadow-lg"
      role="status"
    >
      <span class="flex-1">{{ ui.toast.message }}</span>
      <button v-if="ui.toast.actionLabel" type="button" class="font-semibold text-lime-700" @click="ui.runToastAction">
        {{ ui.toast.actionLabel }}
      </button>
    </div>
  </Transition>
</template>
