<script setup lang="ts">
withDefaults(defineProps<{
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  type?: 'button' | 'submit' | 'reset'
  loading?: boolean
  disabled?: boolean
}>(), { variant: 'primary', size: 'md', type: 'button', loading: false, disabled: false })
</script>

<template>
  <button :type="type" :disabled="loading || disabled" :class="[
    'inline-flex items-center justify-center gap-2 rounded border font-medium transition focus:outline-none focus:ring-2 focus:ring-green-700/25 disabled:cursor-not-allowed disabled:opacity-50',
    { 'border-green-700 bg-green-700 px-3 text-white hover:bg-green-800': variant === 'primary', 'border-neutral-300 bg-white px-3 text-neutral-950 hover:bg-neutral-50': variant === 'secondary', 'border-transparent px-2 text-neutral-700 hover:bg-neutral-100': variant === 'ghost', 'border-rose-700 bg-rose-700 px-3 text-white hover:bg-rose-800': variant === 'danger', 'h-8 text-xs': size === 'sm', 'h-9 text-sm': size === 'md', 'h-10 px-4 text-sm': size === 'lg' },
  ]">
    <span v-if="loading" class="size-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
    <slot />
  </button>
</template>