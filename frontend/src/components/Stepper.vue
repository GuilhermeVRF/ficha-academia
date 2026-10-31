<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{ modelValue: number; step: number; unit: string; decimal?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: number] }>()

const text = ref(format(props.modelValue))
watch(
  () => props.modelValue,
  (value) => (text.value = format(value)),
)

function format(value: number) {
  return props.decimal ? String(value).replace('.', ',') : String(value)
}

function bump(direction: 1 | -1) {
  const next = Math.max(0, Math.round((props.modelValue + direction * props.step) * 100) / 100)
  emit('update:modelValue', next)
  navigator.vibrate?.(8)
}

function commit() {
  const parsed = Number(text.value.replace(',', '.'))
  if (Number.isFinite(parsed) && parsed >= 0) {
    emit('update:modelValue', props.decimal ? Math.round(parsed * 100) / 100 : Math.round(parsed))
  } else {
    text.value = format(props.modelValue)
  }
}
</script>

<template>
  <div class="flex items-center rounded-xl bg-raised">
    <button
      type="button"
      class="grid h-11 w-10 place-items-center text-xl text-muted active:text-accent-ink"
      :aria-label="`Diminuir ${unit}`"
      @click="bump(-1)"
    >
      −
    </button>
    <label class="flex min-w-0 flex-1 items-baseline justify-center gap-0.5">
      <input
        v-model="text"
        class="w-full min-w-0 bg-transparent text-center font-display text-2xl font-bold tabular-nums text-fg outline-none"
        :inputmode="decimal ? 'decimal' : 'numeric'"
        enterkeyhint="done"
        @focus="($event.target as HTMLInputElement).select()"
        @blur="commit"
        @keydown.enter="($event.target as HTMLInputElement).blur()"
      />
      <span class="shrink-0 text-xs text-subtle">{{ unit }}</span>
    </label>
    <button
      type="button"
      class="grid h-11 w-10 place-items-center text-xl text-muted active:text-accent-ink"
      :aria-label="`Aumentar ${unit}`"
      @click="bump(1)"
    >
      +
    </button>
  </div>
</template>
