<script setup lang="ts">
import { ref, watch } from 'vue';
import type { APIKey, APIKeyCreate } from '@/stores/useAPIKeys';
import WButton from '@/Widgets/WButton.vue';
import WDialog from '@/Widgets/WDialog.vue';
import WInput from '@/Widgets/WInput.vue';
import WTextarea from '@/Widgets/WTextarea.vue';

export type APIKeyFormData = Omit<APIKeyCreate, 'secret'> & { secret?: string };

const props = withDefaults(defineProps<{
  apiKey?: APIKey | null;
  loading?: boolean;
}>(), {
  apiKey: null,
  loading: false,
});

const isOpen = defineModel<boolean>({ default: false });
const emit = defineEmits<{ submit: [payload: APIKeyFormData] }>();

const name = ref('');
const description = ref('');
const baseUrl = ref('');
const endpointRows = ref<Array<{ name: string; path: string }>>([]);
const secret = ref('');
const metaJson = ref('{}');
const validationError = ref('');

watch([isOpen, () => props.apiKey], ([open, apiKey]) => {
  if (open) {
    name.value = apiKey?.name ?? '';
    description.value = apiKey?.description ?? '';
    baseUrl.value = apiKey?.base_url ?? '';
    endpointRows.value = Object.entries(apiKey?.endpoints ?? {}).map(([name, path]) => ({ name, path }));
    secret.value = '';
    metaJson.value = JSON.stringify(apiKey?.meta ?? {}, null, 2);
    validationError.value = '';
  } else {
    name.value = '';
    description.value = '';
    baseUrl.value = '';
    endpointRows.value = [];
    secret.value = '';
    metaJson.value = '{}';
    validationError.value = '';
  }
});

function submit(): void {
  const cleanName = name.value.trim();
  const cleanBaseUrl = baseUrl.value.trim();
  const endpoints: Record<string, string> = {};
  for (const endpoint of endpointRows.value) {
    const endpointName = endpoint.name.trim();
    const endpointPath = endpoint.path.trim();
    if (!endpointName || !endpointPath || endpoints[endpointName]) {
      validationError.value = 'Each endpoint needs a unique name and path.';
      return;
    }
    endpoints[endpointName] = endpointPath;
  }
  if (!cleanName || !cleanBaseUrl || Object.keys(endpoints).length === 0) {
    validationError.value = 'Name, base URL, and at least one endpoint are required.';
    return;
  }
  if (!props.apiKey && !secret.value.trim()) {
    validationError.value = 'An API key is required.';
    return;
  }
  let meta: Record<string, unknown>;
  try {
    const parsed: unknown = JSON.parse(metaJson.value);
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      throw new Error('Metadata must be a JSON object.');
    }
    meta = parsed as Record<string, unknown>;
  } catch {
    validationError.value = 'Metadata must be a valid JSON object.';
    return;
  }
  validationError.value = '';
  const payload: APIKeyFormData = {
    name: cleanName,
    description: description.value.trim(),
    base_url: cleanBaseUrl,
    endpoints,
    meta,
  };
  const cleanSecret = secret.value.trim();
  if (cleanSecret) payload.secret = cleanSecret;
  emit('submit', payload);
}

function addEndpoint(): void {
  endpointRows.value.push({ name: '', path: '' });
}

function removeEndpoint(index: number): void {
  endpointRows.value.splice(index, 1);
}
</script>

<template>
  <WDialog
    v-model="isOpen"
    :title="apiKey ? 'Edit API key' : 'Add API key'"
    description="Credentials are stored locally and never shown in the keys table."
  >
    <div class="grid gap-4">
      <WInput v-model="name" label="Name" autocomplete="off" maxlength="120" required />
      <WTextarea v-model="description" label="Description" />
      <WInput
        v-model="baseUrl"
        label="Base URL"
        type="url"
        placeholder="https://api.example.com"
        autocomplete="url"
        required
      />
      <fieldset class="grid gap-3">
        <legend class="text-sm font-medium text-neutral-800">Endpoints</legend>
        <div v-for="(endpoint, index) in endpointRows" :key="index" class="grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)_auto]">
          <WInput v-model="endpoint.name" label="Name" placeholder="chat" maxlength="120" class="min-w-0" />
          <WInput v-model="endpoint.path" label="Path" placeholder="/v1/chat/completions" class="min-w-0" />
          <WButton type="button" variant="ghost" aria-label="Remove endpoint" class="justify-self-end sm:justify-self-auto" @click="removeEndpoint(index)">Remove</WButton>
        </div>
        <div>
          <WButton type="button" variant="secondary" @click="addEndpoint">Add endpoint</WButton>
        </div>
      </fieldset>
      <WInput
        v-model="secret"
        label="Secret / API key"
        type="password"
        :placeholder="apiKey ? 'Leave blank to keep the current key' : 'Enter the secret key'"
        autocomplete="new-password"
        :required="!apiKey"
      />
      <WTextarea
        v-model="metaJson"
        label="Metadata (JSON object)"
        :rows="7"
        spellcheck="false"
        class="font-mono"
      />
      <p v-if="validationError" role="alert" class="text-sm text-rose-700">{{ validationError }}</p>
    </div>
    <template #footer>
      <WButton variant="secondary" :disabled="loading" @click="isOpen = false">Cancel</WButton>
      <WButton :loading="loading" @click="submit">
        {{ apiKey ? 'Save changes' : 'Add API key' }}
      </WButton>
    </template>
  </WDialog>
</template>
