<script setup lang="ts">
defineProps<{ value: string | number; disabled?: boolean }>()
</script>

<template><option :value="value" :disabled="disabled"><slot /></option></template>