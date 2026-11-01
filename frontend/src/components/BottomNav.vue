<script setup lang="ts">
import { useSessionStore } from '@/stores/session'

const session = useSessionStore()

const TABS = [
  { to: '/', label: 'Início', icon: 'M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z' },
  { to: '/fichas', label: 'Fichas', icon: 'M8 4h8M9 2h6v4H9zM6 4H5a1 1 0 0 0-1 1v15a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V5a1 1 0 0 0-1-1h-1M8 11h8M8 15h5' },
  { to: '/configuracoes', label: 'Ajustes', icon: 'M4 7h10M18 7h2M4 17h4M12 17h8M16 5v4M10 15v4' },
  { to: '/perfil', label: 'Perfil', icon: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0' },
] as const
</script>

<template>
  <nav
    class="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-bg/95 pb-[env(safe-area-inset-bottom)] backdrop-blur"
    aria-label="Navegação principal"
  >
    <ul class="mx-auto grid max-w-lg grid-cols-4">
      <li v-for="tab in TABS" :key="tab.to">
        <RouterLink
          :to="tab.to"
          class="relative flex flex-col items-center gap-1 py-2.5 text-[11px] font-medium text-subtle"
          exact-active-class="!text-accent-ink"
        >
          <svg viewBox="0 0 24 24" class="h-6 w-6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path :d="tab.icon" />
          </svg>
          {{ tab.label }}
          <span
            v-if="tab.to === '/' && session.active"
            class="absolute top-2 right-[calc(50%-18px)] h-2 w-2 rounded-full bg-accent"
            aria-label="Treino em andamento"
          />
        </RouterLink>
      </li>
    </ul>
  </nav>
</template>
