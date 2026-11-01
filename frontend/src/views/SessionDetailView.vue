<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { request } from '@/lib/api'
import { formatDuration, formatLongDate } from '@/lib/dates'
import { formatWeight } from '@/lib/format'
import { plateBg } from '@/lib/plates'
import { useHistoryStore } from '@/stores/history'
import { useSessionStore } from '@/stores/session'
import type { SessionDetail, SessionSet } from '@/types'

const props = defineProps<{ id: string }>()

const history = useHistoryStore()
const session = useSessionStore()
const route = useRoute()
const router = useRouter()

const isNew = route.query.novo === '1'
const detail = ref<SessionDetail | null>(session.lastFinished?.id === props.id ? session.lastFinished : null)
const summary = computed(() => detail.value ?? history.sessions.find((item) => item.id === props.id) ?? null)
const loadFailed = ref(false)

onMounted(async () => {
  if (detail.value) return
  try {
    detail.value = await request<SessionDetail>('GET', `/sessions/${props.id}`)
  } catch {
    loadFailed.value = true
  }
})

const exercises = computed(() => {
  const groups = new Map<number, { name: string; sets: SessionSet[] }>()
  for (const item of detail.value?.sets ?? []) {
    const group = groups.get(item.exercise_position) ?? { name: item.exercise_name, sets: [] }
    group.sets.push(item)
    groups.set(item.exercise_position, group)
  }
  return [...groups.entries()].sort(([a], [b]) => a - b).map(([, group]) => group)
})

const durationText = computed(() =>
  summary.value
    ? formatDuration(new Date(summary.value.finished_at).getTime() - new Date(summary.value.started_at).getTime())
    : '',
)

function remove() {
  if (!confirm('Apagar este treino do histórico?')) return
  history.remove(props.id)
  void router.replace('/')
}
</script>

<template>
  <div class="pt-safe pb-safe mx-auto flex max-w-lg flex-col gap-4 px-4">
    <header class="flex items-center gap-2 py-3">
      <RouterLink to="/" class="-ml-2 px-2 text-2xl text-muted" aria-label="Voltar para o início">‹</RouterLink>
      <h1 class="text-sm text-subtle">{{ isNew ? 'Treino concluído' : 'Treino' }}</h1>
    </header>

    <p v-if="!summary && loadFailed" class="mt-10 text-center text-subtle">Treino não encontrado.</p>
    <p v-else-if="!summary" class="mt-10 text-center text-subtle">Carregando…</p>

    <template v-else>
      <section class="flex flex-col gap-1">
        <p v-if="isNew" class="font-display text-lg font-bold tracking-wide text-accent-ink uppercase">Mais um pra conta.</p>
        <div class="flex items-center gap-3">
          <span class="h-4 w-4 shrink-0 rounded-full" :class="plateBg(summary.workout_color)" aria-hidden="true" />
          <h2 class="truncate font-display text-4xl font-extrabold tracking-wide uppercase">{{ summary.workout_name }}</h2>
        </div>
        <p class="text-sm text-subtle first-letter:uppercase">
          {{ formatLongDate(new Date(summary.started_at)) }} ·
          {{ new Date(summary.started_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) }}
        </p>
      </section>

      <section class="grid grid-cols-3 gap-2 text-center">
        <div class="rounded-2xl bg-surface p-3">
          <p class="font-display text-3xl font-extrabold tabular-nums">{{ durationText }}</p>
          <p class="text-xs text-subtle">duração</p>
        </div>
        <div class="rounded-2xl bg-surface p-3">
          <p class="font-display text-3xl font-extrabold tabular-nums">{{ summary.sets_done }}</p>
          <p class="text-xs text-subtle">séries feitas</p>
        </div>
        <div class="rounded-2xl bg-surface p-3">
          <p class="font-display text-3xl font-extrabold tabular-nums">{{ formatWeight(Math.round(summary.volume_kg)) }}</p>
          <p class="text-xs text-subtle">kg de volume</p>
        </div>
      </section>

      <p v-if="!detail && loadFailed" class="text-sm text-subtle">Os detalhes das séries aparecem quando houver conexão.</p>
      <section v-for="exercise in exercises" :key="exercise.name" class="rounded-2xl bg-surface p-3">
        <h3 class="mb-2 font-semibold">{{ exercise.name }}</h3>
        <ol class="flex flex-col gap-1 text-sm tabular-nums">
          <li v-for="item in exercise.sets" :key="item.set_index" class="flex items-center gap-3" :class="item.done ? 'text-fg' : 'text-faint line-through'">
            <span class="w-5 font-display text-base font-bold text-subtle">{{ item.set_index + 1 }}</span>
            <span class="flex-1">{{ formatWeight(item.weight_kg) }} kg × {{ item.reps }}</span>
            <span :aria-label="item.done ? 'feita' : 'não feita'">{{ item.done ? '✓' : '–' }}</span>
          </li>
        </ol>
      </section>

      <RouterLink v-if="isNew" to="/" class="rounded-xl bg-accent py-3 text-center font-semibold text-on-accent">Voltar ao início</RouterLink>
      <button type="button" class="py-2 text-sm text-danger" @click="remove">Apagar este treino</button>
    </template>
  </div>
</template>
