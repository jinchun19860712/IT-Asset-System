import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  },
  // Session cookie 关键：必须 true，浏览器才会把 cookie 带过去
  withCredentials: true
})

// 401 拦截：登录态失效 → 跳登录页
let _onUnauthenticated = null
export function setUnauthenticatedHandler(fn) { _onUnauthenticated = fn }

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    // 后端用 401 + JSON 表示鉴权失败；这里拦截后通知上层处理（清 token + 跳登录）
    if (error?.response?.status === 401 && _onUnauthenticated) {
      try { _onUnauthenticated() } catch (_) {}
    }
    return Promise.reject(error)
  }
)

// 鉴权 API（基础账户体系 B1）
export const authApi = {
  login: (username, password) => {
    const fd = new FormData()
    fd.append('username', username)
    fd.append('password', password)
    return api.post('/auth/login', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
  // 自助改密
  changePassword: (oldPassword, newPassword) =>
    api.post('/auth/change-password', { old_password: oldPassword, new_password: newPassword }),
  // 用户管理（仅 admin）
  listUsers: (keyword) => api.get('/auth/users', { params: keyword ? { keyword } : {} }),
  createUser: (data) => api.post('/auth/users', data),
  updateUser: (id, data) => api.put(`/auth/users/${id}`, data),
  deleteUser: (id) => api.delete(`/auth/users/${id}`),
  resetPassword: (id, newPassword) =>
    api.post(`/auth/users/${id}/reset-password`, { new_password: newPassword })
}

// 文件夹API
export const folderApi = {
  // kind: 'org' 组织机构树 / 'asset' 设备资产树；不传则返回全部
  getTree: (kind) => api.get('/folders/tree', { params: kind ? { kind } : {} }),
  getList: (parentId, kind) => api.get('/folders', { params: { parent_id: parentId, kind } }),
  create: (data) => api.post('/folders', data),
  update: (id, data) => api.put(`/folders/${id}`, data),
  delete: (id) => api.delete(`/folders/${id}`),
  getDescendants: (id) => api.get(`/folders/${id}/descendants`),
  rebuildPaths: () => api.post('/folders/rebuild-paths')
}

// 设备API
export const deviceApi = {
  getList: (params) => api.get('/devices', { params }),
  getDetail: (id) => api.get(`/devices/${id}`),
  create: (data) => api.post('/devices', data),
  update: (id, data) => api.put(`/devices/${id}`, data),
  delete: (id) => api.delete(`/devices/${id}`),
  getAll: () => api.get('/devices/all'),
  getTypes: () => api.get('/devices/types/list'),
  getDepartments: () => api.get('/devices/departments/list'),
  // 批量操作
  bulkDelete: (ids) => api.post('/devices/bulk-delete', { ids }),
  bulkUpdate: (ids, data) => api.post('/devices/bulk-update', { ids, ...data }),
  // 导入导出（以「网络设备台账」Excel 为模板）
  // 预览：解析+差异分析，不写库
  previewImport: (file, opts = {}) => {
    const fd = new FormData()
    fd.append('file', file)
    for (const [k, v] of Object.entries(opts)) {
      if (v !== undefined && v !== null) fd.append(k, v)
    }
    return api.post('/devices/import-preview', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  // 正式导入（单事务，失败整体回滚）
  importXlsx: (file, opts = {}) => {
    const fd = new FormData()
    fd.append('file', file)
    for (const [k, v] of Object.entries(opts)) {
      if (v !== undefined && v !== null) fd.append(k, v)
    }
    return api.post('/devices/import', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  // 导出：可携带端口 / 机柜 Sheet，可按文件夹/资产分类范围、按设备类型筛选
  exportXlsx: (opts = {}) => {
    const params = {}
    for (const [k, v] of Object.entries(opts)) {
      if (v === undefined || v === null) continue
      if (Array.isArray(v)) params[k] = v.join(',')
      else params[k] = v
    }
    return api.get('/devices/export', { params, responseType: 'blob' })
  },
  getImportTemplate: (withSample = false) =>
    api.get('/devices/import-template', { params: { with_sample: withSample }, responseType: 'blob' })
}

// 自定义字段API（增强版）
export const customFieldApi = {
  list: () => api.get('/custom-fields'),
  getList: () => api.get('/custom-fields'),  // 旧方法名兼容
  get: (id) => api.get(`/custom-fields/${id}`),
  create: (data) => api.post('/custom-fields', data),
  update: (id, data) => api.put(`/custom-fields/${id}`, data),
  delete: (id) => api.delete(`/custom-fields/${id}`)
}

// 状态API
export const statusApi = {
  getList: () => api.get('/statuses'),
  create: (data) => api.post('/statuses', data),
  update: (id, data) => api.put(`/statuses/${id}`, data),
  delete: (id) => api.delete(`/statuses/${id}`)
}

// 配置API
export const configApi = {
  getStatus: () => api.get('/config/status'),
  updateStatus: (data) => api.post('/config/status', data),
  getOid: () => api.get('/config/oid'),
  updateOid: (data) => api.post('/config/oid', data),
  getLdap: () => api.get('/config/ldap'),
  updateLdap: (data) => api.post('/config/ldap', data),
  testLdap: (data) => api.post('/config/ldap/test', data)
}

// SNMP API
export const snmpApi = {
  // deviceType 传入后只返回适用于该设备类型的模板
  getTemplates: (deviceType) => api.get('/snmp/templates', {
    params: deviceType ? { device_type: deviceType } : {}
  }),
  getTemplateMetrics: (name) => api.get(`/snmp/templates/${encodeURIComponent(name)}/metrics`),
  getDeviceMetrics: (deviceId) => api.get(`/snmp/devices/${deviceId}/metrics`),
  pollDevice: (deviceId) => api.post(`/snmp/devices/${deviceId}/poll`),
  pollAll: () => api.post('/snmp/poll-all'),
  getAllDeviceMetrics: () => api.get('/snmp/all-device-metrics'),
  // 所有设备已勾选指标的并集，用于驱动设备列表的动态列
  getMetricColumns: () => api.get('/snmp/metric-columns'),
  // 全局采集配置（模拟开关 / 默认团体名 / 超时）
  getSettings: () => api.get('/snmp/settings'),
  updateSettings: (data) => api.put('/snmp/settings', data),
  // 连通性测试：读取 sysDescr / sysName / sysUpTime
  testDevice: (deviceId) => api.post(`/snmp/devices/${deviceId}/test`, null, { timeout: 30000 })
}

// 机柜API
export const rackApi = {
  getList: (folderId) => api.get('/racks', { params: folderId ? { folder_id: folderId } : {} }),
  create: (data) => api.post('/racks', data),
  update: (id, data) => api.put(`/racks/${id}`, data),
  delete: (id) => api.delete(`/racks/${id}`),
  getLayout: (id) => api.get(`/racks/${id}/layout`),
  mount: (rackId, data) => api.post(`/racks/${rackId}/mount`, data),
  unmount: (deviceId) => api.post(`/racks/unmount/${deviceId}`),
  getAvailableDevices: (folderId) => api.get('/racks/available-devices/list', {
    params: folderId ? { folder_id: folderId } : {}
  })
}

// 拓扑API
export const topologyApi = {
  get: (folderId) => api.get('/topology', { params: folderId ? { folder_id: folderId } : {} })
}

// 字典API（产品类型 / 品牌 / 供应商 / 软件分类）
export const dictApi = {
  getTypes: () => api.get('/dictionaries/types'),
  getAll: () => api.get('/dictionaries/all'),
  getByType: (t) => api.get(`/dictionaries/${t}`),
  create: (data) => api.post('/dictionaries', data),
  update: (id, data) => api.put(`/dictionaries/${id}`, data),
  delete: (id) => api.delete(`/dictionaries/${id}`)
}

// 软件资产API
export const softwareApi = {
  getList: (params) => api.get('/softwares', { params }),
  getDetail: (id) => api.get(`/softwares/${id}`),
  create: (data) => api.post('/softwares', data),
  update: (id, data) => api.put(`/softwares/${id}`, data),
  delete: (id) => api.delete(`/softwares/${id}`),
  // 批量操作
  bulkDelete: (ids) => api.post('/softwares/bulk-delete', { ids }),
  bulkUpdate: (ids, data) => api.post('/softwares/bulk-update', { ids, ...data })
}

// 合同附件API
export const contractApi = {
  upload: (file, opts = {}) => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('name', opts.name || file.name)
    if (opts.supplier_id != null) fd.append('supplier_id', opts.supplier_id)
    if (opts.supplier_name != null) fd.append('supplier_name', opts.supplier_name)
    if (opts.related_type != null) fd.append('related_type', opts.related_type)
    if (opts.related_id != null) fd.append('related_id', opts.related_id)
    if (opts.remark != null) fd.append('remark', opts.remark)
    return api.post('/contracts/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  list: (params = {}) => api.get('/contracts', { params }),
  get: (id) => api.get(`/contracts/${id}`),
  update: (id, data) => api.put(`/contracts/${id}`, data),
  remove: (id) => api.delete(`/contracts/${id}`),
  // 浏览器直接下载用的完整路径（含 /api，便于走 vite 代理）
  downloadUrl: (id) => `/api/contracts/${id}/download`
}

// 产品类型API
export const productTypeApi = {
  list: (activeOnly = false) => api.get('/product-types', { params: { active_only: activeOnly } }),
  get: (id) => api.get(`/product-types/${id}`),
  create: (data) => api.post('/product-types', data),
  update: (id, data) => api.put(`/product-types/${id}`, data),
  delete: (id) => api.delete(`/product-types/${id}`),
  // 布局关联
  getFields: (id) => api.get(`/product-types/${id}/fields`),
  linkFields: (id, fieldIds) => api.put(`/product-types/${id}/fields`, { field_ids: fieldIds })
}

// 告警 API（N1 - SNMP 阈值告警）
export const alertApi = {
  list: (params = {}) => api.get('/alerts', { params }),
  active: (limit = 10) => api.get('/alerts/active', { params: { limit } }),
  activeCount: () => api.get('/alerts/active-count'),
  ack: (id) => api.post(`/alerts/${id}/ack`),
  ackBatch: (ids) => api.post('/alerts/ack-batch', { ids }),
  remove: (id) => api.delete(`/alerts/${id}`)
}

// 审计日志 API（N3 - 仅管理员）
export const auditLogApi = {
  list: (params = {}) => api.get('/audit-logs', { params }),
  stats: () => api.get('/audit-logs/stats')
}

export default api
