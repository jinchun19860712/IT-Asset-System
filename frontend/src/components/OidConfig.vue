<template>
  <div class="config-section">
    <el-alert
      title="SNMP OID配置说明"
      description="在此配置各品牌打印机的SNMP OID映射。系统会根据此配置自动轮询设备状态。请根据实际设备MIB文档填写OID。"
      type="info"
      show-icon
      :closable="false"
      style="margin-bottom: 15px"
    />

    <div class="toolbar">
      <el-button type="primary" size="small" @click="showAddTemplate">
        <el-icon><Plus /></el-icon> 添加模板
      </el-button>
      <el-button size="small" type="success" @click="saveConfig">
        <el-icon><Check /></el-icon> 保存配置
      </el-button>
      <el-button size="small" @click="loadConfig">
        <el-icon><Refresh /></el-icon> 刷新
      </el-button>
    </div>

    <el-collapse v-model="activeNames">
      <el-collapse-item v-for="(tpl, idx) in config.templates" :key="idx" :name="idx">
        <template #title>
          <div style="display: flex; align-items: center; gap: 10px; width: 100%;">
            <span style="font-weight: bold;">{{ tpl.name }}</span>
            <el-tag size="small" type="info">{{ tpl.vendor }}</el-tag>
            <el-button type="danger" size="small" link @click.stop="removeTemplate(idx)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </template>

        <el-form :model="tpl" label-width="100px" size="small">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="模板名称">
                <el-input v-model="tpl.name" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="厂商">
                <el-input v-model="tpl.vendor" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-divider>监控指标</el-divider>
          <div v-for="(metric, mIdx) in tpl.metrics" :key="mIdx" class="metric-row">
            <el-row :gutter="10">
              <el-col :span="4">
                <el-input v-model="metric.name" placeholder="指标名称" />
              </el-col>
              <el-col :span="6">
                <el-input v-model="metric.oid" placeholder="OID，如 1.3.6.1.2.1.43.8.2.1.10.1" />
              </el-col>
              <el-col :span="3">
                <el-select v-model="metric.type" placeholder="类型">
                  <el-option label="整数" value="integer" />
                  <el-option label="字符串" value="string" />
                  <el-option label="布尔" value="boolean" />
                  <el-option label="百分比" value="percentage" />
                  <el-option label="计数器" value="counter" />
                </el-select>
              </el-col>
              <el-col :span="4">
                <el-input v-model="metric.description" placeholder="说明" />
              </el-col>
              <el-col :span="4">
                <el-input v-model="metric.warning_threshold" placeholder="告警阈值" v-if="metric.type === 'percentage'" />
              </el-col>
              <el-col :span="3">
                <el-button type="danger" size="small" @click="removeMetric(tpl, mIdx)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </el-col>
            </el-row>
          </div>
          <el-button type="primary" size="small" link @click="addMetric(tpl)">
            <el-icon><Plus /></el-icon> 添加指标
          </el-button>
        </el-form>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { configApi } from '../api/index.js'

const activeNames = ref([0])
const config = ref({ templates: [] })

const loadConfig = async () => {
  const res = await configApi.getOid()
  if (res.code === 0) {
    config.value = res.data || { templates: [] }
  }
}

const saveConfig = async () => {
  try {
    await configApi.updateOid(config.value)
    ElMessage.success('配置已保存')
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

const showAddTemplate = () => {
  config.value.templates.push({
    name: '新模板',
    vendor: '未知',
    metrics: []
  })
  activeNames.value = [config.value.templates.length - 1]
}

const removeTemplate = (idx) => {
  config.value.templates.splice(idx, 1)
}

const addMetric = (tpl) => {
  tpl.metrics.push({
    name: '',
    oid: '',
    type: 'integer',
    description: ''
  })
}

const removeMetric = (tpl, idx) => {
  tpl.metrics.splice(idx, 1)
}

onMounted(loadConfig)
</script>

<style scoped>
.config-section {
  padding: 10px;
}
.toolbar {
  margin-bottom: 15px;
}
.metric-row {
  margin-bottom: 10px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}
</style>
