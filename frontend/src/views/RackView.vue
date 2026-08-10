<template>
  <div class="rack-view">
    <!-- ============ 左侧：机柜列表 ============ -->
    <div class="rack-side">
      <div class="side-header">
        <span class="side-title">机柜列表</span>
        <div class="side-actions">
          <el-button size="small" text @click="loadRacks">
            <el-icon><Refresh /></el-icon>
          </el-button>
          <el-button type="primary" size="small" @click="openCreateRack">
            <el-icon><Plus /></el-icon> 新建
          </el-button>
        </div>
      </div>

      <div class="side-scope">
        <span class="scope-label">部门</span>
        <el-select
          v-model="scopeFolderId"
          placeholder="全部部门"
          clearable
          size="small"
          style="flex: 1"
          @change="onScopeChange"
        >
          <el-option v-for="d in deptOptions" :key="d.id" :label="d.label" :value="d.id" />
        </el-select>
      </div>

      <div class="side-body" v-loading="loading">
        <el-empty v-if="!rackList.length && !loading" description="暂无机柜" :image-size="70">
          <el-button type="primary" @click="openCreateRack">
            <el-icon><Plus /></el-icon> 新建机柜
          </el-button>
        </el-empty>

        <div
          v-for="rack in rackList"
          :key="rack.id"
          class="rack-card"
          :class="{ active: rack.id === selectedRackId }"
          @click="selectRack(rack)"
        >
          <div class="rc-title">
            <el-icon class="rc-icon"><Box /></el-icon>
            <span class="rc-name" :title="rack.name">{{ rack.name }}</span>
          </div>
          <div class="rc-meta">
            <span>{{ rack.location || '未填写位置' }}</span>
            <span v-if="rack.row_label"> · {{ rack.row_label }}</span>
          </div>
          <div class="rc-usage">
            <span class="rc-units">{{ rack.used_units || 0 }} / {{ rack.u_height }} U</span>
            <span class="rc-count">{{ rack.device_count || 0 }} 台</span>
          </div>
          <el-progress
            :percentage="usagePercent(rack)"
            :stroke-width="6"
            :color="progressColor"
            :show-text="false"
          />
        </div>
      </div>
    </div>

    <!-- ============ 中间：可拖拽设备（未上架） ============ -->
    <div class="device-tray" v-if="currentRack" @dragover.prevent @drop.prevent>
      <div class="tray-header">
        <span class="tray-title">未上架设备</span>
        <span class="tray-count">{{ availableDevices.length }}</span>
      </div>
      <el-input
        v-model="trayKeyword"
        size="small"
        class="tray-search"
        placeholder="搜索可拖拽设备"
        clearable
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <div class="tray-body" v-loading="trayLoading">
        <el-empty v-if="!filteredTray.length" :image-size="46" description="暂无可拖拽设备" />
        <div
          v-for="d in filteredTray"
          :key="d.id"
          class="tray-item"
          :style="{ borderLeftColor: typeColor(d.device_type).bd }"
          draggable="true"
          @dragstart="onDragTray($event, d)"
          @dragend="onDragEnd"
          :title="`拖拽到右侧机柜的空闲 U 位即可上架\n${d.name}`"
        >
          <span class="ti-name">{{ d.name }}</span>
          <span class="ti-meta">{{ [d.device_type, d.model].filter(Boolean).join(' · ') || '—' }}</span>
        </div>
      </div>
      <div class="tray-tip">
        <el-icon><Top /></el-icon> 拖动设备到右侧空闲 U 位上架
      </div>
    </div>

    <!-- ============ 右侧：机柜正视图 ============ -->
    <div class="rack-main">
      <el-empty
        v-if="!currentRack"
        description="请从左侧选择一个机柜查看正视图"
        :image-size="110"
      />

      <template v-else>
        <div class="main-toolbar">
          <div class="tb-left">
            <span class="tb-title">{{ currentRack.name }}</span>
            <el-tag size="small" type="info" effect="plain">{{ currentRack.u_height }}U</el-tag>
            <span v-if="currentRack.location" class="tb-sub">{{ currentRack.location }}</span>
            <span v-if="currentRack.row_label" class="tb-sub">{{ currentRack.row_label }}</span>
          </div>
          <div class="tb-right">
            <el-radio-group v-model="currentFace" size="small">
              <el-radio-button value="front">前面板</el-radio-button>
              <el-radio-button value="rear">后面板</el-radio-button>
            </el-radio-group>
            <el-button type="primary" size="small" @click="openMountDialog()">
              <el-icon><Plus /></el-icon> 上架设备
            </el-button>
            <el-button size="small" @click="openEditRack(currentRack)">
              <el-icon><Edit /></el-icon> 编辑
            </el-button>
            <el-button size="small" type="danger" plain @click="handleDeleteRack">
              <el-icon><Delete /></el-icon> 删除
            </el-button>
            <el-button size="small" text @click="loadLayout">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>
        </div>

        <div class="stat-bar">
          <span>当前面板：<b>{{ currentFace === 'front' ? '前面板' : '后面板' }}</b></span>
          <span>已上架：<b>{{ faceDevices.length }}</b> 台</span>
          <span>空闲：<b>{{ freeUnits }}</b> U</span>
          <span v-if="currentRack.folder_full_path" class="stat-path">
            {{ currentRack.folder_full_path }}
          </span>
        </div>

        <div class="rack-body" v-loading="layoutLoading">
          <div class="rack-frame">
            <div class="frame-cap">{{ currentRack.name }} · {{ currentFace === 'front' ? '前视图' : '后视图' }}</div>

            <div
              class="u-stack"
              :style="{ height: currentRack.u_height * U_ROW_H + 'px' }"
              @dragover.prevent
              @drop.prevent
            >
              <!-- 背景 U 行：从上到下渲染，编号自下而上递增（顶部为最大U） -->
              <div
                v-for="u in uRows"
                :key="u"
                class="u-row"
                :style="{ height: U_ROW_H + 'px' }"
              >
                <div class="u-label">{{ u }}</div>
                <div
                  v-if="!occupiedSet.has(u)"
                  class="u-slot free"
                  :class="{ 'drag-over': dragOverU === u }"
                  @click="openMountDialog(u)"
                  @dragover.prevent="onDragOverSlot(u, $event)"
                  @dragleave="onDragLeaveSlot(u)"
                  @drop.prevent="onDropToSlot(u, $event)"
                >
                  <span class="slot-hint">
                    <el-icon><Plus /></el-icon> 上架
                  </span>
                </div>
                <div v-else class="u-slot taken"></div>
              </div>

              <!-- 设备层：按 U 位绝对定位，天然支持跨多个 U 的设备 -->
              <div class="device-layer">
                <div
                  v-for="d in faceDevices"
                  :key="d.device_id"
                  class="device-block"
                  :class="{ 'is-dragging': draggingDeviceId === d.device_id }"
                  :style="blockStyle(d)"
                  :title="`${d.name} (U${d.rack_position}${d.rack_units > 1 ? '-U' + (d.rack_position + d.rack_units - 1) : ''}) · 拖动可调整位置`"
                  draggable="true"
                  @dragstart="onDragBlock($event, d)"
                  @dragend="onDragEnd"
                >
                  <span class="db-name">{{ d.name }}</span>
                  <span v-if="d.model" class="db-meta">{{ d.model }}</span>
                  <span v-if="d.ip_address" class="db-ip">{{ d.ip_address }}</span>
                  <el-tag
                    v-if="d.status_name"
                    size="small"
                    effect="dark"
                    :color="d.status_color"
                    class="db-status"
                  >
                    {{ d.status_name }}
                  </el-tag>
                  <span class="db-u">
                    U{{ d.rack_position }}<template v-if="d.rack_units > 1">-U{{ d.rack_position + d.rack_units - 1 }}</template>
                  </span>
                  <span class="db-spacer"></span>
                  <span class="db-actions">
                    <el-button size="small" text @click.stop="openMoveDialog(d)">
                      <el-icon><Rank /></el-icon> 调整位置
                    </el-button>
                    <el-button size="small" text type="danger" @click.stop="handleUnmount(d)">
                      <el-icon><Download /></el-icon> 下架
                    </el-button>
                  </span>
                </div>
              </div>
            </div>

            <div class="frame-cap bottom">底部 · U1</div>
          </div>
        </div>
      </template>
    </div>

    <!-- ============ 机柜新建/编辑弹窗 ============ -->
    <el-dialog v-model="rackDialogVisible" :title="rackDialogTitle" width="520px">
      <el-form ref="rackFormRef" :model="rackForm" :rules="rackRules" label-width="100px">
        <el-form-item label="机柜名称" prop="name">
          <el-input v-model="rackForm.name" placeholder="如：信息中心-A01机柜" clearable />
        </el-form-item>
        <el-form-item label="U 高度" prop="u_height">
          <el-input-number v-model="rackForm.u_height" :min="1" :max="60" />
          <span class="form-tip">标准机柜通常为 42U</span>
        </el-form-item>
        <el-form-item label="位置">
          <el-input v-model="rackForm.location" placeholder="如：三楼主机房" clearable />
        </el-form-item>
        <el-form-item label="列/排编号">
          <el-input v-model="rackForm.row_label" placeholder="如：A列 01" clearable />
        </el-form-item>
        <el-form-item label="所属文件夹">
          <el-tree-select
            v-model="rackForm.folder_id"
            :data="folderTree"
            :props="{ label: 'name', value: 'id', children: 'children' }"
            check-strictly
            clearable
            :render-after-expand="false"
            placeholder="请选择所属文件夹"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="rackForm.description" type="textarea" :rows="3" placeholder="备注信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rackDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingRack" @click="submitRack">确定</el-button>
      </template>
    </el-dialog>

    <!-- ============ 上架 / 调整位置弹窗 ============ -->
    <el-dialog
      v-model="mountDialogVisible"
      :title="mountMode === 'move' ? '调整设备位置' : '设备上架'"
      width="480px"
    >
      <el-form :model="mountForm" label-width="90px">
        <el-form-item label="设备">
          <el-select
            v-model="mountForm.device_id"
            filterable
            clearable
            placeholder="请选择要上架的设备"
            style="width: 100%"
            :disabled="mountMode === 'move'"
          >
            <el-option
              v-for="d in deviceOptions"
              :key="d.id"
              :label="d.name"
              :value="d.id"
            >
              <span>{{ d.name }}</span>
              <span class="opt-meta">
                {{ [d.device_type, d.model, d.ip_address].filter(Boolean).join(' / ') }}
              </span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="起始U位">
          <el-input-number v-model="mountForm.rack_position" :min="1" :max="maxPosition" />
          <span class="form-tip">U1 为机柜最底层</span>
        </el-form-item>
        <el-form-item label="占用U数">
          <el-input-number v-model="mountForm.rack_units" :min="1" :max="maxUnits" />
        </el-form-item>
        <el-form-item label="朝向">
          <el-radio-group v-model="mountForm.rack_face">
            <el-radio value="front">前面板</el-radio>
            <el-radio value="rear">后面板</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="mountDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingMount" @click="submitMount">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Refresh, Box, Rank, Download, Search, Top } from '@element-plus/icons-vue'
import { rackApi, folderApi } from '../api/index.js'

const props = defineProps({ selectedFolder: Object })

// 机柜视图的部门范围（替代左侧树传来的 selectedFolder，因为机柜视图不再展示文件夹树）
const scopeFolderId = ref(null)
const deptOptions = ref([])

// 单个 U 位的像素高度，设备块的定位换算依赖它
const U_ROW_H = 30

const loading = ref(false)
const layoutLoading = ref(false)
const rackList = ref([])
const selectedRackId = ref(null)
const layout = ref(null)
const currentFace = ref('front')
const folderTree = ref([])

// —— 机柜表单 ——
const rackDialogVisible = ref(false)
const rackDialogTitle = ref('新建机柜')
const savingRack = ref(false)
const editingRackId = ref(null)
const rackFormRef = ref()
const rackForm = ref({
  name: '', u_height: 42, location: '', row_label: '', folder_id: null, description: ''
})
const rackRules = {
  name: [{ required: true, message: '请输入机柜名称', trigger: 'blur' }],
  u_height: [{ required: true, message: '请输入U高度', trigger: 'blur' }]
}

// —— 上架表单 ——
const mountDialogVisible = ref(false)
const savingMount = ref(false)
const mountMode = ref('mount') // mount=新上架，move=调整已上架设备位置
const movingDevice = ref(null)
const availableDevices = ref([])
const trayKeyword = ref('')
const trayLoading = ref(false)
const mountForm = ref({ device_id: null, rack_position: 1, rack_units: 1, rack_face: 'front' })

// —— 拖拽状态 ——
const dragOverU = ref(null)        // 当前悬停的高亮 U 位
const draggingDeviceId = ref(null) // 正在拖拽的设备（用于淡化显示）

// 设备类型底色：浅色主题用低饱和柔色；深色主题用更暗的饱和色，避免在深背景上刺眼
// 实时根据 documentElement 的 data-theme 切换
const TYPE_COLORS_LIGHT = {
  '交换机': { bg: '#eaf1fa', bd: '#6d97c9' },
  '服务器': { bg: '#eaf3ec', bd: '#69a37c' },
  '路由器': { bg: '#f1ecf9', bd: '#8d79bd' },
  '防火墙': { bg: '#fbeeec', bd: '#c98075' },
  'UPS': { bg: '#fdf6e8', bd: '#cca863' },
  '存储': { bg: '#e9f3f5', bd: '#67a2ac' },
  '电脑': { bg: '#eef0f4', bd: '#828d9e' }
}
const FALLBACK_COLORS_LIGHT = [
  { bg: 'var(--app-bg-soft, #eaedf0)', bd: '#8791a1' },
  { bg: '#eef4ee', bd: '#7ba382' },
  { bg: '#f4eff7', bd: '#9a85bb' },
  { bg: '#f7f0ec', bd: '#bf8f74' },
  { bg: '#ebf3f6', bd: '#719fb5' }
]
// 深色主题：深底色 + 更亮的边框，对比度够但不刺眼
const TYPE_COLORS_DARK = {
  '交换机': { bg: '#1e2d44', bd: '#7eb6ff' },
  '服务器': { bg: '#1d2e25', bd: '#7ad49a' },
  '路由器': { bg: '#2a2240', bd: '#b89aff' },
  '防火墙': { bg: '#3a2620', bd: '#ff9988' },
  'UPS': { bg: '#3a3220', bd: '#ffd266' },
  '存储': { bg: '#1e2e35', bd: '#7ed3df' },
  '电脑': { bg: '#262b32', bd: '#a8b3c4' }
}
const FALLBACK_COLORS_DARK = [
  { bg: '#262b32', bd: '#a8b3c4' },
  { bg: '#1f2a22', bd: '#8fce9d' },
  { bg: '#2b2235', bd: '#b89aff' },
  { bg: '#332520', bd: '#d49580' },
  { bg: '#1d2932', bd: '#80b3cb' }
]

const isDarkTheme = () => {
  if (typeof document === 'undefined') return false
  return document.documentElement.getAttribute('data-theme') === 'dark'
}
const typeColor = (type) => {
  const dark = isDarkTheme()
  const palette = dark ? TYPE_COLORS_DARK : TYPE_COLORS_LIGHT
  const fallbacks = dark ? FALLBACK_COLORS_DARK : FALLBACK_COLORS_LIGHT
  const key = type || ''
  if (palette[key]) return palette[key]
  let h = 0
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0
  return fallbacks[h % fallbacks.length]
}

const currentRack = computed(() => {
  if (layout.value?.rack) return layout.value.rack
  return rackList.value.find(r => r.id === selectedRackId.value) || null
})

// 顶部为最大U、底部为U1，符合真实机柜的排列方向
const uRows = computed(() => {
  const h = currentRack.value?.u_height || 0
  const rows = []
  for (let u = h; u >= 1; u--) rows.push(u)
  return rows
})

const faceDevices = computed(() =>
  (layout.value?.mounted || []).filter(d => d.rack_face === currentFace.value)
)

const occupiedSet = computed(() => {
  const set = new Set()
  for (const d of faceDevices.value) {
    for (let u = d.rack_position; u < d.rack_position + d.rack_units; u++) set.add(u)
  }
  return set
})

const freeUnits = computed(() => {
  if (!layout.value) return 0
  const list = currentFace.value === 'front' ? layout.value.free_front : layout.value.free_rear
  return (list || []).length
})

const maxPosition = computed(() => currentRack.value?.u_height || 42)
const maxUnits = computed(() => {
  const h = currentRack.value?.u_height || 42
  const pos = mountForm.value.rack_position || 1
  return Math.max(1, h - pos + 1)
})

const deviceOptions = computed(() => {
  const list = [...availableDevices.value]
  // 调整位置时目标设备已上架，不在可用列表里，需补进去才能正常回显
  if (movingDevice.value && !list.some(d => d.id === movingDevice.value.id)) {
    list.unshift(movingDevice.value)
  }
  return list
})

// 拖拽托盘的设备按关键字过滤
const filteredTray = computed(() => {
  const kw = (trayKeyword.value || '').trim().toLowerCase()
  if (!kw) return availableDevices.value
  return availableDevices.value.filter(d =>
    [d.name, d.device_type, d.model, d.ip_address].some(v => (v || '').toLowerCase().includes(kw))
  )
})

const usagePercent = (rack) => {
  if (!rack?.u_height) return 0
  return Math.min(100, Math.round(((rack.used_units || 0) / rack.u_height) * 100))
}
// 进度条颜色：深色主题用更亮的色值保证可见性
const progressColor = (p) => {
  const dark = isDarkTheme()
  if (p >= 90) return dark ? '#ff9988' : '#d98a80'
  if (p >= 70) return dark ? '#ffc266' : '#dfae69'
  return dark ? '#7ad49a' : '#6ba37f'
}

const blockStyle = (d) => {
  const h = currentRack.value?.u_height || 0
  const topU = d.rack_position + d.rack_units - 1
  const c = typeColor(d.device_type)
  return {
    top: (h - topU) * U_ROW_H + 2 + 'px',
    height: d.rack_units * U_ROW_H - 4 + 'px',
    background: c.bg,
    borderLeft: `4px solid ${c.bd}`
  }
}

// ============ 数据加载 ============
// 机柜视图不再展示文件夹树，改为加载部门下拉选项用于范围筛选
const loadDepartments = async () => {
  try {
    const res = await folderApi.getTree('org')
    if (res.code === 0) {
      const opts = []
      const walk = (nodes, depth) => {
        for (const n of nodes || []) {
          opts.push({ id: n.id, label: (depth ? '　'.repeat(depth) : '') + n.name })
          if (n.children && n.children.length) walk(n.children, depth + 1)
        }
      }
      walk(res.data || [], 0)
      deptOptions.value = opts
    }
  } catch (e) {
    console.error('加载部门失败', e)
  }
}

const onScopeChange = () => {
  selectedRackId.value = null
  layout.value = null
  loadRacks()
}

const loadRacks = async () => {
  loading.value = true
  try {
    const res = await rackApi.getList(scopeFolderId.value)
    if (res.code === 0) {
      rackList.value = res.data || []
      // 切换文件夹后原选中机柜可能已不在列表中
      if (selectedRackId.value && !rackList.value.some(r => r.id === selectedRackId.value)) {
        selectedRackId.value = null
        layout.value = null
      }
      if (!selectedRackId.value && rackList.value.length) {
        await selectRack(rackList.value[0])
      }
    }
  } catch (e) {
    ElMessage.error('加载机柜列表失败')
  } finally {
    loading.value = false
  }
}

const loadLayout = async () => {
  if (!selectedRackId.value) {
    layout.value = null
    return
  }
  layoutLoading.value = true
  try {
    const res = await rackApi.getLayout(selectedRackId.value)
    if (res.code === 0) layout.value = res.data
  } catch (e) {
    ElMessage.error('加载机柜布局失败')
  } finally {
    layoutLoading.value = false
  }
}

const selectRack = async (rack) => {
  if (selectedRackId.value === rack.id) return
  selectedRackId.value = rack.id
  layout.value = null
  await loadLayout()
  await loadAvailableDevices()
}

// ============ 机柜增删改 ============
const openCreateRack = () => {
  editingRackId.value = null
  rackDialogTitle.value = '新建机柜'
  rackForm.value = {
    name: '',
    u_height: 42,
    location: '',
    row_label: '',
    folder_id: scopeFolderId.value || null,
    description: ''
  }
  rackDialogVisible.value = true
  rackFormRef.value?.clearValidate()
}

const openEditRack = (rack) => {
  editingRackId.value = rack.id
  rackDialogTitle.value = '编辑机柜'
  rackForm.value = {
    name: rack.name,
    u_height: rack.u_height,
    location: rack.location || '',
    row_label: rack.row_label || '',
    folder_id: rack.folder_id || null,
    description: rack.description || ''
  }
  rackDialogVisible.value = true
  rackFormRef.value?.clearValidate()
}

const submitRack = async () => {
  if (!rackFormRef.value) return
  try {
    await rackFormRef.value.validate()
  } catch (e) {
    return
  }
  savingRack.value = true
  try {
    const payload = { ...rackForm.value }
    if (editingRackId.value) {
      const res = await rackApi.update(editingRackId.value, payload)
      if (res.code === 0) {
        ElMessage.success('保存成功')
        rackDialogVisible.value = false
        await loadRacks()
        await loadLayout()
      } else {
        ElMessage.error(res.message || '保存失败')
      }
    } else {
      const res = await rackApi.create(payload)
      if (res.code === 0) {
        ElMessage.success('创建成功')
        rackDialogVisible.value = false
        const newId = res.data?.id
        await loadRacks()
        if (newId) {
          selectedRackId.value = newId
          await loadLayout()
        }
      } else {
        ElMessage.error(res.message || '创建失败')
      }
    }
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    savingRack.value = false
  }
}

const handleDeleteRack = async () => {
  const rack = currentRack.value
  if (!rack) return
  try {
    await ElMessageBox.confirm(
      `确定删除机柜 "${rack.name}" 吗？柜内设备将自动下架。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )
  } catch (e) {
    return
  }
  try {
    const res = await rackApi.delete(rack.id)
    if (res.code === 0) {
      ElMessage.success('删除成功')
      selectedRackId.value = null
      layout.value = null
      await loadRacks()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

// ============ 上架 / 下架 ============
const loadAvailableDevices = async () => {
  if (!currentRack.value) return
  trayLoading.value = true
  try {
    const res = await rackApi.getAvailableDevices(scopeFolderId.value)
    if (res.code === 0) availableDevices.value = res.data || []
  } catch (e) {
    console.error('加载可上架设备失败', e)
  } finally {
    trayLoading.value = false
  }
}

const openMountDialog = async (u) => {
  if (!currentRack.value) return
  mountMode.value = 'mount'
  movingDevice.value = null
  mountForm.value = {
    device_id: null,
    rack_position: u || 1,
    rack_units: 1,
    rack_face: currentFace.value
  }
  mountDialogVisible.value = true
  await loadAvailableDevices()
}

const openMoveDialog = async (d) => {
  mountMode.value = 'move'
  movingDevice.value = {
    id: d.device_id,
    name: d.name,
    device_type: d.device_type,
    model: d.model,
    ip_address: d.ip_address
  }
  mountForm.value = {
    device_id: d.device_id,
    rack_position: d.rack_position,
    rack_units: d.rack_units,
    rack_face: d.rack_face
  }
  mountDialogVisible.value = true
  await loadAvailableDevices()
}

const submitMount = async () => {
  if (!mountForm.value.device_id) {
    ElMessage.warning('请选择设备')
    return
  }
  savingMount.value = true
  try {
    const res = await rackApi.mount(selectedRackId.value, {
      device_id: mountForm.value.device_id,
      rack_position: mountForm.value.rack_position,
      rack_units: mountForm.value.rack_units,
      rack_face: mountForm.value.rack_face
    })
    if (res.code === 0) {
      ElMessage.success(mountMode.value === 'move' ? '位置已调整' : '上架成功')
      mountDialogVisible.value = false
      currentFace.value = mountForm.value.rack_face
      await loadLayout()
      await refreshRackStats()
    } else {
      // U位冲突/越界等业务错误由后端给出具体提示
      ElMessage.error(res.message || '操作失败')
    }
  } catch (e) {
    ElMessage.error('操作失败')
  } finally {
    savingMount.value = false
  }
}

const handleUnmount = async (d) => {
  try {
    await ElMessageBox.confirm(
      `确定将设备 "${d.name}" 从机柜下架吗？`,
      '下架确认',
      { type: 'warning', confirmButtonText: '确定下架', cancelButtonText: '取消' }
    )
  } catch (e) {
    return
  }
  try {
    const res = await rackApi.unmount(d.device_id)
    if (res.code === 0) {
      ElMessage.success('已下架')
      await loadLayout()
      await refreshRackStats()
    } else {
      ElMessage.error(res.message || '下架失败')
    }
  } catch (e) {
    ElMessage.error('下架失败')
  }
}

// 上架/下架后左侧卡片的已用U与设备数需要同步，但不能打断当前选中状态
const refreshRackStats = async () => {
  try {
    const res = await rackApi.getList(scopeFolderId.value)
    if (res.code === 0) rackList.value = res.data || []
  } catch (e) {
    console.error('刷新机柜统计失败', e)
  }
}

// ============ 拖拽上架 / 换位 ============
const readDraggedId = (e) => {
  const raw = e.dataTransfer.getData('application/x-device-id') || e.dataTransfer.getData('text/plain')
  const id = parseInt(raw, 10)
  return Number.isNaN(id) ? null : id
}

// 从中间托盘拖出未上架设备
const onDragTray = (e, d) => {
  if (!currentRack.value) return
  e.dataTransfer.setData('application/x-device-id', String(d.id))
  e.dataTransfer.setData('text/plain', String(d.id))
  // 必须和 onDragOverSlot 里的 dropEffect 一致，否则浏览器会拒绝放置并触发原生拖拽搜索
  e.dataTransfer.effectAllowed = 'move'
  draggingDeviceId.value = d.id
}

// 从机柜内拖出已上架设备（用于换位）
const onDragBlock = (e, d) => {
  e.dataTransfer.setData('application/x-device-id', String(d.device_id))
  e.dataTransfer.setData('text/plain', String(d.device_id))
  e.dataTransfer.effectAllowed = 'move'
  draggingDeviceId.value = d.device_id
}

const onDragOverSlot = (u, e) => {
  // 必须阻止默认行为才能成为有效放置目标
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
  dragOverU.value = u
}

const onDragLeaveSlot = (u) => {
  if (dragOverU.value === u) dragOverU.value = null
}

const onDragEnd = () => {
  dragOverU.value = null
  draggingDeviceId.value = null
}

// 放置到空闲 U 位：自动判断是新上架还是已上架设备换位
const onDropToSlot = async (u, e) => {
  const deviceId = readDraggedId(e)
  dragOverU.value = null
  draggingDeviceId.value = null
  if (!deviceId || !selectedRackId.value) return

  // 已上架设备（当前面板内存在）视为换位，沿用其占用 U 数
  const existing = faceDevices.value.find(d => d.device_id === deviceId)
  const rack_units = existing ? (existing.rack_units || 1) : 1
  // 拖到的 U 位作为设备顶部，换算起始（底部）U 位
  const rack_position = Math.max(1, u - rack_units + 1)
  const rack_face = currentFace.value

  savingMount.value = true
  try {
    const res = await rackApi.mount(selectedRackId.value, {
      device_id: deviceId,
      rack_position,
      rack_units,
      rack_face
    })
    if (res.code === 0) {
      ElMessage.success(existing ? '位置已调整' : '上架成功')
      currentFace.value = rack_face
      await loadLayout()
      await loadAvailableDevices()
      await refreshRackStats()
    } else {
      ElMessage.error(res.message || '操作失败')
    }
  } catch (err) {
    ElMessage.error('拖拽上架失败')
  } finally {
    savingMount.value = false
  }
}

watch(scopeFolderId, () => {
  // 范围变化由 onScopeChange 处理重载，这里仅兜底
})

onMounted(() => {
  loadDepartments()
  loadRacks()
})
</script>

<style scoped>
.rack-view {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

/* ---------- 左侧列表 ---------- */
.rack-side {
  width: 280px;
  flex: none;
  background: var(--app-panel, #fff);
  border: 1px solid var(--app-border, #e4e7ed);
  border-radius: 6px;
  display: flex;
  flex-direction: column;
}
.side-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid var(--app-border, #e4e7ed);
}
.side-title { font-weight: 600; color: var(--app-text, #303133); font-size: 14px; }
.side-actions { display: flex; align-items: center; gap: 4px; }
.side-scope {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--el-border-color-lighter, var(--app-border, #e4e7ed));
}
.scope-label {
  font-size: 12px;
  color: var(--el-text-color-secondary, #909399);
  white-space: nowrap;
}

.side-body {
  padding: 10px;
  max-height: calc(100vh - 190px);
  overflow-y: auto;
}

.rack-card {
  border: 1px solid var(--app-border, #e4e7ed);
  border-radius: 6px;
  padding: 10px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: all .18s;
  background: var(--app-bg-soft, #fafbfc);
}
.rack-card:hover { border-color: var(--app-border, #d4dbe2); background: var(--app-accent-soft, #eaf2ff); }
.rack-card.active {
  border-color: var(--app-accent, #409eff);
  background: var(--app-accent-soft, #eaf2ff);
  box-shadow: 0 0 0 1px rgba(64, 158, 255, .25);
}
.rc-title { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.rc-icon { color: #7a8899; }
.rc-name {
  font-weight: 600;
  color: var(--app-text, #303133);
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rc-meta {
  font-size: 12px;
  color: var(--app-text-secondary, #909399);
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rc-usage {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--app-text-secondary, #606266);
  margin-bottom: 5px;
}
.rc-units { font-family: Consolas, Monaco, monospace; }
.rc-count { color: var(--app-text-secondary, #909399); }

/* ---------- 右侧主区 ---------- */
.rack-main {
  flex: 1;
  min-width: 0;
  background: var(--app-panel, #fff);
  border: 1px solid var(--app-border, #e4e7ed);
  border-radius: 6px;
  padding: 14px;
}
.main-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--app-border, #e4e7ed);
}
.tb-left { display: flex; align-items: center; gap: 8px; min-width: 0; }
.tb-title { font-size: 16px; font-weight: 600; color: var(--app-text, #303133); }
.tb-sub { font-size: 12px; color: var(--app-text-secondary, #909399); }
.tb-right { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

.stat-bar {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
  padding: 9px 2px;
  font-size: 12px;
  color: var(--app-text-secondary, #606266);
}
.stat-bar b { color: var(--app-text, #303133); }
.stat-path { color: var(--app-text-secondary, #909399); }

.rack-body {
  max-height: calc(100vh - 260px);
  overflow-y: auto;
  padding: 4px;
  background: var(--app-bg-soft, #f0f0f0);
  border-radius: 6px;
}

/* ---------- 机柜框体 ---------- */
.rack-frame {
  --label-w: 40px;
  border: 2px solid var(--app-border-strong, #cdd3dc);
  border-radius: 6px;
  background: var(--app-panel, #fff);
  overflow: hidden;
  margin: 6px;
}
.frame-cap {
  background: var(--app-bg-soft, #eaedf0);
  border-bottom: 1px solid var(--app-border, #d9dde4);
  padding: 6px 10px;
  font-size: 12px;
  color: var(--app-text-secondary, #909399);
  font-weight: 600;
  text-align: center;
  letter-spacing: .5px;
}
.frame-cap.bottom {
  border-bottom: none;
  border-top: 1px solid var(--app-border, #d9dde4);
  font-weight: 400;
  color: var(--app-text-secondary, #909399);
}

.u-stack { position: relative; }

.u-row {
  display: flex;
  align-items: stretch;
  box-sizing: border-box;
  border-bottom: 1px dotted var(--app-border, #e4e7ed);
}
.u-row:last-child { border-bottom: none; }

.u-label {
  width: var(--label-w);
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: Consolas, Monaco, monospace;
  font-size: 11px;
  color: var(--app-text-secondary, #909399);
  background: var(--app-bg-soft, #f0f0f0);
  border-right: 1px solid #e4e7ed;
  user-select: none;
}

.u-slot { flex: 1; min-width: 0; }
.u-slot.free {
  margin: 2px 6px;
  border: 1px dashed var(--app-border, #e4e7ed);
  border-radius: 3px;
  background: var(--app-bg-soft, #fafbfc);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all .15s;
}
.u-slot.free:hover {
  border-color: var(--app-accent, #409eff);
  background: var(--app-accent-soft, #dbeafe);
}
.slot-hint {
  display: none;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  color: #409eff;
}
.u-slot.free:hover .slot-hint { display: inline-flex; }

/* ---------- 设备块 ---------- */
.device-layer {
  position: absolute;
  top: 0;
  bottom: 0;
  left: var(--label-w);
  right: 0;
  pointer-events: none;
}
.device-block {
  position: absolute;
  left: 6px;
  right: 6px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 8px 0 6px;
  border: 1px solid var(--app-border, #e4e7ed);
  border-radius: 3px;
  overflow: hidden;
  pointer-events: auto;
  transition: box-shadow .15s;
}
.device-block:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, .12);
  z-index: 2;
}
.db-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--app-text-on-rack, #2f3742);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 220px;
}
.db-meta, .db-ip {
  font-size: 12px;
  color: var(--app-text-secondary-on-rack, #6b7583);
  white-space: nowrap;
}
.db-ip { font-family: Consolas, Monaco, monospace; }
.db-u {
  font-size: 11px;
  color: var(--app-text-tertiary-on-rack, #8a94a2);
  font-family: Consolas, Monaco, monospace;
  white-space: nowrap;
}
.db-status { border: none; }
.db-spacer { flex: 1; }
.db-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  opacity: 0;
  transition: opacity .15s;
  white-space: nowrap;
}
.device-block:hover .db-actions { opacity: 1; }
.db-actions :deep(.el-button) { padding: 2px 6px; height: auto; }

/* ---------- 表单 ---------- */
.form-tip { margin-left: 10px; font-size: 12px; color: var(--app-text-secondary, #909399); }
.opt-meta { float: right; color: var(--app-text-secondary, #909399); font-size: 12px; margin-left: 16px; }

/* ---------- 中间：可拖拽设备托盘 ---------- */
.device-tray {
  width: 220px;
  flex: none;
  background: var(--app-panel, #fff);
  border: 1px solid var(--app-border, #e4e7ed);
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 150px);
}
.tray-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid var(--app-border, #e4e7ed);
}
.tray-title { font-weight: 600; color: var(--app-text, #303133); font-size: 14px; }
.tray-count {
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 10px;
  background: var(--app-accent-soft, #dbeafe);
  color: #409eff;
  font-size: 12px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.tray-search { padding: 8px 10px 4px; }
.tray-body {
  flex: 1;
  overflow-y: auto;
  padding: 6px 8px;
  min-height: 80px;
}
.tray-item {
  border: 1px solid var(--app-border, #e4e7ed);
  border-left: 4px solid var(--app-border-strong, #8791a1);
  border-radius: 4px;
  padding: 7px 9px;
  margin-bottom: 7px;
  background: var(--app-bg-soft, #fafbfc);
  cursor: grab;
  transition: all .15s;
}
.tray-item:hover {
  border-color: var(--app-border, #d4dbe2);
  background: var(--app-accent-soft, #eaf2ff);
  box-shadow: 0 1px 5px rgba(64, 158, 255, .15);
}
.tray-item:active { cursor: grabbing; }
.ti-name {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--app-text, #303133);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ti-meta {
  display: block;
  font-size: 11px;
  color: var(--app-text-secondary, #909399);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tray-tip {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 10px;
  border-top: 1px solid var(--app-border, #e4e7ed);
  font-size: 11px;
  color: var(--app-text-secondary, #909399);
}
.tray-tip .el-icon { color: #409eff; }

/* ---------- 拖拽反馈 ---------- */
.u-slot.free.drag-over {
  border-color: #409eff;
  background: var(--app-accent-soft, #c7dbfa);
  box-shadow: inset 0 0 0 1px #409eff;
}
.u-slot.free.drag-over .slot-hint { display: inline-flex; }
.device-block { cursor: grab; }
.device-block:active { cursor: grabbing; }
.device-block.is-dragging { opacity: .4; }
</style>
