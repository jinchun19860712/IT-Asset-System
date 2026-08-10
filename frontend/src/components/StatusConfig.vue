<template>
  <div class="config-section">
    <div class="toolbar">
      <el-button type="primary" size="small" @click="showAddDialog">
        <el-icon><Plus /></el-icon> 添加状态
      </el-button>
      <el-button size="small" @click="loadData">
        <el-icon><Refresh /></el-icon> 刷新
      </el-button>
    </div>

    <el-table :data="statusList" stripe border>
      <el-table-column prop="name" label="状态名称" width="150" />
      <el-table-column label="颜色" width="120">
        <template #default="{ row }">
          <el-color-picker v-model="row.color" size="small" show-alpha disabled />
          <span style="margin-left: 8px; font-size: 12px;">{{ row.color }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="sort_order" label="排序" width="80" />
      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <el-button type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
          <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑状态' : '添加状态'" width="400px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="颜色">
          <el-color-picker v-model="form.color" show-alpha />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { statusApi } from '../api/index.js'

const statusList = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const form = ref({ name: '', color: '#67C23A', sort_order: 0 })

const loadData = async () => {
  const res = await statusApi.getList()
  if (res.code === 0) statusList.value = res.data
}

const showAddDialog = () => {
  isEdit.value = false
  editId.value = null
  form.value = { name: '', color: '#67C23A', sort_order: (statusList.value?.length || 0) + 1 }
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  editId.value = row.id
  form.value = { name: row.name, color: row.color, sort_order: row.sort_order }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!form.value.name.trim()) {
    ElMessage.warning('请输入状态名称')
    return
  }
  try {
    if (isEdit.value) {
      await statusApi.update(editId.value, form.value)
    } else {
      await statusApi.create(form.value)
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    loadData()
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除状态 "${row.name}" 吗？`, '提示', { type: 'warning' })
    await statusApi.delete(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

onMounted(loadData)
</script>

<style scoped>
.config-section {
  padding: 10px;
}
.toolbar {
  margin-bottom: 15px;
}
</style>
