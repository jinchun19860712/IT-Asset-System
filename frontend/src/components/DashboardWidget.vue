<template>
  <div class="dash-widget" :class="{ editing }" :style="widgetStyle">
    <div class="dw-head">
      <div class="dw-head-left">
        <!-- 拖拽手柄必须用 div + draggable="true" —— SVG 元素不响应 HTML5 dragstart；
             同时加 class="drag-handle-global" 让父组件（Dashboard.vue）跨组件 scoped 也能匹配到 -->
        <div v-if="editing"
             class="drag-handle drag-handle-global"
             draggable="true"
             title="拖动排序"
        >
          <el-icon><Rank /></el-icon>
        </div>
        <span class="dw-title">{{ widget.title || defaultTitle }}</span>
      </div>
      <div class="dw-ops">
        <el-tag v-if="widget.config.refresh && widget.config.refresh !== 'manual'" size="small" effect="plain" class="dw-refresh">
          {{ refreshText }}
        </el-tag>
        <el-button v-if="!editing" size="small" text @click="loadData">
          <el-icon><Refresh /></el-icon>
        </el-button>
        <template v-if="editing">
          <el-button size="small" text @click="$emit('edit', widget)">
            <el-icon><Setting /></el-icon>
          </el-button>
          <el-button size="small" text type="danger" @click="$emit('remove', widget)">
            <el-icon><Close /></el-icon>
          </el-button>
        </template>
      </div>
    </div>

    <div class="dw-body">
      <div :key="fadeKey" class="dw-content">
      <!-- 设备看板 -->
      <template v-if="widget.type === 'device-watch'">
        <el-table :data="tableRows" size="small" height="100%" style="width:100%" empty-text="无设备">
          <el-table-column
            v-for="col in tableColumns"
            :key="col.key"
            :label="col.label"
            :prop="col.key"
            show-overflow-tooltip
            :min-width="col.minWidth || 100"
          >
            <template #default="{ row }">
              <span v-if="col.key === 'status_name'">
                <el-tag size="small" :color="row._statusColor" effect="dark" style="color:#fff;border:none">
                  {{ row.status_name || '—' }}
                </el-tag>
              </span>
              <span v-else-if="col.snmp">
                {{ row._metrics[col.key] != null ? row._metrics[col.key] + (col.unit ? ' ' + col.unit : '') : '—' }}
              </span>
              <span v-else>{{ row[col.key] != null && row[col.key] !== '' ? row[col.key] : '—' }}</span>
            </template>
          </el-table-column>
        </el-table>
      </template>

      <!-- SNMP 监控项 -->
      <template v-else-if="widget.type === 'snmp-metrics'">
        <el-table :data="snmpRows" size="small" height="100%" style="width:100%" empty-text="无数据">
          <el-table-column
            v-for="col in snmpColumns"
            :key="col.key"
            :label="col.label"
            show-overflow-tooltip
            :min-width="col.minWidth || 100"
          >
            <template #default="{ row }">
              <span v-if="col.metric">
                {{ row[col.key] != null ? row[col.key] + (col.unit ? ' ' + col.unit : '') : '—' }}
              </span>
              <span v-else>{{ row[col.key] != null && row[col.key] !== '' ? row[col.key] : '—' }}</span>
            </template>
          </el-table-column>
        </el-table>
      </template>

      <!-- 设备状态分布（重做 UI：环图 + 中心总数 + 分两列图例） -->
      <template v-else-if="widget.type === 'status-summary'">
        <div class="status-summary">
          <div class="ss-pie-wrap">
            <MiniChart type="pie" :data="pieData" height="180px" />
            <div class="ss-center">
              <div class="ss-total">{{ totalDevices }}</div>
              <div class="ss-total-label">设备总数</div>
            </div>
          </div>
          <div class="ss-legend">
            <div v-for="d in pieData" :key="d.name" class="ss-legend-item">
              <span class="ss-dot" :style="{ background: d.color }"></span>
              <span class="ss-name" :title="d.name">{{ d.name || '未分类' }}</span>
              <span class="ss-val">{{ d.value }}</span>
              <span class="ss-pct">{{ pct(d.value) }}%</span>
            </div>
            <el-empty v-if="!pieData.length" description="暂无数据" :image-size="60" />
          </div>
        </div>
      </template>

      <!-- 资产分类统计（SVG 横向条形图，自适应高度和宽度，文字不拉伸） -->
      <template v-else-if="widget.type === 'asset-category'">
        <div class="ac-chart" v-if="categoryData.length">
          <div class="ac-info">
            总计 <strong>{{ categoryTotal }}</strong> 台设备 · {{ categoryData.length }} 个分类
          </div>
          <div
            v-for="(cat, i) in categoryData"
            :key="cat.name"
            class="ac-row"
          >
            <div class="ac-label" :title="cat.name">{{ cat.name }}</div>
            <div class="ac-bar-bg">
              <div
                class="ac-bar-fill"
                :style="{
                  width: cat.value ? (cat.value / categoryMax * 100) + '%' : '0%',
                  background: PALETTE[i % PALETTE.length]
                }"
              ></div>
              <span class="ac-val">{{ cat.value }}</span>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无设备数据" :image-size="80" />
      </template>

      <!-- 端口流量（SVG 自绘折线图，自适应容器大小） -->
      <template v-else-if="widget.type === 'port-traffic'">
        <div class="traffic-meta">
          <el-tag size="small" effect="plain">{{ deviceName || '设备' }} · {{ widget.config.portName || '—' }}</el-tag>
          <el-tag size="small" type="warning" effect="plain">模拟流量（演示）</el-tag>
          <span class="traffic-now">
            入 <strong>{{ lastIn }}</strong> / 出 <strong>{{ lastOut }}</strong>
          </span>
        </div>
        <div class="traffic-chart" v-if="trafficSeries.length">
          <!-- 简洁 SVG 图例 -->
          <div class="traffic-legend">
            <span v-for="s in trafficSeries" :key="s.name" class="traffic-legend-item">
              <span class="traffic-legend-dot" :style="{ background: s.color }"></span>
              {{ s.name }}
            </span>
          </div>
          <!-- SVG 自绘双折线图：viewBox + preserveAspectRatio 让文字/几何不被拉伸 -->
          <svg
            class="traffic-svg"
            :viewBox="`0 0 ${TRAFFIC_W} ${TRAFFIC_H}`"
            preserveAspectRatio="none"
          >
            <!-- 横向网格线（4 等分） -->
            <g class="traffic-grid">
              <line v-for="g in 4" :key="g"
                :x1="0" :x2="TRAFFIC_W"
                :y1="(TRAFFIC_H * g) / 4" :y2="(TRAFFIC_H * g) / 4"
                stroke="rgba(127,127,127,0.18)" stroke-width="1" stroke-dasharray="4,4"
              />
            </g>
            <!-- 双折线（用 path 平滑绘制） -->
            <g v-for="(s, si) in trafficSeries" :key="s.name">
              <polyline
                fill="none"
                :stroke="s.color"
                stroke-width="2"
                stroke-linejoin="round"
                stroke-linecap="round"
                :points="buildPathPoints(s.data, si)"
              />
            </g>
          </svg>
        </div>
        <el-empty v-else description="暂无流量数据" :image-size="80" />
      </template>
      </div>
      <!-- /dw-content -->
    </div>

    <!-- 编辑模式：4 角 + 4 边缩放手柄（支持任意方向拖拽） -->
    <template v-if="editing">
      <!-- 四角：nwe / ne / sw / se -->
      <div class="rh rh-corner rh-nw" data-dir="nw" @mousedown.stop="$emit('resize-start', $event, 'nw')"></div>
      <div class="rh rh-corner rh-ne" data-dir="ne" @mousedown.stop="$emit('resize-start', $event, 'ne')"></div>
      <div class="rh rh-corner rh-sw" data-dir="sw" @mousedown.stop="$emit('resize-start', $event, 'sw')"></div>
      <div class="rh rh-corner rh-se" data-dir="se" @mousedown.stop="$emit('resize-start', $event, 'se')">
        <el-icon><BottomRight /></el-icon>
      </div>
      <!-- 四边：n / e / s / w -->
      <div class="rh rh-edge rh-n" data-dir="n" @mousedown.stop="$emit('resize-start', $event, 'n')"></div>
      <div class="rh rh-edge rh-e" data-dir="e" @mousedown.stop="$emit('resize-start', $event, 'e')"></div>
      <div class="rh rh-edge rh-s" data-dir="s" @mousedown.stop="$emit('resize-start', $event, 's')"></div>
      <div class="rh rh-edge rh-w" data-dir="w" @mousedown.stop="$emit('resize-start', $event, 'w')"></div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { Refresh, Setting, Close, Rank, BottomRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import MiniChart from './MiniChart.vue'
import { deviceApi, snmpApi } from '../api/index.js'

const props = defineProps({
  widget: { type: Object, required: true },
  editing: { type: Boolean, default: false },
  dragging: { type: Boolean, default: false },
  resizing: { type: Boolean, default: false }
})
const emit = defineEmits(['remove', 'edit', 'resize-start'])

const PALETTE = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#9254DE', '#13C2C2', '#EB2F96', '#909399']
const REFRESH_MS = { realtime: 2000, '5s': 5000, '10s': 10000, '30s': 30000, manual: 0 }

const fadeKey = ref(0) // 数据批次号，配合 cross-fade 让切换更平滑
const loading = ref(false)
const devices = ref([])
const metricMap = ref({}) // device_id -> { metric_name: value }
const deviceNameMap = ref({})
const metricMeta = ref({}) // metric_name -> { unit }

const widgetStyle = computed(() => ({
  // 真实高度由父 cell 决定（基于网格 h 行数）；这里只确保最小值
  width: '100%',
  height: '100%',
  opacity: props.dragging ? 0.5 : 1
}))

const defaultTitle = computed(() => ({
  'device-watch': '设备看板',
  'snmp-metrics': 'SNMP 监控项',
  'status-summary': '设备状态分布',
  'asset-category': '资产分类统计',
  'port-traffic': '端口流量'
}[props.widget.type] || '部件'))

const refreshText = computed(() => {
  const r = props.widget.config.refresh
  return r === 'realtime' ? '实时刷新' : r === 'manual' ? '手动' : `刷新 ${r}`
})

// —— 设备看板列 ——
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
const tableColumns = computed(() => {
  const fields = props.widget.config.fields || []
  const cols = []
  for (const f of fields) {
    if (f.startsWith('snmp:')) {
      const name = f.slice(5)
      cols.push({ key: f, label: name, snmp: true })
    } else {
      const def = STATIC_FIELDS.find(s => s.key === f)
      if (def) cols.push({ key: def.key, label: def.label })
    }
  }
  return cols
})
const tableRows = computed(() => {
  return (devices.value || []).map(d => ({
    ...d,
    _metrics: metricMap.value[d.id] || {},
    _statusColor: d.status_color || '#909399'
  }))
})

// —— SNMP 监控项 ——
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
const snmpColumns = computed(() => {
  const info = (props.widget.config.infoFields || []).map(k => {
    const def = INFO_FIELDS.find(f => f.key === k)
    return def ? { key: k, label: def.label } : { key: k, label: k }
  })
  const metrics = (props.widget.config.metricNames || []).map(name => ({
    key: 'm_' + name,
    label: name + (metricMeta.value[name]?.unit ? ` (${metricMeta.value[name].unit})` : ''),
    metric: true
  }))
  return [...info, ...metrics]
})
const snmpRows = computed(() => {
  return (devices.value || []).map(d => {
    const row = {}
    for (const k of (props.widget.config.infoFields || [])) row[k] = d[k]
    for (const name of (props.widget.config.metricNames || [])) {
      const val = metricMap.value[d.id]?.[name]
      row['m_' + name] = val != null ? val : '—'
    }
    return row
  })
})

// —— 饼图数据（状态分布）——
const pieData = computed(() => {
  const map = {}
  const colorMap = {}
  for (const d of devices.value) {
    const k = d.status_name || '未分类'
    map[k] = (map[k] || 0) + 1
    if (d.status_color) colorMap[k] = d.status_color
  }
  const entries = Object.entries(map)
  return entries.map(([name, value], i) => ({
    name, value, color: colorMap[name] || PALETTE[i % PALETTE.length]
  }))
})
const pct = (v) => {
  const total = pieData.value.reduce((s, d) => s + d.value, 0)
  return total ? Math.round((v / total) * 100) : 0
}

// —— 资产分类数据（按 asset_folder_name 分组排序）——
const categoryData = computed(() => {
  const map = {}
  for (const d of devices.value) {
    const k = d.asset_folder_name || '未分类'
    map[k] = (map[k] || 0) + 1
  }
  return Object.entries(map)
    .sort((a, b) => b[1] - a[1])
    .map(([name, value]) => ({ name, value }))
})
const categoryTotal = computed(() => categoryData.value.reduce((s, d) => s + d.value, 0))
const categoryMax = computed(() => Math.max(1, ...categoryData.value.map(d => d.value)))

const totalDevices = computed(() => pieData.value.reduce((s, d) => s + d.value, 0))

// —— 端口流量（模拟）——
// SVG viewBox：用固定坐标系展示，容器缩放时只缩放像素不拉伸
const TRAFFIC_W = 600
const TRAFFIC_H = 200
const trafficSeries = ref([])
const trafficLabels = ref([])
const lastIn = ref('—')
const lastOut = ref('—')
const deviceName = computed(() => deviceNameMap.value[props.widget.config.deviceId] || '')

// 自绘 SVG 路径：根据 series.data 转成 (x, y) 坐标点串
function buildPathPoints(data, seriesIdx) {
  if (!data || !data.length) return ''
  const len = data.length
  const vmax = Math.max(...data, 1)
  const pts = []
  for (let i = 0; i < len; i++) {
    const x = (i / Math.max(1, len - 1)) * TRAFFIC_W
    // 上方折线（入方向）占上半部分；下方（出方向）占下半部分 —— 双折线视觉不重叠
    const baseY = seriesIdx === 0 ? TRAFFIC_H * 0.45 : TRAFFIC_H * 0.95
    const ampY = TRAFFIC_H * 0.35
    const y = baseY - (data[i] / vmax) * ampY
    pts.push(`${x.toFixed(2)},${y.toFixed(2)}`)
  }
  return pts.join(' ')
}

function genTraffic() {
  const dev = Number(props.widget.config.deviceId) || 1
  const portName = props.widget.config.portName || 'port1'
  const seed = dev * 31 + portName.split('').reduce((a, c) => a + c.charCodeAt(0), 0)
  const baseIn = 200 + (seed % 600)        // Mbps
  const ampIn = 80 + (seed % 120)
  const baseOut = 60 + (seed % 200)
  const ampOut = 30 + (seed % 80)
  const N = 30
  const rms = REFRESH_MS[props.widget.config.refresh] || 5000
  const step = Math.max(1, rms / 2000)
  const now = Date.now() / 1000
  const inData = [], outData = [], labels = []
  for (let i = 0; i < N; i++) {
    const t = now - (N - 1 - i) * step
    const noise = (Math.sin(t * 3.3 + seed) + Math.sin(t * 1.7)) * 0.5
    const vin = Math.max(0, baseIn + ampIn * Math.sin(t * 0.6 + seed) + ampIn * 0.2 * noise)
    const vout = Math.max(0, baseOut + ampOut * Math.sin(t * 0.5 + seed + 1) + ampOut * 0.2 * noise)
    inData.push(Math.round(vin))
    outData.push(Math.round(vout))
    labels.push('')
  }
  trafficSeries.value = [
    { name: '入方向', color: '#409EFF', data: inData },
    { name: '出方向', color: '#67C23A', data: outData }
  ]
  trafficLabels.value = labels
  lastIn.value = (inData[inData.length - 1] / 1000).toFixed(2) + ' Gbps'
  lastOut.value = (outData[outData.length - 1] / 1000).toFixed(2) + ' Gbps'
}

// —— 数据加载（后台静默：保留旧数据，fetch 不闪 loading，
//                   返回后在 requestAnimationFrame 中应用，配合 fadeKey 做交叉淡入）——
async function applyWithFade(updater) {
  // 应用新数据 + 切换 fadeKey，触发 cross-fade CSS 过渡
  fadeKey.value++
  await nextTick()
  updater()
  requestAnimationFrame(() => { fadeKey.value++ })
}

async function loadData(signal) {
  try {
    loading.value = true
    if (props.widget.type === 'port-traffic') {
      // 端口流量是本地模拟，不需要远程请求
      genTraffic()
      const res = await deviceApi.getList({ page: 1, page_size: 300 })
      if (res.code === 0) {
        const m = {}
        for (const d of (res.data.items || [])) m[d.id] = d.name
        deviceNameMap.value = m
      }
      return
    }
    if (props.widget.type === 'device-watch' || props.widget.type === 'snmp-metrics') {
      const cfg = props.widget.config
      const params = { page: 1, page_size: 1000 }
      // scope=manual/deviceIds 直接走 cfg.deviceIds
      if (cfg.scope === 'asset' && cfg.assetFolderIds && cfg.assetFolderIds.length) params.asset_folder_ids = cfg.assetFolderIds.join(',')
      else if (cfg.scope === 'asset' && cfg.assetFolderId) params.asset_folder_id = cfg.assetFolderId
      if (cfg.scope === 'org' && cfg.orgFolderIds && cfg.orgFolderIds.length) params.folder_ids = cfg.orgFolderIds.join(',')
      else if (cfg.scope === 'org' && cfg.orgFolderId) params.folder_id = cfg.orgFolderId
      if (cfg.scope === 'supplier' && cfg.suppliers && cfg.suppliers.length) params.suppliers = cfg.suppliers.join(',')
      else if (cfg.scope === 'supplier' && cfg.supplier) params.supplier = cfg.supplier
      if (cfg.scope === 'device_type' && cfg.deviceTypes && cfg.deviceTypes.length) params.device_types = cfg.deviceTypes.join(',')
      else if (cfg.scope === 'device_type' && cfg.deviceType) params.device_type = cfg.deviceType
      const [devRes, metRes] = await Promise.all([
        deviceApi.getList(params),
        snmpApi.getAllDeviceMetrics()
      ])
      let items = devRes.code === 0 ? (devRes.data.items || []) : []
      if (cfg.scope === 'manual' && cfg.deviceIds && cfg.deviceIds.length) {
        const set = new Set(cfg.deviceIds)
        items = items.filter(d => set.has(d.id))
      }
      if (props.widget.type === 'snmp-metrics' && cfg.deviceIds && cfg.deviceIds.length) {
        const set = new Set(cfg.deviceIds)
        items = items.filter(d => set.has(d.id))
      }
      const mm = {}
      const meta = {}
      if (metRes.code === 0) {
        for (const [did, list] of Object.entries(metRes.data || {})) {
          const inner = {}
          for (const mv of list) {
            inner[mv.metric_name] = mv.value
            if (!meta[mv.metric_name]) meta[mv.metric_name] = { unit: mv.unit }
          }
          mm[did] = inner
        }
      }
      // 后台静默更新：不显示 loading，等数据备好再切
      await applyWithFade(() => {
        devices.value = items
        metricMap.value = mm
        metricMeta.value = meta
      })
    } else {
      // status-summary / asset-category
      const res = await deviceApi.getList({ page: 1, page_size: 1000 })
      if (res.code === 0) {
        await applyWithFade(() => {
          devices.value = res.data.items || []
        })
      }
    }
  } catch (e) {
    console.error('widget loadData failed:', e)
  } finally {
    loading.value = false
  }
}

// 把 snmp unit 注入列定义（用于展示单位）
watch(tableColumns, () => {
  for (const col of tableColumns.value) {
    if (col.snmp) {
      for (const [name, meta] of Object.entries(metricMeta.value)) {
        if ('snmp:' + name === col.key) { col.unit = meta.unit; break }
      }
    }
  }
}, { deep: true })

// —— 刷新定时器 ——
let timer = null
function setupTimer() {
  if (timer) { clearInterval(timer); timer = null }
  const ms = REFRESH_MS[props.widget.config.refresh] || 0
  if (ms > 0) timer = setInterval(loadData, ms)
}
watch(() => props.widget.config.refresh, setupTimer)
watch(() => props.widget, () => { loadData(); setupTimer() }, { deep: true })

onMounted(() => { loadData(); setupTimer() })
onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
  if (currentAbort) currentAbort.abort()
})
</script>

<style scoped>
.dash-widget {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--app-panel, #fff);
  border: 1px solid var(--app-border, #e4e7ed);
  border-radius: 8px;
  overflow: hidden;
  position: relative;
}
.dash-widget.editing { border-style: dashed; }
.dw-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 12px; border-bottom: 1px solid var(--app-border, #e4e7ed);
}
.dw-head-left { display: flex; align-items: center; gap: 8px; }
.drag-handle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  margin-right: 2px;
  border-radius: 4px;
  cursor: grab;
  color: var(--app-text-secondary, #909399);
  user-select: none;
  transition: background 0.12s, color 0.12s;
}
.drag-handle:hover { background: var(--app-bg-soft, #f5f5f5); color: var(--app-accent, #409eff); }
.drag-handle:active { cursor: grabbing; }
.dw-title { font-weight: 600; font-size: 14px; color: var(--app-text, #303133); }
.dw-ops { display: flex; align-items: center; gap: 2px; }
.dw-refresh { margin-right: 4px; }
.dw-body { flex: 1; padding: 10px 12px; min-height: 0; overflow: auto; position: relative; }
/* 后台静默刷新：dw-content 用 fadeKey 控制交叉淡入淡出，前台不再闪 loading */
.dw-content {
  width: 100%;
  height: 100%;
  animation: fadeIn 0.35s ease;
}
@keyframes fadeIn {
  from { opacity: 0.35; }
  to   { opacity: 1; }
}

/* ========== 设备状态分布 ========== */
.status-summary {
  display: grid;
  grid-template-columns: minmax(140px, 180px) 1fr;
  align-items: stretch;
  gap: 16px;
  height: 100%;
  min-height: 0;
}
.ss-pie-wrap {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 140px;
}
.ss-pie-wrap :deep(.mini-chart) { width: 100%; }
.ss-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}
.ss-total {
  font-size: 26px;
  font-weight: 700;
  color: var(--app-text, #303133);
  line-height: 1.1;
}
.ss-total-label {
  font-size: 12px;
  color: var(--app-text-secondary, #909399);
  margin-top: 2px;
}
.ss-legend {
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow-y: auto;
  padding: 4px 0;
  min-height: 0;
}
.ss-legend-item {
  display: grid;
  grid-template-columns: 12px 1fr auto auto;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  padding: 6px 8px;
  border-radius: 6px;
  transition: background 0.12s;
}
.ss-legend-item:hover { background: var(--app-bg-soft, #fafafa); }
.ss-dot {
  width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0;
}
.ss-name {
  color: var(--app-text, #303133);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0;
}
.ss-val {
  font-weight: 600;
  color: var(--app-text, #303133);
  text-align: right;
}
.ss-pct {
  font-size: 12px;
  color: var(--app-text-secondary, #909399);
  text-align: right;
  min-width: 38px;
}

/* ========== 资产分类（横向条形图） ========== */
.ac-chart {
  display: flex;
  flex-direction: column;
  gap: 8px;
  height: 100%;
  overflow-y: auto;
}
.ac-info {
  font-size: 12px;
  color: var(--app-text-secondary, #909399);
  margin-bottom: 4px;
}
.ac-info strong { color: var(--app-text, #303133); font-size: 14px; }
.ac-row {
  display: grid;
  grid-template-columns: 100px 1fr;
  align-items: center;
  gap: 10px;
}
.ac-label {
  font-size: 13px;
  color: var(--app-text, #303133);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  text-align: right;
}
.ac-bar-bg {
  position: relative;
  height: 18px;
  background: var(--app-bg-soft, #f5f5f5);
  border-radius: 4px;
  overflow: hidden;
}
.ac-bar-fill {
  position: absolute;
  left: 0; top: 0; bottom: 0;
  border-radius: 4px;
  transition: width 0.4s ease;
}
.ac-val {
  position: absolute;
  right: 6px; top: 50%;
  transform: translateY(-50%);
  font-size: 12px;
  font-weight: 600;
  color: var(--app-text, #303133);
  pointer-events: none;
}

/* ========== 端口流量 ========== */
.traffic-meta {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 6px; flex-wrap: wrap;
}
.traffic-now {
  font-size: 12px;
  color: var(--app-text-secondary, #909399);
}
.traffic-now strong { color: var(--app-accent, #409eff); }
.traffic-chart {
  display: flex;
  flex-direction: column;
  height: calc(100% - 32px);
  min-height: 0;
}
.traffic-legend {
  display: flex; gap: 14px;
  font-size: 12px;
  color: var(--app-text-secondary, #909399);
  margin-bottom: 4px;
}
.traffic-legend-item { display: flex; align-items: center; gap: 4px; }
.traffic-legend-dot {
  width: 10px; height: 10px; border-radius: 2px;
}
.traffic-svg {
  flex: 1;
  width: 100%;
  height: 100%;
  min-height: 120px;
  display: block;
}
/* ========== 缩放手柄：4 角 + 4 边 ========== */
.rh {
  position: absolute;
  z-index: 5;
  user-select: none;
  background: transparent;
  transition: background 0.15s;
}
.rh:hover { background: rgba(64, 158, 255, 0.18); }
/* 4 角：18×18 */
.rh-corner { width: 18px; height: 18px; }
.rh-nw { top: 0;    left: 0;   cursor: nwse-resize; border-radius: 0 0 6px 0; }
.rh-ne { top: 0;    right: 0;  cursor: nesw-resize; border-radius: 0 0 0 6px; }
.rh-sw { bottom: 0; left: 0;   cursor: nesw-resize; border-radius: 0 6px 0 0; }
.rh-se { bottom: 0; right: 0;  cursor: nwse-resize; border-radius: 6px 0 0 0; }
.rh-se:hover { color: var(--app-accent, #409eff); }
/* 4 边：宽度/高度 8px */
.rh-edge { background: transparent; }
.rh-n    { top: 0;    left: 18px; right: 18px; height: 6px;  cursor: ns-resize; }
.rh-s    { bottom: 0; left: 18px; right: 18px; height: 6px;  cursor: ns-resize; }
.rh-e    { right: 0;  top: 18px; bottom: 18px; width: 6px;   cursor: ew-resize; }
.rh-w    { left: 0;   top: 18px; bottom: 18px; width: 6px;   cursor: ew-resize; }
</style>
