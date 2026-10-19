import { createRouter, createWebHistory } from 'vue-router'
import Login from './views/Login.vue'
import Workbench from './views/Workbench.vue'
import CandidateDetail from './views/CandidateDetail.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: Login },
    { path: '/', component: Workbench, meta: { requiresAuth: true } },
    { path: '/candidates/:id', component: CandidateDetail, meta: { requiresAuth: true } },
  ],
})

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) return '/login'
  if (to.path === '/login' && token) return '/'
  return true
})

export default router