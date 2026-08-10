import { createRouter, createWebHistory } from 'vue-router'
import Layout from '../views/Layout.vue'
import DeviceList from '../views/DeviceList.vue'
import Dashboard from '../views/Dashboard.vue'
import DeviceForm from '../views/DeviceForm.vue'
import ConfigPage from '../views/ConfigPage.vue'
import RackView from '../views/RackView.vue'
import TopologyView from '../views/TopologyView.vue'
import SoftwareList from '../views/SoftwareList.vue'
import SoftwareForm from '../views/SoftwareForm.vue'
import DictManager from '../views/DictManager.vue'
import ContractList from '../views/ContractList.vue'
import ProductTypeManager from '../views/ProductTypeManager.vue'
import CustomFieldManager from '../views/CustomFieldManager.vue'
import Login from '../views/Login.vue'
import AlertList from '../views/AlertList.vue'
import { useAuth } from '../store/auth.js'

const routes = [
  // 登录页（独立布局，不走 Layout）
  { path: '/login', name: 'Login', component: Login, meta: { public: true } },
  {
    path: '/',
    component: Layout,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'Dashboard', component: Dashboard },
      { path: 'devices', name: 'DeviceList', component: DeviceList },
      { path: 'devices/add', name: 'DeviceAdd', component: DeviceForm },
      { path: 'devices/edit/:id', name: 'DeviceEdit', component: DeviceForm },
      { path: 'softwares', name: 'SoftwareList', component: SoftwareList },
      { path: 'softwares/add', name: 'SoftwareAdd', component: SoftwareForm },
      { path: 'softwares/edit/:id', name: 'SoftwareEdit', component: SoftwareForm },
      { path: 'dict', name: 'DictManager', component: DictManager },
      { path: 'product-types', name: 'ProductTypeManager', component: ProductTypeManager },
      { path: 'custom-fields', name: 'CustomFieldManager', component: CustomFieldManager },
      { path: 'contracts', name: 'ContractList', component: ContractList },
      { path: 'racks', name: 'RackView', component: RackView },
      { path: 'topology', name: 'TopologyView', component: TopologyView },
      { path: 'config', name: 'Config', component: ConfigPage },
      { path: 'alerts', name: 'AlertList', component: AlertList }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫：未登录访问受保护资源 → 跳登录；已登录访问 /login → 跳首页
// 关键：auth.isAuthenticated 是 computed ref 对象，必须用 .value 取实际 boolean 值
// 否则 ref 对象永远 truthy，!ref 永远 false，守卫形同虚设
router.beforeEach((to) => {
  const auth = useAuth()
  const isAuth = auth.isAuthenticated.value  // ★ 解包 ref

  if (to.meta.public) {
    if (isAuth && to.path === '/login') {
      return { path: '/' }
    }
    return true
  }
  if (to.meta.requiresAuth && !isAuth) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router
