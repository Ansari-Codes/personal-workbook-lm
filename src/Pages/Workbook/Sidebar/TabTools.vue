<script setup lang="ts">
import { computed, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { useTools } from '@/stores/useTools';
import { useWorkbookSettings } from '@/stores/useWorkbookSettings';
import { useNotifier } from '@/Widgets';
import WIcon from '@/Widgets/WIcon.vue';
import WInput from '@/Widgets/WInput.vue';
import WCheck from '@/Widgets/WCheck.vue';
import type { ApiError } from '@/stores/api';

const props = defineProps<{ profileId: number; profileName: string; workbookId: number; isLoading: boolean }>();
const tools = useTools();
const settings = useWorkbookSettings();
const { notify } = useNotifier();
const query = ref('');
const isSaving = ref(false);
const filteredTools = computed(() => {
  const value = query.value.trim().toLocaleLowerCase();
  return tools.tools.filter((item) => !value || `${item.title} ${item.description}`.toLocaleLowerCase().includes(value));
});

function errorMessage(error: unknown): string {
  if (error instanceof Error) {
    const apiError = error as ApiError;
    return apiError.status === null || apiError.status === undefined ? error.message : `${error.message} (HTTP ${apiError.status})`;
  }
  return String(error);
}

async function updateSelection(id: number, checked: boolean): Promise<void> {
  const previous = [...settings.selectedToolIds];
  settings.selectedToolIds = checked ? [...new Set([...previous, id])] : previous.filter((item) => item !== id);
  isSaving.value = true;
  try {
    await settings.saveSettings(props.profileId, props.workbookId);
  } catch (error) {
    settings.selectedToolIds = previous;
    notify(`Could not save tool selection: ${errorMessage(error)}`, 'error', 8000);
  } finally {
    isSaving.value = false;
  }
}
</script>

<template>
  <section class="tab-content" aria-label="Tools enabled for this workbook">
    <div v-if="isLoading" class="status-text" role="status">Loading tools…</div>
    <template v-else>
      <WInput v-model="query" type="search" class="workspace-search" aria-label="Search tools" placeholder="Search tools" />
      <p v-if="tools.tools.length === 0" class="empty-state">
        No tools available.
        <RouterLink :to="{ name: 'profile-tools', params: { name: profileName } }">Manage tools</RouterLink>
      </p>
      <ul v-else class="workspace-check-list">
        <li v-for="tool in filteredTools" :key="tool.id">
          <div class="tool-row">
            <WCheck :model-value="settings.selectedToolIds.includes(tool.id)" :disabled="isSaving" @update:model-value="updateSelection(tool.id, $event)" />
            <span><strong>{{ tool.title }}</strong><small>{{ tool.description }}</small></span>
          </div>
        </li>
      </ul>
      <RouterLink class="workspace-manage-link" :to="{ name: 'profile-tools', params: { name: profileName } }">Manage profile tools <WIcon name="arrow_outward" :size="16" /></RouterLink>
    </template>
  </section>
</template>

<style scoped>
.tab-content { height: 100%; min-height: 0; overflow-y: auto; padding: 12px; }
.workspace-search { height: 36px; border-color: #dce3e1; padding-inline: 10px; font-size: 13px; }
.workspace-check-list { display: grid; margin-top: 12px; }
.workspace-check-list li { border-bottom: 1px solid #edf0ef; padding: 10px 2px; }
.tool-row { display: flex; align-items: flex-start; gap: 10px; }
.tool-row > span { display: grid; min-width: 0; gap: 3px; }
.workspace-check-list input { margin-top: 3px; accent-color: #15803d; }
.workspace-check-list span { display: grid; min-width: 0; gap: 3px; }
.workspace-check-list strong { font-size: 12px; }
.workspace-check-list small { overflow-wrap: anywhere; color: #687573; font-size: 11px; line-height: 1.45; }
.workspace-manage-link { display: inline-flex; align-items: center; gap: 5px; margin-top: 16px; color: #166534; font-size: 12px; font-weight: 650; text-decoration: none; }
.empty-state, .status-text { padding: 16px 4px; color: #6b7775; font-size: 13px; line-height: 1.6; }
.empty-state a { color: #166534; font-weight: 650; text-decoration: underline; }
</style>