import { defineStore } from 'pinia';
import { ref } from 'vue';
import { apiRequest } from '@/stores/api';

export interface APIKey {
  id: number;
  name: string;
  description: string;
  base_url: string;
  endpoints: Record<string, string>;
  key_preview: string;
  meta: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface APIModelOption {
  id: string;
  name: string;
  properties: Record<string, unknown>;
}

export interface APIKeyCreate {
  name: string;
  description: string;
  secret: string;
  base_url: string;
  endpoints: Record<string, string>;
  meta?: Record<string, unknown>;
}

export type APIKeyUpdate = Partial<APIKeyCreate>;

export const useAPIKeys = defineStore('apiKeys', () => {
  const apiKeys = ref<APIKey[]>([]);
  const modelsBySelection = ref<Record<string, APIModelOption[]>>({});

  async function fetchAPIKeys(profileId: number): Promise<void> {
    apiKeys.value = await apiRequest<APIKey[]>(`/profiles/${profileId}/api-keys`) ?? [];
  }

  function modelSelectionKey(apiKeyId: number, callerId: number, endpointName: string): string {
    return `${apiKeyId}:${callerId}:${endpointName}`;
  }

  async function fetchModels(
    profileId: number,
    apiKeyId: number,
    callerId: number,
    endpointName: string,
  ): Promise<APIModelOption[]> {
    const models = await apiRequest<APIModelOption[]>(
      `/profiles/${profileId}/api-keys/${apiKeyId}/models?caller_id=${callerId}&endpoint_name=${encodeURIComponent(endpointName)}`,
    ) ?? [];
    modelsBySelection.value[modelSelectionKey(apiKeyId, callerId, endpointName)] = models;
    return models;
  }

  async function createAPIKey(profileId: number, payload: APIKeyCreate): Promise<APIKey> {
    const created = await apiRequest<APIKey>(`/profiles/${profileId}/api-keys`, 'POST', payload);
    if (!created) throw new Error('API did not return the created API key.');
    apiKeys.value.push(created);
    return created;
  }

  async function updateAPIKey(
    profileId: number,
    apiKeyId: number,
    payload: APIKeyUpdate,
  ): Promise<APIKey> {
    const updated = await apiRequest<APIKey>(
      `/profiles/${profileId}/api-keys/${apiKeyId}`,
      'PATCH',
      payload,
    );
    if (!updated) throw new Error('API did not return the updated API key.');
    const index = apiKeys.value.findIndex((item) => item.id === apiKeyId);
    if (index !== -1) apiKeys.value[index] = updated;
    return updated;
  }

  async function deleteAPIKey(profileId: number, apiKeyId: number): Promise<void> {
    await apiRequest<null>(`/profiles/${profileId}/api-keys/${apiKeyId}`, 'DELETE');
    apiKeys.value = apiKeys.value.filter((item) => item.id !== apiKeyId);
  }

  function clear(): void {
    apiKeys.value = [];
    modelsBySelection.value = {};
  }

  return {
    apiKeys,
    modelsBySelection,
    fetchAPIKeys,
    fetchModels,
    createAPIKey,
    updateAPIKey,
    deleteAPIKey,
    clear,
  };
});
