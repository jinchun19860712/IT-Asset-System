<template>
  <el-drawer
    v-model="visible"
    :size="drawerSize"
    direction="rtl"
    :with-header="false"
    class="device-detail-drawer"
    @closed="handleClosed"
  >
    <div v-loading="loading" class="detail-wrap">
      <!-- 头部 -->
      <div class="detail-header">
        <div class="header-main">
          <div class="title-row">
            <span class="dev-name">{{ device.name || '-' }}</span>
            <el-tag
              v-if="device.status_name"
              :color="device.status_color"
              effect="dark"
              size="small"
              class="status-tag"
            >{{ device.status_name }}</el-tag>
            <el-tag v-if="device.device_type" type="info" size="small">{{ device.device_type }}</el-tag>
          </div>
          <div class="sub-row">
            <span v-if="device.ip_address"><el-icon><Connection /></el-icon> {{ device.ip_address }}</span>
            <span v-if="device.brand || device.model">
              <el-icon><Box /></el-icon> {{ [device.brand, device.model].filter(Boolean).join(' ') }}
            </span>
            <span v-if="device.department"><el-icon><OfficeBuilding /></el-icon> {{ device.department }}</span>
            <span v-if="device.user"><el-icon><User /></el-icon> {{ device.user }}</span>
          </div>
        </div>
        <div class="header-actions">
          <el-button type="primary" :icon="Edit" @click="goEdit">编辑</el-button>
          <el-button :icon="Close" circle @click="visible = false" />
        </div>
      </div>

      <el-tabs v-model="activeTab" class="detail-tabs">
        <!-- 基本信息 -->
        <el-tab-pane label="基本信息" name="basic">
          <div class="section">
            <div class="section-title">身份标识</div>
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="设备名称">{{ device.name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="产品类型">{{ device.device_type || '-' }}</el-descriptions-item>
              <el-descriptions-item label="品牌">{{ device.brand || '-' }}</el-descriptions-item>
              <el-descriptions-item label="型号">{{ device.model || '-' }}</el-descriptions-item>
              <el-descriptions-item label="供应商">{{ device.supplier || '-' }}</el-descriptions-item>
              <el-descriptions-item label="服务编码">{{ device.service_code || '-' }}</el-descriptions-item>
              <el-descriptions-item label="上级设备">{{ device.parent_device_name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="停用日期">{{ device.disuse_date || '-' }}</el-descriptions-item>
            </el-descriptions>
          </div>

          <div class="section">
            <div class="section-title">网络参数</div>
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="IP 地址">{{ device.ip_address || '-' }}</el-descriptions-item>
              <el-descriptions-item label="子网掩码">{{ device.network_mask || '-' }}</el-descriptions-item>
              <el-descriptions-item label="MAC 地址">{{ device.mac_address || '-' }}</el-descriptions-item>
              <el-descriptions-item label="管理 VLAN">{{ device.management_vlan || '-' }}</el-descriptions-item>
              <el-descriptions-item label="BMC IP">{{ device.bmc_ip || '-' }}</el-descriptions-item>
              <el-descriptions-item label="BMC MAC">{{ device.bmc_mac || '-' }}</el-descriptions-item>
            </el-descriptions>
          </div>

          <div class="section">
            <div class="section-title">位置与归属</div>
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="所属机构">{{ device.folder_full_path || device.folder_name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="资产分类">{{ device.asset_folder_name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="使用部门">{{ device.department || '-' }}</el-descriptions-item>
              <el-descriptions-item label="使用人">{{ device.user || '-' }}</el-descriptions-item>
              <el-descriptions-item label="区域">{{ device.area || '-' }}</el-descriptions-item>
              <el-descriptions-item label="机房类型">{{ device.room_type || '-' }}</el-descriptions-item>
              <el-descriptions-item label="房间号">{{ device.room_number || '-' }}</el-descriptions-item>
              <el-descriptions-item label="机柜位置">
                <span v-if="device.rack_name">
                  {{ device.rack_name }} · U{{ device.rack_position }}
                  <span v-if="device.rack_units > 1">-U{{ device.rack_position + device.rack_units - 1 }}</span>
                  ({{ device.rack_face === 'rear' ? '后面板' : '前面板' }})
                </span>
                <span v-else>未上架</span>
              </el-descriptions-item>
            </el-descriptions>
          </div>

          <div class="section">
            <div class="section-title">管理方式</div>
            <div class="chip-row">
              <el-tag v-for="s in supportList" :key="s" size="small" type="success" effect="plain">{{ s }}</el-tag>
              <span v-if="!supportList.length" class="empty-hint">未标记任何管理方式</span>
            </div>
            <el-descriptions v-if="device.mgmt_username" :column="2" border size="small" style="margin-top: 10px">
              <el-descriptions-item label="管理账号">{{ device.mgmt_username }}</el-descriptions-item>
              <el-descriptions-item label="管理密码">
                <span v-if="showPassword">{{ device.mgmt_password || '-' }}</span>
                <span v-else>••••••••</span>
                <el-button link type="primary" size="small" @click="showPassword = !showPassword">
                  {{ showPassword ? '隐藏' : '显示' }}
                </el-button>
              </el-descriptions-item>
            </el-descriptions>
          </div>

          <div v-if="device.description || device.remark" class="section">
            <div class="section-title">描述与备注</div>
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item v-if="device.description" label="描述">{{ device.description }}</el-descriptions-item>
              <el-descriptions-item v-if="device.remark" label="备注">{{ device.remark }}</el-descriptions-item>
            </el-descriptions>
          </div>

          <div v-if="customValues.length" class="section">
            <div class="section-title">自定义字段</div>
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item v-for="cv in customValues" :key="cv.id" :label="cv.field_name || '未命名'">
                {{ cv.value || '-' }}
              </el-descriptions-item>
            </el-descriptions>
          </div>

          <div class="section meta-section">
            <span>创建于 {{ formatTime(device.created_at) }}</span>
            <span v-if="device.updated_at">最后更新 {{ formatTime(device.updated_at) }}</span>
          </div>
        </el-tab-pane>

        <!-- 端口 -->
        <el-tab-pane name="ports">
          <template #label>
            端口<el-badge v-if="ports.length" :value="ports.length" class="tab-badge" type="info" />
          </template>
          <el-table v-if="ports.length" :data="ports" size="small" border stripe max-height="520">
            <el-table-column prop="port_name" label="端口名" min-width="110" />
            <el-table-column label="方向" width="80">
              <template #default="{ row }">
                <el-tag :type="portTypeTag(row.port_type)" size="small" effect="plain">
                  {{ portTypeText(row.port_type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="connection_type" label="连接方式" width="95" />
            <el-table-column prop="port_speed" label="速率" width="85" />
            <el-table-column prop="vlan_info" label="VLAN" width="90" show-overflow-tooltip />
            <el-table-column label="对端设备" min-width="130">
              <template #default="{ row }">{{ row.peer_device_name || '-' }}</template>
            </el-table-column>
            <el-table-column label="对端端口" min-width="110">
              <template #default="{ row }">{{ row.peer_port_name || '-' }}</template>
            </el-table-column>
            <el-table-column prop="lag_group" label="聚合组" width="90" />
            <el-table-column prop="description" label="描述" min-width="120" show-overflow-tooltip />
          </el-table>
          <el-empty v-else description="该设备暂无端口记录" :image-size="90" />
        </el-tab-pane>

        <!-- SNMP -->
        <el-tab-pane name="snmp">
          <template #label>
            SNMP 监控<el-badge v-if="metrics.length" :value="metrics.length" class="tab-badge" type="info" />
          </template>
          <div class="snmp-bar">
            <div class="snmp-info">
              <span>模板：<b>{{ device.snmp_template_name || '未配置' }}</b></span>
              <span>协议：<b>{{ (device.snmp_version || 'v2c').toUpperCase() }}</b> · 端口 {{ device.snmp_port || 161 }}</span>
              <span v-if="device.snmp_last_poll_at">上次采集：{{ formatTime(device.snmp_last_poll_at) }}</span>
            </div>
            <div>
              <el-button size="small" :icon="Connection" :loading="testing" @click="testSnmp">连通性测试</el-button>
              <el-button size="small" type="primary" :icon="Refresh" :loading="polling" @click="pollSnmp">立即采集</el-button>
            </div>
          </div>
          <el-alert
            v-if="device.snmp_last_error"
            type="warning"
            :closable="false"
            show-icon
            class="snmp-error"
            title="上次采集存在错误"
            :description="device.snmp_last_error"
          />
          <el-table v-if="metrics.length" :data="metrics" size="small" border stripe max-height="480">
            <el-table-column prop="metric_name" label="指标" min-width="150" />
            <el-table-column label="当前值" width="130">
              <template #default="{ row }">
                <span :class="{ 'metric-bad': row.value === '-' || row.value === '异常' }">
                  {{ row.value }}<span v-if="row.unit && row.value !== '-'" class="unit"> {{ row.unit }}</span>
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="metric_oid" label="OID" min-width="180" show-overflow-tooltip />
            <el-table-column label="更新时间" width="160">
              <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="暂无监控数据，可点击「立即采集」" :image-size="90" />
        </el-tab-pane>

        <!-- 合同附件 -->
        <el-tab-pane name="contracts">
          <template #label>
            合同附件<el-badge v-if="contracts.length" :value="contracts.length" class="tab-badge" type="info" />
          </template>
          <el-table v-if="contracts.length" :data="contracts" size="small" border stripe max-height="520">
            <el-table-column prop="name" label="名称" min-width="180" show-overflow-tooltip />
            <el-table-column prop="supplier_name" label="供应商" min-width="120" />
            <el-table-column label="大小" width="100">
              <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
            </el-table-column>
            <el-table-column label="上传时间" width="160">
              <template #default="{ row }">{{ formatTime(row.uploaded_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="80" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="download(row)">下载</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="该设备暂无关联合同附件" :image-size="90" />
        </el-tab-pane>
      </el-tabs>
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Edit, Close, Refresh, Connection, Box, OfficeBuilding, User } from '@element-plus/icons-vue'
import { deviceApi, snmpApi, contractApi } from '../api'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  deviceId: { type: [Number, String], default: null }
})
const emit = defineEmits(['update:modelValue', 'refresh'])

const router = useRouter()
const visible = ref(props.modelValue)
const loading = ref(false)
const polling = ref(false)
const testing = ref(false)
const showPassword = ref(false)
const activeTab = ref('basic')

const device = ref({})
const metrics = ref([])
const contracts = ref([])

const drawerSize = computed(() => (window.innerWidth < 1200 ? '90%' : '860px'))
const ports = computed(() => device.value.ports || [])
const customValues = computed(() => (device.value.custom_values || []).filter(cv => cv.value))

const supportList = computed(() => {
  const map = {
    support_ssh2: 'SSH2', support_telnet: 'Telnet', support_web: 'Web',
    support_snmp: 'SNMP', support_rdp: 'RDP', support_console: 'Console'
  }
  const list = Object.entries(map).filter(([k]) => device.value[k]).map(([, v]) => v)
  const extra = (device.value.management_services || '').split(/[,，\s]+/).filter(Boolean)
  return [...new Set([...list, ...extra])]
})

watch(() => props.modelValue, v => {
  visible.value = v
  if (v && props.deviceId) load()
})
watch(visible, v => emit('update:modelValue', v))
watch(() => props.deviceId, id => {
  if (visible.value && id) load()
})

async function load() {
  loading.value = true
  activeTab.value = 'basic'
  showPassword.value = false
  try {
    const res = await deviceApi.getDetail(props.deviceId)
    device.value = res.data || {}
    // 监控值与合同并行拉取，任一失败不影响主体展示
    const [m, c] = await Promise.allSettled([
      snmpApi.getDeviceMetrics(props.deviceId),
      contractApi.list({ related_type: 'device', related_id: props.deviceId })
    ])
    metrics.value = m.status === 'fulfilled' ? (m.value.data || []) : []
    const cData = c.status === 'fulfilled' ? c.value.data : null
    contracts.value = Array.isArray(cData) ? cData : (cData?.items || [])
  } catch (e) {
    ElMessage.error('加载设备详情失败')
  } finally {
    loading.value = false
  }
}

async function pollSnmp() {
  if (!device.value.snmp_template_name) {
    ElMessage.warning('该设备未配置 SNMP 模板')
    return
  }
  polling.value = true
  try {
    const res = await snmpApi.pollDevice(props.deviceId)
    if (res.code === 0) ElMessage.success(res.message || '采集完成')
    else ElMessage.warning(res.message || '采集失败')
    const [d, m] = await Promise.all([
      deviceApi.getDetail(props.deviceId),
      snmpApi.getDeviceMetrics(props.deviceId)
    ])
    device.value = d.data || device.value
    metrics.value = m.data || []
    emit('refresh')
  } catch (e) {
    ElMessage.error('采集请求失败')
  } finally {
    polling.value = false
  }
}

async function testSnmp() {
  testing.value = true
  try {
    const res = await snmpApi.testDevice(props.deviceId)
    if (res.code === 0) {
      const sysName = (res.data?.items || []).find(i => i.label === '设备名称')
      ElMessage.success(`连接成功${sysName?.ok ? '：' + sysName.value : ''}`)
    } else {
      ElMessage.error(res.message || '连接失败')
    }
    const d = await deviceApi.getDetail(props.deviceId)
    device.value = d.data || device.value
  } catch (e) {
    ElMessage.error('测试请求失败')
  } finally {
    testing.value = false
  }
}

function goEdit() {
  visible.value = false
  router.push(`/devices/edit/${props.deviceId}`)
}

function portTypeText(t) {
  return { uplink: '上联', downlink: '下联', peer: '对等' }[t] || t || '-'
}

function portTypeTag(t) {
  return { uplink: 'warning', downlink: 'success', peer: 'info' }[t] || 'info'
}

function download(row) {
  window.open(contractApi.downloadUrl(row.id), '_blank')
}

function handleClosed() {
  metrics.value = []
  contracts.value = []
}

function formatTime(t) {
  if (!t) return '-'
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return t
  const p = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

function formatSize(bytes) {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}
</script>

<style scoped>
.detail-wrap {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px 14px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-blank);
}

.title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.dev-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  word-break: break-all;
}

.status-tag {
  border: none;
  color: #fff;
}

.sub-row {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.sub-row span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.detail-tabs {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 0 20px;
}

.detail-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow-y: auto;
  padding-bottom: 20px;
}

.section {
  margin-bottom: 18px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-regular);
  margin-bottom: 8px;
  padding-left: 8px;
  border-left: 3px solid var(--el-color-primary);
}

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.empty-hint {
  font-size: 13px;
  color: var(--el-text-color-placeholder);
}

.meta-section {
  display: flex;
  gap: 20px;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  padding-top: 6px;
  border-top: 1px dashed var(--el-border-color-lighter);
}

.snmp-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.snmp-info {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.snmp-error {
  margin-bottom: 12px;
}

.metric-bad {
  color: var(--el-color-danger);
}

.unit {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.tab-badge {
  margin-left: 6px;
  margin-top: -2px;
}

:deep(.el-descriptions__label) {
  width: 110px;
  color: var(--el-text-color-secondary);
}
</style>
