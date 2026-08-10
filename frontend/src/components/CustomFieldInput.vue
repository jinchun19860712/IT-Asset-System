<template>
  <el-input
    v-if="field.field_type === 'text'"
    v-model="proxyValue"
    :placeholder="field.config?.placeholder"
    clearable
  />
  <el-input
    v-else-if="field.field_type === 'textarea'"
    v-model="proxyValue"
    type="textarea"
    :rows="field.config?.rows || 3"
    :placeholder="field.config?.placeholder"
  />
  <el-input-number
    v-else-if="field.field_type === 'number'"
    v-model.number="proxyValue"
    :min="field.config?.min"
    :max="field.config?.max"
    :precision="0"
    style="width: 100%"
  />
  <el-input-number
    v-else-if="field.field_type === 'decimal'"
    v-model.number="proxyValue"
    :min="field.config?.min"
    :max="field.config?.max"
    :precision="2"
    style="width: 100%"
  />
  <el-input
    v-else-if="field.field_type === 'percentage'"
    v-model.number="proxyValue"
    :placeholder="field.config?.placeholder"
  >
    <template #append>%</template>
  </el-input>
  <el-date-picker
    v-else-if="field.field_type === 'date'"
    v-model="proxyValue"
    type="date"
    value-format="YYYY-MM-DD"
    style="width: 100%"
  />
  <el-date-picker
    v-else-if="field.field_type === 'datetime'"
    v-model="proxyValue"
    type="datetime"
    value-format="YYYY-MM-DD HH:mm:ss"
    style="width: 100%"
  />
  <el-select
    v-else-if="field.field_type === 'select'"
    v-model="proxyValue"
    clearable
    style="width: 100%"
  >
    <el-option
      v-for="opt in normalizedOptions"
      :key="opt.value"
      :label="opt.label"
      :value="opt.value"
    />
  </el-select>
  <el-radio-group v-else-if="field.field_type === 'radio'" v-model="proxyValue">
    <el-radio
      v-for="opt in normalizedOptions"
      :key="opt.value"
      :value="opt.value"
    >{{ opt.label }}</el-radio>
  </el-radio-group>
  <el-switch
    v-else-if="field.field_type === 'checkbox'"
    v-model="proxyValue"
  />
  <el-select
    v-else-if="field.field_type === 'multi_select'"
    v-model="proxyValue"
    multiple
    clearable
    style="width: 100%"
  >
    <el-option
      v-for="opt in normalizedOptions"
      :key="opt.value"
      :label="opt.label"
      :value="opt.value"
    />
  </el-select>
  <el-input v-else v-model="proxyValue" :placeholder="field.config?.placeholder" />
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  field: { type: Object, required: true },
  modelValue: { default: null }
})
const emit = defineEmits(['update:modelValue'])

// v-model 代理：避免在模板里每次都写 :model-value + @update:model-value
const proxyValue = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v)
})

// options 归一化：后端是 [{label, value}] 数组，兼容旧的 "a,b,c" 字符串格式
const normalizedOptions = computed(() => {
  const opts = props.field.options
  if (Array.isArray(opts)) {
    return opts.map(o => {
      if (typeof o === 'string') return { label: o, value: o }
      return { label: o.label ?? o.value ?? '', value: o.value ?? o.label ?? '' }
    })
  }
  if (typeof opts === 'string' && opts) {
    return opts.split(',').map(s => s.trim()).filter(Boolean).map(s => ({ label: s, value: s }))
  }
  return []
})
</script>