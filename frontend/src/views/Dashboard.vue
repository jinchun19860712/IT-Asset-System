<template>
  <div class="dashboard">
    <div class="dash-topbar">
      <div class="db-left">
        <h2 class="db-title">仪表盘</h2>
        <span class="db-hint">可自定义关注的设备与指标，类似 Zabbix 仪表盘</span>
      </div>
      <div class="db-right">
        <template v-if="!editing">
          <el-button @click="editing = true">
            <el-icon><Setting /></el-icon> 编辑仪表盘
          </el-button>
        </template>
        <template v-else>
          <el-button @click="autoLayout">
            <el-icon><Grid /></el-icon> 自动布局
          </el-button>
          <el-button type="primary" @click="openAdd">
            <el-icon><Plus /></el-icon> 添加部件
          </el-button>
          <el-button type="success" @click="editing = false">
            <el-icon><Check /></el-icon> 完成
          </el-button>
        </template>
      </div>
    </div>

    <div v-if="!widgets.length" class="dash-empty">
      <el-empty description="还没有任何部件，点击「编辑仪表盘 → 添加部件」开始定制">
        <el-button type="primary" @click="openAdd">添加部件</el-button>
      </el-empty>
    </div>

    <div v-if="!widgets.length" class="dash-empty">
      <el-empty description="还没有任何部件，点击「编辑仪表盘 → 添加部件」开始定制">
        <el-button type="primary" @click="openAdd">添加部件</el-button>
      </el-empty>
    </div>

    <div
      v-else
      ref="canvasRef"
      class="dash-canvas"
      :class="{ editing }"
      :style="{ height: canvasHeight + 'px' }"
      @dragover="onCanvasDragOver"
      @drop="onCanvasDrop"
      @dragleave="onCanvasDragLeave"
    >
      <div
        v-for="w in widgets"
        :key="w.id"
        class="dw-cell"
        :class="{ dragging: dragId === w.id, resizing: resizeId === w.id }"
        :style="cellStyle(w)"
        :draggable="editing"
        @dragstart="onCellDragStart($event, w.id)"
      >
        <DashboardWidget
          :widget="w"
          :editing="editing"
          :dragging="dragId === w.id"
          :resizing="resizeId === w.id"
          @remove="removeWidget"
          @edit="openEdit"
          @resize-start="(e, dir) => onResizeStart(e, w.id, dir)"
        />
      </div>

      <!-- 拖拽中：半透明占位框提示将放置位置 -->
      <div
        v-if="dragPreview && editing"
        class="dw-placeholder"
        :style="cellStyle({ x: dragPreview.x, y: dragPreview.y, w: dragPreview.w, h: dragPreview.h })"
      >
        <span>将放置到 (列 {{ dragPreview.x + 1 }}, 行 {{ dragPreview.y + 1 }})</span>
      </div>
    </div>

    <!-- 添加 / 编辑部件 -->
    <el-dialog v-model="dialogVisible" :title="dialogMode === 'add' ? '添加部件' : '编辑部件'" width="620px">
      <el-form label-width="100px">
        <el-form-item label="部件类型">
          <el-radio-group v-model="form.type" :disabled="dialogMode === 'edit'">
            <el-radio-button value="device-watch">设备看板</el-radio-button>
            <el-radio-button value="snmp-metrics">SNMP监控项</el-radio-button>
            <el-radio-button value="port-traffic">端口流量</el-radio-button>
            <el-radio-button value="status-summary">状态分布</el-radio-button>
            <el-radio-button value="asset-category">资产分类</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="留空则使用默认标题" style="max-width:280px" />
        </el-form-item>

        <el-form-item label="宽度">
          <el-radio-group v-model="form.span">
            <el-radio-button :value="1">1 列</el-radio-button>
            <el-radio-button :value="2">2 列</el-radio-button>
            <el-radio-button :value="3">3 列</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="高度">
          <el-slider v-model="form.height" :min="180" :max="800" :step="46" show-stops style="max-width:360px" />
          <span class="form-hint">{{ form.height }} px</span>
        </el-form-item>

        <!-- 设备看板配置 -->
        <template v-if="form.type === 'device-watch'">
          <el-form-item label="数据范围">
            <el-select v-model="form.config.scope" style="max-width:280px">
              <el-option label="全部设备" value="all" />
              <el-option label="按资产分类" value="asset" />
              <el-option label="按部门" value="org" />
              <el-option label="按供应商" value="supplier" />
              <el-option label="按产品类型" value="device_type" />
              <el-option label="手动选择" value="manual" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="form.config.scope === 'asset'" label="资产分类">
            <el-select
              v-model="form.config.assetFolderIds"
              multiple filterable collapse-tags collapse-tags-tooltip
              style="width:100%" placeholder="可多选，空则不限"
            >
              <el-option v-for="o in assetOptions" :key="o.id" :label="o.label" :value="o.id" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="form.config.scope === 'org'" label="部门">
            <el-select
              v-model="form.config.orgFolderIds"
              multiple filterable collapse-tags collapse-tags-tooltip
              style="width:100%" placeholder="可多选，空则不限"
            >
              <el-option v-for="o in orgOptions" :key="o.id" :label="o.label" :value="o.id" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="form.config.scope === 'supplier'" label="供应商">
            <el-select
              v-model="form.config.suppliers"
              multiple filterable allow-create default-first-option collapse-tags collapse-tags-tooltip
              style="width:100%" placeholder="可多选，空则不限"
            >
              <el-option v-for="s in supplierOptions" :key="s" :label="s" :value="s" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="form.config.scope === 'device_type'" label="产品类型">
            <el-select
              v-model="form.config.deviceTypes"
              multiple filterable allow-create default-first-option collapse-tags collapse-tags-tooltip
              style="width:100%" placeholder="可多选，空则不限"
            >
              <el-option v-for="t in deviceTypeOptions" :key="t" :label="t" :value="t" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="form.config.scope === 'manual'" label="选择设备">
            <el-select v-model="form.config.deviceIds" multiple filterable style="width:100%" placeholder="可搜索选择">
              <el-option v-for="d in deviceOptions" :key="d.id" :label="`${d.name} (${d.ip_address || '无IP'})`" :value="d.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="显示字段">
            <el-select v-model="form.config.fields" multiple filterable style="width:100%" placeholder="选择要展示的列">
              <el-option v-for="f in fieldOptions" :key="f.key" :label="f.label" :value="f.key" />
            </el-select>
          </el-form-item>
        </template>

        <!-- SNMP 监控项配置 -->
        <template v-if="form.type === 'snmp-metrics'">
          <el-form-item label="选择设备">
            <el-select v-model="form.config.deviceIds" multiple filterable style="width:100%" placeholder="选择要监控的设备">
              <el-option v-for="d in deviceOptions" :key="d.id" :label="`${d.name} (${d.ip_address || '无IP'})`" :value="d.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="监控项">
            <el-select v-model="form.config.metricNames" multiple filterable style="width:100%" placeholder="选择 SNMP 指标">
              <el-option v-for="m in metricOptions" :key="m.metric_name" :label="`${m.metric_name}${m.unit ? ` (${m.unit})` : ''}`" :value="m.metric_name" />
            </el-select>
          </el-form-item>
          <el-form-item label="显示信息">
            <el-select v-model="form.config.infoFields" multiple filterable style="width:100%" placeholder="选择设备信息字段">
              <el-option v-for="f in infoFieldOptions" :key="f.key" :label="f.label" :value="f.key" />
            </el-select>
          </el-form-item>
        </template>

        <!-- 端口流量配置 -->
        <template v-if="form.type === 'port-traffic'">
          <el-form-item label="设备">
            <el-select v-model="form.config.deviceId" filterable style="max-width:320px" placeholder="选择交换机" @change="onTrafficDeviceChange">
              <el-option v-for="d in deviceOptions" :key="d.id" :label="`${d.name} (${d.ip_address || '无IP'})`" :value="d.id" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="trafficPorts.length" label="端口">
            <el-select v-model="form.config.portName" filterable style="max-width:320px" placeholder="选择端口">
              <el-option-group v-if="electricPorts.length" label="电口">
                <el-option v-for="p in electricPorts" :key="p" :label="p" :value="p" />
              </el-option-group>
              <el-option-group v-if="opticalPorts.length" label="光口">
                <el-option v-for="p in opticalPorts" :key="p" :label="p" :value="p" />
              </el-option-group>
            </el-select>
          </el-form-item>
          <el-form-item v-else-if="form.config.deviceId" label="端口">
            <el-input v-model="form.config.portName" style="max-width:200px" placeholder="如 GigabitEthernet1/0/1" />
            <span class="form-hint">该设备未填写端口数量/类型，可手动输入端口名</span>
          </el-form-item>
          <el-form-item label="图表类型">
            <el-radio-group v-model="form.config.chart">
              <el-radio-button value="line">折线图</el-radio-button>
              <el-radio-button value="bar">柱状图</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </template>

        <!-- 状态分布 / 资产分类 -->
        <template v-if="form.type === 'status-summary'">
          <el-form-item label="图表类型">
            <el-radio-group v-model="form.config.chart">
              <el-radio-button value="pie">饼图</el-radio-button>
              <el-radio-button value="bar">柱状图</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </template>

        <el-form-item label="刷新频率">
          <el-select v-model="form.config.refresh" style="max-width:200px">
            <el-option label="实时（2秒）" value="realtime" />
            <el-option label="每 5 秒" value="5s" />
            <el-option label="每 10 秒" value="10s" />
            <el-option label="每 30 秒" value="30s" />
            <el-option label="手动" value="manual" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveWidget">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Setting, Plus, Check, Grid } from '@element-plus/icons-vue'
import DashboardWidget from '../components/DashboardWidget.vue'
import { deviceApi, folderApi, snmpApi, dictApi } from '../api/index.js'

const STORAGE_KEY = 'dashboard_widgets_v2'

const widgets = ref([])
const editing = ref(false)
const dialogVisible = ref(false)
const dialogMode = ref('add')
const form = ref({ id: null, type: 'device-watch', title: '', config: {}, span: 2, height: 320 })

const assetOptions = ref([])
const orgOptions = ref([])
const deviceOptions = ref([])
const deviceTypeOptions = ref([])
const supplierOptions = ref([])
const fieldOptions = ref([])
const metricOptions = ref([])
const infoFieldOptions = ref([])
const trafficDevice = ref(null)

const STATIC_FIELDS = [
  { key: 'name', label: '名称' },
  { key: 'ip_address', label: 'IP' },
  { key: 'device_type', label: '类型' },
  { key: 'status_name', label: '状态' },
  { key: 'user', label: '使用人' },
  { key: 'department', label: '使用部门' },
  { key: 'brand', label: '品牌' },
  { key: 'supplier', label: '供应商' },
  { key: 'asset_folder_name', label: '资产分类' },
  { key: 'area', label: '位置' }
]

const INFO_FIELDS = [
  { key: 'name', label: '名称' },
  { key: 'ip_address', label: 'IP' },
  { key: 'device_type', label: '类型' },
  { key: 'department', label: '使用部门' },
  { key: 'user', label: '使用人' },
  { key: 'supplier', label: '供应商' },
  { key: 'brand', label: '品牌' },
  { key: 'area', label: '位置' }
]

function defaultConfig(type) {
  const base = { refresh: '30s' }
  switch (type) {
    case 'device-watch':
      // 多选配置：scope 为 asset/org/supplier/device_type 时，下面对应字段均支持多个值
      return { ...base, scope: 'all',
        assetFolderId: null, assetFolderIds: [],
        orgFolderId: null, orgFolderIds: [],
        supplier: null, suppliers: [],
        deviceType: null, deviceTypes: [],
        deviceIds: [], fields: ['name', 'ip_address', 'status_name', 'user', 'department'] }
    case 'snmp-metrics':
      return { ...base, deviceIds: [], metricNames: [], infoFields: ['name', 'ip_address', 'department', 'supplier'] }
    case 'status-summary':
      return { ...base, chart: 'pie' }
    case 'asset-category':
      return { ...base, chart: 'bar' }
    case 'port-traffic':
      return { ...base, deviceId: null, portName: '', chart: 'line' }
    default:
      return base
  }
}

// 12 列网格：每列宽度 = 100/12，每行高度 = ROW_H px，部件之间间距 GAP px
const COLS = 12
const ROW_H = 80   // 每行网格高度（px）
const GAP = 12     // 部件间距（px）

function defaultSpan(type) {
  return type === 'device-watch' || type === 'snmp-metrics' ? 6 : 4
}
function defaultHeight(type) {
  return type === 'device-watch' || type === 'snmp-metrics' ? 4 : 3
}
function rowsToPx(rows) { return rows * ROW_H + (rows - 1) * GAP }
// 把 v2 旧数据（只有 span/height）迁移到 v3 自由布局（x/y/w/h），并按规则排版
function migrateLegacy(parsed) {
  if (!Array.isArray(parsed)) return []
  const out = []
  let cursorX = 0, cursorY = 0, rowMaxH = 0
  for (const w of parsed) {
    if (typeof w.x === 'number' && typeof w.y === 'number' &&
        typeof w.w === 'number' && typeof w.h === 'number') {
      out.push({ ...w })
      continue
    }
    const span = Math.min(w.span || defaultSpan(w.type), COLS)
    const rows = Math.max(2, Math.round((w.height || defaultHeight(w.type) * ROW_H) / (ROW_H + GAP)))
    // 排版算法：行内累计，满行换行
    if (cursorX + span > COLS) { cursorY += rowMaxH; cursorX = 0; rowMaxH = 0 }
    out.push({ ...w, x: cursorX, y: cursorY, w: span, h: rows })
    cursorX += span
    rowMaxH = Math.max(rowMaxH, rows)
  }
  return out
}

function loadWidgets() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) {
        widgets.value = migrateLegacy(parsed)
        return true
      }
    }
  } catch (e) { /* ignore */ }
  return false
}
function saveWidgets() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(widgets.value)) } catch (e) { /* ignore */ }
}

async function ensureOptions() {
  try {
    const [assetRes, orgRes, devRes, metRes, typeRes, supRes] = await Promise.all([
      folderApi.getTree('asset'),
      folderApi.getTree('org'),
      deviceApi.getList({ page: 1, page_size: 500 }),
      snmpApi.getMetricColumns(),
      deviceApi.getTypes(),
      dictApi.getByType('supplier')
    ])
    const flat = (nodes, depth = 0) => {
      const out = []
      for (const n of nodes || []) {
        out.push({ id: n.id, label: (depth ? '　'.repeat(depth) : '') + n.name })
        if (n.children) out.push(...flat(n.children, depth + 1))
      }
      return out
    }
    assetOptions.value = assetRes.code === 0 ? flat(assetRes.data) : []
    orgOptions.value = orgRes.code === 0 ? flat(orgRes.data) : []
    deviceOptions.value = devRes.code === 0 ? (devRes.data.items || []) : []
    deviceTypeOptions.value = typeRes.code === 0 ? (typeRes.data || []) : []
    supplierOptions.value = supRes.code === 0 ? (supRes.data || []).map(d => d.name) : []
    const snmpCols = metRes.code === 0 ? (metRes.data || []) : []
    metricOptions.value = snmpCols
    fieldOptions.value = [
      ...STATIC_FIELDS,
      ...snmpCols.map(c => ({ key: 'snmp:' + c.metric_name, label: c.metric_name + (c.unit ? ` (${c.unit})` : '') }))
    ]
    infoFieldOptions.value = INFO_FIELDS
  } catch (e) {
    ElMessage.error('加载选项失败')
  }
}

const trafficPorts = computed(() => {
  if (!form.value.config.deviceId || !trafficDevice.value) return []
  const d = trafficDevice.value
  const total = d.port_count || 0
  if (!total) return []
  const hasElectric = (d.port_types || []).includes('electric')
  const hasOptical = (d.port_types || []).includes('optical')
  const ports = []
  // 简单按数量生成端口名：电口在前，光口在后
  if (hasElectric) {
    for (let i = 1; i <= total; i++) ports.push({ name: `GigabitEthernet1/0/${i}`, type: 'electric' })
  } else if (hasOptical) {
    for (let i = 1; i <= total; i++) ports.push({ name: `GigabitEthernet1/0/${i}`, type: 'optical' })
  } else {
    for (let i = 1; i <= total; i++) ports.push({ name: `GigabitEthernet1/0/${i}`, type: 'unknown' })
  }
  return ports
})
const electricPorts = computed(() => trafficPorts.value.filter(p => p.type === 'electric').map(p => p.name))
const opticalPorts = computed(() => trafficPorts.value.filter(p => p.type === 'optical').map(p => p.name))

function onTrafficDeviceChange(devId) {
  form.value.config.portName = ''
  trafficDevice.value = deviceOptions.value.find(d => d.id === devId) || null
}

function openAdd() {
  form.value = {
    id: null, type: 'device-watch', title: '', config: defaultConfig('device-watch'),
    // 编辑 Dialog 中仍用 span/height（px），保存时再换算成 w/h 网格单位
    span: defaultSpan('device-watch'), height: defaultHeight('device-watch') * (ROW_H + GAP)
  }
  dialogMode.value = 'add'
  dialogVisible.value = true
  trafficDevice.value = null
  ensureOptions()
}
function openEdit(w) {
  form.value = JSON.parse(JSON.stringify(w))
  // 编辑模式：把 w/h 转回 span/height 显示在表单
  form.value.span = w.w || defaultSpan(w.type)
  form.value.height = rowsToPx(w.h || defaultHeight(w.type))
  dialogMode.value = 'edit'
  dialogVisible.value = true
  trafficDevice.value = deviceOptions.value.find(d => d.id === form.value.config.deviceId) || null
  ensureOptions()
}
function saveWidget() {
  if (form.value.type === 'port-traffic' && !form.value.config.deviceId) {
    ElMessage.warning('请选择设备')
    return
  }
  if (form.value.type === 'snmp-metrics' && (!form.value.config.deviceIds || !form.value.config.deviceIds.length)) {
    ElMessage.warning('请至少选择一台设备')
    return
  }
  if (dialogMode.value === 'add') {
    // 新部件：放在画布最末尾的空位
    const span = Math.min(form.value.span || defaultSpan(form.value.type), COLS)
    const rows = Math.max(2, Math.round((form.value.height || rowsToPx(defaultHeight(form.value.type))) / (ROW_H + GAP)))
    const pos = nextFreePosition(span, rows)
    const w = {
      id: 'w_' + Date.now() + '_' + Math.floor(Math.random() * 1000),
      type: form.value.type,
      title: form.value.title,
      config: form.value.config,
      x: pos.x, y: pos.y, w: span, h: rows
    }
    widgets.value.push(w)
  } else {
    const idx = widgets.value.findIndex(x => x.id === form.value.id)
    if (idx >= 0) {
      const span = Math.min(form.value.span || defaultSpan(form.value.type), COLS)
      const rows = Math.max(2, Math.round((form.value.height || rowsToPx(defaultHeight(form.value.type))) / (ROW_H + GAP)))
      // w/h 变化后自动调整 y，把下方被挡的部件下移
      applyResizeShift(widgets.value[idx], span, rows)
      widgets.value[idx].title = form.value.title
      widgets.value[idx].config = form.value.config
      widgets.value[idx].w = span
      widgets.value[idx].h = rows
    }
  }
  saveWidgets()
  dialogVisible.value = false
  ElMessage.success('已保存')
}

// 一键自动布局：把所有部件紧凑排版（按当前 w/h，自动避开重叠）
function autoLayout() {
  // 按 y 升序、x 升序排序后逐个找位置
  const list = [...widgets.value].sort((a, b) => (a.y - b.y) || (a.x - b.x))
  // 清空所有 y, x，再重新排
  for (const w of list) {
    const pos = findFreeSlot(list.filter(x => x !== w), w.w, w.h)
    w.x = pos.x
    w.y = pos.y
  }
  saveWidgets()
  ElMessage.success('已自动整理布局')
}

function findFreeSlot(occupied, w, h) {
  let y = 0
  while (y < 200) {
    for (let x = 0; x <= COLS - w; x++) {
      const ok = !occupied.some(o =>
        o.x < x + w && o.x + o.w > x && o.y < y + h && o.y + o.h > y
      )
      if (ok) return { x, y }
    }
    y += 1
  }
  const maxY = occupied.reduce((m, o) => Math.max(m, o.y + o.h), 0)
  return { x: 0, y: maxY }
}

// 在指定 (w, h) 下找一个不重叠的 (x, y)；找不到就追加到末尾
function nextFreePosition(w, h) {
  let y = 0
  while (y < 200) {
    for (let x = 0; x <= COLS - w; x++) {
      const ok = !widgets.value.some(o =>
        o.x < x + w && o.x + o.w > x && o.y < y + h && o.y + o.h > y
      )
      if (ok) return { x, y }
    }
    y += 1
  }
  const maxY = widgets.value.reduce((m, o) => Math.max(m, o.y + o.h), 0)
  return { x: 0, y: maxY }
}
function removeWidget(w) {
  widgets.value = widgets.value.filter(x => x.id !== w.id)
  saveWidgets()
}

// 首次进入：无保存布局时，注入一组默认部件
async function seedDefaults() {
  if (loadWidgets()) return
  let firstDevId = null
  try {
    const res = await deviceApi.getList({ page: 1, page_size: 1 })
    if (res.code === 0 && res.data.items && res.data.items.length) firstDevId = res.data.items[0].id
  } catch (e) { /* ignore */ }
  widgets.value = [
    { id: 'w_seed_1', type: 'device-watch', title: '', config: defaultConfig('device-watch'),
      x: 0, y: 0, w: 6, h: 4 },
    { id: 'w_seed_2', type: 'status-summary', title: '', config: { chart: 'pie', refresh: '30s' },
      x: 6, y: 0, w: 6, h: 4 },
    { id: 'w_seed_3', type: 'asset-category', title: '', config: { chart: 'bar', refresh: '30s' },
      x: 0, y: 4, w: 6, h: 3 },
    { id: 'w_seed_4', type: 'port-traffic', title: '', config: { deviceId: firstDevId, portName: '', chart: 'line', refresh: '5s' },
      x: 6, y: 4, w: 6, h: 3 }
  ]
  saveWidgets()
}

// seedDefaults 后建立 ResizeObserver；同时监听 localStorage 变化避免热更新时数据缺失
async function initDashboard() {
  await seedDefaults()
  // 等 DOM 渲染完成再测宽度
  await nextTick()
  setupResizeObserver()
}
onMounted(initDashboard)

// 路由切换 / 组件卸载时清理监听器，避免泄漏到 document 全局
onUnmounted(() => {
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', onResizeEnd)
  if (resizeObs) { resizeObs.disconnect(); resizeObs = null }
})

// ========== 自由拖拽（绝对定位 / 12 列网格） ==========
const dragId = ref(null)
const canvasRef = ref(null)
const dragPreview = ref(null)  // {x, y, w, h} 半透明占位框

function onCellDragStart(e, id) {
  // 必须用全局类名 .drag-handle-global —— 子组件 .drag-handle 被 scoped 编译带 hash 后缀，
  // 父组件裸写 .drag-handle 匹配不到跨组件的 DOM
  // 同时避免用户点到「设置/删除」按钮时误拖
  const handle = e.target.closest('.drag-handle-global')
  if (!handle || e.target.closest('.dw-ops')) {
    e.preventDefault()
    return
  }
  const w = widgets.value.find(x => x.id === id)
  if (!w) return
  dragId.value = id
  dragPreview.value = { x: w.x, y: w.y, w: w.w, h: w.h }
  e.dataTransfer.setData('text/widget-id', id)
  e.dataTransfer.effectAllowed = 'move'
}
function onCanvasDragOver(e) {
  if (!dragId.value || !canvasRef.value) {
    // 没有在拖拽：仍允许 drop（用于放置新部件的扩展场景）
    e.preventDefault()
    return
  }
  e.preventDefault()
  e.dataTransfer.dropEffect = 'move'
  // 鼠标位置 → 网格单元
  const rect = canvasRef.value.getBoundingClientRect()
  const cellW = rect.width / COLS
  const mx = Math.max(0, Math.min(COLS - (dragPreview.value?.w || 6), Math.floor((e.clientX - rect.left) / cellW)))
  const my = Math.max(0, Math.floor((e.clientY - rect.top) / (ROW_H + GAP)))
  dragPreview.value = { ...dragPreview.value, x: mx, y: my }
}
function onCanvasDrop(e) {
  e.preventDefault()
  const id = e.dataTransfer.getData('text/widget-id') || dragId.value
  dragId.value = null
  const preview = dragPreview.value
  dragPreview.value = null
  if (!id || !preview) return
  const w = widgets.value.find(x => x.id === id)
  if (!w) return
  // 与当前位置不同才移动
  if (w.x === preview.x && w.y === preview.y) return
  // 检测与其他部件重叠：若重叠，把当前部件 y 推到所有冲突部件的下方
  const conflicts = widgets.value.filter(o =>
    o.id !== w.id && o.x < preview.x + preview.w && o.x + o.w > preview.x &&
    o.y < preview.y + preview.h && o.y + o.h > preview.y
  )
  if (conflicts.length) {
    const minBottom = Math.max(...conflicts.map(c => c.y + c.h))
    if (preview.y < minBottom) preview.y = minBottom
  }
  w.x = preview.x
  w.y = preview.y
  saveWidgets()
}
function onCanvasDragLeave(e) {
  // 仅在离开画布本身时清空（非子元素）
  if (e.target === canvasRef.value) dragPreview.value = null
}

// ========== 大小调整（基于网格：w 列 / h 行） ==========
const resizeId = ref(null)
const resizeStart = ref(null)
// direction: 'n' | 'e' | 's' | 'w' | 'nw' | 'ne' | 'sw' | 'se'
function onResizeStart(e, id, direction = 'se') {
  e.preventDefault()
  e.stopPropagation()
  resizeId.value = id
  const w = widgets.value.find(x => x.id === id)
  resizeStart.value = {
    x: e.clientX, y: e.clientY,
    w: w?.w || defaultSpan(w?.type), h: w?.h || defaultHeight(w?.type),
    direction
  }
  document.addEventListener('mousemove', onResizeMove)
  document.addEventListener('mouseup', onResizeEnd)
  window.addEventListener('blur', onWindowBlur)
}
function onResizeMove(e) {
  if (!resizeId.value || !resizeStart.value) return
  const dx = e.clientX - resizeStart.value.x
  const dy = e.clientY - resizeStart.value.y
  const dir = resizeStart.value.direction
  const idx = widgets.value.findIndex(w => w.id === resizeId.value)
  if (idx < 0) return

  const target = widgets.value[idx]
  // 列宽（左右方向）变化
  if (/e|w/.test(dir)) {
    // 取 canvas 容器宽算每列宽度
    const rect = canvasRef.value?.getBoundingClientRect()
    const perCol = rect ? rect.width / COLS : 120
    const sign = /e/.test(dir) ? 1 : -1
    const wDelta = Math.round((sign * dx) / perCol)
    target.w = Math.min(COLS, Math.max(2, resizeStart.value.w + wDelta))
  }
  // 行高（上下方向）变化
  if (/n|s/.test(dir)) {
    const sign = /s/.test(dir) ? 1 : -1
    const hDelta = Math.round((sign * dy) / (ROW_H + GAP))
    target.h = Math.min(12, Math.max(2, resizeStart.value.h + hDelta))
    // 高度变化触发下方避让：把与目标重叠且 y > 目标旧底部的部件整体下移
    applyCascadeShift(target)
  }
}
function onResizeEnd() {
  resizeId.value = null
  resizeStart.value = null
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', onResizeEnd)
  window.removeEventListener('blur', onResizeEnd)
  saveWidgets()
}

// 兜底：用户切到其他窗口/标签页，mouseup 永远不会触发
// 在 window blur 时强制结束拖拽，避免 mousemove 监听器永久泄漏
function onWindowBlur() {
  if (resizeId.value) onResizeEnd()
}

// 高度变化时自动避让：找出所有与 target 重叠且 y 起点 >= target.y 的部件，
// 把它们整体下移（移到 target 新底部之下，按顺序递归处理）
function applyCascadeShift(target) {
  const targetBottom = target.y + target.h
  // 找出与 target 水平重叠且垂直方向进入 target 区域的部件
  const conflicts = widgets.value.filter(o =>
    o.id !== target.id &&
    o.x < target.x + target.w && o.x + o.w > target.x &&
    o.y + o.h > target.y && o.y < targetBottom
  )
  // 按 y 升序处理：每个部件 y 必须 >= targetBottom
  conflicts.sort((a, b) => a.y - b.y)
  for (const o of conflicts) {
    o.y = targetBottom
  }
}

// 应用 w/h 调整（编辑 Dialog 用）：如果新尺寸变大了，把下方被挡的部件下移
function applyResizeShift(target, newW, newH) {
  const oldH = target.h
  target.w = newW
  target.h = newH
  if (newH > oldH) applyCascadeShift(target)
}

// 部件绝对定位样式：基于 canvas 实际像素宽度计算（避免 calc 百分比 + px 错位）
const canvasW = ref(0)
let resizeObs = null
function setupResizeObserver() {
  if (!canvasRef.value) return
  if (resizeObs) resizeObs.disconnect()
  resizeObs = new ResizeObserver(([entry]) => {
    canvasW.value = entry.contentRect.width
  })
  resizeObs.observe(canvasRef.value)
}

function cellStyle(w) {
  // 初始（canvas 还没测量）给个合理 fallback，避免第一帧错位
  const W = canvasW.value || 1280
  const colW = (W - (COLS - 1) * GAP) / COLS
  const left = (w.x || 0) * (colW + GAP)
  const width = (w.w || 6) * colW + ((w.w || 6) - 1) * GAP
  const top = (w.y || 0) * (ROW_H + GAP)
  const height = rowsToPx(w.h || 3)
  return {
    position: 'absolute',
    left: left + 'px',
    top: top + 'px',
    width: width + 'px',
    height: height + 'px'
  }
}

// 画布整体高度（容纳所有部件 + 底部空白）
const canvasHeight = computed(() => {
  const maxY = widgets.value.reduce((m, w) => Math.max(m, (w.y || 0) + (w.h || 3)), 0)
  return Math.max(400, rowsToPx(maxY) + 80)
})
</script>

<style scoped>
.dashboard { height: 100%; }
.dash-topbar {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 16px;
}
.db-left { display: flex; align-items: baseline; gap: 12px; }
.db-title { margin: 0; font-size: 20px; color: var(--app-text, #303133); }
.db-hint { color: #909399; font-size: 13px; }

/* ========== 自由画布：12 列网格 + 绝对定位 ========== */
.dash-canvas {
  position: relative;
  width: 100%;
  min-height: 400px;
  /* 编辑模式显示网格背景，辅助对齐 */
  background-image:
    linear-gradient(to right, rgba(64,158,255,0.06) 1px, transparent 1px);
  background-size: calc((100% - 16px) / 12) 92px;
}
.dash-canvas.editing {
  background-color: var(--app-bg-soft, #fafbfc);
  border: 1px dashed var(--app-border, #d9dde4);
  border-radius: 6px;
}
.dw-cell {
  /* cell 自身占 widget 的 box，DashboardWidget 撑满 */
  display: flex;
}
.dw-cell > * { flex: 1; width: 100%; }
.dw-cell.dragging { opacity: 0.4; }
.dash-empty { padding: 40px 0; }

/* 拖拽中占位框（半透明预览放置位置） */
.dw-placeholder {
  position: absolute;
  background: rgba(64,158,255,0.18);
  border: 2px dashed var(--app-accent, #409eff);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  color: var(--app-accent, #409eff);
  font-size: 13px;
  font-weight: 600;
  transition: left 0.15s, top 0.15s, width 0.15s, height 0.15s;
  z-index: 10;
}

.form-hint { margin-left: 10px; color: #909399; font-size: 12px; }
</style>
