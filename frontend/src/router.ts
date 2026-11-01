import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from './stores/auth'
import HomeView from './views/HomeView.vue'

declare module 'vue-router' {
  interface RouteMeta {
    /** Reachable while signed out (and pointless while signed in). */
    public?: boolean
  }
}

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    { path: '/entrar', component: () => import('./views/LoginView.vue'), meta: { public: true } },
    { path: '/cadastro', component: () => import('./views/SignupView.vue'), meta: { public: true } },
    { path: '/fichas', component: () => import('./views/FichasView.vue') },
    { path: '/treino/:id', component: () => import('./views/RoutineView.vue'), props: true },
    { path: '/treino/:id/sessao', component: () => import('./views/SessionView.vue'), props: true },
    { path: '/sessao/:id', component: () => import('./views/SessionDetailView.vue'), props: true },
    { path: '/exercicio/:id', component: () => import('./views/ExerciseView.vue'), props: true },
    { path: '/importar', component: () => import('./views/ImportView.vue') },
    { path: '/ajustes', component: () => import('./views/SettingsView.vue') },
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
