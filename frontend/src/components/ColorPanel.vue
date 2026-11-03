<script setup lang="ts">
import { computed } from 'vue'
import { PLATE_BG, PLATE_COLORS } from '@/lib/plates'
import { useRoutineStore } from '@/stores/routine'
import type { PlateColor } from '@/types'

const props = defineProps<{ workoutId: string; modelValue: PlateColor }>()
const emit = defineEmits<{ 'update:modelValue': [color: PlateColor] }>()

const PLATES: Record<PlateColor, { name: string; weight: string }> = {
  red: { name: 'Vermelha', weight: '25 kg' },
  blue: { name: 'Azul', weight: '20 kg' },
  yellow: { name: 'Amarela', weight: '15 kg' },
  green: { name: 'Verde', weight: '10 kg' },
  white: { name: 'Branca', weight: '5 kg' },
}

const routine = useRoutineStore()

/** Initials of the other workouts already using each color, so repeats are a choice, not an accident. */
const usedBy = computed(() => {
  const map = new Map<PlateColor, string[]>()
  for (const workout of routine.workouts) {
    if (workout.id === props.workoutId) continue
    map.set(workout.color, [...(map.get(workout.color) ?? []), initial(workout.name)])
  }
  return map
})

/** "Treino B (cópia)" → "B": the lone letter people use for workouts, else the first letter. */
function initial(name: string) {
  const letter = name.match(/(?:^|\s)(\p{L})(?=\s|$)/u)?.[1] ?? name.trim().charAt(0)
  return letter.toUpperCase()
}
</script>

<template>
  <fieldset class="rounded-2xl bg-surface p-3">
    <legend class="sr-only">Cor da ficha</legend>
    <p class="mb-3 text-xs font-semibold tracking-widest text-subtle uppercase" aria-hidden="true">Cor da ficha</p>
    <div class="grid grid-cols-5 gap-2">
      <label
        v-for="color in PLATE_COLORS"
        :key="color"
        class="flex cursor-pointer flex-col items-center gap-1.5 text-center text-[11px] leading-tight"
        :class="color === modelValue ? 'font-semibold text-fg' : 'text-muted'"
      >
        <input
          type="radio"
          name="workout-color"
          class="peer sr-only"
          :value="color"
          :checked="color === modelValue"
          @change="emit('update:modelValue', color)"
        />
        <span
          class="grid h-11 w-11 place-items-center rounded-full font-display text-base font-extrabold text-[#15171b] shadow-[inset_0_0_0_6px_rgba(0,0,0,0.18)] transition peer-focus-visible:ring-2 peer-focus-visible:ring-accent"
          :class="[PLATE_BG[color], color === modelValue ? 'scale-110 outline-2 outline-offset-3 outline-accent' : '']"
          aria-hidden="true"
        >
          {{ color === modelValue ? '✓' : (usedBy.get(color) ?? []).slice(0, 2).join('') }}
        </span>
        <span>{{ PLATES[color].name }}<br /><span class="text-subtle">{{ PLATES[color].weight }}</span></span>
        <span v-if="usedBy.get(color)?.length && color !== modelValue" class="sr-only">
          já usada por {{ usedBy.get(color)?.length }} ficha(s)
        </span>
      </label>
    </div>
  </fieldset>
</template>
