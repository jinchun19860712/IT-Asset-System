<template>
  <div class="device-list">
    <el-card class="search-card">
      <!-- 当前文件夹范围提示 -->
      <div v-if="selectedFolder" class="scope-bar">
        <el-icon><Folder /></el-icon>
        <span class="scope-text">
          {{ selectedFolder.kind === 'asset' ? '当前资产分类：' : '当前范围：' }}
          <strong>{{ selectedFolder.full_path || selectedFolder.name }}</strong>
          <el-tag size="small" :type="selectedFolder.kind === 'asset' ? 'warning' : 'info'"
                  effect="plain" style="margin-left: 8px">
            {{ selectedFolder.kind === 'asset' ? '含所有子分类' : '含所有子文件夹' }}
          </el-tag>
        </span>
        <el-button link type="primary" size="small" @click="clearFolderScope">查看全部设备</el-button>
      </div>

      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="关键词">
          <el-input v-model="searchForm.keyword" placeholder="名称/IP/MAC" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="searchForm.device_type" placeholder="全部类型" clearable style="width: 140px">
            <el-option v-for="t in deviceTypes" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="部门">
          <el-select v-model="searchForm.department" placeholder="全部部门" clearable style="width: 140px">
            <el-option v-for="d in departments" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status_id" placeholder="全部状态" clearable style="width: 120px">
            <el-option v-for="s in statusList" :key="s.id" :label="s.name" :value="s.id">
              <span :style="{ color: s.color }">●</span> {{ s.name }}
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon> 搜索
          </el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <div class="toolbar">
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon> 添加设备
        </el-button>
        <el-button type="success" plain @click="handleAddSoftware">
          <el-icon><Plus /></el-icon> 添加软件
        </el-button>
        <el-button @click="refreshAll">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
        <el-button @click="handlePollAll" :loading="polling">
          <el-icon><Odometer /></el-icon> 采集监控值
        </el-button>
        <el-button @click="openTemplateDialog">
          <el-icon><Document /></el-icon> 下载模板
        </el-button>
        <el-button @click="openImportDialog">
          <el-icon><Upload /></el-icon> 导入
        </el-button>
        <el-button @click="openExportDialog" :loading="exporting">
          <el-icon><Download /></el-icon> 导出
        </el-button>

        <el-popover placement="bottom-end" :width="340" trigger="click">
          <template #reference>
            <el-button>
              <el-icon><Setting /></el-icon> 列设置
              <el-tag size="small" type="info" effect="plain" style="margin-left: 6px">
                {{ visibleColumns.length }}/{{ allColumns.length }}
              </el-tag>
            </el-button>
          </template>
          <div class="column-selector">
            <div class="column-head">
              <span class="column-title">勾选需要显示的列</span>
              <el-tag size="small" type="success" effect="plain">自动记忆</el-tag>
            </div>

            <el-input v-model="columnFilter" placeholder="搜索列名" clearable size="small" style="margin-bottom: 10px">
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>

            <el-scrollbar max-height="320px">
              <div class="column-group" v-if="filteredBaseColumns.length">
                <div class="group-label">基础字段</div>
                <el-checkbox-group v-model="visibleColumns">
                  <el-checkbox v-for="col in filteredBaseColumns" :key="col.prop" :value="col.prop">
                    {{ col.label }}
                  </el-checkbox>
                </el-checkbox-group>
              </div>

              <div class="column-group" v-if="filteredSnmpColumns.length">
                <div class="group-label">
                  SNMP 监控指标
                  <el-tooltip content="来自各设备在「添加/编辑设备」中勾选的 OID 监控项" placement="top">
                    <el-icon class="hint-icon"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </div>
                <el-checkbox-group v-model="visibleColumns">
                  <el-checkbox v-for="col in filteredSnmpColumns" :key="col.prop" :value="col.prop">
                    {{ col.label }}<span v-if="col.unit" class="unit-hint">（{{ col.unit }}）</span>
                  </el-checkbox>
                </el-checkbox-group>
              </div>

              <el-empty v-if="!filteredBaseColumns.length && !filteredSnmpColumns.length"
                        description="没有匹配的列" :image-size="60" />
            </el-scrollbar>

            <el-divider style="margin: 12px 0" />
            <div class="column-actions">
              <el-button size="small" @click="selectAllColumns">全选</el-button>
              <el-button size="small" @click="resetColumns">恢复默认</el-button>
            </div>
          </div>
        </el-popover>
      </div>
    </el-card>

    <el-card class="table-card">
      <!-- 批量操作条：选中行后浮现 -->
      <transition name="el-fade-in-linear">
        <div v-if="selectedRows.length" class="bulk-bar">
          <div class="bulk-info">
            已选中 <b>{{ selectedRows.length }}</b> 台设备
            <el-button link type="primary" size="small" @click="clearSelection">取消选择</el-button>
          </div>
          <div class="bulk-actions">
            <el-button size="small" :icon="Edit" @click="openBulkEdit">批量修改</el-button>
            <el-button size="small" :icon="Odometer" :loading="bulkPolling" @click="bulkPoll">批量采集</el-button>
            <el-button size="small" type="danger" :icon="Delete" @click="bulkDelete">批量删除</el-button>
          </div>
        </div>
      </transition>

      <el-table
        ref="tableRef"
        :data="deviceList"
        v-loading="loading"
        stripe
        border
        size="small"
        row-key="id"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="42" fixed="left" reserve-selection />
        <el-table-column type="index" width="45" fixed="left" />

        <el-table-column v-if="isVisible('name')" prop="name" label="设备名称" min-width="160" show-overflow-tooltip sortable fixed="left">
          <template #default="{ row }">
            <el-link type="primary" :underline="false" class="device-name-link" @click="openDetail(row)">
              {{ row.name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column v-if="isVisible('device_type')" prop="device_type" label="类型" width="90" sortable />
        <el-table-column v-if="isVisible('brand')" prop="brand" label="品牌" width="80" />
        <el-table-column v-if="isVisible('supplier')" prop="supplier" label="供应商" width="120" show-overflow-tooltip />
        <el-table-column v-if="isVisible('model')" prop="model" label="型号" width="120" show-overflow-tooltip />
        <el-table-column v-if="isVisible('parent_device_name')" prop="parent_device_name" label="父设备" width="140" show-overflow-tooltip />

        <el-table-column v-if="isVisible('ip_address')" prop="ip_address" label="管理IP" width="125" sortable />
        <el-table-column v-if="isVisible('network_mask')" prop="network_mask" label="掩码" width="60" />
        <el-table-column v-if="isVisible('mac_address')" prop="mac_address" label="MAC地址" width="140" />
        <el-table-column v-if="isVisible('management_vlan')" prop="management_vlan" label="VLAN" width="60" />
        <el-table-column v-if="isVisible('bmc_ip')" prop="bmc_ip" label="BMC IP" width="125" />
        <el-table-column v-if="isVisible('bmc_mac')" prop="bmc_mac" label="BMC MAC" width="140" />

        <el-table-column v-if="isVisible('area')" prop="area" label="区域" width="100" />
        <el-table-column v-if="isVisible('room_type')" prop="room_type" label="房间类型" width="100" />
        <el-table-column v-if="isVisible('room_number')" prop="room_number" label="房间号" width="80" />

        <el-table-column v-if="isVisible('service_code')" prop="service_code" label="资产编号" width="150" show-overflow-tooltip />
        <el-table-column v-if="isVisible('status_name')" prop="status_name" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :color="row.status_color" effect="dark" size="small" v-if="row.status_name">{{ row.status_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="isVisible('disuse_date')" prop="disuse_date" label="停用/维修日期" width="110" />
        <el-table-column v-if="isVisible('department')" prop="department" label="部门" width="100" sortable />
        <el-table-column v-if="isVisible('user')" prop="user" label="使用人" width="80" sortable />

        <el-table-column v-if="isVisible('management_services')" prop="management_services" label="管理服务" width="140" show-overflow-tooltip />
        <el-table-column v-if="isVisible('support_tags')" label="管理方式" width="140">
          <template #default="{ row }">
            <el-tag v-if="row.support_ssh2" size="small" class="method-tag">SSH2</el-tag>
            <el-tag v-if="row.support_telnet" size="small" class="method-tag">Telnet</el-tag>
            <el-tag v-if="row.support_web" size="small" class="method-tag">Web</el-tag>
            <el-tag v-if="row.support_snmp" size="small" class="method-tag">SNMP</el-tag>
            <el-tag v-if="row.support_rdp" size="small" class="method-tag">RDP</el-tag>
            <el-tag v-if="row.support_console" size="small" class="method-tag">Console</el-tag>
          </template>
        </el-table-column>

        <el-table-column v-if="isVisible('mgmt_username')" prop="mgmt_username" label="管理账号" width="90" />
        <el-table-column v-if="isVisible('folder_full_path')" prop="folder_full_path" label="所在路径" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.folder_full_path" class="path-text">{{ row.folder_full_path }}</span>
            <el-text v-else type="info" size="small">未归类</el-text>
          </template>
        </el-table-column>

        <el-table-column v-if="isVisible('rack_name')" label="机柜位置" width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.rack_name">{{ row.rack_name }} · U{{ row.rack_position }}</span>
            <el-text v-else type="info" size="small">未上架</el-text>
          </template>
        </el-table-column>

        <el-table-column v-if="isVisible('port_summary')" label="上下联端口" width="130">
          <template #default="{ row }">
            <template v-if="row.ports && row.ports.length">
              <el-tooltip placement="top">
                <template #content>
                  <div v-for="p in row.ports" :key="p.id">
                    {{ p.port_name }} · {{ portTypeLabel(p.port_type) }} · {{ connTypeLabel(p.connection_type) }}
                    <template v-if="p.lag_group">（{{ p.lag_group }}）</template>
                    <template v-if="p.peer_device_name"> → {{ p.peer_device_name }} {{ p.peer_port_name }}</template>
                  </div>
                </template>
                <span>
                  <el-tag size="small" type="warning" effect="plain" v-if="countPorts(row, 'uplink')">
                    上联 {{ countPorts(row, 'uplink') }}
                  </el-tag>
                  <el-tag size="small" type="success" effect="plain" v-if="countPorts(row, 'downlink')" style="margin-left: 4px">
                    下联 {{ countPorts(row, 'downlink') }}
                  </el-tag>
                </span>
              </el-tooltip>
            </template>
            <el-text v-else type="info" size="small">-</el-text>
          </template>
        </el-table-column>

        <el-table-column v-if="isVisible('description')" prop="description" label="备注" min-width="150" show-overflow-tooltip />

        <!-- SNMP 监控列：由各设备勾选的 OID 指标动态生成，且受「列设置」管辖 -->
        <el-table-column
          v-for="metric in visibleSnmpColumns"
          :key="metric.prop"
          :prop="metric.prop"
          :label="metric.label"
          width="150"
          align="right"
        >
          <template #header>
            <el-tooltip :content="`SNMP 监控指标：${metric.label}`" placement="top">
              <span class="snmp-header">{{ metric.label }}</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <span v-if="hasMetricValue(row, metric)" class="metric-value">
              {{ row[metric.prop] }}<span class="metric-unit" v-if="metric.unit">{{ metric.unit }}</span>
            </span>
            <el-tooltip v-else-if="isMetricSelected(row, metric)" content="已勾选该指标，但尚未采集到值，点击工具栏「采集监控值」" placement="top">
              <el-text type="warning" size="small">待采集</el-text>
            </el-tooltip>
            <el-text v-else type="info" size="small">-</el-text>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
            <el-button type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.page_size"
        :page-sizes="[10, 20, 50, 100]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next"
        class="pagination"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </el-card>

    <!-- ========== 导入对话框 ========== -->
    <el-dialog v-model="importDialogVisible" title="导入设备台账" width="820px" top="4vh" destroy-on-close>
      <div class="import-dialog">
        <el-form :inline="true" label-width="84px" class="import-options">
          <el-form-item label="导入模式">
            <el-select v-model="importForm.mode" style="width: 160px">
              <el-option label="有则更新，无则新增" value="upsert" />
              <el-option label="仅新增" value="insert_only" />
              <el-option label="仅更新" value="update_only" />
            </el-select>
          </el-form-item>
          <el-form-item label="端口模式">
            <el-select v-model="importForm.port_mode" style="width: 150px">
              <el-option label="按端口名增量" value="merge" />
              <el-option label="整机替换端口" value="replace" />
            </el-select>
          </el-form-item>
          <el-form-item label="空值策略">
            <el-select v-model="importForm.blank_policy" style="width: 150px">
              <el-option label="留空不覆盖" value="ignore" />
              <el-option label="留空即清空" value="overwrite" />
            </el-select>
          </el-form-item>
          <el-form-item label="导入范围">
            <el-select v-model="importForm.folder_id" clearable placeholder="不指定（按表内路径）" style="width: 210px">
              <el-option v-for="f in folderOptions" :key="f.id" :label="f.full_path" :value="f.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="包含内容">
            <el-checkbox v-model="importForm.import_ports">端口</el-checkbox>
            <el-checkbox v-model="importForm.import_racks">机柜上架</el-checkbox>
          </el-form-item>
          <el-form-item label="自动创建">
            <el-checkbox v-model="importForm.auto_create_folder">文件夹</el-checkbox>
            <el-checkbox v-model="importForm.auto_create_rack">机柜</el-checkbox>
          </el-form-item>
        </el-form>

        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :show-file-list="true"
          :limit="1"
          accept=".xlsx,.xlsm"
          :on-change="onFileSelected"
          drag
          class="import-upload"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">将 Excel 拖到此处，或 <em>点击选择</em></div>
          <template #tip>
            <div class="el-upload__tip">仅支持 .xlsx / .xlsm，可含「设备台账 / 端口 / 机柜」三个 Sheet</div>
          </template>
        </el-upload>

        <div class="import-actions">
          <el-button @click="runPreview" :disabled="!importFile" :loading="previewing">
            <el-icon><View /></el-icon> 预览差异
          </el-button>
          <el-button type="primary" @click="runImport" :disabled="!previewReport" :loading="importing">
            <el-icon><Check /></el-icon> 确认导入
          </el-button>
          <span v-if="previewReport" class="preview-hint">已预览，确认无误后点击导入</span>
        </div>

        <div v-if="previewReport" class="preview-result">
          <el-alert
            :type="previewReport.data.error_count ? 'error' : (previewReport.data.warning_count ? 'warning' : 'success')"
            :closable="false" show-icon>
            <template #title>{{ previewReport.message }}</template>
          </el-alert>

          <div class="stat-row">
            <el-tag type="success">新增 {{ previewReport.data.created }}</el-tag>
            <el-tag type="warning">更新 {{ previewReport.data.updated }}</el-tag>
            <el-tag type="info">无变化 {{ previewReport.data.unchanged }}</el-tag>
            <el-tag type="info">跳过 {{ previewReport.data.skipped }}</el-tag>
          </div>
          <div v-if="extraStats.length" class="stat-row">
            <el-tag v-for="s in extraStats" :key="s.label" :type="s.type">{{ s.label }} {{ s.value }}</el-tag>
          </div>

          <el-tabs v-model="diffTab" class="diff-tabs">
            <el-tab-pane name="rows">
              <template #label>逐行明细 <el-badge :value="previewReport.data.rows.length" :max="999" type="primary" /></template>
              <div class="diff-toolbar">
                <el-radio-group v-model="rowFilter" size="small">
                  <el-radio-button value="all">全部</el-radio-button>
                  <el-radio-button value="create">新增</el-radio-button>
                  <el-radio-button value="update">更新</el-radio-button>
                  <el-radio-button value="unchanged">无变化</el-radio-button>
                  <el-radio-button value="skip">跳过</el-radio-button>
                  <el-radio-button value="error">错误</el-radio-button>
                </el-radio-group>
              </div>
              <el-table :data="filteredRows" size="small" border max-height="300" stripe>
                <el-table-column prop="row" label="行号" width="64" />
                <el-table-column prop="name" label="设备名" min-width="160" show-overflow-tooltip />
                <el-table-column label="动作" width="80">
                  <template #default="{ row }">
                    <el-tag :type="rowActionTag(row.action)" size="small">{{ rowActionLabel(row.action) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="变更 / 说明" min-width="320" show-overflow-tooltip>
                  <template #default="{ row }">
                    <span v-if="row.action === 'update'" class="change-text">{{ rowSummary(row) }}</span>
                    <span v-else>{{ rowSummary(row) }}</span>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>

            <el-tab-pane name="issues">
              <template #label>问题与警告
                <el-badge v-if="previewReport.data.issues.length" :value="previewReport.data.issues.length" :max="999"
                          :type="previewReport.data.error_count ? 'danger' : 'warning'" />
              </template>
              <el-scrollbar max-height="300">
                <div v-if="!previewReport.data.issues.length" class="no-issue">无问题与警告</div>
                <div v-for="(it, i) in previewReport.data.issues" :key="i" class="issue-item">
                  <el-tag :type="it.level === 'error' ? 'danger' : 'warning'" size="small">
                    {{ it.level === 'error' ? '错误' : '警告' }}
                  </el-tag>
                  <span class="issue-row">行 {{ it.row }}</span>
                  <span class="issue-sheet" v-if="it.sheet">{{ it.sheet }}</span>
                  <span class="issue-msg">{{ it.message }}</span>
                </div>
              </el-scrollbar>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
    </el-dialog>

    <!-- ========== 导出对话框 ========== -->
    <el-dialog v-model="exportDialogVisible" title="导出设备台账" width="560px">
      <el-form label-width="92px">
        <el-form-item label="组织机构">
          <el-select v-model="exportForm.folder_id" clearable filterable
                     placeholder="全部（不限机构）" style="width: 100%">
            <el-option v-for="f in folderOptions" :key="f.id" :label="f.full_path" :value="f.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="资产分类">
          <el-select v-model="exportForm.asset_folder_id" clearable filterable
                     placeholder="全部（不限分类）" style="width: 100%">
            <el-option v-for="f in assetFolderOptions" :key="f.id" :label="f.full_path" :value="f.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="设备类型">
          <div class="export-types">
            <div class="export-types-head">
              <el-radio-group v-model="exportForm.typeMode" size="small">
                <el-radio-button value="all">全部设备</el-radio-button>
                <el-radio-button value="custom">自定义勾选</el-radio-button>
              </el-radio-group>
              <div v-if="exportForm.typeMode === 'custom'" class="export-types-ops">
                <el-button link type="primary" size="small" @click="selectAllExportTypes">全选</el-button>
                <el-button link type="info" size="small" @click="exportForm.device_types = []">清空</el-button>
              </div>
            </div>
            <div v-if="exportForm.typeMode === 'custom'" class="export-types-box">
              <el-checkbox-group v-model="exportForm.device_types">
                <el-checkbox v-for="t in exportTypeOptions" :key="t" :value="t" class="type-cb">{{ t }}</el-checkbox>
              </el-checkbox-group>
              <el-empty v-if="!exportTypeOptions.length" description="暂无设备类型" :image-size="50" />
            </div>
          </div>
        </el-form-item>

        <el-form-item label="包含内容">
          <el-checkbox v-model="exportForm.include_ports">端口 Sheet</el-checkbox>
          <el-checkbox v-model="exportForm.include_racks">机柜 Sheet</el-checkbox>
        </el-form-item>

        <el-alert type="info" :closable="false" show-icon style="margin-top: -4px">
          <template #title>
            多个条件为「且」关系；导出的工作簿含「设备台账 / 端口 / 机柜」三张表，可直接改完再导入回来
          </template>
        </el-alert>
      </el-form>
      <template #footer>
        <el-button @click="exportDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="exporting" @click="confirmExport">导出 Excel</el-button>
      </template>
    </el-dialog>

    <!-- ========== 模板对话框 ========== -->
    <el-dialog v-model="templateDialogVisible" title="下载导入模板" width="420px">
      <p class="tpl-tip">模板包含「设备台账 / 端口 / 机柜」三个 Sheet 及填写说明。</p>
      <el-checkbox v-model="templateForm.withSample">附带一行示例数据</el-checkbox>
      <template #footer>
        <el-button @click="templateDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmDownloadTemplate">下载</el-button>
      </template>
    </el-dialog>

    <!-- ========== 批量修改对话框 ========== -->
    <el-dialog v-model="bulkEditVisible" title="批量修改设备" width="560px" destroy-on-close>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        class="bulk-tip"
        :title="`将对选中的 ${selectedRows.length} 台设备生效`"
        description="只有勾选并填写的字段才会被修改，未勾选的字段保持原值不变。"
      />
      <el-form label-width="100px" class="bulk-form">
        <el-form-item v-for="f in bulkFields" :key="f.key" :label="f.label">
          <div class="bulk-row">
            <el-checkbox v-model="bulkEnabled[f.key]" class="bulk-check" />
            <!-- 状态 -->
            <el-select v-if="f.key === 'status_id'" v-model="bulkForm.status_id"
                       :disabled="!bulkEnabled[f.key]" placeholder="选择状态" clearable class="bulk-input">
              <el-option v-for="s in statusList" :key="s.id" :label="s.name" :value="s.id" />
            </el-select>
            <!-- 组织机构 / 资产分类 -->
            <el-select v-else-if="f.key === 'folder_id'" v-model="bulkForm.folder_id" filterable
                       :disabled="!bulkEnabled[f.key]" placeholder="选择组织机构" clearable class="bulk-input">
              <el-option v-for="o in folderOptions" :key="o.id" :label="o.full_path" :value="o.id" />
            </el-select>
            <el-select v-else-if="f.key === 'asset_folder_id'" v-model="bulkForm.asset_folder_id" filterable
                       :disabled="!bulkEnabled[f.key]" placeholder="选择资产分类" clearable class="bulk-input">
              <el-option v-for="o in assetFolderOptions" :key="o.id" :label="o.full_path" :value="o.id" />
            </el-select>
            <!-- 部门（可自由输入） -->
            <el-select v-else-if="f.key === 'department'" v-model="bulkForm.department" filterable allow-create
                       default-first-option :disabled="!bulkEnabled[f.key]" placeholder="选择或输入部门"
                       clearable class="bulk-input">
              <el-option v-for="d in departments" :key="d" :label="d" :value="d" />
            </el-select>
            <!-- 供应商 -->
            <el-select v-else-if="f.key === 'supplier'" v-model="bulkForm.supplier" filterable allow-create
                       default-first-option :disabled="!bulkEnabled[f.key]" placeholder="选择或输入供应商"
                       clearable class="bulk-input">
              <el-option v-for="s in supplierOptions" :key="s" :label="s" :value="s" />
            </el-select>
            <el-input v-else v-model="bulkForm[f.key]" :disabled="!bulkEnabled[f.key]"
                      :placeholder="f.placeholder || '留空则清空该字段'" class="bulk-input" />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="bulkEditVisible = false">取消</el-button>
        <el-button type="primary" :loading="bulkSaving" @click="confirmBulkEdit">
          确认修改（{{ enabledFieldCount }} 项）
        </el-button>
      </template>
    </el-dialog>

    <!-- ========== 设备详情抽屉 ========== -->
    <DeviceDetailDrawer v-model="detailVisible" :device-id="detailDeviceId" @refresh="refreshAll" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick, inject } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Plus, Refresh, Setting, Folder, Odometer, QuestionFilled,
  Upload, Download, Document, UploadFilled, View, Check, Edit, Delete
} from '@element-plus/icons-vue'
import { deviceApi, statusApi, snmpApi, folderApi, rackApi, dictApi } from '../api/index.js'
import DeviceDetailDrawer from '../components/DeviceDetailDrawer.vue'

const props = defineProps({
  // 兼容：直接传 prop 时仍可工作（fallback）
  selectedFolder: { type: Object, default: null }
})
const injectedFolder = inject('selectedFolder', null)
const injectedClear = inject('clearFolder', null)
const selectedFolder = computed(() => injectedFolder?.value ?? props.selectedFolder)
const clearFolder = () => injectedClear?.()
const router = useRouter()
const route = useRoute()

// 当前面板模式：org=组织架构，asset=资产面板，both=双树兼容模式
const panelMode = computed(() => route.query?.tree === 'asset' ? 'asset' : (route.query?.tree === 'org' ? 'org' : 'both'))

const loading = ref(false)
const polling = ref(false)
const deviceList = ref([])
const deviceTypes = ref([])
const departments = ref([])
const exporting = ref(false)
const statusList = ref([])
const allSnmpMetrics = ref({})
const snmpColumnDefs = ref([])
const columnFilter = ref('')

const searchForm = ref({ keyword: '', device_type: '', department: '', status_id: null })
const pagination = ref({ page: 1, page_size: 20, total: 0 })

// ========== 列定义 ==========
const baseColumns = [
  { prop: 'name', label: '设备名称' },
  { prop: 'device_type', label: '类型' },
  { prop: 'brand', label: '品牌' },
  { prop: 'supplier', label: '供应商' },
  { prop: 'model', label: '型号' },
  { prop: 'parent_device_name', label: '父设备' },
  { prop: 'ip_address', label: '管理IP' },
  { prop: 'network_mask', label: '掩码' },
  { prop: 'mac_address', label: 'MAC地址' },
  { prop: 'management_vlan', label: 'VLAN' },
  { prop: 'bmc_ip', label: 'BMC IP' },
  { prop: 'bmc_mac', label: 'BMC MAC' },
  { prop: 'area', label: '区域' },
  { prop: 'room_type', label: '房间类型' },
  { prop: 'room_number', label: '房间号' },
  { prop: 'service_code', label: '资产编号' },
  { prop: 'status_name', label: '状态' },
  { prop: 'disuse_date', label: '停用/维修日期' },
  { prop: 'department', label: '部门' },
  { prop: 'user', label: '使用人' },
  { prop: 'management_services', label: '管理服务' },
  { prop: 'support_tags', label: '管理方式' },
  { prop: 'mgmt_username', label: '管理账号' },
  { prop: 'folder_full_path', label: '所在路径' },
  { prop: 'rack_name', label: '机柜位置' },
  { prop: 'port_summary', label: '上下联端口' },
  { prop: 'description', label: '备注' }
]

const defaultColumns = [
  'name', 'device_type', 'ip_address', 'mac_address', 'department',
  'user', 'status_name', 'folder_full_path', 'support_tags', 'supplier'
]

const STORE_KEY = 'device_list_prefs_v2'
const LEGACY_KEY = 'device_list_columns_v1'

const visibleColumns = ref([...defaultColumns])
// 记录"用户见过哪些列"。新出现的 SNMP 指标应自动显示，
// 而被用户主动取消勾选的列必须保持隐藏 —— 只靠 visibleColumns 无法区分这两种情况。
const knownColumns = ref([])
let prefsLoaded = false

const allColumns = computed(() => [...baseColumns, ...snmpColumnDefs.value])

const filteredBaseColumns = computed(() => {
  const kw = columnFilter.value.trim().toLowerCase()
  if (!kw) return baseColumns
  return baseColumns.filter(c => c.label.toLowerCase().includes(kw))
})

const filteredSnmpColumns = computed(() => {
  const kw = columnFilter.value.trim().toLowerCase()
  if (!kw) return snmpColumnDefs.value
  return snmpColumnDefs.value.filter(c => c.label.toLowerCase().includes(kw))
})

const visibleSnmpColumns = computed(() =>
  snmpColumnDefs.value.filter(c => visibleColumns.value.includes(c.prop))
)

const isVisible = (prop) => visibleColumns.value.includes(prop)

// ========== 偏好持久化 ==========
const loadPrefs = () => {
  try {
    const raw = localStorage.getItem(STORE_KEY)
    if (raw) {
      const saved = JSON.parse(raw)
      if (Array.isArray(saved.visibleColumns) && saved.visibleColumns.length) {
        visibleColumns.value = saved.visibleColumns
      }
      if (Array.isArray(saved.knownColumns)) {
        knownColumns.value = saved.knownColumns
      }
      if (saved.pageSize) pagination.value.page_size = saved.pageSize
    } else {
      // 兼容旧版本只存了列数组的情况
      const legacy = localStorage.getItem(LEGACY_KEY)
      if (legacy) {
        const parsed = JSON.parse(legacy)
        if (Array.isArray(parsed) && parsed.length) visibleColumns.value = parsed
      }
    }
  } catch (e) {
    console.error('读取列设置失败', e)
  }
  if (!knownColumns.value.length) {
    knownColumns.value = baseColumns.map(c => c.prop)
  }
  prefsLoaded = true
}

const savePrefs = () => {
  if (!prefsLoaded) return
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify({
      visibleColumns: visibleColumns.value,
      knownColumns: knownColumns.value,
      pageSize: pagination.value.page_size
    }))
  } catch (e) {
    console.error('保存列设置失败', e)
  }
}

watch(visibleColumns, savePrefs, { deep: true })

const selectAllColumns = () => {
  visibleColumns.value = allColumns.value.map(c => c.prop)
}

const resetColumns = () => {
  // 恢复默认时，保留当前所有 SNMP 指标列（用户特意配过监控才会有这些列）
  visibleColumns.value = [...defaultColumns, ...snmpColumnDefs.value.map(c => c.prop)]
}

// ========== 数据加载 ==========
const loadSnmpColumns = async () => {
  try {
    const res = await snmpApi.getMetricColumns()
    if (res.code !== 0) return
    const cols = (res.data || []).map(c => ({
      prop: c.key,
      label: c.label,
      unit: c.unit || '',
      metric_name: c.metric_name
    }))
    snmpColumnDefs.value = cols

    // 首次出现的监控指标默认可见，之后用户的取消勾选会被尊重
    const fresh = cols.filter(c => !knownColumns.value.includes(c.prop))
    if (fresh.length) {
      visibleColumns.value = [...visibleColumns.value, ...fresh.map(c => c.prop)]
      knownColumns.value = [...knownColumns.value, ...fresh.map(c => c.prop)]
      savePrefs()
    }
  } catch (e) {
    console.error('加载监控指标列失败', e)
  }
}

const loadSnmpMetrics = async () => {
  try {
    const res = await snmpApi.getAllDeviceMetrics()
    if (res.code === 0) allSnmpMetrics.value = res.data || {}
  } catch (e) {
    console.error('加载SNMP监控值失败', e)
  }
}

const attachMetrics = (items) => {
  for (const item of items) {
    const metrics = allSnmpMetrics.value[item.id] || []
    for (const m of metrics) {
      item[`snmp_${m.metric_name}`] = m.value
    }
  }
  return items
}

const loadData = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.value.page,
      page_size: pagination.value.page_size,
      ...searchForm.value
    }
    // 左侧树过滤逻辑：
    // 1. 选中具体节点时，按节点类型及子树过滤。
    // 2. 未选中节点时，按面板模式做默认归类：
    //    - 资产面板：显示「有资产分类」或「无部门」的设备
    //    - 组织架构：显示「有部门/归属组织机构」的设备
    //    - 双树兼容：显示全部
    if (props.selectedFolder?.id) {
      if (props.selectedFolder.kind === 'asset') {
        // 资产树根节点显示该面板默认范围；子节点按子树过滤
        if (props.selectedFolder.parent_id != null) {
          params.asset_folder_id = props.selectedFolder.id
        }
      } else {
        const isGrouping = props.selectedFolder.children && props.selectedFolder.children.length > 0
        if (!isGrouping) params.folder_id = props.selectedFolder.id
      }
    }
    // 未选中节点时，按当前面板做默认过滤
    if (!props.selectedFolder?.id) {
      if (panelMode.value === 'asset') {
        params.scope = 'asset_default'
      } else if (panelMode.value === 'org') {
        params.scope = 'org_default'
      }
    }
    const res = await deviceApi.getList(params)
    if (res.code === 0) {
      deviceList.value = attachMetrics(res.data.items || [])
      pagination.value.total = res.data.total
    }
  } catch (e) {
    ElMessage.error('加载设备列表失败')
  } finally {
    loading.value = false
  }
}

const loadOptions = async () => {
  try {
    const [typesRes, deptsRes, statusRes] = await Promise.all([
      deviceApi.getTypes(), deviceApi.getDepartments(), statusApi.getList()
    ])
    if (typesRes.code === 0) deviceTypes.value = typesRes.data
    if (deptsRes.code === 0) departments.value = deptsRes.data
    if (statusRes.code === 0) statusList.value = statusRes.data
  } catch (e) {
    console.error('加载选项失败', e)
  }
}

// SNMP 值和设备列表必须一起刷新，否则会用上一次的旧监控值渲染新列表
const refreshAll = async () => {
  await Promise.all([loadSnmpColumns(), loadSnmpMetrics()])
  await loadData()
}

// ========== 详情抽屉 ==========
const detailVisible = ref(false)
const detailDeviceId = ref(null)

function openDetail(row) {
  detailDeviceId.value = row.id
  detailVisible.value = true
}

// ========== 批量操作 ==========
const tableRef = ref(null)
const selectedRows = ref([])
const bulkEditVisible = ref(false)
const bulkSaving = ref(false)
const bulkPolling = ref(false)
const supplierOptions = ref([])

const bulkFields = [
  { key: 'department', label: '使用部门' },
  { key: 'user', label: '使用人', placeholder: '留空则清空使用人' },
  { key: 'status_id', label: '状态' },
  { key: 'folder_id', label: '组织机构' },
  { key: 'asset_folder_id', label: '资产分类' },
  { key: 'supplier', label: '供应商' },
  { key: 'area', label: '区域', placeholder: '留空则清空区域' },
  { key: 'remark', label: '备注', placeholder: '留空则清空备注' }
]

const bulkEnabled = ref({})
const bulkForm = ref({})

const enabledFieldCount = computed(
  () => Object.values(bulkEnabled.value).filter(Boolean).length
)

function handleSelectionChange(rows) {
  selectedRows.value = rows
}

function clearSelection() {
  tableRef.value?.clearSelection()
  selectedRows.value = []
}

function openBulkEdit() {
  bulkEnabled.value = {}
  bulkForm.value = {}
  for (const f of bulkFields) {
    bulkEnabled.value[f.key] = false
    bulkForm.value[f.key] = ['status_id', 'folder_id', 'asset_folder_id'].includes(f.key) ? null : ''
  }
  bulkEditVisible.value = true
}

async function confirmBulkEdit() {
  const payload = {}
  for (const f of bulkFields) {
    if (!bulkEnabled.value[f.key]) continue
    const v = bulkForm.value[f.key]
    // 后端把 null 当作"不修改"，清空文本字段要传空串
    if (['status_id', 'folder_id', 'asset_folder_id'].includes(f.key)) {
      if (v === null || v === undefined || v === '') {
        ElMessage.warning(`「${f.label}」已勾选但未选择值`)
        return
      }
      payload[f.key] = v
    } else {
      payload[f.key] = v ?? ''
    }
  }
  if (!Object.keys(payload).length) {
    ElMessage.warning('请至少勾选一个要修改的字段')
    return
  }

  bulkSaving.value = true
  try {
    const ids = selectedRows.value.map(r => r.id)
    const res = await deviceApi.bulkUpdate(ids, payload)
    if (res.code === 0) {
      ElMessage.success(res.message || '批量修改成功')
      bulkEditVisible.value = false
      clearSelection()
      await refreshAll()
      await loadOptions()
    } else {
      ElMessage.warning(res.message || '批量修改失败')
    }
  } catch (e) {
    ElMessage.error('批量修改请求失败')
  } finally {
    bulkSaving.value = false
  }
}

async function bulkDelete() {
  const ids = selectedRows.value.map(r => r.id)
  const preview = selectedRows.value.slice(0, 5).map(r => r.name).join('、')
  const more = ids.length > 5 ? ` 等 ${ids.length} 台` : ''
  try {
    await ElMessageBox.confirm(
      `确定删除 ${preview}${more} 吗？删除后不可恢复，其子设备将解除父子关联。`,
      '批量删除确认',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消', confirmButtonClass: 'el-button--danger' }
    )
  } catch (e) {
    return
  }
  try {
    const res = await deviceApi.bulkDelete(ids)
    if (res.code === 0) {
      ElMessage.success(res.message || '删除成功')
      clearSelection()
      await refreshAll()
    } else {
      ElMessage.warning(res.message || '删除失败')
    }
  } catch (e) {
    ElMessage.error('批量删除请求失败')
  }
}

async function bulkPoll() {
  const targets = selectedRows.value.filter(r => r.snmp_template_name)
  if (!targets.length) {
    ElMessage.warning('选中的设备均未配置 SNMP 模板')
    return
  }
  bulkPolling.value = true
  let ok = 0
  let fail = 0
  try {
    for (const d of targets) {
      try {
        const res = await snmpApi.pollDevice(d.id)
        res.code === 0 ? ok++ : fail++
      } catch (e) {
        fail++
      }
    }
    ElMessage[fail ? 'warning' : 'success'](`采集完成：成功 ${ok} 台${fail ? `，失败 ${fail} 台` : ''}`)
    await refreshAll()
  } finally {
    bulkPolling.value = false
  }
}

async function loadSuppliers() {
  try {
    const res = await dictApi.getByType('supplier')
    if (res.code === 0) {
      supplierOptions.value = (res.data || []).filter(x => x.enabled !== false).map(x => x.name)
    }
  } catch (e) {
    console.error('加载供应商字典失败', e)
  }
}

// ========== 交互 ==========
const hasMetricValue = (row, metric) => {
  const v = row[metric.prop]
  return v !== undefined && v !== null && v !== ''
}

const isMetricSelected = (row, metric) => {
  try {
    const selected = JSON.parse(row.snmp_selected_metrics || '[]')
    return selected.includes(metric.metric_name)
  } catch (e) {
    return false
  }
}

const countPorts = (row, type) =>
  (row.ports || []).filter(p => p.port_type === type).length

const PORT_TYPE_LABELS = { uplink: '上联', downlink: '下联', peer: '互联' }
const CONN_TYPE_LABELS = {
  access: 'Access', trunk: 'Trunk', hybrid: 'Hybrid',
  aggregate: '聚合', stack: '堆叠', routed: '三层路由'
}
const portTypeLabel = (t) => PORT_TYPE_LABELS[t] || t
const connTypeLabel = (t) => CONN_TYPE_LABELS[t] || t

const handlePollAll = async () => {
  polling.value = true
  try {
    const res = await snmpApi.pollAll()
    ElMessage.success(res.message || '采集完成')
    await loadSnmpMetrics()
    await loadData()
  } catch (e) {
    ElMessage.error('采集失败')
  } finally {
    polling.value = false
  }
}

const handleAdd = () => {
  // 带上当前选中节点，添加页可直接预选文件夹/资产分类并推导部门
  const query = {}
  if (props.selectedFolder?.id) {
    if (props.selectedFolder.kind === 'asset') query.asset_folder_id = props.selectedFolder.id
    else query.folder_id = props.selectedFolder.id
  }
  router.push({ path: '/devices/add', query })
}

const handleAddSoftware = () => {
  const query = {}
  if (props.selectedFolder?.id && props.selectedFolder.kind !== 'asset') {
    query.folder_id = props.selectedFolder.id
  }
  router.push({ path: '/softwares/add', query })
}

const clearFolderScope = () => clearFolder?.()

const handleSearch = () => { pagination.value.page = 1; loadData() }
const resetSearch = () => {
  searchForm.value = { keyword: '', device_type: '', department: '', status_id: null }
  handleSearch()
}
const handleSizeChange = (size) => {
  pagination.value.page_size = size
  savePrefs()
  loadData()
}
const handlePageChange = (page) => { pagination.value.page = page; loadData() }
const handleEdit = (row) => { router.push(`/devices/edit/${row.id}`) }

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除设备 "${row.name}" 吗？`, '提示', { type: 'warning' })
    const res = await deviceApi.delete(row.id)
    if (res.code === 0) {
      ElMessage.success('删除成功')
      loadData()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e?.message || '删除失败')
  }
}

watch(() => props.selectedFolder, () => {
  // 切目录时重置：分页、搜索条件、批量选择，避免旧过滤作用于新目录导致列表"无数据"
  pagination.value.page = 1
  searchForm.value = { keyword: '', device_type: '', department: '', status_id: null }
  clearSelection()
  loadData()
})

// ---- 导入 / 导出（以「网络设备台账」Excel 为模板）----
function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function fmtDate(d) {
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}`
}

// 导入对话框状态
const importDialogVisible = ref(false)
const importFile = ref(null)
const previewing = ref(false)
const importing = ref(false)
const previewReport = ref(null)
const diffTab = ref('rows')
const rowFilter = ref('all')

const importForm = ref({
  mode: 'upsert',
  port_mode: 'merge',
  blank_policy: 'ignore',
  folder_id: null,
  import_ports: true,
  import_racks: true,
  auto_create_folder: false,
  auto_create_rack: false
})

// 文件夹 / 机柜 选项与 ID 映射（用于范围选择 + 差异里 ID 反查名称）
const folderOptions = ref([])
const folderId2path = ref({})
const rackId2name = ref({})
const statusId2name = computed(() => {
  const m = {}
  for (const s of statusList.value) m[s.id] = s.name
  return m
})

const exportDialogVisible = ref(false)
const exportForm = ref({
  include_ports: true,
  include_racks: true,
  folder_id: null,
  asset_folder_id: null,
  typeMode: 'all',
  device_types: []
})
// 资产分类树扁平选项（导出范围用）
const assetFolderOptions = ref([])
// 字典里维护的产品类型
const productTypes = ref([])

// 可勾选的设备类型 = 字典产品类型 ∪ 库里已存在的类型
const exportTypeOptions = computed(() => {
  const set = new Set()
  for (const t of productTypes.value) if (t) set.add(t)
  for (const t of deviceTypes.value) if (t) set.add(t)
  return Array.from(set).sort((a, b) => a.localeCompare(b, 'zh'))
})

function selectAllExportTypes() {
  exportForm.value.device_types = [...exportTypeOptions.value]
}

const templateDialogVisible = ref(false)
const templateForm = ref({ withSample: false })

// 把文件夹树拍平成 [{id, full_path}]，同时回填 id→path 映射
function flattenTree(nodes, pathMap) {
  const flat = []
  const walk = (list) => {
    for (const n of list) {
      const p = n.full_path || n.name
      flat.push({ id: n.id, full_path: p })
      if (pathMap) pathMap[n.id] = p
      if (n.children && n.children.length) walk(n.children)
    }
  }
  walk(nodes || [])
  flat.sort((a, b) => a.full_path.localeCompare(b.full_path, 'zh'))
  return flat
}

async function loadFolderOptions() {
  try {
    const pathMap = {}
    const [orgRes, assetRes] = await Promise.all([
      folderApi.getTree('org'),
      folderApi.getTree('asset')
    ])
    if (orgRes.code === 0) folderOptions.value = flattenTree(orgRes.data, pathMap)
    if (assetRes.code === 0) assetFolderOptions.value = flattenTree(assetRes.data, pathMap)
    folderId2path.value = pathMap
  } catch (e) {
    console.error('加载文件夹树失败', e)
  }
}

async function loadProductTypes() {
  try {
    const res = await dictApi.getByType('product_type')
    if (res.code === 0) {
      productTypes.value = (res.data || []).filter(x => x.enabled !== false).map(x => x.name)
    }
  } catch (e) {
    // 字典拉取失败不阻塞导出，退化为只用库里已有类型
    console.error('加载产品类型字典失败', e)
  }
}

function resetImportForm() {
  importForm.value = {
    mode: 'upsert',
    port_mode: 'merge',
    blank_policy: 'ignore',
    folder_id: props.selectedFolder?.id ?? null,
    import_ports: true,
    import_racks: true,
    auto_create_folder: false,
    auto_create_rack: false
  }
}

async function openImportDialog() {
  resetImportForm()
  importFile.value = null
  previewReport.value = null
  importDialogVisible.value = true
  await loadFolderOptions()
  // 提前拉机柜清单，便于差异里把 rack_id 还原成机柜名
  try {
    const r = await rackApi.getList()
    if (r.code === 0) {
      const m = {}
      for (const x of r.data) m[x.id] = x.name
      rackId2name.value = m
    }
  } catch (e) { /* 可选，失败不影响导入 */ }
}

function onFileSelected(uploadFile) {
  importFile.value = uploadFile && uploadFile.raw ? uploadFile.raw : null
  previewReport.value = null
}

function buildImportOpts() {
  const f = importForm.value
  return {
    mode: f.mode,
    folder_id: f.folder_id,
    import_ports: f.import_ports,
    import_racks: f.import_racks,
    auto_create_folder: f.auto_create_folder,
    auto_create_rack: f.auto_create_rack,
    port_mode: f.port_mode,
    blank_policy: f.blank_policy
  }
}

async function runPreview() {
  if (!importFile.value) return
  previewing.value = true
  try {
    const res = await deviceApi.previewImport(importFile.value, buildImportOpts())
    previewReport.value = res
    diffTab.value = 'rows'
    rowFilter.value = 'all'
  } catch (err) {
    ElMessage.error('预览失败：' + detailOf(err))
  } finally {
    previewing.value = false
  }
}

async function runImport() {
  if (!importFile.value || !previewReport.value) return
  try {
    await ElMessageBox.confirm('确认按预览结果写入数据库？', '确认导入', { type: 'warning' })
  } catch (e) {
    return
  }
  importing.value = true
  try {
    const res = await deviceApi.importXlsx(importFile.value, buildImportOpts())
    ElMessage.success(res.message || '导入完成')
    importDialogVisible.value = false
    await refreshAll()
  } catch (err) {
    ElMessage.error('导入失败：' + detailOf(err))
  } finally {
    importing.value = false
  }
}

async function openExportDialog() {
  const sel = props.selectedFolder
  exportForm.value = {
    include_ports: true,
    include_racks: true,
    folder_id: sel && sel.kind !== 'asset' ? sel.id : null,
    asset_folder_id: sel && sel.kind === 'asset' ? sel.id : null,
    // 若搜索栏已选了类型，导出默认沿用该类型
    typeMode: searchForm.value.device_type ? 'custom' : 'all',
    device_types: searchForm.value.device_type ? [searchForm.value.device_type] : []
  }
  exportDialogVisible.value = true
  await Promise.all([loadFolderOptions(), loadProductTypes()])
}

async function confirmExport() {
  const f = exportForm.value
  if (f.typeMode === 'custom' && f.device_types.length === 0) {
    ElMessage.warning('请至少勾选一个设备类型，或切换为「全部设备」')
    return
  }
  exporting.value = true
  try {
    const blob = await deviceApi.exportXlsx({
      include_ports: f.include_ports,
      include_racks: f.include_racks,
      folder_id: f.folder_id,
      asset_folder_id: f.asset_folder_id,
      device_types: f.typeMode === 'custom' ? f.device_types : null
    })
    downloadBlob(blob, `网络设备台账-${fmtDate(new Date())}.xlsx`)
    exportDialogVisible.value = false
  } catch (e) {
    ElMessage.error('导出失败：' + ((e && e.message) || '未知错误'))
  } finally {
    exporting.value = false
  }
}

function openTemplateDialog() {
  templateForm.value = { withSample: false }
  templateDialogVisible.value = true
}

async function confirmDownloadTemplate() {
  try {
    const blob = await deviceApi.getImportTemplate(templateForm.value.withSample)
    downloadBlob(blob, '网络设备台账-导入模板.xlsx')
    templateDialogVisible.value = false
  } catch (e) {
    ElMessage.error('下载模板失败：' + ((e && e.message) || '未知错误'))
  }
}

function detailOf(err) {
  const d = err && err.response && err.response.data && err.response.data.detail
  return d || (err && err.message) || '未知错误'
}

// 差异展示：动作着色、字段中文、ID 反查名称
const ACTION_LABELS = { create: '新增', update: '更新', unchanged: '无变化', skip: '跳过', error: '错误' }
const ACTION_TAG = { create: 'success', update: 'warning', unchanged: 'info', skip: 'info', error: 'danger' }
const FIELD_LABELS = {
  name: '名称', device_type: '类型', brand: '品牌', model: '型号',
  parent_device_name: '父设备', area: '区域', room_type: '房间类型',
  room_number: '房间号', service_code: '资产编号', status_id: '状态',
  disuse_date: '停用/维修日期', support_ssh2: 'SSH2', support_telnet: 'Telnet',
  support_web: 'Web', support_snmp: 'SNMP', support_rdp: 'RDP',
  support_console: 'Console', management_services: '管理服务',
  ip_address: '管理IP', network_mask: '掩码', management_vlan: 'VLAN',
  mac_address: 'MAC', bmc_ip: 'BMC IP', bmc_mac: 'BMC MAC',
  mgmt_username: '账号', mgmt_password: '密码', description: '功能',
  remark: '备注', department: '部门', folder_id: '文件夹',
  rack_id: '机柜', rack_position: 'U位', rack_units: 'U数', rack_face: '正反面'
}

const rowActionTag = (a) => ACTION_TAG[a] || 'info'
const rowActionLabel = (a) => ACTION_LABELS[a] || a

function resolveVal(field, v) {
  if (v === 'TRUE') return '是'
  if (v === 'FALSE') return '否'
  if (v === '' || v === null || v === undefined) return '(空)'
  if (field === 'status_id') return statusId2name.value[v] || v
  if (field === 'folder_id') return folderId2path.value[v] || v
  if (field === 'rack_id') return rackId2name.value[v] || v
  if (field === 'rack_face') return v === 'front' ? '正面' : v === 'rear' ? '背面' : v
  return v
}

function formatChanges(changes) {
  if (!changes) return ''
  return Object.entries(changes)
    .map(([f, v]) => `${FIELD_LABELS[f] || f}: ${resolveVal(f, v[0])} → ${resolveVal(f, v[1])}`)
    .join('；')
}

function rowSummary(row) {
  if (row.action === 'update') return formatChanges(row.changes)
  if (row.action === 'create') return '新增设备'
  if (row.action === 'unchanged') return '与现有数据一致'
  return row.message || ''
}

const filteredRows = computed(() => {
  const rows = previewReport.value?.data?.rows || []
  if (rowFilter.value === 'all') return rows
  return rows.filter((x) => x.action === rowFilter.value)
})

const extraStats = computed(() => {
  const r = previewReport.value?.data
  if (!r) return []
  const out = []
  if (r.racks_created) out.push({ label: '机柜新增', value: r.racks_created, type: 'success' })
  if (r.racks_updated) out.push({ label: '机柜更新', value: r.racks_updated, type: '' })
  if (r.mounted) out.push({ label: '上架', value: r.mounted, type: 'success' })
  if (r.ports_created) out.push({ label: '端口新增', value: r.ports_created, type: 'success' })
  if (r.ports_updated) out.push({ label: '端口更新', value: r.ports_updated, type: '' })
  if (r.parents_linked) out.push({ label: '父子关系', value: r.parents_linked, type: '' })
  return out
})

onMounted(async () => {
  loadPrefs()
  loadOptions()
  loadFolderOptions()
  loadSuppliers()
  await refreshAll()
})
</script>

<style scoped>
.device-list { display: flex; flex-direction: column; gap: 15px; }

/* 批量操作条 */
.bulk-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 8px 14px;
  margin-bottom: 12px;
  background: #ecf5ff;
  border: 1px solid #b3d8ff;
  border-radius: 4px;
}

.bulk-info {
  font-size: 13px;
  color: #409eff;
}

.bulk-info b {
  font-size: 15px;
  margin: 0 2px;
}

.bulk-actions {
  display: flex;
  gap: 8px;
}

.bulk-tip {
  margin-bottom: 14px;
}

.bulk-form .bulk-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.bulk-form .bulk-check {
  flex-shrink: 0;
}

.bulk-form .bulk-input {
  flex: 1;
}

.device-name-link {
  font-weight: 500;
}

.scope-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin-bottom: 14px;
  background: #ecf5ff;
  border: 1px solid #d9ecff;
  border-radius: 4px;
  color: #409eff;
  font-size: 13px;
}
.scope-text { flex: 1; color: #606266; }
.scope-text strong { color: #303133; }

.toolbar {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #e4e7ed;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.pagination { margin-top: 20px; justify-content: flex-end; }

.column-selector { padding: 4px 2px; }
.column-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.column-title { font-weight: bold; color: #303133; }
.column-group { margin-bottom: 14px; }
.group-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
  padding-bottom: 4px;
  border-bottom: 1px dashed #e4e7ed;
  display: flex;
  align-items: center;
  gap: 4px;
}
.hint-icon { font-size: 13px; color: #c0c4cc; }
.unit-hint { color: #909399; font-size: 12px; }
.column-actions { display: flex; gap: 8px; }

:deep(.el-checkbox-group) { display: flex; flex-direction: column; gap: 8px; }
.method-tag {
  margin-right: 4px;
  margin-bottom: 2px;
  /* 深色背景 + 白字 + 加粗边框：解决默认 primary 浅底色在白表格里辨识度太低的问题 */
  background-color: var(--app-accent, #409eff);
  color: #fff;
  border: 1px solid var(--app-accent, #409eff);
  font-weight: 500;
}
.path-text { color: var(--app-text-secondary, #606266); }
.snmp-header { color: var(--app-accent, #409eff); }
.metric-value { font-weight: 500; color: var(--app-text, #303133); font-variant-numeric: tabular-nums; }
.metric-unit { color: #909399; font-size: 12px; margin-left: 2px; font-weight: normal; }

/* ---- 导入 / 导出 对话框 ---- */
.import-dialog { display: flex; flex-direction: column; gap: 16px; }
.import-options {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  margin-bottom: 0;
}
.import-options :deep(.el-form-item) { margin-bottom: 12px; }
.import-upload :deep(.el-upload-dragger) { padding: 18px; }
.import-actions { display: flex; align-items: center; gap: 12px; }
.preview-hint { color: #909399; font-size: 12px; }
.stat-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.diff-tabs { margin-top: 6px; }
.diff-toolbar { margin-bottom: 10px; }

/* 导出对话框：设备类型自定义勾选 */
.export-types { width: 100%; }
.export-types-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.export-types-ops { display: flex; gap: 4px; }
.export-types-box {
  margin-top: 8px;
  max-height: 160px;
  overflow-y: auto;
  padding: 8px 10px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  background: var(--app-bg-soft, #fafafa);
}
.export-types-box .type-cb {
  width: 46%;
  margin-right: 4%;
}
.change-text { color: #e6a23c; font-size: 12px; }
.issue-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 6px 4px;
  border-bottom: 1px dashed #ebeef5;
  font-size: 13px;
  line-height: 1.5;
}
.issue-row { color: #909399; flex: none; }
.issue-sheet {
  color: #fff;
  background: #909399;
  border-radius: 3px;
  padding: 0 5px;
  font-size: 11px;
  flex: none;
}
.issue-msg { color: #606266; flex: 1; }
.no-issue { color: #909399; text-align: center; padding: 20px 0; font-size: 13px; }
.tpl-tip { color: #606266; margin: 0 0 12px; font-size: 13px; }
</style>
