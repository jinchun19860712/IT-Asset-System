<template>
  <div class="config-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>系统配置</span>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="界面布局" name="layout">
          <!-- 界面布局：侧边栏位置等全局显示设置 -->
          <el-form label-width="140px" style="max-width: 600px">
            <el-form-item label="侧边栏位置">
              <el-radio-group
                :model-value="sidebarPosition"
                @change="onPositionChange"
              >
                <el-radio-button label="left">固定在左侧</el-radio-button>
                <el-radio-button label="right">固定在右侧</el-radio-button>
              </el-radio-group>
              <div class="form-hint">
                设备/软件/网络拓扑视图的文件夹树（侧边栏）固定位置，不受浏览器窗口大小、显示器分辨率影响
              </div>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="设备状态" name="status">
          <StatusConfig />
        </el-tab-pane>
        <el-tab-pane label="SNMP OID" name="oid">
          <OidConfig />
        </el-tab-pane>
        <el-tab-pane label="LDAP同步" name="ldap">
          <LdapConfig />
        </el-tab-pane>
        <!-- 用户管理：仅管理员可见 -->
        <el-tab-pane v-if="isAdmin" label="用户管理" name="users">
          <UserManagement />
        </el-tab-pane>
        <!-- 审计日志：仅管理员可见 -->
        <el-tab-pane v-if="isAdmin" label="审计日志" name="audit">
          <AuditLogList />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, inject, provide, computed } from 'vue'
import { ElMessage } from 'element-plus'
import StatusConfig from '../components/StatusConfig.vue'
import OidConfig from '../components/OidConfig.vue'
import LdapConfig from '../components/LdapConfig.vue'
import UserManagement from '../components/UserManagement.vue'
import AuditLogList from './AuditLogList.vue'
import { useAuth } from '../store/auth.js'

const activeTab = ref('layout')

// 侧边栏位置由 Layout.vue 通过 provide 注入（持久化到 localStorage）
const sidebarPosition = inject('sidebarPosition')
const setSidebarPosition = inject('setSidebarPosition')
const onPositionChange = (val) => {
  if (val !== 'left' && val !== 'right') return
  setSidebarPosition(val)
  ElMessage.success(`侧边栏已固定到${val === 'left' ? '左侧' : '右侧'}，刷新或切换路由后生效`)
}

// 鉴权状态：给 UserManagement 子组件提供 isAdmin
// - 模板里直接用 isAdmin（ref 自动 unwrap）
// - 子组件 inject('isAdmin') 拿到的是 computed ref（响应式）
const { isAdmin: isAdminRef } = useAuth()
const isAdmin = computed(() => isAdminRef.value)
provide('isAdmin', isAdmin)
</script>

<style scoped>
.config-page {
  max-width: 1200px;
  margin: 0 auto;
}
.card-header {
  font-weight: bold;
  font-size: 16px;
}
.form-hint {
  font-size: 12px;
  color: var(--app-text-secondary, #909399);
  line-height: 1.5;
  margin-top: 6px;
}
</style>
