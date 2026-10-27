<script setup lang="ts">
import { ref } from 'vue'
import Stepper from './Stepper.vue'
import type { SetData } from '@/types'

defineProps<{ set: SetData; index: number; done: boolean; weightStep: number }>()
const emit = defineEmits<{ update: [set: SetData]; remove: []; toggle: [] }>()

const SWIPE_THRESHOLD = 90
const offset = ref(0)
let startX = 0
let startY = 0
let tracking = false

function onPointerDown(event: PointerEvent) {
  if ((event.target as HTMLElement).closest('input, button')) return
  startX = event.clientX
  startY = event.clientY
  tracking = true
}

function onPointerMove(event: PointerEvent) {
  if (!tracking) return
  const dx = event.clientX - startX
  if (Math.abs(event.clientY - startY) > Math.abs(dx)) {
    tracking = false
    offset.value = 0
    return
  }
  offset.value = Math.min(0, dx)
}

function onPointerUp() {
  if (tracking && offset.value < -SWIPE_THRESHOLD) emit('remove')
  tracking = false
  offset.value = 0
}
</script>

<template>
  <div class="relative overflow-hidden rounded-xl">
    <div v-if="offset < 0" class="absolute inset-0 flex items-center justify-end bg-red-600/80 pr-4 text-sm font-medium text-white">
      Remover
    </div>
    <div
      class="relative flex touch-pan-y items-center gap-2 bg-zinc-900 py-1 transition-[opacity]"
      :class="{ 'opacity-45': done }"
      :style="{ transform: `translateX(${offset}px)`, transition: offset ? 'none' : 'transform 0.2s' }"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerUp"
    >
      <button
        type="button"
        class="grid h-9 w-9 shrink-0 place-items-center rounded-full text-sm font-semibold"
        :class="done ? 'bg-lime-400 text-zinc-950' : 'bg-zinc-800 text-zinc-400'"
        :aria-label="done ? `Desmarcar série ${index + 1}` : `Marcar série ${index + 1} como feita`"
        @click="emit('toggle')"
      >
        {{ done ? '✓' : index + 1 }}
      </button>
      <Stepper
        class="flex-[1.15]"
        :model-value="set.weight_kg"
        :step="weightStep"
        unit="kg"
        decimal
        @update:model-value="emit('update', { ...set, weight_kg: $event })"
      />
      <Stepper
        class="flex-1"
        :model-value="set.reps"
        :step="1"
        unit="rep"
        @update:model-value="emit('update', { ...set, reps: $event })"
      />
    </div>
  </div>
</template>
