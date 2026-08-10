// 前端鉴权状态（简易全局 store）。
//
// 不放 Pinia（多一个依赖），直接 reactive 对象 + module 顶层单例。
//
// 用法：
//   import { useAuth } from '@/store/auth'   （如配了 alias）
//   或者：
//   import { useAuth } from '../store/auth.js'
//
//   const { currentUser, isAdmin, login, logout, refresh } = useAuth()
import { reactive, computed } from 'vue'
import { authApi, setUnauthenticatedHandler } from '../api/index.js'


const state = reactive({
  user: null,        // { id, username, display_name, role, is_active, ... } 或 null
  booted: false      // 启动期 refresh 是否完成
})

let _unauthCb = null

/**
 * 安装鉴权相关的"全局处理"：401 时跳 /login
 * 应在 router 创建后调用，把 handleUnauthenticated 绑到 router.push('/login')
 */
function installUnauthenticatedHandler(handler) {
  _unauthCb = handler
  setUnauthenticatedHandler(() => {
    state.user = null
    if (_unauthCb) _unauthCb()
  })
}

/**
 * 启动时尝试取一次 /auth/me，决定首屏渲染登录还是 Layout。
 * 同时把 401 拦截后的跳转目标装上。
 * @param onUnauthenticated 当会话失效时调用（例如 router.push('/login')）
 * @returns Promise<user|null>  - 已登录返回 user 对象，未登录返回 null
 */
async function bootAuth(onUnauthenticated) {
  installUnauthenticatedHandler(onUnauthenticated)
  try {
    const res = await authApi.me()
    if (res && res.code === 0 && res.data) {
      state.user = res.data
    } else {
      state.user = null
    }
  } catch (e) {
    state.user = null
  } finally {
    state.booted = true
  }
  return state.user
}

async function login(username, password) {
  const res = await authApi.login(username, password)
  if (res && res.code === 0 && res.data) {
    state.user = res.data
    return { ok: true, data: res.data }
  }
  return { ok: false, message: (res && res.message) || '登录失败' }
}

async function logout() {
  try { await authApi.logout() } catch (_) {}
  state.user = null
}

async function refresh() {
  try {
    const res = await authApi.me()
    if (res && res.code === 0 && res.data) {
      state.user = res.data
      return state.user
    }
  } catch (_) {}
  state.user = null
  return null
}

export function useAuth() {
  return {
    currentUser: computed(() => state.user),
    booted: computed(() => state.booted),
    isLoggedIn: computed(() => !!state.user),
    isAuthenticated: computed(() => !!state.user),  // 别名（与 isLoggedIn 等价）
    isAdmin: computed(() => state.user?.role === 'admin'),
    login,
    logout,
    refresh,
    bootAuth
  }
}

// 单独导出 bootAuth，方便 main.js 启动时调用（不需要 useAuth 包一层）
export { bootAuth }

export const _authState = state  // 仅供调试用
