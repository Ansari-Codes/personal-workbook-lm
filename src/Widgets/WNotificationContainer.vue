<script setup lang="ts">
import WNotify from './WNotify.vue'
import { useNotifier } from './useNotifier'
const { notifications, dismiss } = useNotifier()
</script>

<template><div class="fixed right-4 top-4 z-[60] grid w-[min(22rem,calc(100vw-2rem))] gap-3"><TransitionGroup name="notify"><WNotify v-for="item in notifications" :key="item.id" :item="item" @dismiss="dismiss(item.id)" /></TransitionGroup></div></template>

<style scoped>
.notify-enter-active, .notify-leave-active { transition: opacity .2s, transform .2s; }
.notify-enter-from, .notify-leave-to { opacity: 0; transform: translateY(-.5rem); }
</style>