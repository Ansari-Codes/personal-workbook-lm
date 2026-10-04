<script setup lang="ts">
withDefaults(defineProps<{
  name: string;
  size?: number;
  filled?: boolean;
}>(), {
  size: 20,
  filled: false,
});
</script>

<template>
  <span
    class="material-symbols-outlined inline-flex shrink-0 select-none items-center justify-center leading-none"
    :class="{ 'material-symbols-filled': filled }"
    :style="{ fontSize: `${size}px`, width: `${size}px`, height: `${size}px` }"
    aria-hidden="true"
  >{{ name }}</span>
</template>

<style scoped>
.material-symbols-outlined {
  font-family: 'Material Symbols Outlined';
  font-weight: normal;
  font-style: normal;
  font-feature-settings: 'liga';
  -webkit-font-feature-settings: 'liga';
  -webkit-font-smoothing: antialiased;
}

.material-symbols-filled {
  font-variation-settings: 'FILL' 1;
}
</style>