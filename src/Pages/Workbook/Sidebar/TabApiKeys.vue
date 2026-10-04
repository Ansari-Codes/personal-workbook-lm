<script setup lang="ts">
import { computed, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { useAPIKeys } from '@/stores/useAPIKeys';
import { useWorkbookSettings } from '@/stores/useWorkbookSettings';
import { useNotifier } from '@/Widgets';
import WIcon from '@/Widgets/WIcon.vue';
import WInput from '@/Widgets/WInput.vue';
import WCheck from '@/Widgets/WCheck.vue';
import { ApiError } from '@/stores/api';

const props = defineProps<{ profileId: number; profileName: string; workbookId: number; isLoading: boolean }>();
const apiKeys = useAPIKeys();
const settings = useWorkbookSettings();
const { notify } = useNotifier();
const query = ref('');
const isSaving = ref(false);
const filteredApiKeys = computed(() => {
  const value = query.value.trim().toLocaleLowerCase();
  return apiKeys.apiKeys.filter((item) => !value || `${item.name} ${item.base_url} ${Object.keys(item.endpoints).join(' ')}`.toLocaleLowerCase().includes(value));
});

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.status === null ? error.message : `${error.message} (HTTP ${error.status})`;
  if (error instanceof Error) return error.message;
  return String(error);
}

async function updateSelection(id: number, checked: boolean): Promise<void> {
  const previous = [...settings.selectedApiKeyIds];
  settings.selectedApiKeyIds = checked
    ? [...new Set([...previous, id])]
    : previous.filter((item) => item !== id);
  isSaving.value = true;
  try {
    await settings.saveSettings(props.profileId, props.workbookId);
  } catch (error) {
    settings.selectedApiKeyIds = previous;
    notify(`Could not save API key selection: ${errorMessage(error)}`, 'error', 8000);
  } finally {
    isSaving.value = false;
  }
}
</script>

<template>
  <section class="tab-content" aria-label="API keys enabled for this workbook">
    <div v-if="isLoading" class="status-text" role="status">Loading API keys…</div>
    <template v-else>
      <WInput v-model="query" type="search" class="workspace-search" aria-label="Search API keys" placeholder="Search API keys" />
      <p v-if="apiKeys.apiKeys.length === 0" class="empty-state">
        No API keys available.
        <RouterLink :to="{ name: 'profile-apis', params: { name: profileName } }">Manage API keys</RouterLink>
      </p>
      <ul v-else class="workspace-check-list">
        <li v-for="apiKey in filteredApiKeys" :key="apiKey.id">
          <div class="key-row">
            <WCheck :model-value="settings.selectedApiKeyIds.includes(apiKey.id)" :disabled="isSaving" @update:model-value="updateSelection(apiKey.id, $event)" />
            <span><strong>{{ apiKey.name }}</strong><small>{{ apiKey.base_url }}</small></span>
          </div>
        </li>
      </ul>
      <RouterLink class="workspace-manage-link" :to="{ name: 'profile-apis', params: { name: profileName } }">Manage profile API keys <WIcon name="arrow_outward" :size="16" /></RouterLink>
    </template>
  </section>
</template>

<style scoped>
.tab-content { height: 100%; min-height: 0; overflow-y: auto; padding: 12px; }
.workspace-search { height: 36px; border-color: #dce3e1; padding-inline: 10px; font-size: 13px; }
.workspace-check-list { display: grid; margin-top: 12px; }
.workspace-check-list li { border-bottom: 1px solid #edf0ef; padding: 10px 2px; }
.key-row { display: flex; align-items: flex-start; gap: 10px; }
.key-row > span { display: grid; min-width: 0; gap: 3px; }
.workspace-check-list input { margin-top: 3px; accent-color: #15803d; }
.workspace-check-list span { display: grid; min-width: 0; gap: 3px; }
.workspace-check-list strong { font-size: 12px; }
.workspace-check-list small { overflow-wrap: anywhere; color: #687573; font-size: 11px; }
.workspace-manage-link { display: inline-flex; align-items: center; gap: 5px; margin-top: 16px; color: #166534; font-size: 12px; font-weight: 650; text-decoration: none; }
.empty-state, .status-text { padding: 16px 4px; color: #6b7775; font-size: 13px; line-height: 1.6; }
.empty-state a { color: #166534; font-weight: 650; text-decoration: underline; }
</style>