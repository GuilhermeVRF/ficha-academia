<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { NetworkError, request } from '@/lib/api'
import { MUSCLE_GROUPS, MUSCLE_LABEL } from '@/lib/muscles'
import type { CatalogItem, MuscleGroup } from '@/types'

/**
 * Full-screen exercise library. With `multiple`, people tick several and
 * confirm; otherwise the first tap picks. Offline, a typed name can still be
 * added without a photo.
 */
const props = withDefaults(defineProps<{ title?: string; multiple?: boolean; confirmLabel?: string }>(), {
  title: 'Adicionar exercícios',
  multiple: true,
  confirmLabel: 'Adicionar',
})
const emit = defineEmits<{
  pick: [items: CatalogItem[]]
  /** Offline fallback: just a name, no library entry. */
  pickName: [name: string]
  close: []
}>()

const SEARCH_DELAY_MS = 150

const query = ref('')
const group = ref<MuscleGroup | null>(null)
const results = ref<CatalogItem[]>([])
const loading = ref(false)
const offline = ref(false)
const selected = ref<CatalogItem[]>([])
const creating = ref(false)
const searchInput = ref<HTMLInputElement>()
let timer: ReturnType<typeof setTimeout> | undefined
let lastRequest = 0

const trimmed = computed(() => query.value.trim())
const exactMatch = computed(() =>
  results.value.some((item) => item.name.toLowerCase() === trimmed.value.toLowerCase()),
)

onMounted(async () => {
  document.documentElement.style.overflow = 'hidden'
  await nextTick()
  searchInput.value?.focus()
  void search()
})
onUnmounted(() => {
  document.documentElement.style.overflow = ''
  clearTimeout(timer)
})

watch([query, group], () => {
  clearTimeout(timer)
  timer = setTimeout(() => void search(), SEARCH_DELAY_MS)
})

async function search() {
  const requestId = ++lastRequest
  loading.value = true
  const params = new URLSearchParams({ q: trimmed.value })
  if (group.value) params.set('group', group.value)
  try {
    const found = await request<CatalogItem[]>('GET', `/catalog?${params}`)
    if (requestId !== lastRequest) return
    results.value = found
    offline.value = false
  } catch (error) {
    if (requestId !== lastRequest) return
    if (!(error instanceof NetworkError)) throw error
    offline.value = true
  } finally {
    if (requestId === lastRequest) loading.value = false
  }
}

function isSelected(item: CatalogItem) {
  return selected.value.some((other) => other.id === item.id)
}

function toggle(item: CatalogItem) {
  if (!props.multiple) {
    emit('pick', [item])
    return
  }
  selected.value = isSelected(item) ? selected.value.filter((other) => other.id !== item.id) : [...selected.value, item]
}

/** Save the typed name as the user's own exercise, then pick it like any other. */
async function createCustom() {
  if (!trimmed.value || creating.value) return
  creating.value = true
  try {
    const item = await request<CatalogItem>('POST', '/catalog', {
      id: crypto.randomUUID(),
      name: trimmed.value,
      muscle_group: group.value ?? 'peito',
    })
    results.value = [item, ...results.value]
    toggle(item)
  } catch (error) {
    if (!(error instanceof NetworkError)) throw error
    emit('pickName', trimmed.value)
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div class="fixed inset-0 z-40 flex flex-col bg-bg" role="dialog" aria-modal="true" :aria-label="title">
    <header class="pt-safe border-b border-line px-4 pb-3">
      <div class="flex items-center gap-2 py-2">
        <button type="button" class="-ml-2 px-2 text-2xl text-muted" aria-label="Fechar" @click="emit('close')">✕</button>
        <h2 class="flex-1 font-display text-2xl font-extrabold tracking-wide uppercase">{{ title }}</h2>
      </div>
      <input
        id="exercise-search"
        ref="searchInput"
        v-model="query"
        type="search"
        placeholder="Buscar: supino, remada, agachamento…"
        aria-label="Buscar exercício"
        enterkeyhint="search"
        autocomplete="off"
        class="w-full rounded-xl bg-surface px-4 py-3 outline-none focus:ring-2 focus:ring-accent"
      />
      <div class="-mx-4 mt-3 flex gap-2 overflow-x-auto px-4 [scrollbar-width:none]" role="group" aria-label="Grupo muscular">
        <button
          type="button"
          class="shrink-0 rounded-full px-3 py-1.5 text-sm"
          :class="group === null ? 'bg-accent text-on-accent' : 'bg-surface text-fg'"
          :aria-pressed="group === null"
          @click="group = null"
        >
          Todos
        </button>
        <button
          v-for="item in MUSCLE_GROUPS"
          :key="item.key"
          type="button"
          class="shrink-0 rounded-full px-3 py-1.5 text-sm"
          :class="group === item.key ? 'bg-accent text-on-accent' : 'bg-surface text-fg'"
          :aria-pressed="group === item.key"
          @click="group = group === item.key ? null : item.key"
        >
          {{ item.label }}
        </button>
      </div>
    </header>

    <main class="flex-1 overflow-y-auto px-2 py-2" :class="{ 'opacity-60': loading }">
      <p v-if="offline" class="mx-2 my-3 rounded-xl bg-surface p-3 text-sm text-muted">
        Sem conexão: a biblioteca não está disponível. Você ainda pode adicionar pelo nome digitado.
      </p>

      <ul class="flex flex-col">
        <li v-for="item in results" :key="item.id">
          <button
            type="button"
            class="flex w-full items-center gap-3 rounded-xl px-2 py-2 text-left active:bg-surface"
            :aria-pressed="multiple ? isSelected(item) : undefined"
            @click="toggle(item)"
          >
            <img
              v-if="item.images[0]"
              :src="item.images[0]"
              alt=""
              loading="lazy"
              class="h-14 w-14 shrink-0 rounded-lg bg-white object-cover"
            />
            <span v-else class="grid h-14 w-14 shrink-0 place-items-center rounded-lg bg-raised font-display text-2xl font-bold text-subtle uppercase" aria-hidden="true">
              {{ item.name.slice(0, 1) }}
            </span>
            <span class="min-w-0 flex-1">
              <span class="block font-semibold leading-tight">{{ item.name }}</span>
              <span class="block text-xs text-subtle">
                {{ MUSCLE_LABEL[item.muscle_group] }}<template v-if="item.equipment"> · {{ item.equipment }}</template>
                <template v-if="item.custom"> · seu exercício</template>
                <template v-else-if="item.uses"> · já está nas suas fichas</template>
              </span>
            </span>
            <span
              v-if="multiple"
              class="grid h-7 w-7 shrink-0 place-items-center rounded-full text-sm"
              :class="isSelected(item) ? 'bg-accent text-on-accent' : 'ring-1 ring-line'"
              aria-hidden="true"
            >
              {{ isSelected(item) ? '✓' : '' }}
            </span>
          </button>
        </li>
      </ul>

      <p v-if="!loading && !offline && !results.length" class="px-2 py-6 text-center text-sm text-subtle">
        Nada encontrado{{ trimmed ? ` para "${trimmed}"` : '' }}.
      </p>

      <button
        v-if="trimmed && !exactMatch"
        type="button"
        class="mx-2 my-3 flex w-[calc(100%-1rem)] items-center gap-3 rounded-xl border border-dashed border-line px-4 py-3 text-left"
        :disabled="creating"
        @click="createCustom"
      >
        <span class="text-2xl text-accent-ink" aria-hidden="true">+</span>
        <span class="min-w-0 flex-1">
          <span class="block font-semibold">Criar "{{ trimmed }}"</span>
          <span class="block text-xs text-subtle">
            Exercício seu, sem foto{{ group ? `, em ${MUSCLE_LABEL[group]}` : '' }}
          </span>
        </span>
      </button>
    </main>

    <footer v-if="multiple" class="border-t border-line px-4 pt-3 pb-[calc(env(safe-area-inset-bottom)+1rem)]">
      <button
        type="button"
        class="w-full rounded-xl bg-accent py-3 font-semibold text-on-accent disabled:opacity-40"
        :disabled="!selected.length"
        @click="emit('pick', selected)"
      >
        {{ confirmLabel }}{{ selected.length ? ` ${selected.length} exercício${selected.length > 1 ? 's' : ''}` : '' }}
      </button>
    </footer>
  </div>
</template>
