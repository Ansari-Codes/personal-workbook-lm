<script setup lang="ts">
import { computed, ref } from 'vue';
import type { ChatMessage } from '@/stores/useWorkbooks';

const props = defineProps<{
  messages: ChatMessage[];
}>();

const isExpanded = ref(false);

const totalChars = computed(() => 
  props.messages.reduce((sum, m) => sum + m.content.length, 0)
);

const previewText = computed(() => {
  const firstMsg = props.messages[0];
  if (!firstMsg) return '';
  const text = firstMsg.content;
  return text.length > 80 ? text.slice(0, 80) + '…' : text;
});

const stepCount = computed(() => props.messages.length);
</script>

<template>
  <div class="ml-2 my-1 border-l-2 border-violet-200">
    <!-- Compact Header -->
    <button
      class="group flex w-full items-center gap-2 py-1.5 pl-3 pr-2 text-left transition hover:bg-violet-50/50"
      @click="isExpanded = !isExpanded"
    >
      <!-- Timeline dot -->
      <div class="size-2 shrink-0 rounded-full bg-violet-400" />
      
      <!-- Label -->
      <span class="shrink-0 text-xs font-medium text-violet-600">
        💭 Thinking
      </span>
      
      <!-- Preview (hidden when expanded) -->
      <span 
        v-if="!isExpanded"
        class="min-w-0 flex-1 truncate text-xs text-neutral-400 italic"
      >
        {{ previewText }}
      </span>
      
      <!-- Spacer when expanded -->
      <span v-else class="flex-1" />
      
      <!-- Step count -->
      <span class="shrink-0 rounded-full bg-violet-100 px-1.5 py-0.5 text-[10px] font-medium text-violet-600">
        {{ stepCount }} step{{ stepCount !== 1 ? 's' : '' }}
      </span>
      
      <!-- Chevron -->
      <svg 
        class="size-3.5 shrink-0 text-violet-400 transition-transform duration-200"
        :class="{ 'rotate-180': isExpanded }"
        fill="none" 
        viewBox="0 0 24 24" 
        stroke="currentColor"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    <!-- Expandable Content -->
    <div 
      v-show="isExpanded"
      class="space-y-1.5 overflow-hidden pl-6 pr-2 pb-2"
    >
      <div
        v-for="(msg, idx) in messages"
        :key="msg.id"
        class="relative rounded border-l-2 border-violet-200 bg-violet-50/30 py-1.5 pl-3 pr-2 text-xs"
      >
        <!-- Step number -->
        <div class="mb-0.5 text-[10px] font-semibold text-violet-400 uppercase tracking-wide">
          Step {{ idx + 1 }}
        </div>
        <div class="text-neutral-600 italic leading-relaxed">
          {{ msg.content }}
        </div>
      </div>
    </div>
  </div>
</template>