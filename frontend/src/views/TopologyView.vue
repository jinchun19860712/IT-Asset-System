<template>
  <div class="topology-view">
    <!-- ============ 工具栏 ============ -->
    <div class="topo-toolbar">
      <div class="tb-left">
        <span class="tb-title">网络拓扑图</span>
        <el-tag v-if="props.selectedFolder" size="small" type="info" effect="plain">
          {{ props.selectedFolder.name }}
        </el-tag>
        <el-tag v-else size="small" type="info" effect="plain">全部设备</el-tag>
        <span class="tb-sub">设备 <b>{{ rawNodes.length }}</b> 台</span>
        <span class="tb-sub">连线 <b>{{ drawableLinks.length }}</b> 条</span>
        <span class="tb-sub">层级 <b>{{ layerCount }}</b> 层</span>
        <span v-if="isolatedCount" class="tb-sub">未连接 <b>{{ isolatedCount }}</b> 台</span>
      </div>
      <div class="tb-right">
        <span class="zoom-text">{{ scalePercent }}%</span>
        <el-button-group>
          <el-button size="small" title="放大" @click="zoomIn">
            <el-icon><ZoomIn /></el-icon>
          </el-button>
          <el-button size="small" title="缩小" @click="zoomOut">
            <el-icon><ZoomOut /></el-icon>
          </el-button>
        </el-button-group>
        <el-button size="small" title="重置视图" @click="resetView">
          <el-icon><RefreshLeft /></el-icon> 重置
        </el-button>
        <el-button size="small" title="适应窗口" @click="fitView">
          <el-icon><Aim /></el-icon> 适应
        </el-button>
        <el-button type="primary" size="small" title="刷新数据" @click="loadData">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <!-- ============ 画布 ============ -->
    <div ref="canvasRef" class="topo-canvas" v-loading="loading">
      <el-empty
        v-if="!loading && !rawNodes.length"
        description="当前范围内暂无设备，无法生成拓扑图"
        :image-size="120"
      />

      <svg
        v-else
        ref="svgRef"
        class="topo-svg"
        :class="{ panning: isPanning }"
        @wheel.prevent="onWheel"
        @mousedown="onBgMouseDown"
        @click="onBgClick"
      >
        <g :transform="`translate(${tx},${ty}) scale(${scale})`">
          <!-- 分层标签 -->
          <g class="layer-marks">
            <text
              v-for="lb in layerLabels"
              :key="lb.key"
              :x="lb.x"
              :y="lb.y"
              class="layer-label"
            >{{ lb.text }}</text>
          </g>

          <!-- 孤立节点分隔线 -->
          <g v-if="isoDivider">
            <line
              :x1="24"
              :y1="isoDivider.y"
              :x2="canvasW - 24"
              :y2="isoDivider.y"
              stroke="#dcdfe6"
              stroke-width="1"
              stroke-dasharray="5 5"
            />
            <text :x="30" :y="isoDivider.y - 8" class="divider-label">
              {{ isoDivider.text }}
            </text>
          </g>

          <!-- 连线层（先画线，节点覆盖其上） -->
          <g class="links-layer">
            <g
              v-for="lk in drawableLinks"
              :key="lk.key"
              :opacity="linkOpacity(lk)"
              class="topo-link"
            >
              <path
                v-for="(d, i) in lk.paths"
                :key="i"
                :d="d"
                fill="none"
                :stroke="lk.style.color"
                :stroke-width="lk.style.width"
                :stroke-dasharray="lk.style.dash"
                stroke-linecap="round"
              />
              <!-- 加宽的透明命中区，方便鼠标悬停 -->
              <path
                class="link-hit"
                :d="lk.basePath"
                fill="none"
                stroke="rgba(0,0,0,0)"
                stroke-width="14"
                @mouseenter="onLinkEnter(lk, $event)"
                @mousemove="onLinkMove($event)"
                @mouseleave="onLinkLeave"
              />
              <!-- 中点标签：白色底块保证在连线上可读 -->
              <g v-if="lk.label" class="link-label">
                <rect
                  :x="lk.midX - lk.labelW / 2"
                  :y="lk.midY - 9"
                  :width="lk.labelW"
                  height="18"
                  rx="4"
                  fill="#ffffff"
                  fill-opacity="0.92"
                  :stroke="lk.style.color"
                  stroke-width="0.8"
                />
                <text
                  :x="lk.midX"
                  :y="lk.midY + 4"
                  text-anchor="middle"
                  class="link-label-text"
                >{{ lk.label }}</text>
              </g>
            </g>
          </g>

          <!-- 节点层 -->
          <g class="nodes-layer">
            <g
              v-for="nd in layoutNodes"
              :key="nd.id"
              class="topo-node"
              :opacity="nodeOpacity(nd.id)"
              @click.stop="onNodeClick(nd)"
            >
              <rect
                :x="nd.x"
                :y="nd.y"
                :width="NODE_W"
                :height="NODE_H"
                rx="8"
                ry="8"
                :fill="nd.style.fill"
                :stroke="selectedId === nd.id ? '#409eff' : nd.style.stroke"
                :stroke-width="selectedId === nd.id ? 2.5 : 1.2"
              />
              <!-- 状态色条 -->
              <rect
                :x="nd.x + 6"
                :y="nd.y + 9"
                width="4"
                :height="NODE_H - 18"
                rx="2"
                :fill="nd.data.status_color || '#909399'"
              />
              <text :x="nd.x + 18" :y="nd.y + 23" class="node-name" :fill="nd.style.text">
                {{ nd.nameText }}
              </text>
              <text :x="nd.x + 18" :y="nd.y + 41" class="node-ip">
                {{ nd.ipText }}
              </text>
              <text
                :x="nd.x + NODE_W - 8"
                :y="nd.y + 41"
                text-anchor="end"
                class="node-type"
                :fill="nd.style.text"
              >
                {{ nd.typeText }}
              </text>
            </g>
          </g>
        </g>
      </svg>

      <!-- 连线悬停提示（自绘） -->
      <div
        v-if="hoverTip.show"
        class="link-tip"
        :style="{ left: hoverTip.x + 14 + 'px', top: hoverTip.y + 14 + 'px' }"
      >
        <div class="tip-row tip-main">{{ hoverTip.title }}</div>
        <div class="tip-row">{{ hoverTip.ports }}</div>
        <div v-if="hoverTip.extra" class="tip-row tip-sub">{{ hoverTip.extra }}</div>
      </div>

      <!-- 图例 -->
      <div v-if="rawNodes.length" class="legend">
        <div class="legend-title">连线类型</div>
        <div class="legend-grid">
          <div v-for="lg in LEGEND_LINKS" :key="lg.name" class="legend-item">
            <svg width="34" height="12" class="legend-svg">
              <template v-if="lg.double">
                <line x1="2" y1="4" x2="32" y2="4" :stroke="lg.color" :stroke-width="lg.width" />
                <line x1="2" y1="8" x2="32" y2="8" :stroke="lg.color" :stroke-width="lg.width" />
              </template>
              <line
                v-else
                x1="2"
                y1="6"
                x2="32"
                y2="6"
                :stroke="lg.color"
                :stroke-width="lg.width"
                :stroke-dasharray="lg.dash"
              />
            </svg>
            <span class="legend-text">{{ lg.name }}</span>
          </div>
        </div>
        <div class="legend-title">设备类型</div>
        <div class="legend-grid">
          <div v-for="dv in LEGEND_DEVICES" :key="dv.label" class="legend-item">
            <span class="legend-chip" :style="{ background: dv.fill, borderColor: dv.stroke }"></span>
            <span class="legend-text">{{ dv.label }}</span>
          </div>
        </div>
        <div class="legend-tip">滚轮缩放 · 拖拽平移 · 点击节点查看详情</div>
      </div>
    </div>

    <!-- ============ 设备详情抽屉 ============ -->
    <el-drawer
      v-model="drawerVisible"
      :title="selectedNode ? selectedNode.name : '设备详情'"
      size="380px"
      :with-header="true"
    >
      <div v-if="selectedNode" class="detail-body">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="设备名称">
            {{ selectedNode.name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="设备类型">
            {{ selectedNode.device_type || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="品牌型号">
            {{ brandModelText }}
          </el-descriptions-item>
          <el-descriptions-item label="IP 地址">
            {{ selectedNode.ip_address || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag
              v-if="selectedNode.status_name"
              size="small"
              effect="plain"
              :style="{ color: selectedNode.status_color, borderColor: selectedNode.status_color }"
            >
              {{ selectedNode.status_name }}
            </el-tag>
            <span v-else>-</span>
          </el-descriptions-item>
          <el-descriptions-item label="所在路径">
            {{ selectedNode.folder_full_path || selectedNode.folder_name || '-' }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="detail-sub-title">
          连线情况
          <span class="detail-count">{{ selectedConnections.length }} 条</span>
        </div>

        <el-empty
          v-if="!selectedConnections.length"
          description="该设备暂无连线"
          :image-size="60"
        />

        <div v-for="(cn, idx) in selectedConnections" :key="idx" class="conn-card">
          <div class="conn-head">
            <span class="conn-dot" :style="{ background: cn.color }"></span>
            <span class="conn-peer">{{ cn.peerName }}</span>
            <el-tag size="small" effect="dark" type="info">{{ cn.typeName }}</el-tag>
          </div>
          <div class="conn-ports">
            <span class="port-tag">{{ cn.localPort || '未知端口' }}</span>
            <span class="conn-arrow">&lt;-&gt;</span>
            <span class="port-tag">{{ cn.peerPort || '未知端口' }}</span>
          </div>
          <div v-if="cn.label" class="conn-label">{{ cn.label }}</div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch, inject } from 'vue'
import { ElMessage } from 'element-plus'
import { ZoomIn, ZoomOut, Refresh, RefreshLeft, Aim } from '@element-plus/icons-vue'
import { topologyApi } from '../api/index.js'

// 选中目录由 Layout.vue 通过 provide 注入（避免 router-view 透传 prop 污染导致不切换组件）
const props = defineProps({
  // 兼容：直接传 prop 时仍可工作（fallback）
  selectedFolder: { type: Object, default: null }
})
const injectedFolder = inject('selectedFolder', null)
const selectedFolder = computed(() => injectedFolder?.value ?? props.selectedFolder)
defineExpose({})

/* ========================================================================
 * 布局常量
 * ====================================================================== */
const NODE_W = 150        // 节点宽
const NODE_H = 56         // 节点高
const LAYER_H = 130       // 层高（层与层之间的垂直间距）
const GAP_X = 40          // 同层节点最小水平间距
const STEP_X = NODE_W + GAP_X
const PAD_X = 96          // 左右留白（左侧需要放"第N层"标签）
const PAD_TOP = 52
const PAD_BOTTOM = 56
const ISO_GAP = 76        // 主体与孤立节点区之间的间隔（留出分隔线和标题）

/* ========================================================================
 * 设备类型配色（浅色底 + 深色字，契合 light 主题）
 * 采用关键字包含匹配，兼容"核心交换机""三层交换机"等变体写法
 * ====================================================================== */
const DEVICE_STYLES = [
  { label: '交换机', keys: ['交换机', 'switch'], fill: '#ecf5ff', stroke: '#a0cfff', text: '#1d64b5' },
  { label: '路由器', keys: ['路由', 'router'], fill: '#f4ecff', stroke: '#c3a6f5', text: '#6b3fb8' },
  { label: '防火墙', keys: ['防火墙', 'firewall', '安全网关'], fill: '#fef0f0', stroke: '#fab6b6', text: '#c04a4a' },
  { label: '服务器', keys: ['服务器', 'server', '主机'], fill: '#f0f9eb', stroke: '#b3e19d', text: '#4a8f2c' },
  { label: '存储', keys: ['存储', 'storage', 'nas', 'san', '磁盘阵列'], fill: '#e8f7f5', stroke: '#8fd6cc', text: '#2f7f74' },
  { label: '电脑', keys: ['电脑', '笔记本', '台式', '终端', '工作站', 'pc', 'laptop', 'desktop', 'notebook'], fill: '#e9f6fb', stroke: '#9ad2e6', text: '#2b7492' },
  { label: '无线AP', keys: ['无线', 'wifi', 'wlan', 'ap'], fill: '#eef4ff', stroke: '#9fb8f0', text: '#3a5bb0' },
  { label: '打印机', keys: ['打印', 'printer'], fill: '#fdf6ec', stroke: '#f0cfa0', text: '#a06a1f' },
  { label: 'UPS', keys: ['ups', '电源', '配电'], fill: '#fffbe6', stroke: '#e8d67a', text: '#8a7412' },
  { label: '摄像头', keys: ['摄像', 'camera', '监控'], fill: '#f2f4f7', stroke: '#c2cad6', text: '#5a6577' },
  { label: '其他', keys: [], fill: '#f5f7fa', stroke: '#d3d8e0', text: '#606266' }
]
const DEFAULT_STYLE = DEVICE_STYLES[DEVICE_STYLES.length - 1]

// 纯函数：按 device_type 匹配配色
// 注意：ap / pc / ups 这类短英文缩写必须按"独立单词"匹配，
// 否则 "Laptop" 会因为含有 ap 被误判成无线AP。中文关键字直接子串匹配即可。
function matchKeyword (text, key) {
  if (/^[a-z0-9]{1,3}$/.test(key)) {
    return new RegExp('\\b' + key + '\\b').test(text)
  }
  return text.includes(key)
}

function matchDeviceStyle (type) {
  const t = String(type || '').toLowerCase()
  if (!t) return DEFAULT_STYLE
  for (const s of DEVICE_STYLES) {
    if (s.keys.some(k => matchKeyword(t, k))) return s
  }
  return DEFAULT_STYLE
}

/* ========================================================================
 * 连线样式：先看 link_type，再看 connection_type
 * hierarchy 表示仅由 parent_device_id 推断出来的兜底连线，用灰虚线弱化
 * ====================================================================== */
const LINK_STYLES = {
  stack: { color: '#e6a23c', width: 3, dash: '', double: false, name: '堆叠' },
  aggregate: { color: '#409eff', width: 1.8, dash: '', double: true, name: '聚合' },
  trunk: { color: '#409eff', width: 2, dash: '', double: false, name: 'Trunk' },
  access: { color: '#67c23a', width: 1.5, dash: '', double: false, name: 'Access' },
  hybrid: { color: '#909399', width: 2, dash: '4 3', double: false, name: 'Hybrid' },
  routed: { color: '#9254de', width: 2, dash: '', double: false, name: '路由' }
}
const HIERARCHY_STYLE = { color: '#c0c4cc', width: 1.6, dash: '6 5', double: false, name: '层级推断' }
const PLAIN_PORT_STYLE = { color: '#a8abb2', width: 1.5, dash: '', double: false, name: '端口互联' }

function matchLinkStyle (link) {
  if (link.link_type === 'hierarchy') return HIERARCHY_STYLE
  const ct = String(link.connection_type || '').toLowerCase()
  if (!ct) return PLAIN_PORT_STYLE
  return LINK_STYLES[ct] || PLAIN_PORT_STYLE
}

const LEGEND_LINKS = [
  { name: '堆叠 stack', color: '#e6a23c', width: 3, dash: '', double: false },
  { name: '聚合 aggregate', color: '#409eff', width: 1.4, dash: '', double: true },
  { name: 'Trunk', color: '#409eff', width: 2, dash: '', double: false },
  { name: 'Access', color: '#67c23a', width: 1.5, dash: '', double: false },
  { name: 'Hybrid', color: '#909399', width: 2, dash: '4 3', double: false },
  { name: '路由 routed', color: '#9254de', width: 2, dash: '', double: false },
  { name: '端口互联', color: '#a8abb2', width: 1.5, dash: '', double: false },
  { name: '层级推断（父子）', color: '#c0c4cc', width: 1.6, dash: '6 5', double: false }
]
const LEGEND_DEVICES = DEVICE_STYLES

/* ========================================================================
 * 文本工具：SVG 不会自动截断，这里按估算宽度手工截断
 * 中文按 1 个字号宽，西文按 0.55 个字号宽估算，够用且无需测量 DOM
 * ====================================================================== */
function measureText (str, fontSize) {
  let w = 0
  for (const ch of String(str)) {
    w += /[\u4e00-\u9fa5\u3000-\u303f\uff00-\uffef]/.test(ch) ? fontSize : fontSize * 0.55
  }
  return w
}

function truncateText (str, maxWidth, fontSize) {
  const s = String(str == null ? '' : str)
  if (!s) return ''
  if (measureText(s, fontSize) <= maxWidth) return s
  let w = 0
  let out = ''
  const ellipsisW = fontSize * 0.6
  for (const ch of s) {
    const cw = /[\u4e00-\u9fa5\u3000-\u303f\uff00-\uffef]/.test(ch) ? fontSize : fontSize * 0.55
    if (w + cw + ellipsisW > maxWidth) break
    w += cw
    out += ch
  }
  return out + '…'
}

/* ========================================================================
 * 核心：分层布局（纯函数，不依赖任何响应式状态，便于单独理解与测试）
 *
 * 输入 rawNodes / rawLinks，输出每个节点的坐标 + 画布尺寸。
 * 之所以要做父指针"规整 + 断环"，是因为数据库里的 parent_device_id
 * 完全可能是脏数据：指向自己、指向已删除的设备、或者 A->B->A 成环。
 * 若不处理，递归求深度会栈溢出/死循环。
 * ====================================================================== */
function computeLayout (rawNodes, rawLinks) {
  const empty = {
    nodes: [], posMap: new Map(), width: 0, height: 0,
    layerCount: 0, isolatedCount: 0, layerLabels: [], isoDivider: null
  }
  if (!rawNodes || !rawNodes.length) return empty

  const nodeMap = new Map()
  for (const n of rawNodes) nodeMap.set(n.id, n)

  // ---- 步骤 1：规整父指针 ----
  // 只有"父存在于本次数据集中，且不是自己"才算有效父，其余一律视为根节点。
  // 这样就自动兼容了「父设备指向不存在的节点」和「自环」两种脏数据。
  const parentOf = new Map()
  for (const n of rawNodes) {
    const pid = n.parent_device_id
    const valid = pid !== null && pid !== undefined && pid !== n.id && nodeMap.has(pid)
    parentOf.set(n.id, valid ? pid : null)
  }

  // ---- 步骤 2：断环 ----
  // 从每个节点沿父链上溯，把走过的节点记进 path；
  // 一旦发现"下一跳父节点已经在当前路径里"，说明这条边闭合成环，直接把它断开置空。
  // 断开后该节点成为一棵子树的根，既保证了后续求深度一定能终止，又不会丢失任何节点。
  for (const n of rawNodes) {
    const path = new Set()
    let cur = n.id
    while (cur !== null && cur !== undefined) {
      if (path.has(cur)) break
      path.add(cur)
      const p = parentOf.get(cur)
      if (p === null || p === undefined) break
      if (path.has(p)) {
        parentOf.set(cur, null) // 断开成环的这条边
        break
      }
      cur = p
    }
  }

  // ---- 步骤 3：子节点表 & 连线度数 ----
  const childrenOf = new Map()
  for (const n of rawNodes) childrenOf.set(n.id, [])
  for (const n of rawNodes) {
    const p = parentOf.get(n.id)
    if (p !== null && p !== undefined) childrenOf.get(p).push(n.id)
  }

  const degree = new Map()
  for (const n of rawNodes) degree.set(n.id, 0)
  for (const l of (rawLinks || [])) {
    if (degree.has(l.source)) degree.set(l.source, degree.get(l.source) + 1)
    if (degree.has(l.target)) degree.set(l.target, degree.get(l.target) + 1)
  }

  // ---- 步骤 4：挑出孤立节点 ----
  // 定义为：无有效父、无子节点、且没有任何一条连线经过它。
  // 注意不能只看父子关系——有些设备靠端口连线互联但都没填 parent，
  // 那种节点仍应留在主图里参与画线，否则连线会横跨到底部很难看。
  const isolatedSet = new Set()
  for (const n of rawNodes) {
    if (parentOf.get(n.id) === null && childrenOf.get(n.id).length === 0 && degree.get(n.id) === 0) {
      isolatedSet.add(n.id)
    }
  }
  const mainNodes = rawNodes.filter(n => !isolatedSet.has(n.id))
  const isoNodes = rawNodes.filter(n => isolatedSet.has(n.id))

  // ---- 步骤 5：求深度（此时父链已无环，可安全记忆化递归）----
  const depthMemo = new Map()
  const depthOf = (id, guard) => {
    if (depthMemo.has(id)) return depthMemo.get(id)
    const g = guard || 0
    const p = parentOf.get(id)
    // guard 是双保险：即便上游逻辑出现意外，也绝不会无限递归
    const d = (p === null || p === undefined || g > rawNodes.length) ? 0 : depthOf(p, g + 1) + 1
    depthMemo.set(id, d)
    return d
  }

  const layers = []
  for (const n of mainNodes) {
    const d = depthOf(n.id, 0)
    if (!layers[d]) layers[d] = []
    layers[d].push(n)
  }
  for (let i = 0; i < layers.length; i++) {
    if (!layers[i]) layers[i] = []
  }

  // ---- 步骤 6：确定画布宽度 ----
  const mainMax = layers.length ? Math.max(...layers.map(l => l.length)) : 0
  // 孤立节点原则上排在最底部"一行"；但数量很大时一行会把画布拉到上万像素，
  // 因此按主体最宽层（至少 6 个）折行，既保持视觉上的独立区块，又不至于失控。
  const perRow = Math.max(mainMax, 6)
  const isoRows = isoNodes.length ? Math.ceil(isoNodes.length / perRow) : 0
  const maxCount = Math.max(mainMax, Math.min(isoNodes.length, perRow), 1)
  const contentW = maxCount * STEP_X

  const collator = (a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'zh-Hans-CN')
  const posMap = new Map()

  // ---- 步骤 7：逐层排序并分配坐标 ----
  // 自顶向下处理：处理第 d 层时第 d-1 层坐标已确定，
  // 于是"按父节点 x 排序"就能让子节点尽量待在父节点正下方附近，天然减少交叉。
  for (let d = 0; d < layers.length; d++) {
    const layer = layers[d]
    if (d === 0) {
      layer.sort(collator)
    } else {
      layer.sort((a, b) => {
        const pa = posMap.get(parentOf.get(a.id))
        const pb = posMap.get(parentOf.get(b.id))
        const ax = pa ? pa.cx : 0
        const bx = pb ? pb.cx : 0
        if (ax !== bx) return ax - bx
        return collator(a, b)
      })
    }
    const startX = (contentW - layer.length * STEP_X) / 2
    const cy = PAD_TOP + d * LAYER_H + NODE_H / 2
    layer.forEach((n, i) => {
      posMap.set(n.id, { cx: PAD_X + startX + i * STEP_X + STEP_X / 2, cy })
    })
  }

  // ---- 步骤 8：孤立节点区 ----
  const mainH = layers.length ? (layers.length - 1) * LAYER_H + NODE_H : 0
  const isoTop = PAD_TOP + mainH + (layers.length ? ISO_GAP : 0)
  isoNodes.sort(collator)
  isoNodes.forEach((n, idx) => {
    const row = Math.floor(idx / perRow)
    const col = idx % perRow
    const countInRow = Math.min(perRow, isoNodes.length - row * perRow)
    const startX = (contentW - countInRow * STEP_X) / 2
    posMap.set(n.id, {
      cx: PAD_X + startX + col * STEP_X + STEP_X / 2,
      cy: isoTop + row * LAYER_H + NODE_H / 2
    })
  })

  const isoH = isoRows ? (isoRows - 1) * LAYER_H + NODE_H : 0
  const totalH = PAD_TOP + mainH +
    (isoRows ? (layers.length ? ISO_GAP : 0) + isoH : 0) + PAD_BOTTOM
  const totalW = contentW + PAD_X * 2

  // ---- 步骤 9：产出可直接渲染的节点对象 ----
  const outNodes = rawNodes.map(n => {
    const p = posMap.get(n.id)
    const style = matchDeviceStyle(n.device_type)
    return {
      id: n.id,
      data: n,
      style,
      cx: p.cx,
      cy: p.cy,
      x: p.cx - NODE_W / 2,
      y: p.cy - NODE_H / 2,
      isolated: isolatedSet.has(n.id),
      nameText: truncateText(n.name, NODE_W - 30, 12.5),
      ipText: truncateText(n.ip_address || '未配置IP', 76, 11),
      typeText: truncateText(n.device_type || '', 44, 10)
    }
  })

  // ---- 步骤 10：层标签 / 分隔线 ----
  const layerLabels = layers.map((l, d) => ({
    key: 'L' + d,
    x: 24,
    y: PAD_TOP + d * LAYER_H + NODE_H / 2 + 4,
    text: d === 0 ? '核心层' : '第 ' + d + ' 层'
  }))
  const isoDivider = isoRows
    ? { y: isoTop - ISO_GAP / 2, text: '未连接设备（' + isoNodes.length + '）' }
    : null

  return {
    nodes: outNodes,
    posMap,
    width: totalW,
    height: totalH,
    layerCount: layers.length,
    isolatedCount: isoNodes.length,
    layerLabels,
    isoDivider
  }
}

/* ========================================================================
 * 纯函数：计算一条连线的贝塞尔路径
 * 用三次贝塞尔是为了能用公式精确求出 t=0.5 的中点来摆放标签
 * ====================================================================== */
function buildLinkGeometry (s, t) {
  let x0, y0, x1, y1, x2, y2, x3, y3
  if (Math.abs(s.cy - t.cy) < 1) {
    // 同层互联（常见于堆叠/聚合）：从右侧出、左侧入，向下拱一点避免压住节点
    const a = s.cx <= t.cx ? s : t
    const b = s.cx <= t.cx ? t : s
    x0 = a.cx + NODE_W / 2
    y0 = a.cy
    x3 = b.cx - NODE_W / 2
    y3 = b.cy
    const dx = Math.max((x3 - x0) * 0.3, 20)
    const sag = Math.min(46, Math.max(20, (x3 - x0) * 0.16))
    x1 = x0 + dx; y1 = y0 + sag
    x2 = x3 - dx; y2 = y3 + sag
  } else {
    // 跨层：上节点底边中点 -> 下节点顶边中点，垂直方向的控制点做出平滑 S 形
    const up = s.cy < t.cy ? s : t
    const dn = s.cy < t.cy ? t : s
    x0 = up.cx
    y0 = up.cy + NODE_H / 2
    x3 = dn.cx
    y3 = dn.cy - NODE_H / 2
    const dy = (y3 - y0) / 2
    x1 = x0; y1 = y0 + dy
    x2 = x3; y2 = y3 - dy
  }
  return { x0, y0, x1, y1, x2, y2, x3, y3 }
}

function cubicPath (g) {
  return `M ${g.x0} ${g.y0} C ${g.x1} ${g.y1}, ${g.x2} ${g.y2}, ${g.x3} ${g.y3}`
}

// 把整条贝塞尔沿法线平移 off 像素，用于"聚合"的双线效果
function offsetCubic (g, off) {
  const dx = g.x3 - g.x0
  const dy = g.y3 - g.y0
  const len = Math.hypot(dx, dy) || 1
  const ox = (-dy / len) * off
  const oy = (dx / len) * off
  return cubicPath({
    x0: g.x0 + ox, y0: g.y0 + oy,
    x1: g.x1 + ox, y1: g.y1 + oy,
    x2: g.x2 + ox, y2: g.y2 + oy,
    x3: g.x3 + ox, y3: g.y3 + oy
  })
}

/* ========================================================================
 * 响应式状态
 * ====================================================================== */
const loading = ref(false)
const rawNodes = ref([])
const rawLinks = ref([])

const canvasRef = ref(null)
const svgRef = ref(null)

const scale = ref(1)
const tx = ref(0)
const ty = ref(0)
const isPanning = ref(false)
const dragMoved = ref(false)

const selectedId = ref(null)
const drawerVisible = ref(false)
const hoverTip = ref({ show: false, x: 0, y: 0, title: '', ports: '', extra: '' })

const MIN_SCALE = 0.3
const MAX_SCALE = 2.5

/* ========================================================================
 * 派生数据
 * ====================================================================== */
const layout = computed(() => computeLayout(rawNodes.value, rawLinks.value))
const layoutNodes = computed(() => layout.value.nodes)
const canvasW = computed(() => layout.value.width)
const canvasH = computed(() => layout.value.height)
const layerCount = computed(() => layout.value.layerCount)
const isolatedCount = computed(() => layout.value.isolatedCount)
const layerLabels = computed(() => layout.value.layerLabels)
const isoDivider = computed(() => layout.value.isoDivider)

const nodeById = computed(() => {
  const m = new Map()
  for (const n of rawNodes.value) m.set(n.id, n)
  return m
})

// 可绘制连线：过滤掉自环和端点缺失的脏数据，避免出现 NaN 路径
const drawableLinks = computed(() => {
  const posMap = layout.value.posMap
  const out = []
  rawLinks.value.forEach((l, idx) => {
    if (l.source === l.target) return
    const s = posMap.get(l.source)
    const t = posMap.get(l.target)
    if (!s || !t) return
    const style = matchLinkStyle(l)
    const g = buildLinkGeometry(s, t)
    const basePath = cubicPath(g)
    const paths = style.double
      ? [offsetCubic(g, 2.2), offsetCubic(g, -2.2)]
      : [basePath]
    // 三次贝塞尔 t=0.5 处的解析解：(P0 + 3P1 + 3P2 + P3) / 8
    const midX = (g.x0 + 3 * g.x1 + 3 * g.x2 + g.x3) / 8
    const midY = (g.y0 + 3 * g.y1 + 3 * g.y2 + g.y3) / 8
    const label = l.label || ''
    out.push({
      key: `${l.source}-${l.target}-${idx}`,
      raw: l,
      source: l.source,
      target: l.target,
      style,
      paths,
      basePath,
      midX,
      midY,
      label,
      labelW: label ? measureText(label, 11) + 14 : 0
    })
  })
  return out
})

// 选中节点后，需要高亮的节点集合（自身 + 直接邻居）
const highlightSet = computed(() => {
  if (selectedId.value === null) return null
  const s = new Set([selectedId.value])
  for (const l of rawLinks.value) {
    if (l.source === selectedId.value) s.add(l.target)
    if (l.target === selectedId.value) s.add(l.source)
  }
  return s
})

function nodeOpacity (id) {
  const hs = highlightSet.value
  if (!hs) return 1
  return hs.has(id) ? 1 : 0.18
}

function linkOpacity (lk) {
  if (selectedId.value === null) return 1
  return (lk.source === selectedId.value || lk.target === selectedId.value) ? 1 : 0.12
}

const selectedNode = computed(() =>
  selectedId.value === null ? null : (nodeById.value.get(selectedId.value) || null)
)

const brandModelText = computed(() => {
  const n = selectedNode.value
  if (!n) return '-'
  const s = [n.brand, n.model].filter(Boolean).join(' ')
  return s || '-'
})

const selectedConnections = computed(() => {
  if (selectedId.value === null) return []
  const sid = selectedId.value
  return rawLinks.value
    .filter(l => l.source === sid || l.target === sid)
    .map(l => {
      const isSource = l.source === sid
      const peerId = isSource ? l.target : l.source
      const peer = nodeById.value.get(peerId)
      const style = matchLinkStyle(l)
      return {
        peerName: peer ? peer.name : `设备 #${peerId}`,
        localPort: isSource ? l.source_port : l.target_port,
        peerPort: isSource ? l.target_port : l.source_port,
        typeName: style.name,
        color: style.color,
        label: l.label || ''
      }
    })
})

const scalePercent = computed(() => Math.round(scale.value * 100))

/* ========================================================================
 * 数据加载
 * ====================================================================== */
async function loadData () {
  loading.value = true
  try {
    // 分组节点（含子节点，如一级文件夹/资产/组件/软件）点击后不过滤，显示全部
    const sel = props.selectedFolder
    const folderId = sel && sel.id && !(sel.children && sel.children.length) ? sel.id : undefined
    const res = await topologyApi.get(folderId)
    if (res && res.code === 0 && res.data) {
      rawNodes.value = Array.isArray(res.data.nodes) ? res.data.nodes : []
      rawLinks.value = Array.isArray(res.data.links) ? res.data.links : []
    } else {
      rawNodes.value = []
      rawLinks.value = []
      ElMessage.warning((res && res.message) || '拓扑数据返回异常')
    }
    clearSelection()
    await nextTick()
    fitView()
  } catch (e) {
    console.error('加载拓扑失败:', e)
    ElMessage.error('加载拓扑数据失败')
    rawNodes.value = []
    rawLinks.value = []
  } finally {
    loading.value = false
  }
}

/* ========================================================================
 * 视图变换：缩放 / 平移
 * ====================================================================== */
function clampScale (v) {
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, v))
}

// 以某个屏幕坐标为锚点缩放：保证锚点下的图形坐标缩放前后不变
function zoomAt (px, py, factor) {
  const old = scale.value
  const next = clampScale(old * factor)
  if (next === old) return
  const gx = (px - tx.value) / old
  const gy = (py - ty.value) / old
  scale.value = next
  tx.value = px - gx * next
  ty.value = py - gy * next
}

function onWheel (e) {
  const el = canvasRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  zoomAt(e.clientX - rect.left, e.clientY - rect.top, e.deltaY < 0 ? 1.12 : 1 / 1.12)
}

function zoomByCenter (factor) {
  const el = canvasRef.value
  if (!el) return
  zoomAt(el.clientWidth / 2, el.clientHeight / 2, factor)
}
function zoomIn () { zoomByCenter(1.2) }
function zoomOut () { zoomByCenter(1 / 1.2) }

function resetView () {
  const el = canvasRef.value
  scale.value = 1
  if (el && canvasW.value) {
    tx.value = Math.max(20, (el.clientWidth - canvasW.value) / 2)
  } else {
    tx.value = 0
  }
  ty.value = 20
}

function fitView () {
  const el = canvasRef.value
  if (!el || !canvasW.value || !canvasH.value) return
  const vw = el.clientWidth
  const vh = el.clientHeight
  if (!vw || !vh) return
  const k = clampScale(Math.min((vw - 48) / canvasW.value, (vh - 48) / canvasH.value, MAX_SCALE))
  scale.value = k
  tx.value = (vw - canvasW.value * k) / 2
  ty.value = (vh - canvasH.value * k) / 2
}

let panStartX = 0
let panStartY = 0
let panOriginX = 0
let panOriginY = 0

function onBgMouseDown (e) {
  if (e.button !== 0) return
  isPanning.value = true
  dragMoved.value = false
  panStartX = e.clientX
  panStartY = e.clientY
  panOriginX = tx.value
  panOriginY = ty.value
  window.addEventListener('mousemove', onPanMove)
  window.addEventListener('mouseup', onPanUp)
}

function onPanMove (e) {
  if (!isPanning.value) return
  const dx = e.clientX - panStartX
  const dy = e.clientY - panStartY
  if (Math.abs(dx) > 3 || Math.abs(dy) > 3) dragMoved.value = true
  tx.value = panOriginX + dx
  ty.value = panOriginY + dy
}

function onPanUp () {
  isPanning.value = false
  window.removeEventListener('mousemove', onPanMove)
  window.removeEventListener('mouseup', onPanUp)
}

/* ========================================================================
 * 选中 / 高亮 / 提示
 * ====================================================================== */
function onNodeClick (nd) {
  selectedId.value = nd.id
  drawerVisible.value = true
}

function clearSelection () {
  selectedId.value = null
  drawerVisible.value = false
}

// 点击空白处恢复：拖拽结束时浏览器也会触发 click，用 dragMoved 区分开
function onBgClick () {
  if (dragMoved.value) return
  clearSelection()
}

function onLinkEnter (lk, e) {
  const sName = nodeById.value.get(lk.source)
  const tName = nodeById.value.get(lk.target)
  const sp = lk.raw.source_port || '未知端口'
  const tp = lk.raw.target_port || '未知端口'
  hoverTip.value = {
    show: true,
    x: 0,
    y: 0,
    title: `${sName ? sName.name : lk.source} <-> ${tName ? tName.name : lk.target}`,
    ports: `${sp} <-> ${tp}`,
    extra: [lk.style.name, lk.label].filter(Boolean).join(' · ')
  }
  onLinkMove(e)
}

function onLinkMove (e) {
  const el = canvasRef.value
  if (!el || !hoverTip.value.show) return
  const rect = el.getBoundingClientRect()
  hoverTip.value.x = e.clientX - rect.left
  hoverTip.value.y = e.clientY - rect.top
}

function onLinkLeave () {
  hoverTip.value.show = false
}

/* ========================================================================
 * 生命周期
 * ====================================================================== */
watch(() => props.selectedFolder, () => { loadData() })

onMounted(() => { loadData() })

onBeforeUnmount(() => {
  window.removeEventListener('mousemove', onPanMove)
  window.removeEventListener('mouseup', onPanUp)
})
</script>

<style scoped>
.topology-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--app-panel, #fff);
}

/* ===== 工具栏 ===== */
.topo-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid #ebeef5;
  background: #fafbfc;
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: 8px;
}
.tb-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.tb-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}
.tb-sub {
  font-size: 12px;
  color: #909399;
}
.tb-sub b {
  color: #303133;
  font-weight: 600;
}
.tb-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.zoom-text {
  font-size: 12px;
  color: #606266;
  min-width: 42px;
  text-align: right;
}

/* ===== 画布 ===== */
.topo-canvas {
  position: relative;
  flex: 1;
  overflow: hidden;
  background-color: var(--app-bg-soft, #fafbfc);
  /* 淡淡的网格底纹，帮助感知平移缩放 */
  background-image:
    linear-gradient(rgba(64, 158, 255, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(64, 158, 255, 0.05) 1px, transparent 1px);
  background-size: 22px 22px;
}
.topo-svg {
  width: 100%;
  height: 100%;
  display: block;
  cursor: grab;
  user-select: none;
}
.topo-svg.panning {
  cursor: grabbing;
}

/* ===== SVG 元素 ===== */
.topo-node {
  cursor: pointer;
}
.topo-node rect {
  transition: stroke 0.15s;
}
.node-name {
  font-size: 12.5px;
  font-weight: 600;
  pointer-events: none;
}
.node-ip {
  font-size: 11px;
  fill: #909399;
  pointer-events: none;
}
.node-type {
  font-size: 10px;
  opacity: 0.75;
  pointer-events: none;
}
.layer-label {
  font-size: 12px;
  fill: #a8abb2;
  font-weight: 600;
  pointer-events: none;
}
.divider-label {
  font-size: 12px;
  fill: #a8abb2;
  pointer-events: none;
}
.link-label-text {
  font-size: 11px;
  fill: #303133;
  pointer-events: none;
}
.link-hit {
  cursor: pointer;
  pointer-events: stroke;
}

/* ===== 连线悬停提示 ===== */
.link-tip {
  position: absolute;
  z-index: 20;
  pointer-events: none;
  background: rgba(48, 49, 51, 0.92);
  color: #fff;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.6;
  max-width: 320px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.18);
}
.tip-row {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tip-main {
  font-weight: 600;
}
.tip-sub {
  color: #c8c9cc;
  font-size: 11px;
}

/* ===== 图例 ===== */
.legend {
  position: absolute;
  right: 14px;
  bottom: 14px;
  z-index: 10;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 10px 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.07);
  max-width: 260px;
}
.legend-title {
  font-size: 12px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 6px;
}
.legend-title:not(:first-child) {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed #ebeef5;
}
.legend-grid {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.legend-svg {
  flex-shrink: 0;
}
.legend-chip {
  width: 22px;
  height: 11px;
  border-radius: 3px;
  border: 1px solid #d3d8e0;
  flex-shrink: 0;
  display: inline-block;
}
.legend-text {
  font-size: 11px;
  color: #606266;
}
.legend-tip {
  margin-top: 8px;
  padding-top: 7px;
  border-top: 1px dashed #ebeef5;
  font-size: 11px;
  color: #a8abb2;
}

/* ===== 详情抽屉 ===== */
.detail-body {
  padding-bottom: 20px;
}
.detail-sub-title {
  margin: 18px 0 10px;
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
}
.detail-count {
  font-size: 12px;
  font-weight: 400;
  color: #909399;
}
.conn-card {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 9px 10px;
  margin-bottom: 8px;
  background: #fafbfc;
}
.conn-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.conn-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.conn-peer {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.conn-ports {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.port-tag {
  font-size: 11px;
  color: #606266;
  background: #eef1f6;
  border-radius: 3px;
  padding: 1px 6px;
  font-family: Consolas, Monaco, monospace;
}
.conn-arrow {
  font-size: 11px;
  color: #a8abb2;
}
.conn-label {
  margin-top: 5px;
  font-size: 11px;
  color: #909399;
}
</style>
