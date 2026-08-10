<script setup>
/**
 * 告警列表页（N1）
 *
 * 功能：
 *  - 全部 / warning / critical / ok 状态切换（el-tabs）
 *  - 关键字搜索（设备名 / 指标名 / message）
 *  - ack / 批量 ack / 删除
 *  - 点击行跳转设备详情（如有）
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { alertApi } from '../api/index.js'

const router = useRouter()

const loading = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const activeTab = ref('active')
const keyword = ref('')

const LEVEL_OPTS = [
  { value: 'critical', label: '严重', tag: 'danger' },
  { value: 'warning',  label: '警告', tag: 'warning' },
  { value: 'ok',       label: '已恢复', tag: 'success' }
]

function tagFor(level) {
  const o = LEVEL_OPTS.find(x => x.value === level)
  return o ? o.tag : 'info'
}
function labelFor(level) {
  const o = LEVEL_OPTS.find(x => x.value === level)
  return o ? o.label : level
}

// 当前 filter 状态决定是否传 acknowledged
const filterParams = computed(() => {
  const p = { page: page.value, page_size: pageSize.value }
  if (keyword.value.trim()) p.keyword = keyword.value.trim()
  if (activeTab.value === 'active') p.acknowledged = false
  if (activeTab.value === 'acked') p.acknowledged = true
  if (activeTab.value === 'critical' || activeTab.value === 'warning' || activeTab.value === 'ok') {
    p.level = activeTab.value
  }
  return p
})

async function fetchList() {
  loading.value = true
  try {
    const res = await alertApi.list(filterParams.value)
    if (res.code === 0) {
      list.value = res.data.items || []
      total.value = res.data.total
    } else {
      ElMessage.error(res.message || '加载告警列表失败')
    }
  } catch (e) {
    ElMessage.error('请求失败：' + (e?.message || '网络异常'))
  } finally {
    loading.value = false
  }
}

function onTabChange() {
  page.value = 1
  fetchList()
}

async function ackOne(row) {
  try {
    const res = await alertApi.ack(row.id)
    if (res.code === 0) ElMessage.success('已确认')
    else ElMessage.error(res.message || '操作失败')
    fetchList()
  } catch (e) {
    ElMessage.error('请求失败：' + (e?.message || '网络异常'))
  }
}

const selectedRows = ref([])
async function ackBatch() {
  if (!selectedRows.value.length) return ElMessage.warning('请先勾选告警')
  try {
    const res = await alertApi.ackBatch(selectedRows.value.map(r => r.id))
    if (res.code === 0) ElMessage.success(res.message)
    else ElMessage.error(res.message || '操作失败')
    fetchList()
  } catch (e) {
    ElMessage.error('请求失败：' + (e?.message || '网络异常'))
  }
}

async function ackAll() {
  try {
    await ElMessageBox.confirm(
      '确认全部标记为已读？此操作不可撤销。',
      '批量确认',
      { confirmButtonText: '全部确认', cancelButtonText: '取消', type: 'warning' }
    )
  } catch (_) { return }
  await ackBatch(list.value.filter(r => !r.acknowledged))
}

async function removeRow(row) {
  try {
    await ElMessageBox.confirm('确定要删除该告警吗？', '删除确认', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning'
    })
  } catch (_) { return }
  try {
    const res = await alertApi.remove(row.id)
    if (res.code === 0) ElMessage.success('已删除')
    else ElMessage.error(res.message || '操作失败')
    fetchList()
  } catch (e) {
    ElMessage.error('请求失败：' + (e?.message || '网络异常'))
  }
}

function goDevice(row) {
  router.push({ name: 'DeviceList', query: { device_id: row.device_id } })
}

const fmtTime = (s) => s || '—'

// 30 秒轮询一次，让运维看到实时变更
let pollTimer = null
onMounted(() => {
  fetchList()
  pollTimer = setInterval(fetchList, 30000)
})
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="alert-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>告警中心（N1 - SNMP 阈值告警）</span>
          <div class="header-right">
            <el-input v-model="keyword" placeholder="搜索设备/指标/消息" clearable style="width:240px"
                      @keyup.enter="fetchList" @clear="fetchList" />
            <el-button @click="fetchList" :loading="loading">刷新</el-button>
          </div>
        </div>
      </template>

      <el-tabs v-model="activeTab" @tab-change="onTabChange">
        <el-tab-pane label="待处理" name="active" />
        <el-tab-pane label="已确认" name="acked" />
        <el-tab-pane label="严重" name="critical" />
        <el-tab-pane label="警告" name="warning" />
        <el-tab-pane label="已恢复" name="ok" />
        <el-tab-pane label="全部" name="all" />
      </el-tabs>

      <div class="batch-bar" v-if="selectedRows.length || list.some(r => !r.acknowledged && activeTab !== 'acked')">
        <span>已选 {{ selectedRows.length }} 条</span>
        <el-button type="primary" size="small" :disabled="!selectedRows.length" @click="ackBatch">
          批量确认
        </el-button>
        <el-button v-if="activeTab !== 'acked'" size="small" type="success" @click="ackAll">
          全部确认
        </el-button>
      </div>

      <el-table :data="list" v-loading="loading" border stripe
                @selection-change="rows => selectedRows = rows">
        <el-table-column type="selection" width="44" />
        <el-table-column label="级别" width="80">
          <template #default="{ row }">
            <el-tag :type="tagFor(row.level)" effect="dark" size="small">
              {{ labelFor(row.level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="设备" min-width="160">
          <template #default="{ row }">
            <el-link type="primary" :underline="false" @click="goDevice(row)">{{ row.device_name }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="metric_name" label="指标" min-width="120" />
        <el-table-column label="采集值" width="120">
          <template #default="{ row }">{{ row.value }}{{ row.unit }}</template>
        </el-table-column>
        <el-table-column prop="threshold" label="阈值" width="100" />
        <el-table-column prop="message" label="详情" min-width="220" show-overflow-tooltip />
        <el-table-column label="触发时间" width="170">
          <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="160">
          <template #default="{ row }">
            <template v-if="row.acknowledged">
              <el-tag type="info" effect="plain" size="small">
                ✓ {{ row.acknowledged_by }} @ {{ fmtTime(row.acknowledged_at).slice(11) }}
              </el-tag>
            </template>
            <el-tag v-else type="danger" effect="dark" size="small">未确认</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link v-if="!row.acknowledged" type="primary" size="small" @click="ackOne(row)">
              确认
            </el-button>
            <el-button link type="danger" size="small" @click="removeRow(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无告警" />
        </template>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 16px; justify-content: flex-end"
        @current-change="fetchList"
        @size-change="fetchList"
      />
    </el-card>
  </div>
</template>

<style scoped>
.alert-page {
  max-width: 1400px;
  margin: 0 auto;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
  font-size: 16px;
}
.header-right {
  display: flex;
  gap: 8px;
}
.batch-bar {
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: var(--app-text-secondary, #909399);
}
.batch-bar span {
  margin-right: 4px;
}
</style>
