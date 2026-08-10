<template>
  <el-dropdown trigger="click" placement="bottom-end" @command="onCommand">
    <el-button class="theme-btn">
      <el-icon size="18"><Brush /></el-icon>
      <span class="theme-label">{{ currentLabel }}</span>
      <el-icon><ArrowDown /></el-icon>
    </el-button>
    <template #dropdown>
      <div class="theme-panel">
        <div class="tp-title">主题预设</div>
        <div class="tp-presets">
          <div
            v-for="(p, key) in presets"
            :key="key"
            class="tp-preset"
            :class="{ active: current.preset === key }"
            @click="choosePreset(key)"
          >
            <span class="tp-swatch" :style="{ background: p.headerBg }">
              <span class="tp-dot" :style="{ background: p.accent }"></span>
            </span>
            <span class="tp-name">{{ p.label }}</span>
            <el-icon v-if="current.preset === key" class="tp-check"><Check /></el-icon>
          </div>
        </div>

        <div class="tp-title" style="margin-top: 12px;">强调色</div>
        <div class="tp-accent">
          <el-color-picker
            :model-value="current.accent || presets[current.preset]?.accent"
            @change="onAccent"
            show-alpha
          />
          <el-button link type="primary" size="small" @click="resetAccent">重置为预设</el-button>
          <span class="tp-accent-hint">当前：{{ current.accent || presets[current.preset]?.accent }}</span>
        </div>
      </div>
    </template>
  </el-dropdown>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Brush, ArrowDown, Check } from '@element-plus/icons-vue'
import { THEME_PRESETS, loadTheme, applyTheme, setPreset, setAccent, clearAccent } from '../theme.js'

const presets = THEME_PRESETS
const current = ref(loadTheme())

const currentLabel = computed(() => presets[current.value.preset]?.label || '主题')

onMounted(() => { applyTheme(current.value) })

const choosePreset = (key) => {
  current.value = setPreset(key)
}
const onAccent = (color) => {
  if (!color) { resetAccent(); return }
  current.value = setAccent(color)
}
const resetAccent = () => {
  current.value = clearAccent()
}
// 保留 command 占位以兼容 el-dropdown 事件（实际用 div click 处理）
const onCommand = () => {}
</script>

<style scoped>
.theme-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  color: var(--app-header-text, var(--app-menu-text, #fff)) !important;
  background-color: rgba(255, 255, 255, 0.12) !important;
  border: 1px solid rgba(255, 255, 255, 0.25) !important;
  border-radius: 6px;
  font-size: 13px;
  transition: background-color 0.2s, border-color 0.2s;
}
.theme-btn:hover {
  background-color: rgba(255, 255, 255, 0.22) !important;
  border-color: rgba(255, 255, 255, 0.4) !important;
}
.theme-label { font-size: 13px; white-space: nowrap; }
.theme-panel { width: 240px; padding: 12px; }
.tp-title { font-size: 12px; color: var(--el-text-color-secondary); margin-bottom: 8px; }
.tp-presets { display: flex; flex-direction: column; gap: 6px; }
.tp-preset {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 8px;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid transparent;
}
.tp-preset:hover { background: var(--el-fill-color-light); }
.tp-preset.active { background: var(--el-color-primary-light-9); border-color: var(--el-color-primary); }
.tp-swatch {
  width: 28px; height: 18px; border-radius: 4px;
  display: inline-flex; align-items: center; justify-content: flex-end;
  padding-right: 4px; box-shadow: inset 0 0 0 1px rgba(0,0,0,0.12);
}
.tp-dot { width: 8px; height: 8px; border-radius: 50%; }
.tp-name { flex: 1; font-size: 13px; color: var(--el-text-color-primary); }
.tp-check { color: var(--el-color-primary); }
.tp-accent { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.tp-accent-hint { font-size: 12px; color: var(--el-text-color-secondary); width: 100%; }
</style>
