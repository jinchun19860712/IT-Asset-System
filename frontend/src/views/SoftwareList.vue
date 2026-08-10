<template>
  <div class="software-list">
    <el-card class="search-card">
      <div v-if="scopeFolder" class="scope-bar">
        <el-icon><Folder /></el-icon>
        <span class="scope-text">
          当前范围：<strong>{{ scopeFolder.full_path || scopeFolder.name }}</strong>
          <el-tag size="small" type="info" effect="plain" style="margin-left: 8px">含所有子文件夹</el-tag>
        </span>
        <el-button link type="primary" size="small" @click="clearFolder">查看全部软件</el-button>
      </div>
      <div v-else-if="selectedSoftwareCategory" class="scope-bar cat-bar">
        <el-icon><Coin /></el-icon>
        <span class="scope-text">
          当前分类：<strong>{{ selectedSoftwareCategory }}</strong>
        </span>
        <el-button link type="primary" size="small" @click="clearSoftwareCategory">查看全部分类</el-button>
      </div>
      <div v-else-if="selectedFolder" class="scope-bar asset-bar">
        <el-icon><InfoFilled /></el-icon>
        <span class="scope-text">
          软件按「组织机构」归属，当前选中的是资产分类
          <strong>{{ selectedFolder.name }}</strong>，已显示全部软件
        </span>
      </div>

      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="关键词">
          <el-input v-model="searchForm.keyword" placeholder="软件名称/版本/供应商" clearable
                    @keyup.enter="handleSearch" style="width: 220px" />
        </el-form-item>
        <el-form-item label="软件分类">
          <el-select v-model="searchForm.category" placeholder="全部分类" clearable style="width: 160px">
            <el-option v-for="c in categoryOptions" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon> 搜索
          </el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <div class="toolbar">
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon> 添加软件
        </el-button>
        <el-button @click="loadData">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
        <el-button @click="$router.push('/dict')">
          <el-icon><Collection /></el-icon> 维护软件分类
        </el-button>
      </div>
    </el-card>

    <el-card class="table-card">
      <transition name="el-fade-in-linear">
        <div v-if="selectedRows.length" class="bulk-bar">
          <div class="bulk-info">
            已选中 <b>{{ selectedRows.length }}</b> 条软件记录
            <el-button link type="primary" size="small" @click="clearSelection">取消选择</el-button>
          </div>
          <div class="bulk-actions">
            <el-button size="small" :icon="Edit" @click="openBulkEdit">批量修改</el-button>
            <el-button size="small" type="danger" :icon="Delete" @click="bulkDelete">批量删除</el-button>
          </div>
        </div>
      </transition>

      <el-table
        ref="tableRef"
        :data="list"
        v-loading="loading"
        border
        stripe
        row-key="id"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="42" fixed="left" reserve-selection />
        <el-table-column prop="name" label="软件名称" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <el-link type="primary" @click="handleEdit(row)">{{ row.name }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="version" label="采购版本" width="150" show-overflow-tooltip />
        <el-table-column prop="category" label="软件分类" width="140">
          <template #default="{ row }">
            <el-tag v-if="row.category" size="small" effect="plain">{{ row.category }}</el-tag>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="supplier" label="供应商" width="170" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.supplier">{{ row.supplier }}</span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="folder_name" label="所属机构" width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.folder_name">{{ row.folder_name }}</span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.remark">{{ row.remark }}</span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && !list.length" description="暂无软件记录，点击「添加软件」新建" :image-size="90" />

      <div class="pagination" v-if="pagination.total > 0">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :page-sizes="[20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 批量修改 -->
    <el-dialog v-model="bulkEditVisible" title="批量修改软件" width="520px" destroy-on-close>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        class="bulk-tip"
        :title="`将对选中的 ${selectedRows.length} 条记录生效`"
        description="只有勾选并填写的字段才会被修改，未勾选的字段保持原值不变。"
      />
      <el-form label-width="90px" class="bulk-form">
        <el-form-item v-for="f in bulkFields" :key="f.key" :label="f.label">
          <div class="bulk-row">
            <el-checkbox v-model="bulkEnabled[f.key]" class="bulk-check" />
            <el-select v-if="f.key === 'category'" v-model="bulkForm.category" filterable allow-create
                       default-first-option :disabled="!bulkEnabled[f.key]" placeholder="选择或输入分类"
                       clearable class="bulk-input">
              <el-option v-for="c in categoryOptions" :key="c" :label="c" :value="c" />
            </el-select>
            <el-select v-else-if="f.key === 'supplier'" v-model="bulkForm.supplier" filterable allow-create
                       default-first-option :disabled="!bulkEnabled[f.key]" placeholder="选择或输入供应商"
                       clearable class="bulk-input">
              <el-option v-for="s in supplierOptions" :key="s" :label="s" :value="s" />
            </el-select>
            <el-select v-else-if="f.key === 'folder_id'" v-model="bulkForm.folder_id" filterable
                       :disabled="!bulkEnabled[f.key]" placeholder="选择所属机构" clearable class="bulk-input">
              <el-option v-for="o in folderOptions" :key="o.id" :label="o.full_path" :value="o.id" />
            </el-select>
            <el-input v-else v-model="bulkForm[f.key]" :disabled="!bulkEnabled[f.key]"
                      :placeholder="f.placeholder || '留空则清空该字段'" class="bulk-input" />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="bulkEditVisible = false">取消</el-button>
        <el-button type="primary" :loading="bulkSaving" @click="confirmBulkEdit">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, inject } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Refresh, Folder, Collection, InfoFilled, Edit, Delete } from '@element-plus/icons-vue'
import { softwareApi, dictApi, folderApi } from '../api/index.js'

// 选中目录由 Layout.vue 通过 provide 注入（避免 router-view 透传 prop 污染导致不切换组件）
const props = defineProps({
  // 兼容：直接传 prop 时仍可工作（fallback）
  selectedFolder: { type: Object, default: null }
})
const injectedFolder = inject('selectedFolder', null)
const injectedClear = inject('clearFolder', null)
const selectedFolder = computed(() => injectedFolder?.value ?? props.selectedFolder)
const clearFolder = () => injectedClear?.()

// 软件分类由 Layout.vue 通过 provide 注入（来自「软件面板」）
const injectedCategory = inject('selectedSoftwareCategory', null)
const injectedClearCategory = inject('clearSoftwareCategory', null)
const selectedSoftwareCategory = computed(() => injectedCategory?.value ?? null)
const clearSoftwareCategory = () => injectedClearCategory?.()

defineExpose({})

const router = useRouter()
const list = ref([])
const loading = ref(false)
const categoryOptions = ref([])
const searchForm = ref({ keyword: '', category: '' })
const pagination = ref({ page: 1, page_size: 20, total: 0 })

// 软件只挂在组织机构树上，选中资产分类时不做过滤
const scopeFolder = computed(() =>
  props.selectedFolder && props.selectedFolder.kind !== 'asset' ? props.selectedFolder : null
)

const loadData = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.value.page,
      page_size: pagination.value.page_size,
      keyword: searchForm.value.keyword || undefined,
      category: searchForm.value.category || undefined
    }
    // 分组节点（含子节点）点击后显示全部软件，避免空列表
    if (scopeFolder.value?.id && !(scopeFolder.value.children && scopeFolder.value.children.length)) {
      params.folder_id = scopeFolder.value.id
    }
    const res = await softwareApi.getList(params)
    if (res.code === 0) {
      list.value = res.data.items || []
      pagination.value.total = res.data.total || 0
    }
  } catch (e) {
    ElMessage.error('加载软件列表失败')
  } finally {
    loading.value = false
  }
}

const loadCategories = async () => {
  try {
    const res = await dictApi.getByType('software_category')
    if (res.code === 0) {
      categoryOptions.value = (res.data || []).filter(x => x.enabled !== false).map(x => x.name)
    }
  } catch (e) {
    console.error('加载软件分类失败', e)
  }
}

const handleSearch = () => { pagination.value.page = 1; loadData() }
const resetSearch = () => {
  searchForm.value = { keyword: '', category: '' }
  handleSearch()
}
const handleSizeChange = (size) => { pagination.value.page_size = size; loadData() }
const handlePageChange = (page) => { pagination.value.page = page; loadData() }

const handleAdd = () => {
  const query = scopeFolder.value?.id ? { folder_id: scopeFolder.value.id } : {}
  router.push({ path: '/softwares/add', query })
}

const handleEdit = (row) => router.push(`/softwares/edit/${row.id}`)

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除软件「${row.name}」吗？`, '提示', { type: 'warning' })
    const res = await softwareApi.delete(row.id)
    if (res.code === 0) {
      ElMessage.success('删除成功')
      loadData()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e?.message || '删除失败')
  }
}

// ========== 批量操作 ==========
const tableRef = ref(null)
const selectedRows = ref([])
const bulkEditVisible = ref(false)
const bulkSaving = ref(false)
const supplierOptions = ref([])
const folderOptions = ref([])

const bulkFields = [
  { key: 'category', label: '软件分类' },
  { key: 'supplier', label: '供应商' },
  { key: 'folder_id', label: '所属机构' },
  { key: 'version', label: '采购版本', placeholder: '留空则清空版本' },
  { key: 'remark', label: '备注', placeholder: '留空则清空备注' }
]

const bulkEnabled = ref({})
const bulkForm = ref({})

const handleSelectionChange = (rows) => { selectedRows.value = rows }
const clearSelection = () => {
  tableRef.value?.clearSelection()
  selectedRows.value = []
}

const openBulkEdit = () => {
  bulkEnabled.value = {}
  bulkForm.value = {}
  for (const f of bulkFields) {
    bulkEnabled.value[f.key] = false
    bulkForm.value[f.key] = f.key === 'folder_id' ? null : ''
  }
  bulkEditVisible.value = true
}

const confirmBulkEdit = async () => {
  const payload = {}
  for (const f of bulkFields) {
    if (!bulkEnabled.value[f.key]) continue
    const v = bulkForm.value[f.key]
    if (f.key === 'folder_id') {
      if (v === null || v === undefined || v === '') {
        ElMessage.warning('「所属机构」已勾选但未选择值')
        return
      }
      payload.folder_id = v
    } else {
      payload[f.key] = v ?? ''
    }
  }
  if (!Object.keys(payload).length) {
    ElMessage.warning('请至少勾选一个要修改的字段')
    return
  }

  bulkSaving.value = true
  try {
    const ids = selectedRows.value.map(r => r.id)
    const res = await softwareApi.bulkUpdate(ids, payload)
    if (res.code === 0) {
      ElMessage.success(res.message || '批量修改成功')
      bulkEditVisible.value = false
      clearSelection()
      await loadData()
      await loadCategories()
    } else {
      ElMessage.warning(res.message || '批量修改失败')
    }
  } catch (e) {
    ElMessage.error('批量修改请求失败')
  } finally {
    bulkSaving.value = false
  }
}

const bulkDelete = async () => {
  const ids = selectedRows.value.map(r => r.id)
  const preview = selectedRows.value.slice(0, 5).map(r => r.name).join('、')
  const more = ids.length > 5 ? ` 等 ${ids.length} 条` : ''
  try {
    await ElMessageBox.confirm(`确定删除 ${preview}${more} 吗？删除后不可恢复。`, '批量删除确认', {
      type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消'
    })
  } catch (e) {
    return
  }
  try {
    const res = await softwareApi.bulkDelete(ids)
    if (res.code === 0) {
      ElMessage.success(res.message || '删除成功')
      clearSelection()
      await loadData()
    } else {
      ElMessage.warning(res.message || '删除失败')
    }
  } catch (e) {
    ElMessage.error('批量删除请求失败')
  }
}

const loadSuppliers = async () => {
  try {
    const res = await dictApi.getByType('supplier')
    if (res.code === 0) {
      supplierOptions.value = (res.data || []).filter(x => x.enabled !== false).map(x => x.name)
    }
  } catch (e) {
    console.error('加载供应商字典失败', e)
  }
}

const loadFolderOptions = async () => {
  try {
    const res = await folderApi.getTree('org')
    if (res.code !== 0) return
    const flat = []
    const walk = (nodes, prefix = '') => {
      for (const n of nodes || []) {
        const p = prefix ? `${prefix} / ${n.name}` : n.name
        flat.push({ id: n.id, full_path: p })
        if (n.children?.length) walk(n.children, p)
      }
    }
    walk(res.data)
    folderOptions.value = flat
  } catch (e) {
    console.error('加载机构树失败', e)
  }
}

watch(() => props.selectedFolder, () => {
  // 切目录时重置：分页、搜索条件、批量选择
  pagination.value.page = 1
  searchForm.value = { keyword: '', category: '' }
  selectedRows.value = []
  tableRef.value?.clearSelection()
  loadData()
})

// 软件面板选中的分类变化时，同步到搜索条件并刷新
watch(selectedSoftwareCategory, (val) => {
  searchForm.value.category = val || ''
  pagination.value.page = 1
  selectedRows.value = []
  tableRef.value?.clearSelection()
  loadData()
})

onMounted(() => {
  loadCategories()
  loadSuppliers()
  loadFolderOptions()
  loadData()
})
</script>

<style scoped>
.search-card { margin-bottom: 16px; }
.scope-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin-bottom: 12px;
  background: #ecf5ff;
  border: 1px solid #d9ecff;
  border-radius: 4px;
  font-size: 13px;
  color: #409eff;
}
.asset-bar {
  background: #fdf6ec;
  border-color: #faecd8;
  color: #e6a23c;
}
.cat-bar {
  background: #f0f9eb;
  border-color: #d9ead3;
  color: #67c23a;
}
.scope-text { flex: 1; }
.search-form { margin-bottom: 0; }
.toolbar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 6px;
}
.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.muted { color: #c0c4cc; }

.bulk-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 8px 14px;
  margin-bottom: 12px;
  background: #ecf5ff;
  border: 1px solid #b3d8ff;
  border-radius: 4px;
}
.bulk-info { font-size: 13px; color: #409eff; }
.bulk-info b { font-size: 15px; margin: 0 2px; }
.bulk-actions { display: flex; gap: 8px; }
.bulk-tip { margin-bottom: 14px; }
.bulk-form .bulk-row { display: flex; align-items: center; gap: 10px; width: 100%; }
.bulk-form .bulk-check { flex-shrink: 0; }
.bulk-form .bulk-input { flex: 1; }
</style>
