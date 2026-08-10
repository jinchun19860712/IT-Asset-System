<template>
  <div class="device-form">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ isEdit ? '编辑设备' : '添加设备' }}</span>
        </div>
      </template>

      <el-form :model="form" :rules="rules" ref="formRef" label-width="110px">
        <!-- 基本信息 -->
        <el-divider>基本信息</el-divider>
        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
            <el-form-item label="设备名称" prop="name">
              <el-input v-model="form.name" placeholder="如：sw-h3c-s7510x" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="设备类型">
              <el-select
                v-model="form.device_type"
                placeholder="选择已有类型或输入新类型"
                filterable
                allow-create
                default-first-option
                clearable
                style="width: 100%"
              >
                <el-option v-for="t in deviceTypeOptions" :key="t" :label="t" :value="t" />
              </el-select>
              <div class="folder-path-hint">
                仅作设备型号/类型的快速标签（不会写入字典）。如需管理预定义的产品类型并自动推导资产分类，请用下方「"关联产品类型"」
              </div>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
            <el-form-item label="关联产品类型">
              <el-select
                v-model="form.product_type_id"
                placeholder="选择预定义类型（可选）"
                filterable
                clearable
                style="width: 100%"
                @change="onProductTypeChange"
              >
                <el-option v-for="pt in productTypeItems" :key="pt.id" :label="ptLabel(pt)" :value="pt.id" />
              </el-select>
              <div class="folder-path-hint">来自「产品类型管理」，选择后将自动显示该类型专属字段并推导资产分类</div>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
            <el-form-item label="品牌">
              <el-select
                v-model="form.brand"
                placeholder="选择或输入品牌"
                filterable
                allow-create
                default-first-option
                clearable
                style="width: 100%"
                @change="(v) => onDictFieldChange('brand', v)"
              >
                <el-option v-for="b in brandOptions" :key="b" :label="b" :value="b" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="型号">
              <el-input v-model="form.model" placeholder="如：S7510X" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
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
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
            <el-form-item label="父设备">
              <el-select v-model="form.parent_device_id" placeholder="选择父设备" clearable filterable style="width: 100%">
                <el-option v-for="d in selectableParents" :key="d.id" :label="d.name" :value="d.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="16">
            <el-form-item label="资产分类">
              <el-tree-select
                v-model="form.asset_folder_id"
                :data="assetFolderTree"
                :props="{ label: 'name', value: 'id', children: 'children' }"
                placeholder="选择资产分类（设备资产树）"
                style="width: 100%"
                check-strictly
                clearable
                filterable
              />
              <div class="folder-path-hint" v-if="currentAssetPath">
                完整路径：<strong>{{ currentAssetPath }}</strong>
              </div>
              <div class="folder-path-hint" v-else>
                与左侧「设备资产」树对应，可按 资产 / 组件 / IT / 非IT 归类
              </div>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- SNMP 监控配置 -->
        <el-divider>SNMP 监控配置</el-divider>
        <el-alert
          v-if="!form.device_type"
          title="建议先选择「设备类型」"
          description="选定类型后，下方只会列出适用于该类型的 SNMP 模板（例如打印机只显示打印机模板）。"
          type="info" show-icon :closable="false" style="margin-bottom: 15px"
        />
        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
            <el-form-item label="SNMP模板">
              <el-select
                v-model="form.snmp_template_name"
                placeholder="选择SNMP监控模板"
                clearable
                style="width: 100%"
                @change="onTemplateChange"
              >
                <el-option v-for="t in snmpTemplates" :key="t.name" :label="t.name" :value="t.name">
                  <span>{{ t.name }}</span>
                  <el-tag size="small" type="info" style="margin-left: 8px">{{ t.vendor }}</el-tag>
                  <span class="opt-count">{{ t.metric_count }} 项指标</span>
                </el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="">
              <el-checkbox v-model="showAllTemplates" @change="loadSnmpTemplates">
                显示全部模板（不按设备类型过滤）
              </el-checkbox>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 指标勾选区：默认不勾任何项，由用户自行挑选 -->
        <div v-if="currentTemplateMetrics.length > 0" class="metrics-selector">
          <div class="metrics-title">
            <span class="metrics-label">
              选择要监控的指标
              <el-tag size="small" :type="selectedMetrics.length ? 'primary' : 'warning'">
                已选 {{ selectedMetrics.length }} / {{ currentTemplateMetrics.length }}
              </el-tag>
            </span>
            <div class="metrics-ops">
              <el-button size="small" text type="primary" @click="selectAllMetrics">全选</el-button>
              <el-button size="small" text @click="clearAllMetrics">清空</el-button>
            </div>
          </div>

          <el-alert
            v-if="selectedMetrics.length === 0"
            title="未勾选任何指标，系统不会为该设备采集监控值，设备列表中也不会出现对应的列。"
            type="warning" show-icon :closable="false" style="margin-bottom: 12px"
          />

          <el-checkbox-group v-model="selectedMetrics" class="metric-grid">
            <el-checkbox v-for="m in currentTemplateMetrics" :key="m.oid" :value="m.name" class="metric-item">
              <div class="metric-box">
                <span class="metric-name">
                  {{ m.name }}
                  <span class="metric-unit" v-if="m.unit">（{{ m.unit }}）</span>
                </span>
                <span class="metric-oid">{{ m.oid }}</span>
              </div>
            </el-checkbox>
          </el-checkbox-group>

          <div class="metrics-tip">
            勾选的指标会作为独立的列出现在设备列表中，可在列表的「列设置」里控制显示与否。
          </div>
        </div>

        <!-- 端口与连接 -->
        <el-divider>端口与连接</el-divider>
        <el-row :gutter="20" style="margin-bottom: 12px;">
          <el-col :xs="24" :sm="12">
            <el-form-item label="端口类型">
              <el-select v-model="form.port_types" multiple style="width: 100%" placeholder="可多选">
                <el-option label="电口" value="electric" />
                <el-option label="光口" value="optical" />
                <el-option label="管理口" value="mgmt" />
                <el-option label="Console口" value="console" />
              </el-select>
              <div class="folder-path-hint">勾选后会展开对应的「数量」输入框</div>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="端口总数">
              <el-input
                :model-value="totalPortCount"
                readonly
                size="default"
                style="width: 100%"
                placeholder="由各类型自动汇总"
              >
                <template #append>个</template>
              </el-input>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 按端口类型分别填写数量（动态渲染，仅显示已勾选的类型） -->
        <div v-if="form.port_types.length" class="ports-counts">
          <div class="ports-counts-title">各类型数量明细</div>
          <el-row :gutter="12">
            <el-col
              v-for="pt in form.port_types"
              :key="pt"
              :xs="12" :sm="8" :md="6"
              class="ports-count-col"
            >
              <div class="ports-count-item">
                <span class="ports-count-label">{{ portTypeLabel(pt) }}</span>
                <el-input-number
                  :model-value="form.port_count_by_type?.[pt] || 0"
                  :min="0" :max="256"
                  size="small"
                  style="width: 100%"
                  @change="(v) => setPortCountByType(pt, v)"
                />
              </div>
            </el-col>
          </el-row>
        </div>
        <div v-else class="ports-counts-empty">
          勾选「端口类型」后，此处显示对应数量明细输入框
        </div>

        <div class="ports-section">
          <div class="ports-head">
            <span class="ports-hint">记录本设备的上联 / 下联端口及对端设备，用于生成网络拓扑图</span>
            <el-button type="primary" size="small" @click="addPort">
              <el-icon><Plus /></el-icon> 添加端口
            </el-button>
          </div>

          <el-table :data="ports" size="small" border v-if="ports.length" class="ports-table">
            <el-table-column label="端口名称" min-width="170">
              <template #default="{ row }">
                <el-input v-model="row.port_name" size="small" placeholder="GigabitEthernet1/0/1" />
              </template>
            </el-table-column>

            <el-table-column label="方向" width="110">
              <template #default="{ row }">
                <el-select v-model="row.port_type" size="small">
                  <el-option label="上联" value="uplink" />
                  <el-option label="下联" value="downlink" />
                  <el-option label="互联" value="peer" />
                </el-select>
              </template>
            </el-table-column>

            <el-table-column label="连接类型" width="130">
              <template #default="{ row }">
                <el-select v-model="row.connection_type" size="small" @change="onConnTypeChange(row)">
                  <el-option label="Access" value="access" />
                  <el-option label="Trunk" value="trunk" />
                  <el-option label="Hybrid" value="hybrid" />
                  <el-option label="聚合" value="aggregate" />
                  <el-option label="堆叠" value="stack" />
                  <el-option label="三层路由" value="routed" />
                </el-select>
              </template>
            </el-table-column>

            <!-- 条件字段：聚合口显示聚合组号，堆叠显示成员号，二层口显示VLAN -->
            <el-table-column label="附加参数" min-width="200">
              <template #default="{ row }">
                <div v-if="row.connection_type === 'aggregate'" class="extra-cell">
                  <el-input v-model="row.lag_group" size="small" placeholder="聚合组号 如 BAGG1">
                    <template #prepend>聚合口</template>
                  </el-input>
                  <el-select v-model="row.lag_mode" size="small" placeholder="模式" style="width: 100px">
                    <el-option label="LACP" value="lacp" />
                    <el-option label="静态" value="static" />
                  </el-select>
                </div>
                <el-input v-else-if="row.connection_type === 'stack'" v-model="row.stack_id"
                          size="small" placeholder="堆叠成员号 如 1">
                  <template #prepend>成员号</template>
                </el-input>
                <el-input v-else-if="row.connection_type === 'access'" v-model="row.vlan_info"
                          size="small" placeholder="如 VLAN100">
                  <template #prepend>VLAN</template>
                </el-input>
                <el-input v-else-if="row.connection_type === 'trunk' || row.connection_type === 'hybrid'"
                          v-model="row.vlan_info" size="small" placeholder="允许VLAN 如 1,10-20,100">
                  <template #prepend>允许</template>
                </el-input>
                <el-text v-else type="info" size="small">无需附加参数</el-text>
              </template>
            </el-table-column>

            <el-table-column label="对端设备" min-width="150">
              <template #default="{ row }">
                <el-select v-model="row.peer_device_id" size="small" clearable filterable placeholder="选择对端">
                  <el-option v-for="d in selectableParents" :key="d.id" :label="d.name" :value="d.id" />
                </el-select>
              </template>
            </el-table-column>

            <el-table-column label="对端端口" min-width="150">
              <template #default="{ row }">
                <el-input v-model="row.peer_port_name" size="small" placeholder="对端端口名" />
              </template>
            </el-table-column>

            <el-table-column label="速率" width="100">
              <template #default="{ row }">
                <el-select v-model="row.port_speed" size="small" clearable placeholder="速率">
                  <el-option label="100M" value="100M" />
                  <el-option label="1G" value="1G" />
                  <el-option label="2.5G" value="2.5G" />
                  <el-option label="10G" value="10G" />
                  <el-option label="25G" value="25G" />
                  <el-option label="40G" value="40G" />
                  <el-option label="100G" value="100G" />
                </el-select>
              </template>
            </el-table-column>

            <el-table-column label="操作" width="70" align="center">
              <template #default="{ $index }">
                <el-button type="danger" size="small" link @click="removePort($index)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-empty v-else description="尚未添加端口" :image-size="60" />
        </div>

        <!-- 网络信息 -->
        <el-divider>网络信息</el-divider>
        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
            <el-form-item label="管理IP">
              <el-input v-model="form.ip_address" placeholder="172.20.10.1" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="子网掩码">
              <el-input v-model="form.network_mask" placeholder="23" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="MAC地址">
              <el-input v-model="form.mac_address" placeholder="00:1A:2B:3C:4D:5E" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
            <el-form-item label="管理VLAN">
              <el-input v-model="form.management_vlan" placeholder="7" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="BMC IP">
              <el-input v-model="form.bmc_ip" placeholder="172.0.0.19" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="BMC MAC">
              <el-input v-model="form.bmc_mac" placeholder="9C-C2-C4-02-0A-86" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 位置信息 -->
        <el-divider>位置信息</el-divider>
        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
            <el-form-item label="区域">
              <el-input v-model="form.area" placeholder="如：行政楼" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="房间类型">
              <el-input v-model="form.room_type" placeholder="如：中心机房" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="房间号">
              <el-input v-model="form.room_number" placeholder="如：206" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
            <el-form-item label="所在机柜">
              <el-select v-model="form.rack_id" placeholder="选择机柜" clearable filterable style="width: 100%">
                <el-option v-for="r in rackList" :key="r.id" :label="r.name" :value="r.id">
                  <span>{{ r.name }}</span>
                  <span class="opt-count">{{ r.used_units }}/{{ r.u_height }}U</span>
                </el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="起始U位">
              <el-input-number v-model="form.rack_position" :min="1" :max="60" controls-position="right"
                               style="width: 100%" placeholder="从下往上数" :disabled="!form.rack_id" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="占用U数">
              <el-input-number v-model="form.rack_units" :min="1" :max="20" controls-position="right"
                               style="width: 100%" :disabled="!form.rack_id" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 资产信息 -->
        <el-divider>资产信息</el-divider>
        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
            <el-form-item label="资产编号">
              <el-input v-model="form.service_code" placeholder="如：210235A1YHX2290P0016" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="设备状态">
              <el-select v-model="form.status_id" placeholder="选择状态" style="width: 100%">
                <el-option v-for="s in statusList" :key="s.id" :label="s.name" :value="s.id">
                  <span :style="{ color: s.color }">●</span> {{ s.name }}
                </el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="停用/维修日期">
              <el-input v-model="form.disuse_date" placeholder="如：2024-06-01" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
            <el-form-item label="使用部门">
              <el-tree-select
                v-model="form.folder_id"
                :data="folderTree"
                :props="{ label: 'name', value: 'id', children: 'children' }"
                placeholder="选择使用部门（组织机构树）"
                style="width: 100%"
                check-strictly
                filterable
                clearable
                @change="onFolderChange"
              />
              <div class="folder-path-hint" v-if="currentFolderPath">
                完整路径：<strong>{{ currentFolderPath }}</strong>
              </div>
              <div class="folder-path-hint" v-else>
                选择部门后，设备会归入「组织机构」对应部门下
              </div>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="使用人员">
              <el-input v-model="form.user" placeholder="使用人员" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 管理方式 -->
        <el-divider>支持的管理方式</el-divider>
        <el-form-item label="">
          <el-checkbox v-model="form.support_ssh2">SSH2</el-checkbox>
          <el-checkbox v-model="form.support_telnet">Telnet</el-checkbox>
          <el-checkbox v-model="form.support_web">Web</el-checkbox>
          <el-checkbox v-model="form.support_snmp">SNMP</el-checkbox>
          <el-checkbox v-model="form.support_rdp">RDP</el-checkbox>
          <el-checkbox v-model="form.support_console">Console</el-checkbox>
        </el-form-item>
        <el-form-item label="管理服务">
          <el-input v-model="form.management_services" placeholder="如：SSH2, Web, SNMP, Console" />
        </el-form-item>

        <!-- 管理账号 -->
        <el-divider>管理账号</el-divider>
        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
            <el-form-item label="用户名">
              <el-input v-model="form.mgmt_username" placeholder="admin" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="密码">
              <el-input v-model="form.mgmt_password" type="password" show-password placeholder="密码" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 备注 -->
        <el-form-item label="备注说明">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="功能/用途说明" />
        </el-form-item>

        <!-- 自定义字段（旧系统兼容） -->
        <el-divider v-if="customFields.length > 0 && layoutFields.length === 0">自定义字段</el-divider>
        <el-row :gutter="20" v-for="field in (layoutFields.length > 0 ? [] : customFields)" :key="field.id">
          <el-col :xs="24" :sm="12">
            <el-form-item :label="field.name" :required="field.is_required">
              <CustomFieldInput :field="field" v-model="customValues[field.id]" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 产品类型专属字段（新系统，动态渲染） -->
        <el-divider v-if="form.product_type_id">「{{ layoutTypeName }}」专属字段</el-divider>
        <!-- 已配置专属字段：直接渲染 -->
        <el-row v-if="form.product_type_id && layoutFields.length > 0" :gutter="20">
          <el-col :span="12" v-for="field in layoutFields" :key="field.id">
            <el-form-item :label="field.name" :required="field.is_required">
              <CustomFieldInput :field="field" v-model="layoutValues[field.id]" />
            </el-form-item>
          </el-col>
        </el-row>
        <!-- 已选产品类型但未配置专属字段：给引导提示 -->
        <el-alert
          v-else-if="form.product_type_id && layoutFields.length === 0"
          type="info"
          :closable="false"
          show-icon
          class="layout-config-tip"
        >
          <template #title>
            <span>该产品类型尚未配置专属字段</span>
          </template>
          <div class="layout-config-tip-body">
            去「<el-link type="primary" :underline="false" @click="goProductTypeManager">产品类型管理</el-link>」页面，
            找到「<strong>{{ layoutTypeName }}</strong>」点击「"字段布局"」按钮，从左侧穿梭框选择字段移到右侧即可。
          </div>
        </el-alert>

        <el-divider>合同附件</el-divider>
        <ContractAttach ref="contractAttachRef" related-type="device" :related-id="deviceId" />

        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="submitting">保存</el-button>
          <el-button @click="$router.push('/devices')">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import {
  deviceApi, statusApi, customFieldApi, folderApi, snmpApi, rackApi, dictApi, productTypeApi
} from '../api/index.js'
import ContractAttach from '../components/ContractAttach.vue'
import CustomFieldInput from '../components/CustomFieldInput.vue'

const route = useRoute()
const router = useRouter()
const formRef = ref()
const contractAttachRef = ref()
const isEdit = ref(false)
const deviceId = ref(null)
const submitting = ref(false)

const form = ref({
  name: '', device_type: '', product_type_id: null, brand: '', model: '', parent_device_id: null,
  snmp_template_name: '', snmp_selected_metrics: '',
  ip_address: '', network_mask: '', mac_address: '', management_vlan: '',
  area: '', room_type: '', room_number: '',
  rack_id: null, rack_position: null, rack_units: 1, rack_face: 'front',
  service_code: '', status_id: null, disuse_date: '', department: '', user: '',
  support_ssh2: false, support_telnet: false, support_web: false,
  support_snmp: false, support_rdp: false, support_console: false,
  management_services: '',
  port_count: 0, port_types: [], port_count_by_type: {},
  bmc_ip: '', bmc_mac: '', mgmt_username: '', mgmt_password: '',
  folder_id: null, asset_folder_id: null, supplier: '', description: ''
})

const rules = {
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }]
}

// 端口类型枚举（与后端 models.Device.port_types 保持一致）
const PORT_TYPE_OPTIONS = [
  { value: 'electric', label: '电口' },
  { value: 'optical', label: '光口' },
  { value: 'mgmt', label: '管理口' },
  { value: 'console', label: 'Console口' }
]
const portTypeLabel = (v) => PORT_TYPE_OPTIONS.find(o => o.value === v)?.label || v

// 各类型端口数量（自动汇总）
const totalPortCount = computed(() => {
  const m = form.value.port_count_by_type || {}
  let total = 0
  for (const k of (form.value.port_types || [])) {
    total += Number(m[k] || 0)
  }
  return total
})

const setPortCountByType = (type, val) => {
  if (!form.value.port_count_by_type) form.value.port_count_by_type = {}
  form.value.port_count_by_type[type] = Number(val || 0)
  // 同步更新 form.port_count（避免后端依赖自动汇总导致状态显示延迟）
  form.value.port_count = totalPortCount.value
}

// 当勾选端口类型变化时，自动清理已不存在的类型；新增类型默认 0
watch(() => form.value.port_types, (newTypes) => {
  const m = form.value.port_count_by_type || {}
  const next = {}
  for (const t of newTypes) {
    next[t] = Number(m[t] || 0)
  }
  form.value.port_count_by_type = next
  form.value.port_count = totalPortCount.value
})

const deviceTypes = ref([])
const statusList = ref([])
const folderTree = ref([])
const assetFolderTree = ref([])
const assetFolderIndex = ref({})
// 字典：设备类型 / 品牌 / 供应商（产品类型已迁移到独立页面）
const dictDeviceTypes = ref([])
const dictBrands = ref([])
const dictSuppliers = ref([])
const allDevices = ref([])
const customFields = ref([])
const customValues = ref({})
// 新系统：产品类型 → 布局字段
const productTypeItems = ref([])
const layoutFields = ref([])
const layoutValues = ref({})
const layoutTypeName = ref('')

const ptLabel = (pt) => {
  const catMap = { 'asset,it': '·IT资产', 'asset,non_it': '·非IT资产', 'component,it': '·IT组件', 'component,non_it': '·非IT组件' }
  const cat = catMap[`${pt.asset_type},${pt.asset_category}`] || ''
  return `${pt.name} ${cat}`
}

const loadProductTypes = async () => {
  try {
    const res = await productTypeApi.list(true)
    if (res.code === 0) productTypeItems.value = res.data || []
  } catch (e) { /* ignore */ }
}

const onProductTypeChange = async (ptId) => {
  layoutFields.value = []
  layoutValues.value = {}
  layoutTypeName.value = ''
  if (!ptId) return
  try {
    const res = await productTypeApi.getFields(ptId)
    if (res.code === 0) {
      layoutFields.value = res.data || []
      // 选中产品类型时，如果该类型有 device_type 关联且当前 device_type 为空，自动回填
      const pt = productTypeItems.value.find(p => p.id === ptId)
      layoutTypeName.value = pt?.name || ''
      if (pt?.device_type && !(form.value.device_type || '').trim()) {
        form.value.device_type = pt.device_type
      }
      // 初始化默认值
      for (const f of layoutFields.value) {
        const dv = f.config?.default_value
        if (dv !== undefined && dv !== null) layoutValues.value[f.id] = dv
        else if (f.field_type === 'checkbox') layoutValues.value[f.id] = false
        else if (f.field_type === 'multi_select') layoutValues.value[f.id] = []
        else layoutValues.value[f.id] = ''
      }
    }
  } catch (e) { /* ignore */ }
}

// 引导提示点击：跳转到产品类型管理页面
const goProductTypeManager = () => {
  router.push('/product-types')
}
const snmpTemplates = ref([])
const currentTemplateMetrics = ref([])
const selectedMetrics = ref([])
const rackList = ref([])
const ports = ref([])
const showAllTemplates = ref(false)

// 「设备类型」下拉数据 = 字典项（基础数据 → 设备类型，后端启动时已注入 PRESET 兜底）
//                       + 库里已用过的（保证编辑已有设备时仍能保留原值）
// 用户在「基础数据 → 设备类型」里增删改即可统一管理
const deviceTypeOptions = computed(() => {
  return Array.from(new Set([...dictDeviceTypes.value, ...deviceTypes.value])).filter(Boolean)
})

const brandOptions = computed(() => Array.from(new Set(dictBrands.value)).filter(Boolean))
const supplierOptions = computed(() => Array.from(new Set(dictSuppliers.value)).filter(Boolean))

// 下拉里 allow-create 出来的新值，顺手写进字典，省得再去基础数据页补录
const onDictFieldChange = async (dictType, value) => {
  const v = (value || '').trim()
  if (!v) return
  const pool = dictType === 'brand' ? dictBrands : dictSuppliers
  if (pool.value.includes(v)) return
  try {
    await dictApi.create({ type: dictType, name: v, sort_order: 0, enabled: true })
    pool.value = [...pool.value, v]
  } catch (e) {
    // 字典写入失败不影响设备保存，值仍会存到设备上
    console.error('新增字典项失败', e)
  }
}

// 父设备 / 对端设备候选：排除自身，避免自己连自己
const selectableParents = computed(() =>
  allDevices.value.filter(d => !isEdit.value || d.id !== Number(deviceId.value))
)

// 扁平化文件夹树，便于按 id 反查路径与部门
const folderIndex = ref({})

const flattenTree = (nodes) => {
  const map = {}
  const walk = (list) => {
    for (const n of list || []) {
      map[n.id] = n
      if (n.children) walk(n.children)
    }
  }
  walk(nodes)
  return map
}

const currentFolderPath = computed(() => {
  const node = folderIndex.value[form.value.folder_id]
  return node ? (node.full_path || node.name) : ''
})

const currentAssetPath = computed(() => {
  const node = assetFolderIndex.value[form.value.asset_folder_id]
  return node ? (node.full_path || node.name) : ''
})

// ========== 加载 ==========
const loadSnmpTemplates = async () => {
  try {
    const dt = showAllTemplates.value ? null : (form.value.device_type || null)
    const res = await snmpApi.getTemplates(dt)
    if (res.code === 0) snmpTemplates.value = res.data || []
  } catch (e) {
    snmpTemplates.value = []
  }
}

const loadTemplateMetrics = async (templateName) => {
  if (!templateName) {
    currentTemplateMetrics.value = []
    return
  }
  try {
    const res = await snmpApi.getTemplateMetrics(templateName)
    currentTemplateMetrics.value = res.code === 0 ? (res.data || []) : []
  } catch (e) {
    currentTemplateMetrics.value = []
  }
}

const loadOptions = async () => {
  try {
    const [typesRes, statusRes, fieldsRes, folderRes, allDevRes, rackRes, assetRes, dictRes] =
      await Promise.all([
        deviceApi.getTypes(),
        statusApi.getList(),
        customFieldApi.getList(),
        folderApi.getTree('org'),
        deviceApi.getAll(),
        rackApi.getList(),
        folderApi.getTree('asset'),
        dictApi.getAll()
      ])
    if (typesRes.code === 0) deviceTypes.value = typesRes.data || []
    if (statusRes.code === 0) statusList.value = statusRes.data || []
    if (fieldsRes.code === 0) customFields.value = fieldsRes.data || []
    if (folderRes.code === 0) {
      folderTree.value = folderRes.data || []
      folderIndex.value = flattenTree(folderRes.data)
    }
    if (allDevRes.code === 0) allDevices.value = allDevRes.data || []
    if (rackRes.code === 0) rackList.value = rackRes.data || []
    if (assetRes.code === 0) {
      assetFolderTree.value = assetRes.data || []
      assetFolderIndex.value = flattenTree(assetRes.data)
    }
    if (dictRes.code === 0) {
      const g = dictRes.data || {}
      const pick = (arr) => (arr || []).filter(x => x.enabled !== false).map(x => x.name)
      // 注：product_type 已迁移到独立「产品类型管理」页，不再从字典读取
      dictDeviceTypes.value = pick(g.device_type)
      dictBrands.value = pick(g.brand)
      dictSuppliers.value = pick(g.supplier)
    }
  } catch (e) {
    console.error('加载选项失败', e)
    ElMessage.error('部分数据加载失败，请刷新重试')
  }
}

const loadDetail = async () => {
  if (!isEdit.value) return
  try {
    const res = await deviceApi.getDetail(deviceId.value)
    if (res.code !== 0) return
    const d = res.data
    form.value = {
      name: d.name, device_type: d.device_type, product_type_id: d.product_type_id || null,
      brand: d.brand, model: d.model,
      parent_device_id: d.parent_device_id,
      snmp_template_name: d.snmp_template_name || '',
      snmp_selected_metrics: d.snmp_selected_metrics || '',
      ip_address: d.ip_address, network_mask: d.network_mask,
      mac_address: d.mac_address, management_vlan: d.management_vlan,
      area: d.area, room_type: d.room_type, room_number: d.room_number,
      rack_id: d.rack_id, rack_position: d.rack_position,
      rack_units: d.rack_units || 1, rack_face: d.rack_face || 'front',
      service_code: d.service_code, status_id: d.status_id,
      disuse_date: d.disuse_date, department: d.department, user: d.user,
      support_ssh2: d.support_ssh2, support_telnet: d.support_telnet,
      support_web: d.support_web, support_snmp: d.support_snmp,
      support_rdp: d.support_rdp, support_console: d.support_console,
      management_services: d.management_services,
      port_count: d.port_count || 0,
      port_types: Array.isArray(d.port_types) ? d.port_types : [],
      port_count_by_type: (d.port_count_by_type && typeof d.port_count_by_type === 'object') ? d.port_count_by_type : {},
      bmc_ip: d.bmc_ip, bmc_mac: d.bmc_mac,
      mgmt_username: d.mgmt_username, mgmt_password: d.mgmt_password,
      folder_id: d.folder_id, asset_folder_id: d.asset_folder_id ?? null,
      supplier: d.supplier || '', description: d.description
    }
    ;(d.custom_values || []).forEach(cv => { customValues.value[cv.field_id] = cv.value })

    // 加载产品类型布局字段并回填值
    if (d.product_type_id) {
      await onProductTypeChange(d.product_type_id)
      // 回填已有的自定义值（从 custom_values 合并到 layoutValues）
      // 注意：multi_select 类型存的是逗号分隔字符串，回填时需还原成数组
      const fieldMap = Object.fromEntries(layoutFields.value.map(f => [f.id, f]))
      ;(d.custom_values || []).forEach(cv => {
        if (!fieldMap[cv.field_id]) return
        const ft = fieldMap[cv.field_id].field_type
        if (ft === 'multi_select') {
          layoutValues.value[cv.field_id] = String(cv.value || '').split(',').filter(Boolean)
        } else if (ft === 'checkbox') {
          layoutValues.value[cv.field_id] = cv.value === true || cv.value === 'true' || cv.value === '1'
        } else if (ft === 'number') {
          layoutValues.value[cv.field_id] = cv.value === '' || cv.value == null ? '' : Number(cv.value)
        } else {
          layoutValues.value[cv.field_id] = cv.value
        }
      })
    }

    ports.value = (d.ports || []).map(p => ({
      port_name: p.port_name || '',
      port_type: p.port_type || 'downlink',
      connection_type: p.connection_type || 'access',
      peer_device_id: p.peer_device_id,
      peer_port_name: p.peer_port_name || '',
      lag_group: p.lag_group || '',
      lag_mode: p.lag_mode || '',
      stack_id: p.stack_id || '',
      vlan_info: p.vlan_info || '',
      port_speed: p.port_speed || '',
      description: p.description || ''
    }))

    // 编辑态：模板列表按该设备类型过滤，再回填已勾选的指标
    await loadSnmpTemplates()
    if (form.value.snmp_template_name) {
      await loadTemplateMetrics(form.value.snmp_template_name)
      // 若该模板不在过滤结果里（比如类型改过），自动放开过滤，避免下拉显示空白
      if (!snmpTemplates.value.some(t => t.name === form.value.snmp_template_name)) {
        showAllTemplates.value = true
        await loadSnmpTemplates()
      }
      try {
        selectedMetrics.value = d.snmp_selected_metrics
          ? JSON.parse(d.snmp_selected_metrics) : []
      } catch (e) {
        selectedMetrics.value = []
      }
    }
  } catch (e) {
    console.error('加载详情失败', e)
  }
}

// ========== 交互 ==========
// 「设备类型」变化时：仅同步 SNMP 模板 + 输入新值时写入「设备类型」字典
const onDeviceTypeChange = async () => {
  const v = (form.value.device_type || '').trim()
  if (v && !dictDeviceTypes.value.includes(v)) {
    try {
      await dictApi.create({ type: 'device_type', name: v, sort_order: 0, enabled: true })
      dictDeviceTypes.value = [...dictDeviceTypes.value, v]
    } catch (e) { /* ignore */ }
  }
  await loadSnmpTemplates()
  // 类型变化后，原模板若已不适用则清空，避免出现类型与模板不匹配的组合
  if (form.value.snmp_template_name &&
      !snmpTemplates.value.some(t => t.name === form.value.snmp_template_name)) {
    form.value.snmp_template_name = ''
    currentTemplateMetrics.value = []
    selectedMetrics.value = []
  }
}

const onTemplateChange = async (val) => {
  // 需求：选模板后不自动打包全部指标，交给用户自己勾
  selectedMetrics.value = []
  await loadTemplateMetrics(val)
}

const selectAllMetrics = () => {
  selectedMetrics.value = currentTemplateMetrics.value.map(m => m.name)
}
const clearAllMetrics = () => { selectedMetrics.value = [] }

const onFolderChange = (folderId) => {
  // 使用部门决定 department：选部门即回填，清空部门即清空派生值
  if (!folderId) {
    form.value.department = ''
    return
  }
  const node = folderIndex.value[folderId]
  if (!node) return
  const dept = node.effective_department
  if (dept) form.value.department = dept
}

const addPort = () => {
  ports.value.push({
    port_name: '', port_type: 'downlink', connection_type: 'access',
    peer_device_id: null, peer_port_name: '',
    lag_group: '', lag_mode: '', stack_id: '', vlan_info: '',
    port_speed: '', description: ''
  })
}

const removePort = (index) => { ports.value.splice(index, 1) }

const onConnTypeChange = (row) => {
  // 切换连接类型时清掉不再适用的附加参数，避免脏数据带到后端
  if (row.connection_type !== 'aggregate') { row.lag_group = ''; row.lag_mode = '' }
  if (row.connection_type !== 'stack') row.stack_id = ''
  if (!['access', 'trunk', 'hybrid'].includes(row.connection_type)) row.vlan_info = ''
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
  } catch (e) {
    // Element Plus validate 失败时 reject，已由组件自己显示错误
    return
  }

  const invalidPort = ports.value.find(p => !p.port_name.trim())
  if (invalidPort) {
    ElMessage.warning('存在未填写名称的端口，请补全或删除该行')
    return
  }
  const missingLag = ports.value.find(p => p.connection_type === 'aggregate' && !p.lag_group.trim())
  if (missingLag) {
    ElMessage.warning('聚合端口必须填写聚合组号')
    return
  }

  // 旧系统自定义值
  const custom_values = Object.entries(customValues.value)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([field_id, value]) => ({ field_id: parseInt(field_id), value: String(value) }))
  // 新系统布局字段值
  const layout_vals = Object.entries(layoutValues.value)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([field_id, value]) => {
      const strVal = Array.isArray(value) ? value.join(',') : String(value)
      return { field_id: parseInt(field_id), value: strVal }
    })
  // 合并去重（新系统优先）
  const mergedValues = [...custom_values]
  for (const lv of layout_vals) {
    const existingIdx = mergedValues.findIndex(cv => cv.field_id === lv.field_id)
    if (existingIdx >= 0) mergedValues[existingIdx] = lv
    else mergedValues.push(lv)
  }

  const data = {
    ...form.value,
    custom_values: mergedValues,
    ports: ports.value.map((p, i) => ({ ...p, sort_order: i })),
    snmp_selected_metrics: selectedMetrics.value.length
      ? JSON.stringify(selectedMetrics.value) : ''
  }

  submitting.value = true
  try {
    const result = isEdit.value
      ? await deviceApi.update(deviceId.value, data)
      : await deviceApi.create(data)

    const savedId = result?.data?.id || deviceId.value
    // 新建设备时先上传的合同，保存后自动关联到本设备
    try { await contractAttachRef.value?.flushPending(savedId) } catch (e) {}
    ElMessage.success(isEdit.value ? '更新成功' : '添加成功')

    // 勾了指标就立刻采一次，让列表马上有值可看
    if (form.value.snmp_template_name && selectedMetrics.value.length && savedId) {
      try { await snmpApi.pollDevice(savedId) } catch (e) { /* 采集失败不影响保存 */ }
    }
    router.push('/devices')
  } catch (e) {
    console.error('保存失败详情:', e)
    ElMessage.error(e?.response?.data?.detail || e?.message || '保存失败')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  deviceId.value = route.params.id
  isEdit.value = !!deviceId.value

  await loadOptions()
  await loadProductTypes()

  if (isEdit.value) {
    await loadDetail()
  } else {
    // 新建时若从某个文件夹进入，预选该文件夹并带出部门
    const qFolder = route.query.folder_id
    if (qFolder) {
      form.value.folder_id = Number(qFolder)
      onFolderChange(form.value.folder_id)
    }
    // 从「设备资产」树进入时，预选资产分类
    const qAsset = route.query.asset_folder_id
    if (qAsset) form.value.asset_folder_id = Number(qAsset)
    await loadSnmpTemplates()
  }
})
</script>

<style scoped>
.device-form { max-width: 1200px; margin: 0 auto; }
.card-header { font-weight: bold; font-size: 16px; }
:deep(.el-divider__text) { font-size: 14px; color: #606266; font-weight: bold; }

.opt-count { float: right; color: #909399; font-size: 12px; }

.metrics-selector {
  padding: 15px;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  margin-bottom: 15px;
}
.metrics-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.metrics-label { display: flex; align-items: center; gap: 8px; font-size: 14px; color: #303133; }
.metrics-ops { display: flex; gap: 4px; }
.metrics-tip { margin-top: 10px; font-size: 12px; color: #909399; }

.metric-grid {
  display: grid !important;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 10px;
}
.metric-item {
  height: auto;
  margin-right: 0;
  padding: 8px 10px;
  background: var(--app-panel, #fff);
  border: 1px solid var(--app-border, #e4e7ed);
  border-radius: 4px;
}
.metric-box { display: flex; flex-direction: column; line-height: 1.5; }
.metric-name { color: #303133; font-size: 13px; }
.metric-unit { color: #909399; font-size: 12px; }
.metric-oid { color: #a8abb2; font-size: 11px; font-family: monospace; }

.ports-section {
  padding: 15px;
  background: var(--app-bg-soft, #fafafa);
  border: 1px solid var(--app-border, #e4e7ed);
  border-radius: 4px;
  margin-bottom: 15px;
}
.ports-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.ports-hint { font-size: 13px; color: var(--app-text-secondary, #909399); }
.ports-table {
  /* 表格背景跟随主题：避免深色主题下出现纯白块 */
  background: transparent;
}
.ports-counts {
  padding: 12px 15px;
  margin-bottom: 12px;
  background: var(--app-bg-soft, #fafafa);
  border: 1px solid var(--app-border, #e4e7ed);
  border-radius: 4px;
}
.ports-counts-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--app-text, #303133);
  margin-bottom: 8px;
}
.ports-count-col { margin-bottom: 8px; }
.ports-count-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ports-count-label {
  font-size: 12px;
  color: var(--app-text-secondary, #909399);
}
.ports-counts-empty {
  padding: 10px 15px;
  margin-bottom: 12px;
  font-size: 12px;
  color: var(--app-text-secondary, #909399);
  background: var(--app-bg-soft, #fafafa);
  border: 1px dashed var(--app-border, #e4e7ed);
  border-radius: 4px;
  text-align: center;
}
.extra-cell { display: flex; gap: 6px; }

.folder-path-hint { font-size: 12px; color: var(--app-text-secondary, #909399); line-height: 1.6; margin-top: 2px; }
.folder-path-hint strong { color: var(--app-accent, #409eff); }
.layout-config-tip { margin-bottom: 16px; }
.layout-config-tip-body { font-size: 13px; line-height: 1.7; padding-left: 4px; }
</style>
