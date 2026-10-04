<script setup lang="ts">
import { useId } from 'vue';
import WButton from './WButton.vue';

const props = withDefaults(
  defineProps<{
    title?: string;
    disabled?: boolean;
  }>(),
  {
    title: '',
    disabled: false,
  }
);

const isOpen = defineModel<boolean>({ default: false });
const emit = defineEmits<{ toggle: [open: boolean] }>();
const panelId = `w-collapsible-${useId()}`;

function toggle(): void {
  if (props.disabled) return;
  isOpen.value = !isOpen.value;
  emit('toggle', isOpen.value);
}
</script>

<template>
  <section class="overflow-hidden rounded border border-neutral-200 bg-white">
    <WButton
      type="button"
      variant="ghost"
      class="flex min-h-12 w-full justify-between rounded-none border-0 px-4 py-3 text-left text-sm font-semibold text-neutral-900 focus-visible:ring-inset"
      :disabled="disabled"
      :aria-expanded="isOpen"
      :aria-controls="panelId"
      @click="toggle"
    >
      <slot name="header">
        <span>{{ title }}</span>
      </slot>
      <span
        aria-hidden="true"
        class="size-2 shrink-0 border-b-2 border-r-2 border-current transition-transform duration-200"
        :class="isOpen ? 'rotate-[-135deg] translate-y-0.5' : 'rotate-45 -translate-y-0.5'"
      />
    </WButton>

    <!-- FIX: use max-height instead of grid-rows for reliable animation -->
    <div
      :id="panelId"
      class="transition-[max-height,opacity] duration-200 ease-out"
      :class="isOpen ? 'max-h-250 opacity-100' : 'max-h-0 opacity-0'"
      :style="{ overflow: 'hidden' }"
    >
      <div class="border-t border-neutral-200 px-4 py-4 text-sm text-neutral-700">
        <slot />
      </div>
    </div>
  </section>
</template>