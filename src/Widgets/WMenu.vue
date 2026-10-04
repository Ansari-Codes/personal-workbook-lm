<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, type CSSProperties } from 'vue';
import WButton from './WButton.vue';

const props = withDefaults(defineProps<{
  closeOnSelect?: boolean;
  disabled?: boolean;
  placement?: 'top-end' | 'bottom-end' | 'bottom-start';
  triggerLabel?: string;
}>(), {
  closeOnSelect: true,
  disabled: false,
  placement: 'bottom-end',
  triggerLabel: 'Open menu',
});

const isOpen = ref(false);
const trigger = ref<HTMLElement | null>(null);
const panel = ref<HTMLElement | null>(null);
const position = ref<CSSProperties>({});

function positionPanel(): void {
  const anchor = trigger.value?.getBoundingClientRect();
  const menu = panel.value;
  if (!anchor || !menu) return;
  const menuRect = menu.getBoundingClientRect();
  let top = props.placement === 'top-end' ? anchor.top - menuRect.height - 4 : anchor.bottom + 4;
  if (top < 8 || top + menuRect.height > window.innerHeight - 8) {
    top = anchor.top - menuRect.height - 4;
    if (top < 8) top = Math.max(8, window.innerHeight - menuRect.height - 8);
  }
  let left = props.placement === 'bottom-start' ? anchor.left : anchor.right - menuRect.width;
  left = Math.max(8, Math.min(left, window.innerWidth - menuRect.width - 8));
  position.value = { position: 'fixed', zIndex: 999, top: `${top}px`, left: `${left}px`, maxWidth: 'calc(100vw - 16px)' };
}

async function open(): Promise<void> {
  isOpen.value = true;
  await nextTick();
  positionPanel();
}

function toggle(event: MouseEvent): void {
  trigger.value = event.currentTarget as HTMLElement;
  if (isOpen.value) isOpen.value = false;
  else void open();
}

function close(): void {
  isOpen.value = false;
}

function onOutsidePointer(event: PointerEvent): void {
  const target = event.target;
  if (!(target instanceof Node)) return;
  if (trigger.value?.contains(target) || panel.value?.contains(target)) return;
  close();
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape' && isOpen.value) close();
}

function onMenuClick(): void {
  if (props.closeOnSelect) close();
}

onMounted(() => {
  document.addEventListener('pointerdown', onOutsidePointer);
  document.addEventListener('keydown', onKeydown);
  window.addEventListener('resize', positionPanel);
  window.addEventListener('scroll', positionPanel, true);
});
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onOutsidePointer);
  document.removeEventListener('keydown', onKeydown);
  window.removeEventListener('resize', positionPanel);
  window.removeEventListener('scroll', positionPanel, true);
});
</script>

<template>
  <span class="inline-flex">
    <WButton
      size="sm"
      variant="ghost"
      :disabled="disabled"
      :aria-label="triggerLabel"
      aria-haspopup="menu"
      :aria-expanded="isOpen"
      @click="toggle"
    ><slot name="trigger" /></WButton>
  </span>
  <Teleport to="body">
    <div v-if="isOpen" ref="panel" class="w-menu-panel" :style="position" role="menu" @click="onMenuClick">
      <slot />
    </div>
  </Teleport>
</template>

<style scoped>
.w-menu-panel { display: grid; min-width: 160px; max-height: min(70vh, 480px); overflow: auto; border: 1px solid #d9dfdd; background: #fff; padding: 4px; box-shadow: 0 8px 24px #18232120; }
</style>