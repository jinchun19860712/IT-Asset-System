<template>
  <div class="folder-panel">
    <div class="panel-header">
      <span class="title">{{ activeKind === 'org' ? '组织机构' : '设备资产' }}</span>
      <div class="header-ops">
        <el-tooltip content="刷新" placement="top">
          <el-button size="small" text @click="loadFolders">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip :content="`新建${activeKind === 'org' ? '一级文件夹' : '一级节点'}`" placement="top">
          <el-button type="primary" size="small" @click="showAddDialog(null)">
            <el-icon><Plus /></el-icon>
          </el-button>
        </el-tooltip>
      </div>
    </div>

    <!-- 两种树的切换（仅 both 模式显示标签，org/asset 模式只显示对应一棵树） -->
    <el-tabs
      v-if="mode === 'both'"
      v-model="activeKind"
      class="tree-tabs"
      @tab-change="onTabChange"
    >
      <el-tab-pane label="组织机构" name="org" />
      <el-tab-pane label="设备资产" name="asset" />
    </el-tabs>

    <el-input v-model="filterText" placeholder="搜索文件夹" clearable size="small" class="filter-input">
      <template #prefix><el-icon><Search /></el-icon></template>
    </el-input>

    <div class="scope-tip">
      {{ activeKind === 'org'
        ? '点击任意部门，右侧显示该部门及其下级设备'
        : '点击任意资产分类，右侧显示归入该分类的设备' }}
    </div>

    <el-tree
      ref="treeRef"
      :data="folderTree"
      :props="defaultProps"
      node-key="id"
      highlight-current
      default-expand-all
      :filter-node-method="filterNode"
      :expand-on-click-node="false"
      @node-click="handleNodeClick"
      @node-contextmenu="handleContextMenu"
    >
      <template #default="{ node, data }">
        <span class="tree-node">
          <el-icon v-if="!data.children || data.children.length === 0"><Document /></el-icon>
          <el-icon v-else><Folder /></el-icon>
          <span class="node-label">{{ node.label }}</span>
          <el-tag v-if="data.is_department" size="small" type="success" effect="plain" class="dept-tag">部门</el-tag>
        </span>
      </template>
    </el-tree>

    <!-- 右键菜单 -->
    <el-dropdown ref="contextMenuRef" trigger="contextmenu" @command="handleCommand">
      <span style="position: fixed;" :style="menuStyle"></span>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item command="add">添加子节点</el-dropdown-item>
          <el-dropdown-item command="rename">重命名</el-dropdown-item>
          <el-dropdown-item command="toggleDept" divided v-if="activeKind === 'org'">
            {{ currentNode?.is_department ? '取消部门标记' : '标记为部门' }}
          </el-dropdown-item>
          <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>

    <!-- 添加/重命名对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="360px">
      <el-form label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="folderName" placeholder="请输入名称" @keyup.enter="confirmFolder" />
        </el-form-item>
        <el-form-item label="部门节点" v-if="dialogMode === 'add' && activeKind === 'org'">
          <el-switch v-model="markAsDept" />
          <div class="dialog-hint">开启后，该节点下的设备会自动归属到这个部门</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmFolder">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Search, Folder, Document } from '@element-plus/icons-vue'
import { folderApi } from '../api/index.js'

const emit = defineEmits(['select-folder'])
const props = defineProps({
  activeFolderId: Number,
  // both=组织机构+设备资产双树；org=仅组织机构；asset=仅设备资产
  mode: { type: String, default: 'both' }
})

const activeKind = ref('org')
const treeRef = ref()
const lastClickedId = ref(null)
const folderTree = ref([])
const contextMenuRef = ref()
const menuStyle = ref({ left: '0px', top: '0px' })
const currentNode = ref(null)
const dialogVisible = ref(false)
const dialogTitle = ref('')
const folderName = ref('')
const dialogMode = ref('add')
const markAsDept = ref(false)
const filterText = ref(null)

const defaultProps = { children: 'children', label: 'name' }

watch(filterText, (val) => { treeRef.value?.filter(val) })

// 外部切换模式（组织机构 / 设备资产）时，同步当前树并重新加载
watch(() => props.mode, (m) => {
  if (m === 'org' || m === 'asset') {
    if (activeKind.value !== m) {
      activeKind.value = m
      emit('select-folder', null)
      loadFolders()
    }
  }
}, { immediate: true })

const filterNode = (value, data) => {
  if (!value) return true
  return (data.name || '').includes(value)
}

const loadFolders = async () => {
  const res = await folderApi.getTree(activeKind.value)
  if (res.code === 0) folderTree.value = res.data || []
}

const onTabChange = () => {
  // 切换树时清空右侧已选范围
  currentNode.value = null
  lastClickedId.value = null
  folderTree.value = []
  emit('select-folder', null)
  loadFolders()
}

const handleNodeClick = (data) => {
  // 再次点击已选节点 → 取消选择，右侧恢复显示全部
  if (lastClickedId.value === data.id) {
    lastClickedId.value = null
    treeRef.value?.setCurrentKey(null)
    emit('select-folder', null)
    return
  }
  lastClickedId.value = data.id
  emit('select-folder', { ...data, kind: activeKind.value })
}

const clearSelection = () => {
  treeRef.value?.setCurrentKey(null)
}

const handleContextMenu = (event, data) => {
  event.preventDefault()
  currentNode.value = data
  menuStyle.value = { left: event.clientX + 'px', top: event.clientY + 'px' }
  setTimeout(() => { contextMenuRef.value?.handleOpen() }, 10)
}

const handleCommand = (cmd) => {
  if (cmd === 'add') showAddDialog(currentNode.value)
  else if (cmd === 'rename') showRenameDialog(currentNode.value)
  else if (cmd === 'toggleDept') toggleDepartment(currentNode.value)
  else if (cmd === 'delete') handleDelete(currentNode.value)
}

const showAddDialog = (parent) => {
  dialogMode.value = 'add'
  dialogTitle.value = parent ? `在「${parent.name}」下新建` : `新建一级节点`
  folderName.value = ''
  // 二级目录通常就是部门，默认帮用户勾上（仅组织机构树）
  markAsDept.value = activeKind.value === 'org' && !!parent && !parent.parent_id
  currentNode.value = parent
  dialogVisible.value = true
}

const showRenameDialog = (node) => {
  dialogMode.value = 'rename'
  dialogTitle.value = '重命名'
  folderName.value = node.name
  currentNode.value = node
  dialogVisible.value = true
}

const toggleDepartment = async (node) => {
  try {
    await folderApi.update(node.id, { is_department: !node.is_department })
    ElMessage.success(node.is_department ? '已取消部门标记' : '已标记为部门')
    loadFolders()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const confirmFolder = async () => {
  if (!folderName.value.trim()) {
    ElMessage.warning('请输入名称')
    return
  }
  try {
    if (dialogMode.value === 'add') {
      await folderApi.create({
        name: folderName.value.trim(),
        parent_id: currentNode.value?.id || null,
        sort_order: 0,
        is_department: activeKind.value === 'org' ? markAsDept.value : false,
        kind: activeKind.value
      })
      ElMessage.success('添加成功')
    } else {
      await folderApi.update(currentNode.value.id, { name: folderName.value.trim() })
      ElMessage.success('重命名成功')
    }
    dialogVisible.value = false
    loadFolders()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const handleDelete = async (node) => {
  try {
    await ElMessageBox.confirm(
      `确定删除「${node.name}」吗？其所有子节点也会一并删除。`,
      '提示', { type: 'warning' }
    )
    await folderApi.delete(node.id)
    ElMessage.success('删除成功')
    emit('select-folder', null)
    loadFolders()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

onMounted(loadFolders)

defineExpose({ loadFolders, clearSelection })
</script>

<style scoped>
.folder-panel { padding: 15px; height: 100%; }
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e4e7ed;
}
.header-ops { display: flex; gap: 4px; align-items: center; }
.title { font-weight: bold; font-size: 16px; }
.tree-tabs { margin-bottom: 4px; }
.tree-tabs :deep(.el-tabs__header) { margin-bottom: 8px; }
.filter-input { margin-bottom: 8px; }
.scope-tip {
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
  margin-bottom: 10px;
  padding: 6px 8px;
  background: #f4f4f5;
  border-radius: 4px;
}
.tree-node { display: flex; align-items: center; gap: 5px; }
.node-label { margin-left: 4px; }
.dept-tag { margin-left: 6px; transform: scale(0.85); }
.dialog-hint { font-size: 12px; color: #909399; line-height: 1.5; }
</style>
