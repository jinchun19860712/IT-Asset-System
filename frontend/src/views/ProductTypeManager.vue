<template>
  <div class="pt-manager">
    <div class="page-header">
      <h2>产品类型管理</h2>
      <el-button type="primary" @click="openCreate"><el-icon><Plus /></el-icon> 新建产品类型</el-button>
    </div>
    <el-card>
      <el-table :data="list" stripe v-loading="loading">
        <el-table-column prop="name" label="名称" width="160" />
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column label="资产类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.asset_type === 'asset' ? 'success' : 'warning'" size="small">
              {{ row.asset_type === 'asset' ? '资产' : '组件' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="资产分类" width="110">
          <template #default="{ row }">
            <el-tag
              size="small"
              effect="dark"
              :type="assetCategoryTagType(row.asset_type, row.asset_category)"
            >
              {{ assetCategoryLabel(row.asset_type, row.asset_category) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="关联字段数" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.field_links?.length" size="small" effect="dark" type="success">
              {{ row.field_links.length }} 个
            </el-tag>
            <el-tag v-else size="small" effect="dark" type="warning">
              未配置
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="启用" width="70">
          <template #default="{ row }">{{ row.is_active ? '是' : '否' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-tooltip :content="`配置「${row.name}」的专属字段（关联后，在添加设备页选择此类型会自动显示这些字段）`" placement="top">
              <el-button size="small" type="primary" @click="openLayout(row)">
                <el-icon><Connection /></el-icon> 字段布局
              </el-button>
            </el-tooltip>
            <el-popconfirm title="确定删除？" @confirm="handleDelete(row.id)">
              <template #reference><el-button size="small" type="danger">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑产品类型' : '新建产品类型'" width="540px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="如：打印机、服务器、交换机" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="产品类型描述" />
        </el-form-item>
        <el-form-item label="资产类型" prop="asset_type">
          <el-radio-group v-model="form.asset_type">
            <el-radio value="asset">资产</el-radio>
            <el-radio value="component">组件</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="资产分类" prop="asset_category">
          <el-select v-model="form.asset_category" style="width:200px">
            <template v-if="form.asset_type === 'asset'">
              <el-option label="IT资产" value="it" />
              <el-option label="非IT资产" value="non_it" />
            </template>
            <template v-else>
              <el-option label="IT组件" value="it" />
              <el-option label="非IT组件" value="non_it" />
            </template>
          </el-select>
        </el-form-item>
        <el-form-item label="设备类型">
          <el-select
            v-model="form.device_type"
            placeholder="关联基础数据中的设备类型（可选）"
            filterable
            clearable
            allow-create
            default-first-option
            style="width:300px"
          >
            <el-option v-for="t in deviceTypeOptions" :key="t" :label="t" :value="t" />
          </el-select>
          <div class="form-hint">
            关联后，在添加设备选择此产品类型时，「"设备类型"」字段会自动填入此值；输入新值会写入「"基础数据 → 设备类型"」字典
          </div>
        </el-form-item>
        <el-form-item label="排序" prop="sort_order">
          <el-input-number v-model="form.sort_order" :min="0" />
        </el-form-item>
        <el-form-item label="图标" prop="icon">
          <el-input v-model="form.icon" placeholder="可选，Element Plus 图标名" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 字段布局抽屉 -->
    <el-drawer v-model="layoutDrawer" title="字段布局" size="780px">
      <template v-if="layoutPt">
        <!-- 顶部说明卡 -->
        <el-card shadow="never" class="layout-info-card">
          <div class="layout-info-head">
            <el-icon size="20"><Connection /></el-icon>
            <strong>{{ layoutPt.name }}</strong>
            <el-tag size="small" :type="assetCategoryTagType(layoutPt.asset_type, layoutPt.asset_category)" effect="dark">
              {{ assetTypeLabel(layoutPt.asset_type) }} · {{ assetCategoryLabel(layoutPt.asset_type, layoutPt.asset_category) }}
            </el-tag>
          </div>
          <div class="layout-info-desc">
            将自定义字段关联到本类型，关联后，在「添加设备」页选择此类型会自动显示这些专属字段。
          </div>
        </el-card>

        <el-alert
          v-if="allFields.length === 0"
          type="info"
          :closable="false"
          show-icon
          class="layout-alert"
        >
          系统中暂无自定义字段，请先到「自定义字段」页面创建字段后再来关联。
        </el-alert>

        <template v-else>
          <!-- 顶部操作栏：标题 + 快捷按钮 -->
          <div class="layout-toolbar">
            <span class="layout-stat">
              已选 <strong>{{ layoutSelected.length }}</strong> / 共 {{ allFields.length }} 个字段
            </span>
            <div class="layout-toolbar-actions">
              <el-button size="small" @click="selectAllFields">全选</el-button>
              <el-button size="small" @click="clearAllFields">清空</el-button>
            </div>
          </div>

          <!-- 左右穿梭框（带类型 tag 的字段项） -->
          <el-transfer
            v-model="layoutSelected"
            :data="allFields"
            :titles="['可用字段', '已选字段']"
            :props="{ key: 'id', label: 'desc' }"
            filterable
            :left-default-checked="[]"
            :right-default-checked="[]"
            :render-content="renderTransferItem"
            style="width:100%"
          />

          <div class="layout-footer">
            <el-button @click="layoutDrawer = false">取消</el-button>
            <el-button type="primary" :icon="Check" @click="saveLayout">保存布局</el-button>
          </div>
        </template>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Connection, Check } from '@element-plus/icons-vue'
import { productTypeApi, customFieldApi, dictApi } from '../api'

const list = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const editingId = ref(null)
const saving = ref(false)
const formRef = ref(null)

const form = ref({
  name: '', description: '', asset_type: 'asset', asset_category: 'it',
  device_type: '', icon: '', sort_order: 0, is_active: true
})
const rules = { name: [{ required: true, message: '请输入名称' }] }

// 设备类型字典（基础数据 → 设备类型）
const deviceTypeOptions = ref([])
const loadDeviceTypeOptions = async () => {
  try {
    const res = await dictApi.getByType('device_type')
    if (res.code === 0) {
      deviceTypeOptions.value = (res.data || [])
        .filter(x => x.enabled !== false)
        .map(x => x.name)
    }
  } catch (e) { /* ignore */ }
}

const loadList = async () => {
  loading.value = true
  try {
    const res = await productTypeApi.list()
    if (res.code === 0) list.value = res.data || []
  } finally { loading.value = false }
}

const openCreate = () => {
  editingId.value = null
  form.value = { name: '', description: '', asset_type: 'asset', asset_category: 'it', device_type: '', icon: '', sort_order: 0, is_active: true }
  dialogVisible.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  form.value = { ...row }
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!formRef.value) return
  await formRef.value.validate()
  saving.value = true
  try {
    // 如果 device_type 输入了新值（非空且不在字典里），自动写入「设备类型」字典
    const dt = (form.value.device_type || '').trim()
    if (dt && !deviceTypeOptions.value.includes(dt)) {
      try {
        await dictApi.create({ type: 'device_type', name: dt, sort_order: 0, enabled: true })
        deviceTypeOptions.value = [...deviceTypeOptions.value, dt]
      } catch (e) { /* ignore */ }
    }
    if (editingId.value) {
      await productTypeApi.update(editingId.value, form.value)
    } else {
      await productTypeApi.create(form.value)
    }
    ElMessage.success(editingId.value ? '更新成功' : '创建成功')
    dialogVisible.value = false
    loadList()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '操作失败') }
  finally { saving.value = false }
}

const handleDelete = async (id) => {
  try {
    await productTypeApi.delete(id)
    ElMessage.success('删除成功')
    loadList()
  } catch (e) { ElMessage.error('删除失败') }
}

const assetTypeLabel = (t) => ({ asset: '资产', component: '组件' }[t] || t)

const assetCategoryLabel = (assetType, cat) => {
  const map = {
    'asset,it': 'IT资产', 'asset,non_it': '非IT资产',
    'component,it': 'IT组件', 'component,non_it': '非IT组件'
  }
  return map[`${assetType},${cat}`] || cat
}

// 资产分类标签配色：4 种组合用 4 种深色，互不混淆，强对比辨识
const assetCategoryTagType = (assetType, cat) => {
  const key = `${assetType},${cat}`
  const map = {
    'asset,it': '',            // IT资产 → 默认 primary（蓝）
    'asset,non_it': 'warning', // 非IT资产 → 橙
    'component,it': 'success', // IT组件 → 绿
    'component,non_it': 'info' // 非IT组件 → 灰
  }
  return map[key] || ''
}

// ====== 字段布局 ======
const layoutDrawer = ref(false)
const layoutPt = ref(null)
const layoutSelected = ref([])
// allFields 元素结构：{ id, name, field_type, key, required, desc }
const allFields = ref([])

// 字段类型 → tag 颜色（深底配色，强对比）
const FIELD_TYPE_TAG_TYPE = {
  text: '',           // 蓝
  textarea: '',
  number: 'success',  // 绿
  decimal: 'success',
  percentage: 'success',
  date: 'warning',    // 橙
  datetime: 'warning',
  checkbox: 'info',   // 灰
  radio: 'info',
  select: '',
  multi_select: ''
}
const FIELD_TYPE_LABELS = {
  text: '文本', textarea: '多行', number: '数字', decimal: '小数',
  percentage: '百分比', date: '日期', datetime: '日期时间',
  checkbox: '布尔', radio: '单选', select: '下拉', multi_select: '多选'
}

const openLayout = async (pt) => {
  layoutPt.value = pt
  layoutSelected.value = (pt.field_links || []).map(l => l.field_id)
  try {
    const res = await customFieldApi.list()
    if (res.code === 0) {
      allFields.value = (res.data || []).map(f => ({
        id: f.id,
        name: f.name,
        field_type: f.field_type,
        key: f.field_key,
        required: f.is_required,
        // 兼容 el-transfer 默认渲染
        desc: `${f.name}`
      }))
    }
  } catch (e) { /* ignore */ }
  layoutDrawer.value = true
}

const selectAllFields = () => { layoutSelected.value = allFields.value.map(f => f.id) }
const clearAllFields = () => { layoutSelected.value = [] }

// 自定义 el-transfer 每行渲染：字段名 + 类型 tag + 必填标记
const renderTransferItem = (h, option) => {
  const tagType = FIELD_TYPE_TAG_TYPE[option.field_type] ?? ''
  const typeLabel = FIELD_TYPE_LABELS[option.field_type] || option.field_type
  return h('div', { class: 'transfer-item' }, [
    h('span', { class: 'transfer-item-name' }, option.name),
    h('span', { class: 'transfer-item-tags' }, [
      option.required ? h('span', { class: 'transfer-required' }, '必填') : null,
      h('el-tag', {
        size: 'small', effect: 'dark', type: tagType, round: true,
        style: 'margin-left:6px'
      }, () => typeLabel),
      option.key ? h('span', { class: 'transfer-key' }, option.key) : null
    ])
  ])
}

const saveLayout = async () => {
  try {
    await productTypeApi.linkFields(layoutPt.value.id, layoutSelected.value)
    ElMessage.success('布局保存成功')
    layoutDrawer.value = false
    loadList()
  } catch (e) { ElMessage.error('保存布局失败') }
}

onMounted(() => { loadList(); loadDeviceTypeOptions() })
</script>

<style scoped>
.pt-manager { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; font-size: 18px; }
.layout-hint { color: var(--app-text-secondary, #909399); font-size: 14px; margin-bottom: 12px; line-height: 1.6; }
.layout-alert { margin-bottom: 12px; }

.layout-info-card { margin-bottom: 16px; }
.layout-info-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 15px;
}
.layout-info-head strong { color: var(--app-text, #303133); }
.layout-info-desc {
  font-size: 13px;
  color: var(--app-text-secondary, #909399);
  line-height: 1.6;
}

.layout-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  margin-bottom: 4px;
}
.layout-toolbar-actions { display: flex; gap: 4px; }
.layout-stat { font-size: 13px; color: var(--app-text-secondary, #909399); }
.layout-stat strong { color: var(--app-accent, #409eff); font-size: 16px; margin: 0 4px; }

/* el-transfer 自定义项：字段名 + 类型 tag */
.transfer-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 2px 0;
}
.transfer-item-name {
  flex: 1;
  color: var(--app-text, #303133);
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.transfer-item-tags {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}
.transfer-required {
  font-size: 11px;
  color: #fff;
  background: var(--el-color-danger, #f56c6c);
  padding: 1px 5px;
  border-radius: 3px;
}
.transfer-key {
  font-size: 11px;
  color: var(--app-text-secondary, #909399);
  font-family: monospace;
  background: var(--app-bg-soft, #fafafa);
  padding: 1px 5px;
  border-radius: 3px;
  margin-left: 4px;
}

/* el-transfer 在抽屉里的样式微调 */
:deep(.el-transfer) { display: flex; align-items: stretch; gap: 12px; }
:deep(.el-transfer-panel) { flex: 1; min-width: 0; }
:deep(.el-transfer-panel__list) { min-height: 360px; }
:deep(.el-transfer__buttons) { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; }
:deep(.el-transfer__buttons .el-button) { padding: 6px 8px; }

.layout-footer {
  margin-top: 24px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}
</style>
