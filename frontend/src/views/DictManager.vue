<template>
  <div class="dict-manager">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>基础数据维护</span>
          <span class="header-tip">这里维护的选项会出现在「添加设备 / 添加软件」的下拉框里</span>
        </div>
      </template>

      <el-tabs v-model="activeType" @tab-change="loadList">
        <el-tab-pane
          v-for="t in dictTypes"
          :key="t.type"
          :label="t.label"
          :name="t.type"
        />
      </el-tabs>

      <div class="toolbar">
        <el-input
          v-if="activeType !== 'supplier'"
          v-model="newName"
          :placeholder="`新增${currentLabel}，回车即可添加`"
          style="width: 260px"
          clearable
          @keyup.enter="handleAdd"
        >
          <template #prefix><el-icon><Plus /></el-icon></template>
        </el-input>
        <el-button type="primary" @click="handleAdd">添加</el-button>
        <el-input
          v-model="filterText"
          placeholder="搜索"
          clearable
          style="width: 200px; margin-left: auto"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button @click="loadList">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>

      <el-alert
        v-if="activeType === 'supplier'"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 12px"
        title="供应商为设备与软件共用，两边下拉框读取的是同一份数据"
      />

      <el-table :data="filteredList" v-loading="loading" border stripe size="default">
        <el-table-column type="index" label="#" width="60" align="center" />
        <el-table-column prop="name" :label="currentLabel" min-width="200">
          <template #default="{ row }">
            <el-input
              v-if="editingId === row.id"
              v-model="editingName"
              size="small"
              @keyup.enter="confirmEdit(row)"
            />
            <span v-else>{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" label="排序" width="120" align="center">
          <template #default="{ row }">
            <el-input-number
              v-if="editingId === row.id"
              v-model="editingSort"
              size="small"
              :min="0"
              controls-position="right"
              style="width: 96px"
            />
            <span v-else>{{ row.sort_order }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="activeType === 'supplier'" prop="contact_person" label="姓名" min-width="110">
          <template #default="{ row }">
            <el-input v-if="editingId === row.id" v-model="editingContact" size="small" placeholder="联系人" />
            <span v-else>{{ row.contact_person || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="activeType === 'supplier'" prop="contact_phone" label="联系方式" min-width="140">
          <template #default="{ row }">
            <el-input v-if="editingId === row.id" v-model="editingPhone" size="small" placeholder="电话/微信" />
            <span v-else>{{ row.contact_phone || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="activeType === 'supplier'" prop="company_name" label="公司名称" min-width="160">
          <template #default="{ row }">
            <el-input v-if="editingId === row.id" v-model="editingCompany" size="small" placeholder="公司名称" />
            <span v-else>{{ row.company_name || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="activeType === 'supplier'" prop="company_address" label="公司地址" min-width="200">
          <template #default="{ row }">
            <el-input v-if="editingId === row.id" v-model="editingAddress" size="small" placeholder="公司地址" />
            <span v-else>{{ row.company_address || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="启用" width="100" align="center">
          <template #default="{ row }">
            <el-switch
              :model-value="row.enabled"
              @change="(v) => toggleEnabled(row, v)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" align="center" fixed="right">
          <template #default="{ row }">
            <template v-if="editingId === row.id">
              <el-button link type="primary" size="small" @click="confirmEdit(row)">保存</el-button>
              <el-button link type="info" size="small" @click="cancelEdit">取消</el-button>
            </template>
            <template v-else>
              <el-button link type="primary" size="small" @click="startEdit(row)">编辑</el-button>
              <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>

      <el-empty
        v-if="!loading && !list.length"
        :description="activeType === 'supplier' ? `还没有${currentLabel}，点击添加按钮录入` : `还没有${currentLabel}，在上方输入框添加一个`"
        :image-size="80"
      />

      <!-- 供应商：带联系信息的对话框 -->
      <el-dialog v-model="supplierDialog" :title="supplierDialogMode === 'add' ? '添加供应商' : '编辑供应商'" width="480px">
        <el-form label-width="110px">
          <el-form-item label="供应商名称" required>
            <el-input v-model="supplierForm.name" placeholder="如：合肥联翔科技" />
          </el-form-item>
          <el-form-item label="姓名">
            <el-input v-model="supplierForm.contact_person" placeholder="联系人姓名" />
          </el-form-item>
          <el-form-item label="联系方式">
            <el-input v-model="supplierForm.contact_phone" placeholder="电话 / 微信 / 邮箱" />
          </el-form-item>
          <el-form-item label="公司名称">
            <el-input v-model="supplierForm.company_name" placeholder="公司全称" />
          </el-form-item>
          <el-form-item label="公司地址">
            <el-input v-model="supplierForm.company_address" placeholder="公司地址" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="supplierDialog = false">取消</el-button>
          <el-button type="primary" @click="confirmSupplierDialog">确定</el-button>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { dictApi } from '../api/index.js'

const FALLBACK_TYPES = [
  // product_type 已迁移到「产品类型」独立管理
  { type: 'device_type', label: '设备类型' },
  { type: 'brand', label: '品牌' },
  { type: 'supplier', label: '供应商' },
  { type: 'software_category', label: '软件分类' }
]

const dictTypes = ref(FALLBACK_TYPES)
const activeType = ref('brand')
const list = ref([])
const loading = ref(false)
const newName = ref('')
const filterText = ref('')

const editingId = ref(null)
const editingName = ref('')
const editingSort = ref(0)
// 供应商联系信息（编辑态临时副本；实际编辑走对话框）
const editingContact = ref('')
const editingPhone = ref('')
const editingCompany = ref('')
const editingAddress = ref('')
// 供应商对话框
const supplierDialog = ref(false)
const supplierDialogMode = ref('add')
const editingSupplierId = ref(null)
const supplierForm = ref({ name: '', contact_person: '', contact_phone: '', company_name: '', company_address: '' })

const currentLabel = computed(
  () => dictTypes.value.find(t => t.type === activeType.value)?.label || '选项'
)

const filteredList = computed(() => {
  const kw = filterText.value.trim()
  if (!kw) return list.value
  return list.value.filter(x => (x.name || '').includes(kw))
})

const loadTypes = async () => {
  try {
    const res = await dictApi.getTypes()
    if (res.code === 0 && res.data?.length) dictTypes.value = res.data
  } catch (e) {
    // 后端没返回就用本地兜底列表
    console.error('加载字典分类失败', e)
  }
}

const loadList = async () => {
  loading.value = true
  cancelEdit()
  try {
    const res = await dictApi.getByType(activeType.value)
    list.value = res.code === 0 ? (res.data || []) : []
  } catch (e) {
    ElMessage.error('加载失败')
    list.value = []
  } finally {
    loading.value = false
  }
}

const handleAdd = async () => {
  // 供应商：直接弹出带联系信息的对话框，顶部不再保留内联输入框
  if (activeType.value === 'supplier') {
    openSupplierDialog('add')
    return
  }
  const name = newName.value.trim()
  if (!name) {
    ElMessage.warning(`请输入${currentLabel.value}名称`)
    return
  }
  if (list.value.some(x => x.name === name)) {
    ElMessage.warning('该项已存在')
    return
  }
  try {
    await dictApi.create({
      type: activeType.value,
      name,
      sort_order: list.value.length,
      enabled: true
    })
    ElMessage.success('添加成功')
    newName.value = ''
    await loadList()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '添加失败')
  }
}

const openSupplierDialog = (mode, row) => {
  supplierDialogMode.value = mode
  if (mode === 'edit' && row) {
    editingSupplierId.value = row.id
    supplierForm.value = {
      name: row.name,
      contact_person: row.contact_person || '',
      contact_phone: row.contact_phone || '',
      company_name: row.company_name || '',
      company_address: row.company_address || ''
    }
  } else {
    editingSupplierId.value = null
    supplierForm.value = { name: '', contact_person: '', contact_phone: '', company_name: '', company_address: '' }
  }
  supplierDialog.value = true
}

const confirmSupplierDialog = async () => {
  const name = supplierForm.value.name.trim()
  if (!name) {
    ElMessage.warning('请输入供应商名称')
    return
  }
  const payload = {
    type: 'supplier',
    name,
    contact_person: supplierForm.value.contact_person,
    contact_phone: supplierForm.value.contact_phone,
    company_name: supplierForm.value.company_name,
    company_address: supplierForm.value.company_address,
    sort_order: list.value.length,
    enabled: true
  }
  try {
    if (supplierDialogMode.value === 'edit' && editingSupplierId.value) {
      await dictApi.update(editingSupplierId.value, {
        name,
        contact_person: payload.contact_person,
        contact_phone: payload.contact_phone,
        company_name: payload.company_name,
        company_address: payload.company_address
      })
      ElMessage.success('已保存')
    } else {
      if (list.value.some(x => x.name === name)) {
        ElMessage.warning('该供应商已存在')
        return
      }
      await dictApi.create(payload)
      ElMessage.success('添加成功')
    }
    supplierDialog.value = false
    newName.value = ''
    await loadList()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

const startEdit = (row) => {
  // 供应商通过对话框编辑联系信息；其余类型走行内编辑
  if (activeType.value === 'supplier') {
    openSupplierDialog('edit', row)
    return
  }
  editingId.value = row.id
  editingName.value = row.name
  editingSort.value = row.sort_order ?? 0
}

const cancelEdit = () => {
  editingId.value = null
  editingName.value = ''
  editingSort.value = 0
}

const confirmEdit = async (row) => {
  const name = editingName.value.trim()
  if (!name) {
    ElMessage.warning('名称不能为空')
    return
  }
  try {
    await dictApi.update(row.id, { name, sort_order: editingSort.value })
    ElMessage.success('已保存')
    cancelEdit()
    await loadList()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  }
}

const toggleEnabled = async (row, val) => {
  try {
    await dictApi.update(row.id, { enabled: val })
    row.enabled = val
    ElMessage.success(val ? '已启用' : '已停用')
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定删除「${row.name}」吗？已经用了这个值的设备/软件不会被改动。`,
      '提示',
      { type: 'warning' }
    )
    await dictApi.delete(row.id)
    ElMessage.success('删除成功')
    await loadList()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

onMounted(async () => {
  await loadTypes()
  await loadList()
})
</script>

<style scoped>
.dict-manager { max-width: 1000px; margin: 0 auto; }
.card-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  font-weight: bold;
  font-size: 16px;
}
.header-tip { font-weight: normal; font-size: 12px; color: #909399; }
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}
</style>
