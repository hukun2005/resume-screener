import { createRouter, createWebHistory } from 'vue-router'
import Login from './views/Login.vue'
import Workbench from './views/Workbench.vue'
import CandidateDetail from './views/CandidateDetail.vue'
import Kanban from './views/Kanban.vue'
import Interviews from './views/Interviews.vue'
import Users from './views/Users.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: Login },
    { path: '/', component: Workbench, meta: { requiresAuth: true, roles: ['admin', 'hr'] } },
    { path: '/candidates/:id', component: CandidateDetail, meta: { requiresAuth: true } },
    { path: '/kanban', component: Kanban, meta: { requiresAuth: true } },
    {
      path: '/interviews',
      component: Interviews,
      meta: { requiresAuth: true, roles: ['admin', 'hr', 'tech'], title: '面试管理' },
    },
    {
      path: '/users',
      component: Users,
      meta: { requiresAuth: true, roles: ['admin'], title: '账号与权限' },
    },
  ],
})

// 技术部的落地页是看板，HR / 管理员是工作台
function homeOf(role) {
  return role === 'tech' ? '/kanban' : '/'
}

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  const role = localStorage.getItem('role') || ''
  if (to.meta.requiresAuth && !token) return '/login'
  if (to.path === '/login' && token) return homeOf(role)
  if (to.meta.roles && !to.meta.roles.includes(role)) return homeOf(role)
  return true
})

export default router
