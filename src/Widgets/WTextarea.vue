<script setup lang="ts">
defineProps<{ label?: string; error?: string; hint?: string; rows?: number }>()
defineOptions({ inheritAttrs: false })
const model = defineModel<string>({ default: '' })
</script>

<template>
  <label class="grid gap-1.5 text-sm font-medium text-neutral-700">
    <span v-if="label">{{ label }}</span>
    <textarea v-model="model" v-bind="$attrs" :rows="rows ?? 4"
      :class="['w-full resize-y rounded border bg-white px-2.5 py-2 text-sm font-normal outline-none transition placeholder:text-neutral-400 focus:border-green-700 focus:ring-2 focus:ring-green-700/10', error ? 'border-rose-400' : 'border-neutral-300']" />
    <span v-if="error" class="text-xs font-medium text-rose-500">{{ error }}</span>
    <span v-else-if="hint" class="text-xs font-normal text-slate-500">{{ hint }}</span>
  </label>
</template>