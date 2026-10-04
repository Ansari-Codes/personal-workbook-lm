import { defineStore } from 'pinia';
import { ref } from 'vue';
import { apiRequest } from '@/stores/api';

interface WorkbookConfig {
  selected_caller_id?: number | null;
  selected_api_key_ids?: number[];
  selected_tool_ids?: number[];
  use_tools?: boolean;
  source_folders?: string[];
  output_folders?: string[];
}

export const useWorkbookSettings = defineStore('workbookSettings', () => {
  const selectedCallerId = ref<number | null>(null);
  const selectedApiKeyIds = ref<number[]>([]);
  const selectedToolIds = ref<number[]>([]);
  const useTools = ref(true);
  const sourceFolders = ref<string[]>([]);
  const outputFolders = ref<string[]>([]);

  function normalizeSourceFolders(folders: string[] | undefined): string[] {
    return [...new Set((folders ?? []).map((folder) => folder.replace(/^(Local|Links)(\/|$)/, '')).filter(Boolean))];
  }

  function endpoint(profileId: number, workbookId: number): string {
    return `/profiles/${profileId}/workbooks/${workbookId}/config`;
  }

  async function fetchSettings(profileId: number, workbookId: number): Promise<void> {
    const config = await apiRequest<WorkbookConfig>(endpoint(profileId, workbookId));
    selectedCallerId.value = config?.selected_caller_id ?? null;
    selectedApiKeyIds.value = config?.selected_api_key_ids ?? [];
    selectedToolIds.value = config?.selected_tool_ids ?? [];
    useTools.value = config?.use_tools ?? true;
    sourceFolders.value = normalizeSourceFolders(config?.source_folders);
    outputFolders.value = config?.output_folders ?? [];
  }

  async function saveSettings(profileId: number, workbookId: number): Promise<void> {
    const config = await apiRequest<WorkbookConfig>(endpoint(profileId, workbookId), 'PATCH', {
      selected_caller_id: selectedCallerId.value,
      selected_api_key_ids: selectedApiKeyIds.value,
      selected_tool_ids: selectedToolIds.value,
      use_tools: useTools.value,
      source_folders: normalizeSourceFolders(sourceFolders.value),
      output_folders: outputFolders.value,
    });
    if (config) {
      selectedCallerId.value = config.selected_caller_id ?? null;
      selectedApiKeyIds.value = config.selected_api_key_ids ?? [];
      selectedToolIds.value = config.selected_tool_ids ?? [];
      useTools.value = config.use_tools ?? true;
      sourceFolders.value = normalizeSourceFolders(config.source_folders);
      outputFolders.value = config.output_folders ?? [];
    }
  }

  function clear(): void {
    selectedCallerId.value = null;
    selectedApiKeyIds.value = [];
    selectedToolIds.value = [];
    useTools.value = true;
    sourceFolders.value = [];
    outputFolders.value = [];
  }

  return { selectedCallerId, selectedApiKeyIds, selectedToolIds, useTools, sourceFolders, outputFolders, fetchSettings, saveSettings, clear };
});
