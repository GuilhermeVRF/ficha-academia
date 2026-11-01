<script setup lang="ts">
import { computed } from 'vue'
import { dayKey } from '@/lib/dates'
import { plateBg } from '@/lib/plates'
import type { SessionSummary } from '@/types'

const props = defineProps<{
  year: number
  month: number
  /** Sessions grouped by local day key. */
  byDay: Map<string, SessionSummary[]>
  selected: string
}>()
const emit = defineEmits<{ select: [day: string]; move: [delta: number] }>()

const WEEKDAYS = ['S', 'T', 'Q', 'Q', 'S', 'S', 'D']
const MAX_DOTS = 3

const title = computed(() =>
  new Date(props.year, props.month, 1).toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' }),
)
const today = dayKey(new Date())

const cells = computed(() => {
  const first = new Date(props.year, props.month, 1)
  const leading = (first.getDay() + 6) % 7
  const days = new Date(props.year, props.month + 1, 0).getDate()
  const result: ({ key: string; day: number; sessions: SessionSummary[] } | null)[] = Array(leading).fill(null)
  for (let day = 1; day <= days; day++) {
    const key = dayKey(new Date(props.year, props.month, day))
    result.push({ key, day, sessions: props.byDay.get(key) ?? [] })
  }
  return result
})

const monthCount = computed(() => cells.value.reduce((total, cell) => total + (cell?.sessions.length ?? 0), 0))
const isCurrentMonth = computed(() => {
  const now = new Date()
  return now.getFullYear() === props.year && now.getMonth() === props.month
})
</script>

<template>
  <section class="rounded-2xl bg-surface p-3" aria-label="Calendário de treinos">
    <header class="mb-2 flex items-center gap-1">
      <button type="button" class="grid h-9 w-9 place-items-center rounded-lg text-xl text-muted active:bg-raised" aria-label="Mês anterior" @click="emit('move', -1)">‹</button>
      <div class="flex-1 text-center">
        <p class="font-display text-xl font-bold tracking-wide uppercase">{{ title }}</p>
        <p class="text-xs text-subtle">{{ monthCount }} {{ monthCount === 1 ? 'treino' : 'treinos' }}</p>
      </div>
      <button
        type="button"
        class="grid h-9 w-9 place-items-center rounded-lg text-xl text-muted active:bg-raised disabled:opacity-30"
        aria-label="Próximo mês"
        :disabled="isCurrentMonth"
        @click="emit('move', 1)"
      >
        ›
      </button>
    </header>

    <div class="grid grid-cols-7 gap-1 text-center tabular-nums">
      <span v-for="(weekday, index) in WEEKDAYS" :key="index" class="pb-1 text-[11px] font-semibold text-subtle">{{ weekday }}</span>
      <template v-for="(cell, index) in cells" :key="cell?.key ?? `empty-${index}`">
        <span v-if="!cell" />
        <button
          v-else
          type="button"
          class="relative flex h-11 flex-col items-center justify-center gap-1 rounded-lg text-sm"
          :class="[
            cell.key === selected ? 'bg-raised' : '',
            cell.key === today ? 'font-bold text-accent-ink ring-1 ring-accent' : cell.key > today ? 'text-faint' : 'text-fg',
          ]"
          :aria-label="`${cell.day}${cell.sessions.length ? `, ${cell.sessions.length} treino(s)` : ''}`"
          :aria-pressed="cell.key === selected"
          @click="emit('select', cell.key)"
        >
          {{ cell.day }}
          <span class="flex h-1.5 gap-0.5">
            <span
              v-for="item in cell.sessions.slice(0, MAX_DOTS)"
              :key="item.id"
              class="h-1.5 w-1.5 rounded-full"
              :class="plateBg(item.workout_color)"
            />
          </span>
        </button>
      </template>
    </div>
  </section>
</template>
