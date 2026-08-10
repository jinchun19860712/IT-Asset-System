<template>
  <div class="software-panel">
    <div class="panel-header">
      <span class="title">软件面板</span>
      <div class="header-ops">
        <el-tooltip content="刷新" placement="top">
          <el-button size="small" text @click="loadCategories">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </el-tooltip>
      </div>
    </div>

    <el-input v-model="filterText" placeholder="搜索分类" clearable size="small" class="filter-input">
      <template #prefix><el-icon><Search /></el-icon></template>
    </el-input>

    <div class="scope-tip">
      点击任意软件分类，右侧显示归入该分类的软件；再次点击或点击「全部软件」恢复显示全部
    </div>

    <!-- 全部软件（默认未选中状态） -->
    <div
      class="all-row"
      :class="{ active: !selectedCategory }"
      @click="selectAll"
    >
      <el-icon><Files /></el-icon>
      <span>全部软件</span>
    </div>

    <!-- 分类列表 -->
    <div class="cat-list">
      <div
        v-for="c in filteredCategories"
        :key="c.id"
        class="cat-row"
        :class="{ active: selectedCategory === c.name }"
        @click="selectOne(c)"
      >
        <el-icon><Coin /></el-icon>
        <span class="cat-name">{{ c.name }}</span>
        <el-tag v-if="c.remark" size="small" type="info" effect="plain" class="cat-remark">
          {{ c.remark }}
        </el-tag>
      </div>
      <el-empty v-if="filteredCategories.length === 0" description="暂无分类" :image-size="60" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Refresh, Search, Files, Coin } from '@element-plus/icons-vue'
import { dictApi } from '../api/index.js'

const props = defineProps({
  // 当前选中的软件分类名称
  activeCategory: { type: String, default: null }
})
const emit = defineEmits(['select-category'])

const categories = ref([])
const filterText = ref(null)

const filteredCategories = computed(() => {
  if (!filterText.value) return categories.value
  const kw = filterText.value.toLowerCase()
  return categories.value.filter(c => (c.name || '').toLowerCase().includes(kw))
})

const selectedCategory = computed(() => props.activeCategory)

const loadCategories = async () => {
  try {
    const res = await dictApi.getByType('software_category')
    if (res.code === 0) {
      categories.value = (res.data || []).filter(x => x.enabled !== false)
    }
  } catch (e) {
    ElMessage.error('加载软件分类失败')
  }
}

const selectAll = () => {
  emit('select-category', null)
}

const selectOne = (c) => {
  // 再次点击已选 → 取消
  if (selectedCategory.value === c.name) {
    emit('select-category', null)
  } else {
    emit('select-category', c.name)
  }
}

const clearSelection = () => {
  emit('select-category', null)
}

onMounted(loadCategories)

defineExpose({ loadCategories, clearSelection })
</script>

<style scoped>
.software-panel { padding: 15px; height: 100%; }
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--app-border, #e4e7ed);
}
.header-ops { display: flex; gap: 4px; align-items: center; }
.title { font-weight: bold; font-size: 16px; }
.filter-input { margin-bottom: 8px; }
.scope-tip {
  font-size: 12px;
  color: var(--app-text-secondary, #909399);
  line-height: 1.5;
  margin-bottom: 10px;
  padding: 6px 8px;
  background: var(--app-tip-bg, #f4f4f5);
  border-radius: 4px;
}
.all-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: 6px;
  background: var(--app-accent-soft, #ecf5ff);
  color: var(--app-accent, #409eff);
  font-weight: 500;
  transition: background 0.15s;
}
.all-row:hover { background: var(--app-accent-soft-hover, #d9ecff); }
.cat-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.cat-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  color: var(--app-text, #303133);
}
.cat-row:hover { background: var(--app-row-hover, #f5f7fa); }
.cat-row.active {
  background: var(--app-accent-soft, #ecf5ff);
  color: var(--app-accent, #409eff);
  font-weight: 500;
}
.cat-name { flex: 1; }
.cat-remark { transform: scale(0.85); }
</style>
