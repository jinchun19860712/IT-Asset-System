<template>
  <div class="config-section">
    <el-alert
      title="LDAP/AD同步配置"
      description="配置LDAP服务器参数后，点击'测试连接'验证连通性，再点击'保存配置'保存。同步功能将在后续版本实现。"
      type="info"
      show-icon
      :closable="false"
      style="margin-bottom: 15px"
    />

    <el-form :model="form" label-width="120px" style="max-width: 600px;">
      <el-form-item label="服务器地址">
        <el-input v-model="form.server" placeholder="ldap://192.168.1.100" />
      </el-form-item>
      <el-form-item label="端口">
        <el-input-number v-model="form.port" :min="1" :max="65535" />
      </el-form-item>
      <el-form-item label="使用SSL">
        <el-switch v-model="form.use_ssl" />
      </el-form-item>
      <el-form-item label="Base DN">
        <el-input v-model="form.base_dn" placeholder="dc=company,dc=com" />
      </el-form-item>
      <el-form-item label="管理员DN">
        <el-input v-model="form.admin_dn" placeholder="cn=admin,dc=company,dc=com" />
      </el-form-item>
      <el-form-item label="管理员密码">
        <el-input v-model="form.admin_password" type="password" show-password />
      </el-form-item>
      <el-form-item label="用户过滤条件">
        <el-input v-model="form.user_filter" placeholder="(objectClass=person)" />
      </el-form-item>
      <el-form-item label="OU过滤条件">
        <el-input v-model="form.ou_filter" placeholder="(objectClass=organizationalUnit)" />
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="testConnection">
          <el-icon><Connection /></el-icon> 测试连接
        </el-button>
        <el-button type="success" @click="saveConfig">
          <el-icon><Check /></el-icon> 保存配置
        </el-button>
      </el-form-item>
    </el-form>

    <el-result v-if="testResult" :icon="testResult.icon" :title="testResult.title" :sub-title="testResult.message" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { configApi } from '../api/index.js'

const form = ref({
  server: 'ldap://192.168.1.100',
  port: 389,
  use_ssl: false,
  base_dn: 'dc=company,dc=com',
  admin_dn: 'cn=admin,dc=company,dc=com',
  admin_password: '',
  user_filter: '(objectClass=person)',
  ou_filter: '(objectClass=organizationalUnit)',
  sync_enabled: false,
  sync_interval: '0 2 * * *'
})

const testResult = ref(null)

const loadConfig = async () => {
  const res = await configApi.getLdap()
  if (res.code === 0 && res.data) {
    form.value = { ...form.value, ...res.data }
  }
}

const testConnection = async () => {
  testResult.value = null
  try {
    const res = await configApi.testLdap(form.value)
    if (res.code === 0) {
      testResult.value = { icon: 'success', title: '连接成功', message: res.message }
      ElMessage.success(res.message)
    } else {
      testResult.value = { icon: 'error', title: '连接失败', message: res.message }
      ElMessage.error(res.message)
    }
  } catch (e) {
    testResult.value = { icon: 'error', title: '请求异常', message: e.message }
    ElMessage.error('测试失败')
  }
}

const saveConfig = async () => {
  try {
    await configApi.updateLdap(form.value)
    ElMessage.success('配置已保存')
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

onMounted(loadConfig)
</script>

<style scoped>
.config-section {
  padding: 10px;
}
</style>
