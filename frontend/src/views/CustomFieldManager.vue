<template>
  <div class="cf-manager">
    <div class="page-header">
      <h2>自定义字段管理</h2>
      <el-button type="primary" @click="openCreate"><el-icon><Plus /></el-icon> 新建字段</el-button>
    </div>
    <el-card>
      <el-table :data="list" stripe v-loading="loading">
        <el-table-column prop="name" label="名称" width="140" />
        <el-table-column prop="field_key" label="Key" width="140" show-overflow-tooltip />
        <el-table-column label="类型" width="120">
          <template #default="{ row }">
            <el-tag size="small" effect="dark" :type="typeTagType(row.field_type)">
              {{ typeLabel(row.field_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="可选项" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="['select','radio','checkbox','multi_select'].includes(row.field_type) && row.options?.length">
              {{ row.options.map(o => o.label || o.value).join('、') }}
            </span>
            <span v-else class="na">—</span>
          </template>
        </el-table-column>
        <el-table-column label="必填" width="70">
          <template #default="{ row }">{{ row.is_required ? '是' : '否' }}</template>
        </el-table-column>
        <el-table-column label="启用" width="70">
          <template #default="{ row }">{{ row.is_active ? '是' : '否' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-popconfirm title="确定删除？关联布局和设备值将一并清除" @confirm="handleDelete(row.id)">
              <template #reference><el-button size="small" type="danger">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑字段' : '新建字段'" width="620px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="字段显示名，如：打印速度" />
        </el-form-item>
        <el-form-item label="字段 Key" prop="field_key">
          <el-input v-model="form.field_key" placeholder="机器名，留空自动生成" :disabled="!!editingId" />
        </el-form-item>
        <el-form-item label="字段类型" prop="field_type">
          <el-select v-model="form.field_type" @change="onTypeChange">
            <el-option label="单行文本" value="text" />
            <el-option label="多行文本" value="textarea" />
            <el-option label="数字" value="number" />
            <el-option label="小数" value="decimal" />
            <el-option label="百分比" value="percentage" />
            <el-option label="日期" value="date" />
            <el-option label="日期时间" value="datetime" />
            <el-option label="复选框" value="checkbox" />
            <el-option label="单选按钮" value="radio" />
            <el-option label="下拉列表" value="select" />
            <el-option label="多选列表" value="multi_select" />
          </el-select>
        </el-form-item>

        <!-- 可选项（仅 select/radio/checkbox/multi_select 需要） -->
        <el-form-item v-if="needsOptions" label="可选项">
          <div v-for="(opt, idx) in form.options" :key="idx" class="opt-row">
            <el-input v-model="opt.label" placeholder="选项标签" style="width:180px" />
            <el-input v-model="opt.value" placeholder="选项值" style="width:180px;margin-left:8px" />
            <el-button type="danger" :icon="Delete" circle size="small" @click="removeOption(idx)" />
          </div>
          <el-button size="small" @click="addOption" style="margin-top:6px">+ 添加选项</el-button>
        </el-form-item>

        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
        <el-form-item label="配置项">
          <div class="cfg-grid">
            <label class="cfg-item"><input type="checkbox" v-model="form.is_required"> 必填</label>
            <el-input v-model="form.config.placeholder" placeholder="占位提示文字" style="width:180px;margin-left:12px" />
          </div>
          <div class="cfg-grid" v-if="['number','decimal','percentage'].includes(form.field_type)" style="margin-top:8px">
            <span style="font-size:13px;color:#909399">最小值</span>
            <el-input-number v-model="form.config.min" size="small" style="width:100px;margin-left:4px" />
            <span style="font-size:13px;color:#909399;margin-left:12px">最大值</span>
            <el-input-number v-model="form.config.max" size="small" style="width:100px;margin-left:4px" />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import { customFieldApi } from '../api'

const FIELD_TYPES = {
  text: '单行文本', textarea: '多行文本', number: '数字', decimal: '小数',
  percentage: '百分比', date: '日期', datetime: '日期时间',
  checkbox: '复选框', radio: '单选按钮', select: '下拉列表', multi_select: '多选列表'
}
const typeLabel = (t) => FIELD_TYPES[t] || t

// 字段类型标签配色：不同类型用不同深色，互相区分不混淆，强对比辨识
const TYPE_TAG_TYPES = {
  text: '',            // 蓝（默认）
  textarea: '',
  number: 'success',   // 绿
  decimal: 'success',
  percentage: 'success',
  date: 'warning',     // 橙
  datetime: 'warning',
  checkbox: 'info',    // 灰
  radio: 'info',
  select: '',
  multi_select: ''
}
const typeTagType = (t) => TYPE_TAG_TYPES[t] ?? ''

const list = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const editingId = ref(null)
const saving = ref(false)
const formRef = ref(null)

const defaultForm = () => ({
  name: '', field_key: '', field_type: 'text', is_required: false,
  options: [], config: {}, is_active: true, sort_order: 0
})
const form = ref(defaultForm())

const needsOptions = computed(() => ['select','radio','checkbox','multi_select'].includes(form.value.field_type))
const rules = { name: [{ required: true, message: '请输入名称' }] }

const onTypeChange = () => {
  if (needsOptions.value && !form.value.options.length) {
    form.value.options = [{ label: '', value: '' }]
  }
  if (!needsOptions.value) form.value.options = []
}

const addOption = () => form.value.options.push({ label: '', value: '' })
const removeOption = (idx) => form.value.options.splice(idx, 1)

const loadList = async () => {
  loading.value = true
  try {
    const res = await customFieldApi.list()
    if (res.code === 0) list.value = res.data || []
  } finally { loading.value = false }
}

const openCreate = () => {
  editingId.value = null
  form.value = defaultForm()
  dialogVisible.value = true
}

const openEdit = async (row) => {
  editingId.value = row.id
  // deep copy to avoid reference issues
  const res = await customFieldApi.get(row.id)
  const data = res
  form.value = {
    name: data.name || '', field_key: data.field_key || '',
    field_type: data.field_type || 'text', is_required: data.is_required || false,
    options: JSON.parse(JSON.stringify(data.options || [])),
    config: JSON.parse(JSON.stringify(data.config || {})),
    is_active: data.is_active !== false, sort_order: data.sort_order || 0
  }
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!formRef.value) return
  await formRef.value.validate()
  saving.value = true
  try {
    const payload = {
      ...form.value,
      options: needsOptions.value ? form.value.options.filter(o => o.label || o.value) : []
    }
    if (editingId.value) {
      await customFieldApi.update(editingId.value, payload)
    } else {
      await customFieldApi.create(payload)
    }
    ElMessage.success(editingId.value ? '更新成功' : '创建成功')
    dialogVisible.value = false
    loadList()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '操作失败') }
  finally { saving.value = false }
}

const handleDelete = async (id) => {
  try {
    await customFieldApi.delete(id)
    ElMessage.success('删除成功')
    loadList()
  } catch (e) { ElMessage.error('删除失败') }
}

onMounted(loadList)
</script>

<style scoped>
.cf-manager { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; font-size: 18px; }
.na { color: #c0c4cc; }
.opt-row { display: flex; align-items: center; margin-bottom: 6px; }
.cfg-grid { display: flex; align-items: center; }
.cfg-item { display: flex; align-items: center; font-size: 13px; gap: 4px; }
</style>
