<script setup>
/**
 * 审计日志查看页（N3，仅管理员）。
 * 列表 + 按 actor / action / 关键字 / 时间筛选 + 详情抽屉查看 diff。
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { auditLogApi } from '../api/index.js'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const keyword = ref('')
const actionFilter = ref('')
const targetTypeFilter = ref('')

const detailVisible = ref(false)
const detailRow = ref(null)

const ACTION_OPTS = [
  { value: 'login',   label: '登录',  type: 'primary' },
  { value: 'logout',  label: '登出',  type: 'info' },
  { value: 'create',  label: '创建',  type: 'success' },
  { value: 'update',  label: '修改',  type: 'warning' },
  { value: 'delete',  label: '删除',  type: 'danger' },
  { value: 'import',  label: '导入',  type: 'info' },
  { value: 'export',  label: '导出',  type: 'info' },
  { value: 'ack',     label: '确认',  type: 'success' },
  { value: 'poll',    label: '采集',  type: 'primary' }
]

function tagForAction(a) {
  const o = ACTION_OPTS.find(x => x.value === a)
  return o ? o.type : 'info'
}
function labelForAction(a) {
  const o = ACTION_OPTS.find(x => x.value === a)
  return o ? o.label : a
}

const filterParams = computed(() => {
  const p = { page: page.value, page_size: pageSize.value }
  if (keyword.value.trim()) p.keyword = keyword.value.trim()
  if (actionFilter.value) p.action = actionFilter.value
  if (targetTypeFilter.value) p.target_type = targetTypeFilter.value
  return p
})

async function fetchList() {
  loading.value = true
  try {
    const res = await auditLogApi.list(filterParams.value)
    if (res.code === 0) {
      list.value = res.data.items || []
      total.value = res.data.total
    } else {
      ElMessage.error(res.message || '加载审计日志失败')
    }
  } catch (e) {
    ElMessage.error('请求失败：' + (e?.message || '网络异常'))
  } finally {
    loading.value = false
  }
}

function fmtTime(s) { return s || '—' }

function tryParseDiff(d) {
  if (!d) return null
  try { return JSON.parse(d) } catch (_) { return null }
}

function showDetail(row) {
  detailRow.value = row
  detailVisible.value = true
}

let pollTimer = null
onMounted(() => {
  fetchList()
  pollTimer = setInterval(fetchList, 60000)  // 每分钟刷新
})
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="audit-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>操作审计日志（N3）</span>
          <span class="meta">当前用户、IP、User-Agent、变更内容均记录，用于追责审计。</span>
        </div>
      </template>

      <div class="filter-bar">
        <el-input v-model="keyword" placeholder="搜索操作者/对象/消息" clearable style="width:240px"
                  @keyup.enter="fetchList" @clear="fetchList" />
        <el-select v-model="actionFilter" placeholder="动作" clearable style="width:140px" @change="fetchList">
          <el-option v-for="o in ACTION_OPTS" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
        <el-input v-model="targetTypeFilter" placeholder="对象类型" clearable style="width:120px"
                  @keyup.enter="fetchList" @clear="fetchList" />
        <el-button type="primary" @click="fetchList">查询</el-button>
        <el-button @click="fetchList" :loading="loading">刷新</el-button>
      </div>

      <el-table :data="list" v-loading="loading" border stripe @row-click="showDetail" style="cursor:pointer">
        <el-table-column prop="created_at" label="时间" width="170" />
        <el-table-column label="操作者" min-width="100">
          <template #default="{ row }">
            {{ row.actor_name || '(匿名)' }}
          </template>
        </el-table-column>
        <el-table-column label="动作" width="80">
          <template #default="{ row }">
            <el-tag :type="tagForAction(row.action)" effect="dark" size="small">
              {{ labelForAction(row.action) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="target_type" label="对象" width="100" />
        <el-table-column prop="target_name" label="对象名" min-width="140" show-overflow-tooltip />
        <el-table-column prop="message" label="消息" min-width="220" show-overflow-tooltip />
        <el-table-column label="结果" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.success" type="success" size="small" effect="dark">成功</el-tag>
            <el-tag v-else type="danger" size="small" effect="dark">失败</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ip" label="IP" width="130" />
        <template #empty>
          <el-empty description="暂无审计日志" />
        </template>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100, 200]"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 16px; justify-content: flex-end"
        @current-change="fetchList"
        @size-change="fetchList"
      />
    </el-card>

    <!-- 详情抽屉 -->
    <el-dialog v-model="detailVisible" title="审计详情" width="640px">
      <div v-if="detailRow" class="detail-body">
        <div class="kv"><label>时间：</label><span>{{ fmtTime(detailRow.created_at) }}</span></div>
        <div class="kv"><label>操作者：</label><span>{{ detailRow.actor_name || '(匿名)' }} <span v-if="detailRow.actor_id" class="dim">#{{ detailRow.actor_id }}</span></span></div>
        <div class="kv"><label>动作：</label><span>{{ detailRow.action }} / {{ detailRow.target_type }} #{{ detailRow.target_id || '-' }}</span></div>
        <div class="kv"><label>对象名：</label><span>{{ detailRow.target_name }}</span></div>
        <div class="kv"><label>消息：</label><span>{{ detailRow.message }}</span></div>
        <div class="kv"><label>来源 IP：</label><span>{{ detailRow.ip || '—' }}</span></div>
        <div class="kv"><label>User-Agent：</label><span>{{ detailRow.user_agent || '—' }}</span></div>
        <div class="kv" v-if="detailRow.diff">
          <label>差异（diff）：</label>
          <pre class="diff-json">{{ tryParseDiff(detailRow.diff) }}</pre>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.audit-page { max-width: 1400px; margin: 0 auto; }
.card-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-weight: bold;
  font-size: 16px;
}
.meta { font-size: 12px; color: var(--app-text-secondary, #909399); font-weight: normal; }
.filter-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.detail-body .kv {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
  font-size: 13px;
}
.detail-body label {
  flex: 0 0 110px;
  color: var(--app-text-secondary, #909399);
}
.detail-body span {
  flex: 1;
  color: var(--app-text, #303133);
  word-break: break-all;
}
.diff-json {
  flex: 1;
  background: var(--app-bg-soft, #fafbfc);
  border: 1px solid var(--app-border, #ebeef5);
  border-radius: 4px;
  padding: 10px 12px;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  max-height: 320px;
  overflow: auto;
}
.dim { color: var(--app-text-secondary, #909399); font-size: 11px; margin-left: 4px; }
</style>
