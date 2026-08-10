<template>
  <!--
    v5.0 极简：直接渲染 router-view
    登录态检查完全由 router beforeEach 守卫负责
  -->
  <router-view />
</template>

<script setup>
// 无任何跳转逻辑
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB',
    'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  background-color: #f5f7fa;
}
</style>
