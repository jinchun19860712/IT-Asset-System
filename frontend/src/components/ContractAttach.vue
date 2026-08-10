<template>
  <div class="contract-attach">
    <div class="ca-head">
      <span class="ca-title">合同附件</span>
      <div class="ca-ops">
        <el-button size="small" type="primary" @click="openUpload">上传合同</el-button>
        <el-button size="small" @click="openLink">关联已有</el-button>
        <el-button size="small" @click="reload" v-if="relatedId">刷新</el-button>
      </div>
    </div>

    <!-- 已关联 -->
    <el-table :data="linked" v-loading="loading" size="small" border style="margin-top: 8px">
      <el-table-column prop="name" label="合同名称" min-width="160" show-overflow-tooltip />
      <el-table-column prop="supplier_name" label="供应商" width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.supplier_name || '-' }}</template>
      </el-table-column>
      <el-table-column prop="file_type" label="类型" width="70" align="center">
        <template #default="{ row }">{{ (row.file_type || '').toUpperCase() }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150" align="center" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="download(row)">下载</el-button>
          <el-button link type="danger" size="small" @click="unlink(row)">移除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && !linked.length && !pending.length" :image-size="60"
      description="暂无合同附件，可上传或关联已有合同" />

    <!-- 待关联（新建设备尚未保存时上传） -->
    <div v-if="pending.length" class="pending-box">
      <div class="pending-tip">以下合同将在「保存设备」后自动关联到本{{ typeLabel }}：</div>
      <el-tag v-for="p in pending" :key="p.id" closable class="pending-tag" @close="dropPending(p)">
        {{ p.name }}
      </el-tag>
    </div>

    <!-- 上传对话框 -->
    <el-dialog v-model="uploadVisible" title="上传合同" width="460px">
      <el-form label-width="90px">
        <el-form-item label="合同文件" required>
          <el-upload
            :auto-upload="false"
            :limit="1"
            :on-change="onFileChange"
            :on-exceed="() => ElMessage.warning('只能选择一个文件')"
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

    <!-- 关联已有对话框 -->
    <el-dialog v-model="linkVisible" title="关联已有合同" width="560px">
      <el-input v-model="linkKw" placeholder="搜索合同名称 / 供应商" clearable style="margin-bottom: 10px"
        @input="loadAllContracts" />
      <el-table :data="allContracts" size="small" border max-height="320" v-loading="linkLoading">
        <el-table-column prop="name" label="合同名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="supplier_name" label="供应商" width="140" show-overflow-tooltip />
        <el-table-column label="操作" width="90" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="doLink(row)">关联</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { contractApi, dictApi } from '../api/index.js'

const props = defineProps({
  relatedType: { type: String, required: true },  // 'device' | 'software'
  relatedId: { type: [Number, null], default: null }
})
const emit = defineEmits(['changed'])

const typeLabel = computed(() => props.relatedType === 'software' ? '软件' : '设备')

const linked = ref([])
const loading = ref(false)
const pending = ref([])          // 新建时先上传、保存后再关联的合同 id 列表
const suppliers = ref([])

const uploadVisible = ref(false)
const form = ref({ file: null, name: '', supplier_id: null, remark: '' })

const linkVisible = ref(false)
const linkKw = ref('')
const allContracts = ref([])
const linkLoading = ref(false)

const reload = async () => {
  if (!props.relatedId) { linked.value = []; return }
  loading.value = true
  try {
    const res = await contractApi.list({
      related_type: props.relatedType, related_id: props.relatedId
    })
    linked.value = res.code === 0 ? (res.data || []) : []
  } catch (e) {
    linked.value = []
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
      related_type: props.relatedType,
      related_id: props.relatedId ?? null,
      remark: form.value.remark
    })
    if (res.code !== 0) { ElMessage.error(res.message || '上传失败'); return }
    const c = res.data
    if (props.relatedId) {
      linked.value = [...linked.value, c]
    } else {
      c._new = true                            // 新上传的待关联项，移除时一并删除库记录
      pending.value = [...pending.value, c]   // 保存设备后自动关联
    }
    ElMessage.success('上传成功')
    uploadVisible.value = false
    emit('changed')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '上传失败')
  }
}

const download = (row) => {
  window.open(contractApi.downloadUrl(row.id), '_blank')
}

const unlink = async (row) => {
  try {
    await contractApi.remove(row.id)
    linked.value = linked.value.filter(x => x.id !== row.id)
    ElMessage.success('已移除')
    emit('changed')
  } catch (e) {
    ElMessage.error('移除失败')
  }
}

// 保存设备/软件后，把待关联的合同绑定到刚保存的对象
const flushPending = async (newRelatedId) => {
  if (!pending.value.length || !newRelatedId) { pending.value = []; return }
  for (const c of pending.value) {
    try {
      await contractApi.update(c.id, { related_type: props.relatedType, related_id: newRelatedId })
    } catch (e) { /* 忽略单个失败 */ }
  }
  pending.value = []
  await reload()
}

const dropPending = async (p) => {
  // 仅新上传的待关联项需要删除库记录；"关联已有"的已有合同只是取消关联，不应误删
  if (p._new) {
    try { await contractApi.remove(p.id) } catch (e) {}
  }
  pending.value = pending.value.filter(x => x.id !== p.id)
}

const loadAllContracts = async () => {
  linkLoading.value = true
  try {
    const res = await contractApi.list({ keyword: linkKw.value || undefined })
    allContracts.value = res.code === 0 ? (res.data || []) : []
  } catch (e) { allContracts.value = [] }
  finally { linkLoading.value = false }
}

const openLink = () => {
  linkKw.value = ''
  linkVisible.value = true
  loadAllContracts()
}

const doLink = async (row) => {
  try {
    if (props.relatedId) {
      await contractApi.update(row.id, { related_type: props.relatedType, related_id: props.relatedId })
      await reload()
    } else {
      // 新建态：先记下待关联
      if (!pending.value.some(p => p.id === row.id)) pending.value.push(row)
    }
    ElMessage.success('已关联')
    linkVisible.value = false
    emit('changed')
  } catch (e) {
    ElMessage.error('关联失败')
  }
}

onMounted(() => { loadSuppliers(); reload() })
defineExpose({ flushPending })
</script>

<style scoped>
.contract-attach { border: 1px solid #ebeef5; border-radius: 6px; padding: 12px 14px; }
.ca-head { display: flex; align-items: center; justify-content: space-between; }
.ca-title { font-weight: 600; }
.ca-ops { display: flex; gap: 8px; }
.pending-box { margin-top: 10px; padding: 8px 10px; background: #fdf6ec; border-radius: 4px; }
.pending-tip { font-size: 12px; color: #e6a23c; margin-bottom: 6px; }
.pending-tag { margin: 0 6px 6px 0; }
</style>
