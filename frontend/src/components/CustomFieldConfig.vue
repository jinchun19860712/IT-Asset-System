<template>
  <div class="config-section">
    <div class="toolbar">
      <el-button type="primary" size="small" @click="showAddDialog">
        <el-icon><Plus /></el-icon> 添加字段
      </el-button>
      <el-button size="small" @click="loadData">
        <el-icon><Refresh /></el-icon> 刷新
      </el-button>
    </div>

    <el-table :data="fieldList" stripe border>
      <el-table-column prop="name" label="字段名称" width="150" />
      <el-table-column prop="field_type" label="类型" width="100">
        <template #default="{ row }">
          <el-tag size="small" effect="dark" :type="typeTagType(row.field_type)">
            {{ typeMap[row.field_type] || row.field_type }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_required" label="必填" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_required ? 'danger' : 'info'" size="small">
            {{ row.is_required ? '是' : '否' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="options" label="选项" min-width="200" show-overflow-tooltip />
      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <el-button type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
          <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑字段' : '添加字段'" width="450px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="如：购买日期" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.field_type" style="width: 100%">
            <el-option label="文本" value="text" />
            <el-option label="数字" value="number" />
            <el-option label="日期" value="date" />
            <el-option label="下拉选择" value="select" />
            <el-option label="开关" value="boolean" />
          </el-select>
        </el-form-item>
        <el-form-item label="必填">
          <el-switch v-model="form.is_required" />
        </el-form-item>
        <el-form-item label="选项" v-if="form.field_type === 'select'">
          <el-input v-model="form.options" type="textarea" :rows="2" placeholder="逗号分隔，如：选项1,选项2,选项3" />
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
import { customFieldApi } from '../api/index.js'

const fieldList = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const form = ref({ name: '', field_type: 'text', is_required: false, options: '', sort_order: 0 })

const typeMap = {
  text: '文本',
  number: '数字',
  date: '日期',
  select: '下拉',
  boolean: '开关'
}

// 字段类型标签配色：不同类型用不同深色，互相区分不混淆，强对比辨识
const typeTagType = (t) => {
  const map = {
    text: '',           // 蓝（默认）
    number: 'success',  // 绿
    date: 'warning',    // 橙
    select: 'info',     // 灰
    boolean: 'info'
  }
  return map[t] ?? ''
}

const loadData = async () => {
  const res = await customFieldApi.getList()
  if (res.code === 0) fieldList.value = res.data
}

const showAddDialog = () => {
  isEdit.value = false
  editId.value = null
  form.value = { name: '', field_type: 'text', is_required: false, options: '', sort_order: (fieldList.value?.length || 0) + 1 }
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  editId.value = row.id
  form.value = { name: row.name, field_type: row.field_type, is_required: row.is_required, options: row.options, sort_order: row.sort_order }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!form.value.name.trim()) {
    ElMessage.warning('请输入字段名称')
    return
  }
  try {
    if (isEdit.value) {
      await customFieldApi.update(editId.value, form.value)
    } else {
      await customFieldApi.create(form.value)
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
    await ElMessageBox.confirm(`确定删除字段 "${row.name}" 吗？`, '提示', { type: 'warning' })
    await customFieldApi.delete(row.id)
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
