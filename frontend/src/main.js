import { createApp } from 'vue'
import App from './App.vue'
import router from './router.js'
import { syncUser } from './lib/auth.js'
import './style.css'

createApp(App).use(router).mount('#app')

// 用 token 换回最新角色，避免管理员调整角色后前端仍显示旧权限
syncUser()
