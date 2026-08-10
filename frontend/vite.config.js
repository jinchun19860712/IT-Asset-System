import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    // main.js v7.0 用了 top-level await，需 es2022+ 目标
    target: 'es2022'
  },
  server: {
    port: 5173,
    // 关键：给所有响应（包括 .vue / .js / index.html）加最严的 no-store 头
    // 防止 vite HMR 状态下浏览器磁盘缓存了之前的旧版本（导致用户看到"默认角色"/
    // "加载设备列表失败"等旧版本硬编码字眼）
    headers: {
      'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0'
    },
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
