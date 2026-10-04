<script setup lang="ts">
defineProps<{ label?: string; error?: string; hint?: string }>()
defineOptions({ inheritAttrs: false })
const model = defineModel<string>({ default: '' })
</script>

<template>
  <label class="grid gap-1.5 text-sm font-medium text-neutral-700">
    <span v-if="label">{{ label }}</span>
    <input v-model="model" v-bind="$attrs" :class="['h-9 w-full rounded border bg-white px-2.5 text-sm font-normal outline-none transition placeholder:text-neutral-400 focus:border-green-700 focus:ring-2 focus:ring-green-700/10', error ? 'border-rose-400' : 'border-neutral-300']" />
    <span v-if="error" class="text-xs font-medium text-rose-500">{{ error }}</span>
    <span v-else-if="hint" class="text-xs font-normal text-slate-500">{{ hint }}</span>
  </label>
</template>