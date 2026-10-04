<script setup lang="ts">
import type { NotificationItem } from './useNotifier'
import WButton from './WButton.vue'
import WIcon from './WIcon.vue'
defineProps<{ item: NotificationItem }>()
const emit = defineEmits<{ dismiss: [] }>()
</script>

<template><div :class="['flex items-start gap-3 rounded border px-3 py-2 text-sm shadow-md', item.kind === 'success' ? 'border-green-200 bg-green-50 text-green-900' : item.kind === 'error' ? 'border-rose-200 bg-rose-50 text-rose-900' : item.kind === 'warning' ? 'border-amber-200 bg-amber-50 text-amber-900' : 'border-neutral-200 bg-white text-neutral-900']"><span class="flex-1">{{ item.message }}</span><WButton variant="ghost" size="sm" aria-label="Dismiss notification" @click="emit('dismiss')"><WIcon name="close" /></WButton></div></template>