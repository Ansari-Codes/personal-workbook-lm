<script setup lang="ts">
withDefaults(defineProps<{ label?: string; disabled?: boolean }>(), { disabled: false })
const model = defineModel<boolean>({ default: false })
</script>

<template>
  <label class="inline-flex cursor-pointer items-start gap-2 text-sm font-medium text-neutral-700" :class="disabled && 'cursor-not-allowed opacity-50'">
    <input v-model="model" type="checkbox" :disabled="disabled" class="mt-0.5 size-4 shrink-0 accent-green-700" />
    <span><slot>{{ label }}</slot></span>
  </label>
</template>