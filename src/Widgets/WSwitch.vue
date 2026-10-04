<script setup lang="ts">
withDefaults(defineProps<{ label?: string; disabled?: boolean }>(), { disabled: false })
const model = defineModel<boolean>({ default: false })
</script>

<template>
  <button type="button" role="switch" :aria-checked="model" :disabled="disabled" class="inline-flex items-center gap-3 text-sm font-medium text-slate-700 dark:text-slate-200 disabled:opacity-50" @click="model = !model">
    <span :class="['flex h-6 w-11 rounded-full p-1 transition', model ? 'bg-green-700' : 'bg-neutral-300']"><span :class="['size-4 rounded-full bg-white shadow-sm transition', model && 'translate-x-5']" /></span>
    <slot>{{ label }}</slot>
  </button>
</template>