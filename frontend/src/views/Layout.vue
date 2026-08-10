<template>
  <el-container class="layout-container">
    <!-- 顶部导航 -->
    <el-header class="header">
      <div class="logo">
        <el-icon size="24"><Monitor /></el-icon>
        <span>IT资产管理系统</span>
      </div>

      <!-- 顶部菜单：完全用 div+@click 实现，绕开 el-menu 全部怪异行为
           每个 menuItem 用原生 button 渲染，加 .active 类表示当前路由 -->
      <nav class="nav-menu">
        <button
          v-for="m in menuItems"
          :key="m.id"
          type="button"
          class="nav-btn"
          :class="{ active: activeMenuId === m.id }"
          @click="goTo(m)"
        >
          <el-icon><component :is="m.icon" /></el-icon>
          <span>{{ m.label }}</span>
        </button>
      </nav>

      <!-- 主题切换 + 当前用户 -->
      <div class="header-right">
        <!-- 告警铃铛（N1） -->
        <el-popover
          v-model:visible="alertsPopVisible"
          placement="bottom-end"
          :width="380"
          trigger="click"
          popper-class="alerts-popover"
        >
          <template #reference>
            <el-badge
              :value="alertCount.total"
              :max="99"
              :hidden="alertCount.total === 0"
              :is-dot="false"
              class="alert-bell-wrap"
            >
              <el-button
                link
                class="alert-bell-btn"
                :title="alertCount.critical ? `严重告警 ${alertCount.critical} 条` : '告警中心'"
                @click.stop
              >
                <el-icon :size="20"><Bell /></el-icon>
              </el-button>
            </el-badge>
          </template>

          <div class="alerts-popover-body">
            <div class="alerts-header">
              <span>告警中心</span>
              <span class="alerts-meta">
                <el-tag v-if="alertCount.critical" type="danger" effect="dark" size="small">
                  严重 {{ alertCount.critical }}
                </el-tag>
                <el-tag v-if="alertCount.warning" type="warning" effect="dark" size="small">
                  警告 {{ alertCount.warning }}
                </el-tag>
              </span>
            </div>
            <div v-if="!activeAlerts.length" class="alerts-empty">暂无未确认告警</div>
            <ul v-else class="alerts-list">
              <li v-for="a in activeAlerts" :key="a.id" class="alert-item"
                  :class="['level-' + a.level]"
                  @click="goAlerts">
                <div class="alert-row1">
                  <el-tag size="small" :type="a.level === 'critical' ? 'danger' : 'warning'" effect="dark">
                    {{ a.level === 'critical' ? '严重' : '警告' }}
                  </el-tag>
                  <span class="alert-device">{{ a.device_name }}</span>
                  <span class="alert-time">{{ (a.created_at || '').slice(11, 16) }}</span>
                </div>
                <div class="alert-msg">{{ a.message }}</div>
              </li>
            </ul>
            <div class="alerts-footer">
              <el-button link type="primary" size="small" @click="goAlerts">查看全部 →</el-button>
            </div>
          </div>
        </el-popover>

        <ThemePicker />

        <!-- 当前用户下拉菜单：改密 / 登出 -->
        <el-dropdown v-if="currentUser" trigger="click" class="user-menu" @command="handleUserCommand">
          <span class="user-trigger">
            <el-avatar :size="26" class="user-avatar">
              {{ avatarText }}
            </el-avatar>
            <span class="user-name">{{ currentUser.display_name || currentUser.username }}</span>
            <el-icon class="user-caret"><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled>
                <span class="user-dd-meta">
                  <strong>{{ currentUser.username }}</strong>
                  <el-tag v-if="currentUser.role === 'admin'" size="small" type="warning" effect="dark">管理员</el-tag>
                  <el-tag v-else size="small" type="info" effect="dark">普通用户</el-tag>
                </span>
              </el-dropdown-item>
              <el-dropdown-item command="change-password" :icon="Key">修改密码</el-dropdown-item>
              <el-dropdown-item command="logout" :icon="SwitchButton" divided>登出</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <!-- 修改密码弹窗 -->
      <el-dialog v-model="pwdDialogVisible" title="修改密码" width="440px" :close-on-click-modal="false">
        <el-form :model="pwdForm" label-width="90px" @submit.prevent>
          <el-form-item label="原密码">
            <el-input v-model="pwdForm.old" type="password" show-password placeholder="请输入当前密码" />
          </el-form-item>
          <el-form-item label="新密码">
            <el-input v-model="pwdForm.new" type="password" show-password placeholder="至少 6 个字符" />
          </el-form-item>
          <el-form-item label="确认密码">
            <el-input v-model="pwdForm.confirm" type="password" show-password placeholder="再输入一次新密码" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="pwdDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="pwdSaving" @click="submitChangePassword">保存</el-button>
        </template>
      </el-dialog>
    </el-header>

    <!-- 主体内容
         外层 class 控制侧边栏位置：'sidebar-left' / 'sidebar-right'（系统配置中可切换） -->
    <el-container
      class="main-container"
      :class="`sidebar-${sidebarPosition}`"
    >
      <!-- 侧边栏：设备/拓扑显示文件夹树，软件管理显示软件面板 -->
      <el-aside v-if="showSidebar" width="280px" class="sidebar">
        <!-- 软件管理：专用软件面板（按软件分类过滤） -->
        <SoftwareTreePanel
          v-if="route.name === 'SoftwareList'"
          ref="softwareTreeRef"
          :active-category="selectedSoftwareCategory"
          @select-category="handleSelectSoftwareCategory"
        />
        <!-- 设备/拓扑：通用文件夹树（组织机构 + 设备资产） -->
        <FolderTreePanel
          v-else
          ref="folderTreeRef"
          :mode="sidebarMode"
          :active-folder-id="selectedFolder?.id || null"
          @select-folder="handleSelectFolder"
        />
      </el-aside>

      <!-- 右侧内容区：直接 <component :is> 渲染 + 强制 key 递增
           forceKey 在 route 变化时 +1，无论什么情况都强制重新挂载新组件 -->
      <el-main class="main-content">
        <component
          :is="currentComponent"
          :key="forceKey"
          v-if="currentComponent"
        />
        <div v-else class="empty-state">路由未匹配：{{ route.name }} ({{ route.path }})</div>
        <!-- 错误兜底：单个组件渲染失败时显示错误信息，不污染后续路由切换 -->
        <div v-if="renderError" class="render-error">
          <el-icon size="32"><WarningFilled /></el-icon>
          <div class="render-error-title">页面渲染失败</div>
          <div class="render-error-msg">{{ renderError }}</div>
          <el-button type="primary" size="small" @click="reloadPage">重新加载</el-button>
        </div>
      </el-main>
    </el-container>

    <!-- 页脚版权声明 -->
    <footer class="app-footer">
      © 2026 黄山健康职业学院 金纯. 基于 MIT 许可证开源。
    </footer>
  </el-container>
</template>

<script setup>
import { ref, computed, watch, provide, markRaw, nextTick, onErrorCaptured, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { WarningFilled, Key, ArrowDown, SwitchButton, Bell } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  Monitor, Odometer, OfficeBuilding, Box, Grid, Files, Share, Setting,
  Coin, Collection, Document, PriceTag
} from '@element-plus/icons-vue'
import FolderTreePanel from '../components/FolderTreePanel.vue'
import SoftwareTreePanel from '../components/SoftwareTreePanel.vue'
import ThemePicker from '../components/ThemePicker.vue'
import { useAuth } from '../store/auth.js'
import { authApi, alertApi } from '../api/index.js'

// 显式导入所有路由组件
import Dashboard from './Dashboard.vue'
import DeviceList from './DeviceList.vue'
import DeviceForm from './DeviceForm.vue'
import SoftwareList from './SoftwareList.vue'
import SoftwareForm from './SoftwareForm.vue'
import RackView from './RackView.vue'
import TopologyView from './TopologyView.vue'
import DictManager from './DictManager.vue'
import ContractList from './ContractList.vue'
import ProductTypeManager from './ProductTypeManager.vue'
import CustomFieldManager from './CustomFieldManager.vue'
import ConfigPage from './ConfigPage.vue'
import AlertList from './AlertList.vue'

const route = useRoute()
const router = useRouter()
const folderTreeRef = ref()
const softwareTreeRef = ref()
const selectedFolder = ref(null)
const selectedSoftwareCategory = ref(null)

// 强制递增 key：route 变化时 +1，强制 <component :is> 重新挂载
const forceKey = ref(0)

// 组件渲染错误兜底：捕获子组件 setup/render 抛错，避免污染路由切换
const renderError = ref('')
const reloadPage = () => {
  renderError.value = ''
  forceKey.value++ // 强制重新挂载
}
onErrorCaptured((err) => {
  console.error('[Layout] 子组件渲染错误:', err)
  renderError.value = (err && err.message) || String(err)
  // 返回 false 让错误不再向上传播
  return false
})

// ========== 侧边栏位置（系统配置可切换，localStorage 持久化） ==========
// 解决「浏览器缩放时侧栏跑到右边」问题：固定由 CSS class 决定位置，与窗口大小无关
const SIDEBAR_POSITION_KEY = 'itam-sidebar-position'
const savedPosition = (() => {
  try { return localStorage.getItem(SIDEBAR_POSITION_KEY) } catch { return null }
})()
const sidebarPosition = ref(savedPosition === 'right' ? 'right' : 'left')
const setSidebarPosition = (pos) => {
  if (pos !== 'left' && pos !== 'right') return
  sidebarPosition.value = pos
  try { localStorage.setItem(SIDEBAR_POSITION_KEY, pos) } catch {}
}

// ========== 顶部菜单（纯 div + @click，零 el-menu） ==========
const menuItems = [
  { id: 'dashboard',     icon: Odometer,       label: '仪表盘',     path: '/dashboard' },
  { id: 'org-tree',      icon: OfficeBuilding, label: '组织架构',   path: '/devices',    query: { tree: 'org' } },
  { id: 'asset-panel',   icon: Box,            label: '资产面板',   path: '/devices',    query: { tree: 'asset' } },
  { id: 'softwares',     icon: Coin,           label: '软件管理',   path: '/softwares' },
  { id: 'racks',         icon: Grid,           label: '机柜视图',   path: '/racks' },
  { id: 'topology',      icon: Share,          label: '网络拓扑',   path: '/topology' },
  { id: 'dict',          icon: Collection,     label: '基础数据',   path: '/dict' },
  { id: 'product-types', icon: PriceTag,       label: '产品类型',   path: '/product-types' },
  { id: 'custom-fields', icon: Files,          label: '自定义字段',   path: '/custom-fields' },
  { id: 'contracts',     icon: Document,       label: '合同附件',   path: '/contracts' },
  { id: 'alerts',        icon: Bell,           label: '告警中心',   path: '/alerts' },
  { id: 'config',        icon: Setting,        label: '系统配置',   path: '/config' }
]

// 组件映射：route.name → 对应的组件实例
const COMPONENT_MAP = {
  Dashboard: markRaw(Dashboard),
  DeviceList: markRaw(DeviceList),
  DeviceAdd: markRaw(DeviceForm),
  DeviceEdit: markRaw(DeviceForm),
  SoftwareList: markRaw(SoftwareList),
  SoftwareAdd: markRaw(SoftwareForm),
  SoftwareEdit: markRaw(SoftwareForm),
  RackView: markRaw(RackView),
  TopologyView: markRaw(TopologyView),
  DictManager: markRaw(DictManager),
  ContractList: markRaw(ContractList),
  ProductTypeManager: markRaw(ProductTypeManager),
  CustomFieldManager: markRaw(CustomFieldManager),
  Config: markRaw(ConfigPage),
  AlertList: markRaw(AlertList)
}

const currentComponent = computed(() => {
  const c = COMPONENT_MAP[route.name] || null

  return c
})

// 菜单激活态
const activeMenuId = computed(() => {
  const cur = menuItems.find(m =>
    m.path === route.path &&
    JSON.stringify(m.query || {}) === JSON.stringify(route.query || {})
  )
  if (cur) return cur.id
  const byPath = menuItems.find(m => m.path === route.path)
  return byPath ? byPath.id : route.path
})

const goTo = (m) => {
  if (!m) return

  if (route.path === m.path && JSON.stringify(route.query || {}) === JSON.stringify(m.query || {})) {

    return
  }
  router.push({ path: m.path, query: m.query || {} })
    
    .catch(err => {
      if (err?.name !== 'NavigationDuplicated') {
        console.error('[Layout] 路由跳转失败:', err)
      } else {

      }
    })
}

// ========== 关键：watch route 变化，强制 forceKey + 1 ==========
// 不依赖任何 <component :is> 的内部行为，key 一变 Vue 必须重新挂载
watch(
  () => [route.name, route.fullPath],
  ([newName, newPath], [oldName, oldPath]) => {
    if (newName === oldName && newPath === oldPath) return

    forceKey.value++
    renderError.value = '' // 路由切换时清空 renderError，给新组件一次干净机会
    console.log('[Layout] route changed', { from: oldName, to: newName, forceKey: forceKey.value })

    // nextTick 后再次确认 key 生效（双保险）
    nextTick(() => {

    })
  },
  { flush: 'post' }
)

// ========== 侧边栏（文件夹树）显隐与模式 ==========
const SIDEBAR_ROUTES = ['DeviceList', 'SoftwareList', 'TopologyView']
const showSidebar = computed(() => SIDEBAR_ROUTES.includes(route.name))

const sidebarMode = ref('both')
watch(
  () => [route.name, route.query.tree],
  ([name, tree]) => {
    if (name === 'DeviceList') {
      const m = tree === 'org' || tree === 'asset' ? tree : 'both'
      if (m !== sidebarMode.value) {
        selectedFolder.value = null
        selectedSoftwareCategory.value = null
        folderTreeRef.value?.clearSelection()
        softwareTreeRef.value?.clearSelection()
      }
      sidebarMode.value = m
    } else if (name === 'SoftwareList') {
      // 切换到软件管理时，清空文件夹树选中（仅清理文件夹树，软件分类由 SoftwareList 自身管理）
      selectedFolder.value = null
      folderTreeRef.value?.clearSelection()
    } else {
      // 离开设备/软件/拓扑视图时，清空所有选中
      selectedFolder.value = null
      selectedSoftwareCategory.value = null
      folderTreeRef.value?.clearSelection()
      softwareTreeRef.value?.clearSelection()
    }
  },
  { immediate: true }
)

// 给子组件共享 selectedFolder（provide/inject）
provide('selectedFolder', selectedFolder)
provide('clearFolder', () => {
  selectedFolder.value = null
  selectedSoftwareCategory.value = null
  folderTreeRef.value?.clearSelection()
  softwareTreeRef.value?.clearSelection()
})
// 给软件列表共享软件分类选中
provide('selectedSoftwareCategory', selectedSoftwareCategory)
provide('clearSoftwareCategory', () => {
  selectedSoftwareCategory.value = null
  softwareTreeRef.value?.clearSelection()
})
// 给系统配置页共享侧边栏位置切换函数
provide('sidebarPosition', sidebarPosition)
provide('setSidebarPosition', setSidebarPosition)

const handleSelectFolder = (folder) => {
  selectedFolder.value = folder
}

const handleSelectSoftwareCategory = (category) => {
  selectedSoftwareCategory.value = category
}

// ========== 当前用户 + 登出 + 改密 ==========
const { currentUser, logout: doLogout } = useAuth()

// ========== 告警中心（N1） ==========
// 顶部铃铛：每 30s 拉一次 active-count + active 列表；下拉直接显示最近 10 条
const alertsPopVisible = ref(false)
const alertCount = ref({ total: 0, warning: 0, critical: 0, ok: 0 })
const activeAlerts = ref([])
let alertsTimer = null
let prevTotal = 0

async function refreshAlerts(showOnChange = false) {
  try {
    const [r1, r2] = await Promise.all([
      alertApi.activeCount(),
      alertApi.active(10)
    ])
    if (r1.code === 0 && r1.data) alertCount.value = r1.data
    if (r2.code === 0 && Array.isArray(r2.data)) activeAlerts.value = r2.data
    // 新告警浮窗提醒：总数增加且当前用户在点击别处（不强制打断）
    if (showOnChange && r1.code === 0 && r1.data?.total > prevTotal && prevTotal > 0) {
      // 用 el-notification 弹最后一条新告警
      const newest = activeAlerts.value[0]
      if (newest) {
        const { ElNotification } = await import('element-plus')
        ElNotification({
          title: newest.level === 'critical' ? '⚠ 严重告警' : '⚡ 警告',
          message: newest.message,
          type: newest.level === 'critical' ? 'error' : 'warning',
          duration: 6000,
          offset: 50
        })
      }
    }
    prevTotal = r1.code === 0 && r1.data ? r1.data.total : prevTotal
  } catch (e) {
    // 静默失败，轮询稍后继续
  }
}

function goAlerts() {
  alertsPopVisible.value = false
  router.push({ name: 'AlertList' })
}

onMounted(() => {
  refreshAlerts(false)
  alertsTimer = setInterval(() => refreshAlerts(true), 30000)
})
onUnmounted(() => {
  if (alertsTimer) clearInterval(alertsTimer)
})

const avatarText = computed(() => {
  const u = currentUser.value
  if (!u) return ''
  const s = u.display_name || u.username || ''
  return s ? s.charAt(0).toUpperCase() : 'U'
})

const pwdDialogVisible = ref(false)
const pwdSaving = ref(false)
const pwdForm = ref({ old: '', new: '', confirm: '' })

function openChangePassword() {
  pwdForm.value = { old: '', new: '', confirm: '' }
  pwdDialogVisible.value = true
}

async function submitChangePassword() {
  const { old, new: np, confirm } = pwdForm.value
  if (!old || !np) return ElMessage.warning('请填写原密码和新密码')
  if (np.length < 6) return ElMessage.warning('新密码至少 6 个字符')
  if (np !== confirm) return ElMessage.warning('两次新密码不一致')
  pwdSaving.value = true
  try {
    const res = await authApi.changePassword(old, np)
    if (res.code === 0) {
      ElMessage.success('密码已修改，请用新密码重新登录')
      pwdDialogVisible.value = false
      // 改密后强制登出，重登录
      await doLogout()
      router.replace({ name: 'Login' })
    } else {
      ElMessage.error(res.message || '修改失败')
    }
  } catch (e) {
    ElMessage.error('修改请求失败：' + (e?.message || '网络异常'))
  } finally {
    pwdSaving.value = false
  }
}

async function doLogoutAndRedirect() {
  await doLogout()
  router.replace({ name: 'Login' })
}

async function handleUserCommand(cmd) {
  if (cmd === 'change-password') {
    openChangePassword()
  } else if (cmd === 'logout') {
    try {
      await ElMessageBoxConfirmSafe('确定要登出当前账号吗？')
    } catch (_) {
      return // 取消
    }
    await doLogoutAndRedirect()
  }
}

// ElMessageBox.confirm 的薄包装，避免在模板里使用 element-plus 全局组件栈
async function ElMessageBoxConfirmSafe(message) {
  const { ElMessageBox } = await import('element-plus')
  return ElMessageBox.confirm(message, '确认', {
    confirmButtonText: '登出',
    cancelButtonText: '取消',
    type: 'warning'
  })
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  background-color: var(--app-header-bg, #001529);
  color: var(--app-menu-text, #fff);
  display: flex;
  align-items: center;
  padding: 0 20px;
  height: 60px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: bold;
  margin-right: 24px;
  white-space: nowrap;
}

.nav-menu {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 4px;
  height: 100%;
  /* 窄窗口下横向滚动而不是文字竖排 */
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: thin;
  /* IE/Edge */
  -ms-overflow-style: none;
}
.nav-menu::-webkit-scrollbar { height: 4px; }
.nav-menu::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.18);
  border-radius: 2px;
}

.nav-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 44px;
  padding: 0 14px;
  background: transparent;
  border: none;
  color: var(--app-menu-text, #fff);
  font-size: 14px;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.15s, color 0.15s;
  outline: none;
  font-family: inherit;
  /* 关键：禁止文字换行 + 文字竖排（窄窗口时整体滚动而不是挤压文字） */
  white-space: nowrap;
  flex-shrink: 0;
}

.nav-btn:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.nav-btn.active {
  background-color: var(--app-accent, #409eff);
  color: #fff;
  font-weight: 500;
}

.empty-state {
  padding: 40px;
  text-align: center;
  color: var(--app-text-secondary, #909399);
  font-size: 14px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: 16px;
}

/* 告警铃铛（N1） */
.alert-bell-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 8px;
  border-radius: 6px;
  color: var(--app-menu-text, #fff);
  transition: background 0.15s;
}
.alert-bell-wrap:hover {
  background: rgba(255, 255, 255, 0.1);
}
.alert-bell-btn {
  color: inherit !important;
  font-size: 20px;
}

.alerts-popover-body { padding: 4px 2px 0; }
.alerts-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 8px 8px;
  border-bottom: 1px dashed var(--app-border, #ebeef5);
  font-weight: 600;
  font-size: 14px;
  color: var(--app-text, #303133);
}
.alerts-meta { display: inline-flex; gap: 6px; }
.alerts-empty {
  padding: 30px 0;
  text-align: center;
  color: var(--app-text-secondary, #909399);
  font-size: 13px;
}
.alerts-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 360px;
  overflow-y: auto;
}
.alert-item {
  padding: 10px 8px;
  border-bottom: 1px solid var(--app-border, #f5f7fa);
  cursor: pointer;
  transition: background 0.15s;
}
.alert-item:hover { background: var(--app-bg-soft, #f7faff); }
.alert-item:last-child { border-bottom: none; }
.alert-row1 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  margin-bottom: 4px;
}
.alert-device { font-weight: 600; color: var(--app-text, #303133); }
.alert-time { margin-left: auto; font-size: 12px; color: var(--app-text-secondary, #909399); }
.alert-msg {
  font-size: 12px;
  color: var(--app-text-secondary, #606266);
  line-height: 1.5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.alert-item.level-critical .alert-msg { color: var(--el-color-danger, #f56c6c); }
.alerts-footer {
  padding: 8px 8px 4px;
  border-top: 1px dashed var(--app-border, #ebeef5);
  text-align: right;
}

/* 用户下拉菜单触发器 */
.user-menu {
  cursor: pointer;
}
.user-trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 6px;
  color: var(--app-menu-text, #fff);
  transition: background 0.15s;
}
.user-trigger:hover {
  background: rgba(255, 255, 255, 0.1);
}
.user-name {
  font-size: 14px;
  white-space: nowrap;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.user-caret {
  font-size: 12px;
}
.user-avatar {
  background: var(--app-accent, #409eff);
  color: #fff;
  font-weight: 600;
  font-size: 13px;
}
.user-dd-meta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--app-text, #303133);
}

.main-container {
  flex: 1;
  overflow: hidden;
}

.app-footer {
  flex-shrink: 0;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: var(--app-text-secondary, #909399);
  background-color: var(--app-panel, #fff);
  border-top: 1px solid var(--app-border, #e4e7ed);
}

.sidebar {
  background-color: var(--app-panel, #fff);
  border-right: 1px solid var(--app-border, #e4e7ed);
  overflow-y: auto;
}

.main-content {
  padding: 20px;
  overflow-y: auto;
  background-color: var(--app-bg, #f5f7fa);
}

.render-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
  color: var(--app-text-secondary, #909399);
  gap: 12px;
}
.render-error-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--app-text, #303133);
}
.render-error-msg {
  font-size: 13px;
  font-family: monospace;
  max-width: 600px;
  word-break: break-all;
  background: var(--app-bg-soft, #fafafa);
  padding: 10px 14px;
  border-radius: 4px;
  border: 1px solid var(--app-border, #e4e7ed);
}

/* ========== 侧边栏位置控制 ========== */
/* 主容器在 el-aside 后面（row 方向）排布：
   - sidebar-left：默认（aside 在左、main 在右）
   - sidebar-right：aside 移到右边（用 row-reverse 把 aside 推到最后） */
.main-container.sidebar-right {
  flex-direction: row-reverse;
}
.main-container.sidebar-right .sidebar {
  border-right: none;
  border-left: 1px solid var(--app-border, #e4e7ed);
}
</style>
