<template>
  <div class="software-form">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ isEdit ? '编辑软件' : '添加软件' }}</span>
        </div>
      </template>

      <el-form :model="form" :rules="rules" ref="formRef" label-width="110px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="软件名称" prop="name">
              <el-input v-model="form.name" placeholder="如：Microsoft Office" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="采购版本">
              <el-input v-model="form.version" placeholder="如：2021 专业增强版 / v5.2.1" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="软件分类">
              <el-select
                v-model="form.category"
                placeholder="选择或输入新分类"
                filterable
                allow-create
                default-first-option
                clearable
                style="width: 100%"
                @change="(v) => onDictFieldChange('software_category', v)"
              >
                <el-option v-for="c in categoryOptions" :key="c" :label="c" :value="c" />
              </el-select>
              <div class="hint">来自「基础数据 → 软件分类」，直接输入新值会自动加入字典</div>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="供应商">
              <el-select
                v-model="form.supplier"
                placeholder="选择或输入供应商"
                filterable
                allow-create
                default-first-option
                clearable
                style="width: 100%"
                @change="(v) => onDictFieldChange('supplier', v)"
              >
                <el-option v-for="s in supplierOptions" :key="s" :label="s" :value="s" />
              </el-select>
              <div class="hint">与设备共用同一份供应商清单</div>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="所属机构">
              <el-tree-select
                v-model="form.folder_id"
                :data="folderTree"
                :props="{ label: 'name', value: 'id', children: 'children' }"
                placeholder="选择组织机构文件夹（可不填）"
                style="width: 100%"
                check-strictly
                clearable
                filterable
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="授权数量、到期时间、许可证号等" />
        </el-form-item>

        <el-divider>合同附件</el-divider>
        <ContractAttach ref="contractAttachRef" related-type="software" :related-id="softwareId" />

        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            {{ isEdit ? '保存修改' : '确认添加' }}
          </el-button>
          <el-button @click="router.push('/softwares')">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { softwareApi, dictApi, folderApi } from '../api/index.js'
import ContractAttach from '../components/ContractAttach.vue'

const route = useRoute()
const router = useRouter()
const formRef = ref()
const contractAttachRef = ref()
const isEdit = ref(false)
const softwareId = ref(null)
const submitting = ref(false)

const form = ref({
  name: '', version: '', category: '', supplier: '', folder_id: null, remark: ''
})

const rules = {
  name: [{ required: true, message: '请输入软件名称', trigger: 'blur' }]
}

const categoryOptions = ref([])
const supplierOptions = ref([])
const folderTree = ref([])

const onDictFieldChange = async (dictType, value) => {
  const v = (value || '').trim()
  if (!v) return
  const pool = dictType === 'software_category' ? categoryOptions : supplierOptions
  if (pool.value.includes(v)) return
  try {
    await dictApi.create({ type: dictType, name: v, sort_order: 0, enabled: true })
    pool.value = [...pool.value, v]
  } catch (e) {
    // 字典写入失败不影响软件保存
    console.error('新增字典项失败', e)
  }
}

const loadOptions = async () => {
  try {
    const [dictRes, folderRes] = await Promise.all([
      dictApi.getAll(),
      folderApi.getTree('org')
    ])
    if (dictRes.code === 0) {
      const g = dictRes.data || {}
      const pick = (arr) => (arr || []).filter(x => x.enabled !== false).map(x => x.name)
      categoryOptions.value = pick(g.software_category)
      supplierOptions.value = pick(g.supplier)
    }
    if (folderRes.code === 0) folderTree.value = folderRes.data || []
  } catch (e) {
    console.error('加载选项失败', e)
  }
}

const loadDetail = async () => {
  if (!isEdit.value) return
  try {
    const res = await softwareApi.getDetail(softwareId.value)
    if (res.code !== 0) return
    const d = res.data
    form.value = {
      name: d.name || '',
      version: d.version || '',
      category: d.category || '',
      supplier: d.supplier || '',
      folder_id: d.folder_id ?? null,
      remark: d.remark || ''
    }
  } catch (e) {
    ElMessage.error('加载详情失败')
  }
}

const handleSubmit = async () => {
  await formRef.value.validate()
  submitting.value = true
  try {
    let savedId = softwareId.value
    if (isEdit.value) await softwareApi.update(softwareId.value, form.value)
    else {
      const res = await softwareApi.create(form.value)
      savedId = res?.data?.id ?? null
    }
    // 新建软件时先上传的合同，保存后自动关联到本软件
    try { await contractAttachRef.value?.flushPending(savedId) } catch (e) {}
    ElMessage.success(isEdit.value ? '更新成功' : '添加成功')
    router.push('/softwares')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '保存失败')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  softwareId.value = route.params.id
  isEdit.value = !!softwareId.value
  await loadOptions()
  if (isEdit.value) {
    await loadDetail()
  } else {
    const qFolder = route.query.folder_id
    if (qFolder) form.value.folder_id = Number(qFolder)
  }
})
</script>

<style scoped>
.software-form { max-width: 900px; margin: 0 auto; }
.card-header { font-weight: bold; font-size: 16px; }
.hint { font-size: 12px; color: #909399; line-height: 1.6; }
</style>
