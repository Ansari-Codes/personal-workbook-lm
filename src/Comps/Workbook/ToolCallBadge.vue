<script setup lang="ts">
import { computed, ref } from 'vue';
import type { ChatMessage } from '@/stores/useWorkbooks';
import WButton from '@/Widgets/WButton.vue';
import WIcon from '@/Widgets/WIcon.vue';

const props = defineProps<{
    messages: ChatMessage[];
}>();

const expanded = ref(false);

const toolCalls = computed(() =>
    props.messages.filter(m => m.role === 'tool_call')
);

const toolOutputs = computed(() =>
    props.messages.filter(m => m.role === 'tool_output')
);

const getToolName = (content: string) => {
    try {
        const parsed = JSON.parse(content);
        return parsed.name || 'Tool';
    } catch {
        return content.split('"')[1] || 'Tool';
    }
};
</script>

<template>
    <div class="flex flex-wrap items-center gap-2 py-1">
        <WButton v-for="call in toolCalls" :key="call.id" size="sm" variant="secondary"
            class="gap-1.5 border-green-200 bg-green-50 text-green-800 hover:bg-green-100"
            :aria-expanded="expanded" @click="expanded = !expanded">
            <WIcon name="settings_suggest" :size="15" />
            {{ getToolName(call.content) }}
        </WButton>

        <!-- Expanded details -->
        <div v-if="expanded" class="w-full mt-2 rounded-lg border border-neutral-200 bg-neutral-50 p-3 space-y-2">
            <div v-for="msg in messages" :key="msg.id" class="text-xs">
                <div class="font-semibold text-neutral-500 mb-1">
                    {{ msg.role === 'tool_call' ? 'Call' : 'Result' }}
                </div>
                <pre
                    class="overflow-x-auto rounded bg-white p-2 text-neutral-700 border border-neutral-200">{{ msg.content }}</pre>
            </div>
        </div>
    </div>
</template>