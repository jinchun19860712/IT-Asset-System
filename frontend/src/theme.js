// 主题系统：预设 + 自定义强调色，写入 CSS 变量并切换 Element Plus 深色模式
// 预设均经过对比度校验，确保浅色下文字深、深色下文字浅

const STORAGE_KEY = 'app_theme_v1'

export const THEME_PRESETS = {
  default: {
    label: '默认浅色', mode: 'light',
    headerBg: '#1a2233', menuText: '#ffffff',
    bg: '#f2f4f7', bgSoft: '#fafbfc', panel: '#ffffff', text: '#1f2329', textSecondary: '#5f6672',
    border: '#d9dde4', borderStrong: '#cdd3dc', accent: '#2563eb',
    accentSoft: '#eaf2ff',
    // 机柜设备块专用文字色：浅色主题下底色是浅蓝/浅绿/浅紫，用深色文字
    textOnRack: '#2f3742',
    textSecondaryOnRack: '#5f6672',
    textTertiaryOnRack: '#909399'
  },
  cool: {
    label: '冷灰浅色', mode: 'light',
    headerBg: '#2c3e50', menuText: '#f0f4f8',
    bg: '#eef1f4', bgSoft: '#f5f7f9', panel: '#ffffff', text: '#1a1d21', textSecondary: '#55606f',
    border: '#d6dbe1', borderStrong: '#c5cbd1', accent: '#0f766e',
    accentSoft: '#e6f3f1',
    textOnRack: '#1a1d21',
    textSecondaryOnRack: '#55606f',
    textTertiaryOnRack: '#7a8899'
  },
  sky: {
    label: '天空浅色', mode: 'light',
    headerBg: '#0ea5e9', menuText: '#ffffff',
    bg: '#f0f9ff', bgSoft: '#f7fbff', panel: '#ffffff', text: '#1e293b', textSecondary: '#4b5563',
    border: '#d4e6f1', borderStrong: '#bfd9eb', accent: '#0284c7',
    accentSoft: '#e0f0fc',
    textOnRack: '#1e293b',
    textSecondaryOnRack: '#4b5563',
    textTertiaryOnRack: '#64748b'
  },
  midnight: {
    label: '午夜深色', mode: 'dark',
    headerBg: '#0b0d10', menuText: '#e1e7ef',
    bg: '#12151a', bgSoft: '#232830', panel: '#1a1e24', text: '#e6eaf1', textSecondary: '#94a3b8',
    border: '#2a303a', borderStrong: '#3a414c', accent: '#3b82f6',
    accentSoft: '#1f2a44',
    // 深色主题下底色是深色块，用浅色文字保证对比度
    textOnRack: '#f1f5fb',
    textSecondaryOnRack: '#cbd5e1',
    textTertiaryOnRack: '#94a3b8'
  }
}

export function loadTheme() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      // 兼容旧 preset 名
      if (!THEME_PRESETS[parsed.preset]) {
        parsed.preset = 'default'
        parsed.accent = null
      }
      return parsed
    }
  } catch (e) { /* ignore */ }
  return { preset: 'default', accent: null, mode: null }
}

// 把 #rrggbb 解析成 [r,g,b]
function hexToRgb(hex) {
  const h = (hex || '#000000').replace('#', '')
  const s = h.length === 3 ? h.split('').map(c => c + c).join('') : h
  return [
    parseInt(s.slice(0, 2), 16),
    parseInt(s.slice(2, 4), 16),
    parseInt(s.slice(4, 6), 16)
  ]
}

// 混合两种颜色：t 为 b 所占比例（0~1）
function mix(a, b, t) {
  const ca = hexToRgb(a), cb = hexToRgb(b)
  const r = Math.round(ca[0] * (1 - t) + cb[0] * t)
  const g = Math.round(ca[1] * (1 - t) + cb[1] * t)
  const bl = Math.round(ca[2] * (1 - t) + cb[2] * t)
  return `#${[r, g, bl].map(x => x.toString(16).padStart(2, '0')).join('')}`
}

// 基于背景亮度决定前景色（黑/白），保证对比度
function contrastText(hex) {
  const [r, g, b] = hexToRgb(hex)
  const yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000
  return yiq >= 160 ? '#1f2329' : '#ffffff'
}

export function applyTheme(theme) {
  const preset = THEME_PRESETS[theme.preset] || THEME_PRESETS.default
  const root = document.documentElement
  const mode = theme.mode || preset.mode
  const accent = theme.accent || preset.accent

  root.setAttribute('data-theme', mode)
  root.classList.toggle('dark', mode === 'dark')

  root.style.setProperty('--app-header-bg', preset.headerBg)
  root.style.setProperty('--app-menu-text', preset.menuText)
  root.style.setProperty('--app-bg', preset.bg)
  root.style.setProperty('--app-bg-soft', preset.bgSoft)
  root.style.setProperty('--app-panel', preset.panel)
  root.style.setProperty('--app-text', preset.text)
  root.style.setProperty('--app-text-secondary', preset.textSecondary)
  root.style.setProperty('--app-border', preset.border)
  root.style.setProperty('--app-border-strong', preset.borderStrong)
  root.style.setProperty('--app-accent', accent)
  root.style.setProperty('--app-accent-soft', preset.accentSoft || 'rgba(64,158,255,0.12)')
  root.style.setProperty('--app-text-on-rack', preset.textOnRack || '#2f3742')
  root.style.setProperty('--app-text-secondary-on-rack', preset.textSecondaryOnRack || '#5f6672')
  root.style.setProperty('--app-text-tertiary-on-rack', preset.textTertiaryOnRack || '#909399')

  // Element Plus 主色及衍生色阶（hover / active 等状态）
  root.style.setProperty('--el-color-primary', accent)
  root.style.setProperty('--el-color-primary-light-3', mix('#ffffff', accent, 0.3))
  root.style.setProperty('--el-color-primary-light-5', mix('#ffffff', accent, 0.5))
  root.style.setProperty('--el-color-primary-light-7', mix('#ffffff', accent, 0.7))
  root.style.setProperty('--el-color-primary-light-8', mix('#ffffff', accent, 0.8))
  root.style.setProperty('--el-color-primary-light-9', mix('#ffffff', accent, 0.9))
  root.style.setProperty('--el-color-primary-dark-2', mix('#000000', accent, 0.2))

  // 让 header 上的按钮/图标自动取高对比前景
  root.style.setProperty('--app-header-text', preset.menuText)

  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(theme)) } catch (e) { /* ignore */ }
}

export function setPreset(presetName) {
  const t = loadTheme()
  t.preset = presetName
  // 切换预设时不强制改自定义强调色，但若用户没自定义过则跟随预设
  if (!t.accent) t.accent = THEME_PRESETS[presetName]?.accent || null
  applyTheme(t)
  return t
}

export function setAccent(color) {
  const t = loadTheme()
  t.accent = color
  applyTheme(t)
  return t
}

export function clearAccent() {
  const t = loadTheme()
  t.accent = null
  applyTheme(t)
  return t
}
