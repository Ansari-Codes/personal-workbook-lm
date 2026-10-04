<script setup lang="ts">
import { computed, ref } from 'vue';
import type { APIKey } from '@/stores/useAPIKeys';
import type { Caller } from '@/stores/useCallers';
import type { ChatConfiguration, ChatSendPayload } from '@/stores/useWorkbooks';
import WSelect from '@/Widgets/WSelect.vue';
import WOption from '@/Widgets/WOption.vue';
import WIcon from '@/Widgets/WIcon.vue';
import WMenu from '@/Widgets/WMenu.vue';
import WInput from '@/Widgets/WInput.vue';
import WTextarea from '@/Widgets/WTextarea.vue';
import WButton from '@/Widgets/WButton.vue';

const props = defineProps<{
  apiKeys: APIKey[];
  callers: Caller[];
  allowedApiKeyIds: number[];
  models: string[];
  isGenerating: boolean;
  disabled?: boolean;
}>();

const configuration = defineModel<ChatConfiguration>('configuration', { required: true });
const emit = defineEmits<{
  send: [payload: ChatSendPayload];
  stop: [];
}>();

const prompt = ref('');
const additionalParametersError = ref('');
const availableApiKeys = computed(() => props.apiKeys.filter((key) => props.allowedApiKeyIds.includes(key.id)));
const selectedApiKey = computed(() => availableApiKeys.value.find((key) => key.id === configuration.value.apiKeyId));
const apiKeySelection = computed<string | number>({
  get: () => configuration.value.apiKeyId ?? '',
  set: (value) => {
    const apiKeyId = value === '' ? null : Number(value);
    configuration.value.apiKeyId = apiKeyId;
    const selected = props.apiKeys.find((key) => key.id === apiKeyId);
    const names = Object.keys(selected?.endpoints ?? {});
    configuration.value.endpointName = names.includes('chat') ? 'chat' : names[0] ?? '';
  },
});
const endpointSelection = computed<string>({
  get: () => configuration.value.endpointName,
  set: (value) => { configuration.value.endpointName = value; },
});
const callerSelection = computed<string | number>({
  get: () => configuration.value.callerId ?? '',
  set: (value) => {
    configuration.value.callerId = value === '' ? null : Number(value);
  },
});
const modelSelection = computed<string | number>({
  get: () => configuration.value.model,
  set: (value) => { configuration.value.model = String(value); },
});

function submit(): void {
  if (props.isGenerating) {
    emit('stop');
    return;
  }
  if (props.disabled) return;
  if (configuration.value.callerId === null || configuration.value.apiKeyId === null || !configuration.value.endpointName) return;
  const cleanPrompt = prompt.value.trim();
  if (!cleanPrompt) return;
  try {
    const value: unknown = JSON.parse(configuration.value.additionalParameters || '{}');
    if (value === null || Array.isArray(value) || typeof value !== 'object') throw new Error();
  } catch {
    additionalParametersError.value = 'Additional parameters must be a JSON object.';
    return;
  }
  additionalParametersError.value = '';
  emit('send', {
    prompt: cleanPrompt,
    ...configuration.value,
  });
  prompt.value = '';
}

function onPromptKeydown(event: KeyboardEvent): void {
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
    event.preventDefault();
    submit();
  }
}
</script>

<template>
  <div class="relative border-t border-neutral-200 bg-white p-3 sm:p-4">
    <div class="mb-2 flex items-center justify-between gap-3">
      <WMenu placement="top-end" :close-on-select="false" :disabled="disabled" trigger-label="API key, endpoint, caller, model, and parameters">
        <template #trigger><WIcon name="tune" :size="17" /><span>Model &amp; API</span></template>
        <section class="chat-config-menu">
          <WSelect v-model="apiKeySelection" label="API key" :disabled="disabled">
            <WOption value="">No API key selected</WOption>
            <WOption v-for="apiKey in availableApiKeys" :key="apiKey.id" :value="apiKey.id">{{ apiKey.name }}</WOption>
          </WSelect>
          <WSelect v-model="endpointSelection" label="Endpoint" :disabled="disabled || !selectedApiKey">
            <WOption value="">Select an endpoint</WOption>
            <WOption v-for="(path, name) in selectedApiKey?.endpoints ?? {}" :key="name" :value="name">{{ name }} · {{ path }}</WOption>
          </WSelect>
          <WSelect v-model="callerSelection" label="Caller" :disabled="disabled">
            <WOption value="">Select a caller</WOption>
            <WOption v-for="caller in callers" :key="caller.id" :value="caller.id">{{ caller.name }}</WOption>
          </WSelect>
          <WSelect :accept-custom="true" v-model="modelSelection" label="Model" :disabled="disabled || models.length === 0">
            <WOption v-for="model in models" :key="model" :value="model">{{ model }}</WOption>
          </WSelect>
          <WTextarea v-model="configuration.additionalParameters" label="Additional parameters (JSON)" :rows="5" :disabled="disabled" spellcheck="false" />
          <p v-if="additionalParametersError" role="alert" class="text-xs text-rose-700">{{ additionalParametersError }}</p>
        </section>
      </WMenu>
      <span class="truncate text-[11px] text-neutral-500">{{ configuration.model }}</span>
    </div>

    <WTextarea
      v-model="prompt"
      class="prompt-input"
      :rows="3"
      aria-label="Message prompt"
      placeholder="Write a message…"
      :disabled="disabled"
      @keydown="onPromptKeydown"
    />

    <div class="mt-2 flex items-center justify-between gap-3">
      <div class="flex items-center gap-2 text-xs text-neutral-500">
        <span class="inline-flex items-center gap-1.5"><WIcon name="history" :size="15" />{{ configuration.contextLength }} history messages</span>
      </div>
      <WButton
        :variant="isGenerating ? 'danger' : 'primary'"
        size="sm"
        :disabled="isGenerating ? false : disabled || callerSelection === '' || apiKeySelection === '' || !endpointSelection || !prompt.trim()"
        @click="submit"
      >
        <WIcon :name="isGenerating ? 'stop' : 'arrow_upward'" :size="17" />
        {{ isGenerating ? 'Stop' : 'Send' }}
      </WButton>
    </div>
    <p class="mt-2 text-[11px] text-neutral-400">Ctrl/⌘ + Enter to send</p>
  </div>
</template>

<style scoped>
.chat-config-menu { display: grid; width: min(320px, calc(100vw - 24px)); gap: 14px; padding: 14px; }
.prompt-input :deep(textarea) { min-height: 76px; max-height: 192px; border-radius: 4px; border-color: #d4d9d7; }
</style>
