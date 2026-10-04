<script setup lang="ts">
withDefaults(defineProps<{ top?: string }>(), { top: 'top-4' })
</script>

<template><div :class="['sticky z-20', top]"><slot /></div></template>