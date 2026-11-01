import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from './stores/auth'
import HomeView from './views/HomeView.vue'

declare module 'vue-router' {
  interface RouteMeta {
    /** Reachable while signed out (and pointless while signed in). */
    public?: boolean
    /** One of the bottom-bar tabs, which show the navigation bar. */
    tab?: boolean
  }
}

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView, meta: { tab: true } },
    { path: '/entrar', component: () => import('./views/LoginView.vue'), meta: { public: true } },
    { path: '/cadastro', component: () => import('./views/SignupView.vue'), meta: { public: true } },
    { path: '/fichas', component: () => import('./views/FichasView.vue'), meta: { tab: true } },
    { path: '/treino/:id', component: () => import('./views/RoutineView.vue'), props: true },
    { path: '/treino/:id/sessao', component: () => import('./views/SessionView.vue'), props: true },
    { path: '/sessao/:id', component: () => import('./views/SessionDetailView.vue'), props: true },
    { path: '/exercicio/:id', component: () => import('./views/ExerciseView.vue'), props: true },
    { path: '/importar', component: () => import('./views/ImportView.vue') },
    { path: '/configuracoes', component: () => import('./views/SettingsView.vue'), meta: { tab: true } },
    { path: '/perfil', component: () => import('./views/ProfileView.vue'), meta: { tab: true } },
    { path: '/ajustes', redirect: '/configuracoes' },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.init()
  if (to.meta.public) return auth.user ? '/' : true
  if (!auth.user) return { path: '/entrar', query: to.fullPath === '/' ? {} : { voltar: to.fullPath } }
  return true
})
