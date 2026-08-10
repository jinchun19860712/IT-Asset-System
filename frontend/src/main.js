// frontend/src/main.js  v7.0 — 终极修复
// 关键：app.use(router) 立即激活 initial navigation，
//       必须在 use(router) 之前完成 bootAuth，否则 initial nav 看到 state.user=null，跳 /login
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import './theme.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import { loadTheme, applyTheme } from './theme.js'

applyTheme(loadTheme())

const app = createApp(App)
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}
app.use(ElementPlus)

// 关键：动态 import 把 await 拉到顶层，**保证 bootAuth 在 use(router) 之前完成**
const [{ default: router }, { bootAuth, _authState }] = await Promise.all([
  import('./router/index.js'),
  import('./store/auth.js')
])

console.log('[main v7] before bootAuth, state.user=', _authState.user && _authState.user.username)
await bootAuth()
console.log('[main v7] bootAuth done, state.user=', _authState.user && _authState.user.username, ', booted=', _authState.booted)

app.use(router)
app.mount('#app')
