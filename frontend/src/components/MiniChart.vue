<template>
  <div class="mini-chart" :style="{ height: height }">
    <!-- 折线 / 柱状 -->
    <svg
      v-if="type !== 'pie'"
      :viewBox="`0 0 ${W} ${H}`"
      preserveAspectRatio="xMidYMid meet"
      class="chart-svg"
    >
      <!-- 横向网格 + Y 轴刻度 -->
      <g class="grid">
        <line
          v-for="g in gridLines"
          :key="g.y"
          :x1="padL" :y1="g.y" :x2="W - padR" :y2="g.y"
          class="grid-line"
        />
        <text :x="padL" :y="g.y - 3" class="grid-label" v-for="g in gridLines" :key="'t'+g.y">{{ g.text }}</text>
      </g>

      <!-- 折线 -->
      <g v-if="type === 'line'">
        <g v-for="(s, si) in series" :key="'s'+si">
          <polygon
            v-if="s.data.length > 1"
            :points="areaPoints(s)"
            :fill="s.color"
            fill-opacity="0.12"
          />
          <polyline
            :points="linePoints(s)"
            fill="none"
            :stroke="s.color"
            stroke-width="2"
            stroke-linejoin="round"
            stroke-linecap="round"
          />
          <circle
            v-for="(p, i) in points(s)"
            :key="i"
            :cx="p.x" :cy="p.y" r="2.5"
            :fill="s.color"
          />
        </g>
      </g>

      <!-- 柱状（分组） -->
      <g v-else-if="type === 'bar'">
        <g v-for="(cat, ci) in labels" :key="'c'+ci">
          <rect
            v-for="(s, si) in series"
            :key="'b'+si"
            :x="barX(ci, si)"
            :y="barY(s.data[ci])"
            :width="barW"
            :height="Math.max(0, H - padB - barY(s.data[ci]))"
            :fill="s.color"
            rx="1.5"
          />
        </g>
      </g>

      <!-- X 轴标签 -->
      <text
        v-for="(lb, i) in xTickLabels"
        :key="'x'+i"
        :x="lb.x" :y="H - 4"
        class="x-label"
        text-anchor="middle"
      >{{ lb.text }}</text>
    </svg>

    <!-- 饼 / 环图 -->
    <svg v-else :viewBox="`0 0 200 200`" class="chart-svg pie">
      <circle
        v-for="(d, i) in pieSlices"
        :key="i"
        cx="100" cy="100" :r="70"
        fill="none"
        :stroke="d.color"
        stroke-width="26"
        :stroke-dasharray="`${d.len} ${C - d.len}`"
        :stroke-dashoffset="`-${d.offset}`"
        transform="rotate(-90 100 100)"
      />
      <text x="100" y="96" text-anchor="middle" class="pie-total">{{ pieTotal }}</text>
      <text x="100" y="116" text-anchor="middle" class="pie-total-sub">总计</text>
    </svg>

    <div v-if="empty" class="chart-empty">暂无数据</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  type: { type: String, default: 'line' }, // line | bar | pie
  // line/bar: series=[{name,color,data:number[]}], labels=string[]
  series: { type: Array, default: () => [] },
  labels: { type: Array, default: () => [] },
  // pie: data=[{name,value,color}]
  data: { type: Array, default: () => [] },
  height: { type: String, default: '220px' }
})

const W = 480
const H = 240
const padL = 36
const padR = 12
const padT = 14
const padB = 26
const plotW = W - padL - padR
const plotH = H - padT - padB

const PALETTE = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#9254DE', '#13C2C2', '#EB2F96', '#909399']

const empty = computed(() => {
  if (props.type === 'pie') return !props.data.length
  return !props.series.length || props.series.every(s => !s.data || !s.data.length)
})

const allValues = computed(() => {
  const arr = []
  props.series.forEach(s => (s.data || []).forEach(v => { if (typeof v === 'number') arr.push(v) }))
  return arr
})
const maxV = computed(() => {
  if (!allValues.value.length) return 1
  const m = Math.max(...allValues.value, 0)
  return m <= 0 ? 1 : m
})
const minV = computed(() => {
  if (!allValues.value.length) return 0
  const m = Math.min(...allValues.value, 0)
  return m < 0 ? m : 0
})

const gridLines = computed(() => {
  const lines = []
  const steps = 4
  for (let i = 0; i <= steps; i++) {
    const v = minV.value + (maxV.value - minV.value) * (i / steps)
    const y = padT + plotH * (1 - i / steps)
    lines.push({ y, text: fmt(v) })
  }
  return lines
})

const xTickLabels = computed(() => {
  const n = props.labels.length
  if (!n) return []
  const idxs = n <= 6 ? props.labels.map((_, i) => i) : [0, Math.floor(n / 2), n - 1]
  return idxs.map(i => ({
    x: padL + (n === 1 ? plotW / 2 : (i / (n - 1)) * plotW),
    text: props.labels[i]
  }))
})

function fmt(v) {
  if (Math.abs(v) >= 1000) return (v / 1000).toFixed(1) + 'k'
  return Number.isInteger(v) ? String(v) : v.toFixed(1)
}
function yOf(v) {
  const t = (v - minV.value) / (maxV.value - minV.value || 1)
  return padT + plotH * (1 - t)
}
function xOf(i) {
  const n = props.series[0]?.data?.length || props.labels.length || 1
  return padL + (n === 1 ? plotW / 2 : (i / (n - 1)) * plotW)
}
function points(s) {
  return (s.data || []).map((v, i) => ({ x: xOf(i), y: yOf(v) }))
}
function linePoints(s) {
  return points(s).map(p => `${p.x},${p.y}`).join(' ')
}
function areaPoints(s) {
  const ps = points(s)
  if (!ps.length) return ''
  const first = ps[0], last = ps[ps.length - 1]
  return `${first.x},${padT + plotH} ` + ps.map(p => `${p.x},${p.y}`).join(' ') + ` ${last.x},${padT + plotH}`
}
// 柱状分组
const barW = computed(() => {
  const n = props.labels.length || 1
  const groupW = plotW / n
  const sw = props.series.length || 1
  return Math.max(2, groupW / (sw + 0.6) - 2)
})
function barX(ci, si) {
  const n = props.labels.length || 1
  const groupW = plotW / n
  const sw = props.series.length || 1
  const totalW = barW.value * sw + 2 * (sw - 1)
  const start = padL + ci * groupW + (groupW - totalW) / 2
  return start + si * (barW.value + 2)
}
function barY(v) {
  return yOf(v)
}

// 饼图
const C = 2 * Math.PI * 70
const pieTotal = computed(() => props.data.reduce((s, d) => s + (d.value || 0), 0))
const pieSlices = computed(() => {
  let offset = 0
  return props.data.map((d, i) => {
    const v = d.value || 0
    const len = pieTotal.value ? (v / pieTotal.value) * C : 0
    const slice = { color: d.color || PALETTE[i % PALETTE.length], len, offset }
    offset += len
    return slice
  })
})
</script>

<style scoped>
.mini-chart { width: 100%; position: relative; }
.chart-svg { width: 100%; height: 100%; display: block; }
.grid-line { stroke: var(--el-border-color-lighter, #ebeef5); stroke-width: 1; }
.grid-label { fill: #909399; font-size: 10px; }
.x-label { fill: #909399; font-size: 10px; }
.pie-total { fill: var(--el-text-color-primary, #303133); font-size: 22px; font-weight: bold; }
.pie-total-sub { fill: #909399; font-size: 11px; }
.chart-empty {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  color: #909399; font-size: 13px;
}
</style>
