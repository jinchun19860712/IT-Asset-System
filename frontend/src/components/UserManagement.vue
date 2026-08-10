<script setup>
/**
 * 用户管理组件（仅管理员可见/可操作）。
 *
 * 功能：
 *  - 列表：账号 / 显示名 / 角色 / 状态 / 最后登录 / 创建时间
 *  - 新建：账号、显示名、初始密码、角色
 *  - 编辑：改显示名、改角色、启停用
 *  - 重置密码：管理员重置某用户的密码
 *  - 删除：删除用户（默认 admin 不能删 / 自己是 admin 且是最后一名 admin 时不能删）
 *
 * 通过 inject('isAdmin') 判断权限；非 admin 时只读浏览。
 */
import { ref, inject, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { authApi } from '../api/index.js'

const isAdmin = inject('isAdmin', ref(false))

const loading = ref(false)
const list = ref([])
const keyword = ref('')

const dialogVisible = ref(false)
const dialogMode = ref('create')  // create / edit
const dialogFormRef = ref()
const submitting = ref(false)

const form = ref({
  id: null,
  username: '',
  display_name: '',
  password: '',
  role: 'user',
  is_active: true
})

const pwdDialogVisible = ref(false)
const pwdTarget = ref(null)
const pwdForm = ref({ new: '', confirm: '' })
const pwdSubmitting = ref(false)

const rules = {
  username: [{ required: true, message: '账号不能为空', trigger: 'blur' }],
  password: [{ required: true, message: '密码至少 6 个字符', trigger: 'blur' }]
}

async function fetchList() {
  loading.value = true
  try {
    const res = await authApi.listUsers(keyword.value || undefined)
    if (res.code === 0) {
      list.value = res.data || []
    } else {
      ElMessage.error(res.message || '加载用户列表失败')
    }
  } catch (e) {
    ElMessage.error('请求失败：' + (e?.message || '网络异常'))
  } finally {
    loading.value = false
  }
}

function openCreate() {
  dialogMode.value = 'create'
  form.value = {
    id: null,
    username: '',
    display_name: '',
    password: '',
    role: 'user',
    is_active: true
  }
  dialogVisible.value = true
}

function openEdit(row) {
  dialogMode.value = 'edit'
  form.value = {
    id: row.id,
    username: row.username,
    display_name: row.display_name,
    password: '',
    role: row.role,
    is_active: !!row.is_active
  }
  dialogVisible.value = true
}

async function submitDialog() {
  if (submitting.value) return
  // 校验表单（仅 create 模式有 rules）
  if (dialogMode.value === 'create' && dialogFormRef.value?.validate) {
    let valid = true
    try {
      await dialogFormRef.value.validate()
    } catch (_) {
      valid = false
    }
    if (!valid) return
  }
  submitting.value = true
  try {
    let res
    if (dialogMode.value === 'create') {
      res = await authApi.createUser({
        username: form.value.username.trim(),
        display_name: (form.value.display_name || '').trim(),
        password: form.value.password,
        role: form.value.role
      })
    } else {
      res = await authApi.updateUser(form.value.id, {
        display_name: (form.value.display_name || '').trim(),
        role: form.value.role,
        is_active: form.value.is_active
      })
    }
    if (res.code === 0) {
      ElMessage.success(dialogMode.value === 'create' ? '创建成功' : '更新成功')
      dialogVisible.value = false
      fetchList()
    } else {
      ElMessage.error(res.message || '操作失败')
    }
  } catch (e) {
    ElMessage.error('请求失败：' + (e?.message || '网络异常'))
  } finally {
    submitting.value = false
  }
}

async function toggleActive(row) {
  try {
    const res = await authApi.updateUser(row.id, { is_active: !row.is_active })
    if (res.code === 0) {
      ElMessage.success(row.is_active ? '已停用' : '已启用')
      fetchList()
    } else {
      ElMessage.error(res.message || '操作失败')
    }
  } catch (e) {
    ElMessage.error('请求失败：' + (e?.message || '网络异常'))
  }
}

async function deleteRow(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除账号「${row.username}」吗？该操作不可撤销。`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch (_) { return }
  try {
    const res = await authApi.deleteUser(row.id)
    if (res.code === 0) {
      ElMessage.success('已删除')
      fetchList()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (e) {
    ElMessage.error('请求失败：' + (e?.message || '网络异常'))
  }
}

function openResetPassword(row) {
  pwdTarget.value = row
  pwdForm.value = { new: '', confirm: '' }
  pwdDialogVisible.value = true
}

async function submitResetPassword() {
  if (pwdSubmitting.value) return
  const np = pwdForm.value.new
  const cp = pwdForm.value.confirm
  if (!np || np.length < 6) return ElMessage.warning('新密码至少 6 个字符')
  if (np !== cp) return ElMessage.warning('两次密码不一致')
  pwdSubmitting.value = true
  try {
    const res = await authApi.resetPassword(pwdTarget.value.id, np)
    if (res.code === 0) {
      ElMessage.success(`已重置「${pwdTarget.value.username}」的密码`)
      pwdDialogVisible.value = false
    } else {
      ElMessage.error(res.message || '重置失败')
    }
  } catch (e) {
    ElMessage.error('请求失败：' + (e?.message || '网络异常'))
  } finally {
    pwdSubmitting.value = false
  }
}

function formatTime(s) {
  return s || '—'
}

onMounted(fetchList)
</script>

<template>
  <div class="user-management">
    <div class="um-toolbar">
      <el-input
        v-model="keyword"
        placeholder="按账号 / 显示名搜索"
        clearable
        style="width: 240px"
        @keyup.enter="fetchList"
        @clear="fetchList"
      />
      <el-button type="primary" :icon="Plus" @click="openCreate" :disabled="!isAdmin">新建用户</el-button>
      <el-button @click="fetchList">刷新</el-button>
    </div>

    <el-table :data="list" v-loading="loading" border stripe style="width: 100%">
      <el-table-column prop="username" label="账号" min-width="120" />
      <el-table-column prop="display_name" label="显示名" min-width="120">
        <template #default="{ row }">{{ row.display_name || '—' }}</template>
      </el-table-column>
      <el-table-column prop="role" label="角色" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.role === 'admin'" size="small" type="warning" effect="dark">管理员</el-tag>
          <el-tag v-else size="small" type="info" effect="dark">普通用户</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'" effect="dark" size="small">
            {{ row.is_active ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="last_login_at" label="最后登录" min-width="160">
        <template #default="{ row }">{{ formatTime(row.last_login_at) }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" min-width="160">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column v-if="isAdmin" label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-button link type="primary" size="small" @click="openResetPassword(row)">重置密码</el-button>
          <el-button link :type="row.is_active ? 'warning' : 'success'" size="small" @click="toggleActive(row)">
            {{ row.is_active ? '停用' : '启用' }}
          </el-button>
          <el-button link type="danger" size="small" @click="deleteRow(row)">删除</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无用户" />
      </template>
    </el-table>

    <!-- 新建 / 编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新建用户' : '编辑用户'"
      width="480px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="dialogFormRef"
        :model="form"
        :rules="dialogMode === 'create' ? rules : {}"
        label-width="90px"
      >
        <el-form-item label="账号" prop="username">
          <el-input v-model="form.username" :disabled="dialogMode === 'edit'" placeholder="登录账号（不可重复）" />
        </el-form-item>
        <el-form-item label="显示名">
          <el-input v-model="form.display_name" placeholder="可选" />
        </el-form-item>
        <el-form-item v-if="dialogMode === 'create'" label="初始密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="至少 6 个字符" />
        </el-form-item>
        <el-form-item label="角色">
          <el-radio-group v-model="form.role">
            <el-radio-button label="user">普通用户</el-radio-button>
            <el-radio-button label="admin">管理员</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="dialogMode === 'edit'" label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitDialog">保存</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码弹窗 -->
    <el-dialog v-model="pwdDialogVisible" title="重置密码" width="440px" :close-on-click-modal="false">
      <div v-if="pwdTarget" class="reset-target">
        目标账号：<strong>{{ pwdTarget.username }}</strong>
      </div>
      <el-form label-width="90px">
        <el-form-item label="新密码">
          <el-input v-model="pwdForm.new" type="password" show-password placeholder="至少 6 个字符" />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="pwdForm.confirm" type="password" show-password placeholder="再输入一次" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="pwdSubmitting" @click="submitResetPassword">重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.user-management {
  max-width: 1100px;
}
.um-toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 14px;
}
.reset-target {
  padding: 10px 14px;
  margin-bottom: 14px;
  background: var(--app-bg-soft, #fafbfc);
  border: 1px solid var(--app-border, #ebeef5);
  border-radius: 4px;
  font-size: 13px;
  color: var(--app-text-secondary, #606266);
}
</style>
