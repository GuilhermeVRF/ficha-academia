import { createRouter, createWebHistory } from 'vue-router'
import RoutineView from './views/RoutineView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: RoutineView },
    { path: '/exercicio/:id', component: () => import('./views/ExerciseView.vue'), props: true },
    { path: '/importar', component: () => import('./views/ImportView.vue') },
    { path: '/ajustes', component: () => import('./views/SettingsView.vue') },
  ],
})
