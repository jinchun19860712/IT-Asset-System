<script setup>
import { ref, reactive, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuth } from '../store/auth.js'

const route = useRoute()
const { login } = useAuth()

const form = reactive({
  username: 'admin',
  password: ''
})
const loading = ref(false)
const errorMsg = ref('')

// 登录成功后跳转：query.redirect 优先，否则去 /dashboard
const redirectTarget = computed(() => {
  const r = route.query.redirect
  if (typeof r === 'string' && r.startsWith('/')) return r
  return '/dashboard'
})

function goAfterLogin() {
  // ★ 用 window.location.replace，不用 router.replace（绕开 vue-router 4 时序 bug）
  window.location.replace(redirectTarget.value)
}

async function handleSubmit(e) {
  // 关键：原生 form submit 会触发，必须 preventDefault！
  if (e && e.preventDefault) e.preventDefault()
  if (loading.value) return
  const u = (form.username || '').trim()
  const p = form.password || ''
  if (!u || !p) {
    errorMsg.value = '请输入账号和密码'
    return
  }
  loading.value = true
  errorMsg.value = ''
  console.log('[Login] submit:', { username: u, passwordLen: p.length })
  try {
    const res = await login(u, p)
    console.log('[Login] login() result:', res)
    if (res.ok) {
      console.log('[Login] success, window.location.replace →', redirectTarget.value)
      // ★ state.user 已由 login() 完成；window.location.replace 会整页 reload
      goAfterLogin()
    } else {
      errorMsg.value = res.message || '登录失败'
      console.warn('[Login] failed:', res.message)
      loading.value = false
    }
  } catch (e) {
    console.error('[Login] exception:', e)
    errorMsg.value = '登录请求失败：' + (e?.message || '网络异常')
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="login-title">IT 资产管理系统</div>
      </div>

      <!-- ★ 关键：原生 <form> 而不是 <el-form> -->
      <!-- @submit.prevent 拦截原生 submit -->
      <form
        class="login-form"
        @submit.prevent="handleSubmit"
        autocomplete="on"
      >
        <div class="field">
          <label for="login-username">账号</label>
          <input
            id="login-username"
            v-model="form.username"
            type="text"
            placeholder="请输入账号"
            class="el-input el-input--large native-input"
            autocomplete="username"
            :disabled="loading"
          />
        </div>

        <div class="field">
          <label for="login-password">密码</label>
          <input
            id="login-password"
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            class="el-input el-input--large native-input"
            autocomplete="current-password"
            :disabled="loading"
          />
        </div>

        <div v-if="errorMsg" class="login-error">
          <span class="el-icon"><svg viewBox="0 0 1024 1024" width="14" height="14"><path fill="currentColor" d="M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm0 820c-205.4 0-372-166.6-372-372s166.6-372 372-372 372 166.6 372 372-166.6 372-372 372z"/><path fill="currentColor" d="M464 688a48 48 0 1096 0 48 48 0 10-96 0zm48-286c-30.9 0-56 25.1-56 56v192c0 30.9 25.1 56 56 56s56-25.1 56-56V458c0-30.9-25.1-56-56-56z"/></svg></span>
          <span>{{ errorMsg }}</span>
        </div>

        <button
          type="submit"
          class="login-btn"
          :disabled="loading"
          @click="handleSubmit"
        >
          <span v-if="!loading">登 录</span>
          <span v-else>登录中…</span>
        </button>
      </form>

      <div class="login-footer">
        <div class="hint">默认管理员：admin / admin123（首次登录后请尽快修改）</div>
        <div class="copyright">© 2026 黄山健康职业学院 金纯. 基于 MIT 许可证开源。</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(ellipse at top, var(--app-accent-soft, #eaf2ff), transparent 60%),
    var(--app-bg, #f5f7fa);
  padding: 16px;
}

.login-card {
  width: 100%;
  max-width: 420px;
  background: var(--app-panel, #fff);
  border-radius: 16px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.08);
  padding: 36px 32px 24px;
}

.login-header { text-align: center; margin-bottom: 32px; }
.login-title { font-size: 22px; font-weight: 600; color: var(--app-text, #2c3e50); margin-bottom: 6px; }
.login-subtitle { font-size: 13px; color: var(--app-text-secondary, #909399); }

.login-form { display: block; }

.login-form .field { margin-bottom: 18px; }

.login-form .field label {
  display: block;
  font-size: 13px;
  color: var(--app-text-secondary, #606266);
  margin-bottom: 6px;
}

/* 原生 input 但用 el-input 样式 */
.login-form .native-input {
  width: 100%;
  padding: 11px 13px;
  font-size: 14px;
  line-height: 1.4;
  color: var(--app-text, #2c3e50);
  background: #fff;
  border: 1px solid var(--app-border, #dcdfe6);
  border-radius: 4px;
  box-sizing: border-box;
  outline: none;
  transition: border-color 0.2s;
}

.login-form .native-input:focus {
  border-color: var(--el-color-primary, #409eff);
}

.login-form .native-input:disabled {
  background: #f5f7fa;
  color: #c0c4cc;
  cursor: not-allowed;
}

.login-error {
  margin: -4px 0 14px;
  padding: 9px 12px;
  background: var(--app-danger-bg, #fef0f0);
  color: var(--el-color-danger, #f56c6c);
  font-size: 13px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.login-btn {
  width: 100%;
  margin-top: 4px;
  padding: 12px 20px;
  font-size: 16px;
  font-weight: 500;
  color: #fff;
  background: var(--el-color-primary, #409eff);
  border: 0;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.login-btn:hover:not(:disabled) {
  background: var(--el-color-primary-light-3, #66b1ff);
}

.login-btn:disabled {
  background: var(--el-color-primary-light-5, #c0d8ff);
  cursor: not-allowed;
}

.login-footer {
  margin-top: 28px;
  padding-top: 18px;
  border-top: 1px dashed var(--app-border, #ebeef5);
  text-align: center;
}

.login-footer .hint { font-size: 12px; color: var(--app-text-secondary, #909399); }

.login-footer .copyright { margin-top: 8px; font-size: 12px; color: var(--app-text-secondary, #909399); }

.el-icon { display: inline-flex; }
</style>
