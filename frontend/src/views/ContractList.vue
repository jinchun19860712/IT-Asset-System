<template>
  <div class="contract-list">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>合同附件管理</span>
          <span class="header-tip">上传设备 / 软件采购合同（PDF / PNG / JPG），可按合同名或供应商检索</span>
        </div>
      </template>

      <div class="toolbar">
        <el-input
          v-model="keyword"
          placeholder="搜索合同名称 / 供应商"
          clearable
          style="width: 280px"
          @input="reload"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button type="primary" @click="openUpload">上传合同</el-button>
        <el-button @click="reload"><el-icon><Refresh /></el-icon> 刷新</el-button>
      </div>

      <el-table :data="list" v-loading="loading" border stripe>
        <el-table-column prop="name" label="合同名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="supplier_name" label="供应商" width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.supplier_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="关联对象" width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <template v-if="row.related_id">
              <el-tag size="small" :type="row.related_type === 'software' ? 'warning' : 'info'">
                {{ row.related_type === 'software' ? '软件' : '设备' }}
              </el-tag>
              {{ relatedName(row) }}
            </template>
            <span v-else class="muted">未关联</span>
          </template>
        </el-table-column>
        <el-table-column prop="file_type" label="类型" width="80" align="center">
          <template #default="{ row }">{{ (row.file_type || '').toUpperCase() }}</template>
        </el-table-column>
        <el-table-column prop="file_size" label="大小" width="100" align="center">
          <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column prop="uploaded_at" label="上传时间" width="170">
          <template #default="{ row }">{{ fmtTime(row.uploaded_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="download(row)">下载</el-button>
            <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && !list.length" description="还没有合同附件" :image-size="80" />
    </el-card>

    <!-- 上传对话框 -->
    <el-dialog v-model="uploadVisible" title="上传合同" width="460px">
      <el-form label-width="90px">
        <el-form-item label="合同文件" required>
          <el-upload
            :auto-upload="false"
            :limit="1"
            :on-change="onFileChange"
            drag
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖入或点击选择（PDF / PNG / JPG，≤20MB）</div>
          </el-upload>
        </el-form-item>
        <el-form-item label="合同名称">
          <el-input v-model="form.name" placeholder="默认取文件名" />
        </el-form-item>
        <el-form-item label="供应商">
          <el-select v-model="form.supplier_id" placeholder="选择供应商（可空）" clearable filterable style="width: 100%">
            <el-option v-for="s in suppliers" :key="s.id" :label="s.name" :value="s.id">
              <span>{{ s.name }}</span>
              <small v-if="s.company_name" style="color:#909399">（{{ s.company_name }}）</small>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!form.file" @click="confirmUpload">上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, UploadFilled } from '@element-plus/icons-vue'
import { contractApi, dictApi, deviceApi, softwareApi } from '../api/index.js'

const list = ref([])
const loading = ref(false)
const keyword = ref('')
const suppliers = ref([])
const deviceNameMap = ref({})
const softwareNameMap = ref({})

const uploadVisible = ref(false)
const form = ref({ file: null, name: '', supplier_id: null, remark: '' })

const reload = async () => {
  loading.value = true
  try {
    const res = await contractApi.list({ keyword: keyword.value || undefined })
    list.value = res.code === 0 ? (res.data || []) : []
  } catch (e) {
    list.value = []
  } finally {
    loading.value = false
  }
}

const loadSuppliers = async () => {
  try {
    const res = await dictApi.getByType('supplier')
    suppliers.value = res.code === 0 ? (res.data || []) : []
  } catch (e) { suppliers.value = [] }
}

const loadNameMaps = async () => {
  try {
    const d = await deviceApi.getAll()
    if (d.code === 0) d.data.forEach(x => { deviceNameMap.value[x.id] = x.name })
  } catch (e) {}
  try {
    const s = await softwareApi.getList({ page: 1, page_size: 9999 })
    if (s.code === 0) (s.data.items || []).forEach(x => { softwareNameMap.value[x.id] = x.name })
  } catch (e) {}
}

const relatedName = (row) => {
  if (row.related_type === 'software') return softwareNameMap.value[row.related_id] || `#${row.related_id}`
  if (row.related_type === 'device') return deviceNameMap.value[row.related_id] || `#${row.related_id}`
  return ''
}

const onFileChange = (file) => {
  const okExt = /\.(pdf|png|jpe?g)$/i.test(file.name)
  if (!okExt) { ElMessage.warning('仅支持 PDF / PNG / JPG'); return }
  form.value.file = file.raw
  if (!form.value.name) form.value.name = file.name.replace(/\.[^.]+$/, '')
}

const openUpload = () => {
  form.value = { file: null, name: '', supplier_id: null, remark: '' }
  uploadVisible.value = true
}

const confirmUpload = async () => {
  if (!form.value.file) { ElMessage.warning('请选择文件'); return }
  const sup = suppliers.value.find(s => s.id === form.value.supplier_id)
  try {
    const res = await contractApi.upload(form.value.file, {
      name: form.value.name,
      supplier_id: form.value.supplier_id ?? null,
      supplier_name: sup ? sup.name : '',
      remark: form.value.remark
    })
    if (res.code !== 0) { ElMessage.error(res.message || '上传失败'); return }
    ElMessage.success('上传成功')
    uploadVisible.value = false
    await reload()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '上传失败')
  }
}

const download = (row) => window.open(contractApi.downloadUrl(row.id), '_blank')

const remove = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除合同「${row.name}」吗？文件也会一并删除。`, '提示', { type: 'warning' })
    await contractApi.remove(row.id)
    ElMessage.success('删除成功')
    await reload()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const formatSize = (n) => {
  if (!n) return '-'
  if (n < 1024) return n + ' B'
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB'
  return (n / 1024 / 1024).toFixed(2) + ' MB'
}
const fmtTime = (t) => (t ? String(t).replace('T', ' ').slice(0, 19) : '-')

onMounted(async () => {
  await Promise.all([loadSuppliers(), loadNameMaps()])
  await reload()
})
</script>

<style scoped>
.contract-list { max-width: 1100px; margin: 0 auto; }
.card-header { display: flex; align-items: baseline; gap: 12px; font-weight: bold; font-size: 16px; }
.header-tip { font-weight: normal; font-size: 12px; color: #909399; }
.toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.muted { color: #c0c4cc; }
</style>
