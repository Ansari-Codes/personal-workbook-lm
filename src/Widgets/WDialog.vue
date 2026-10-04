<script setup lang="ts">
import WButton from './WButton.vue';
import WIcon from './WIcon.vue';
defineProps<{ title?: string; description?: string }>()
const model = defineModel<boolean>({ default: false })
</script>

<template>
  <Teleport to="body">
    <div v-if="model" class="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-neutral-950/35 p-3 sm:p-4"
      @click.self="model = false">
      <section role="dialog" aria-modal="true" class="my-auto max-h-[calc(100dvh-1.5rem)] w-full min-w-0 max-w-lg overflow-y-auto rounded-md border border-neutral-200 bg-white p-4 shadow-lg sm:max-h-[calc(100dvh-2rem)] sm:p-5">
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0 break-words">
            <h2 class="text-base font-semibold text-neutral-950">{{ title }}</h2>
            <p v-if="description" class="mt-1 text-sm text-neutral-600">{{ description }}</p>
          </div>
          <WButton variant="ghost" size="sm" aria-label="Close dialog" @click="model = false"><WIcon name="close" /></WButton>
        </div>
        <div class="mt-5">
          <slot />
        </div>
        <div v-if="$slots.footer" class="mt-5 flex flex-wrap justify-end gap-2">
          <slot name="footer" />
        </div>
      </section>
    </div>
  </Teleport>
</template>