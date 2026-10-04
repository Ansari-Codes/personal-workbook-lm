import { defineStore } from 'pinia';
import { ref } from 'vue';
import { apiRequest } from '@/stores/api';

export interface WorkbookOutput {
  id: number;
  name: string;
  description: string;
  folder: string;
  size: number;
  media_type: string;
  created_at: string;
  updated_at: string;
}

export interface WorkbookOutputContent extends WorkbookOutput {
  content: string | null;
  content_base64: string | null;
  encoding: 'utf-8' | 'base64';
}

export interface WorkbookOutputUpdate {
  name?: string;
  description?: string;
  content?: string;
  folder?: string;
}

export interface WorkbookOutputCreate {
  name: string;
  description?: string;
  content?: string;
  folder?: string;
}

export const useOutputs = defineStore('outputs', () => {
  const outputs = ref<WorkbookOutput[]>([]);

  function endpoint(profileId: number, workbookId: number): string {
    return `/profiles/${profileId}/workbooks/${workbookId}/outputs`;
  }

  async function fetchOutputs(profileId: number, workbookId: number): Promise<void> {
    outputs.value = await apiRequest<WorkbookOutput[]>(endpoint(profileId, workbookId)) ?? [];
  }

  async function createOutput(
    profileId: number,
    workbookId: number,
    payload: WorkbookOutputCreate,
  ): Promise<WorkbookOutput> {
    const output = await apiRequest<WorkbookOutput>(endpoint(profileId, workbookId), 'POST', payload);
    if (!output) throw new Error('API did not return the created output.');
    outputs.value.unshift(output);
    return output;
  }

  async function readOutput(
    profileId: number,
    workbookId: number,
    outputId: number,
  ): Promise<WorkbookOutputContent> {
    const output = await apiRequest<WorkbookOutputContent>(`${endpoint(profileId, workbookId)}/${outputId}/content`);
    if (!output) throw new Error('API did not return output content.');
    return output;
  }

  async function updateOutput(
    profileId: number,
    workbookId: number,
    outputId: number,
    updates: WorkbookOutputUpdate,
  ): Promise<void> {
    const output = await apiRequest<WorkbookOutput>(`${endpoint(profileId, workbookId)}/${outputId}`, 'PATCH', updates);
    if (!output) throw new Error('API did not return the updated output.');
    const index = outputs.value.findIndex((item) => item.id === outputId);
    if (index !== -1) outputs.value[index] = output;
  }

  async function replaceOutputFile(
    profileId: number,
    workbookId: number,
    outputId: number,
    file: File,
  ): Promise<void> {
    const form = new FormData();
    form.set('file', file);
    const output = await apiRequest<WorkbookOutput, FormData>(
      `${endpoint(profileId, workbookId)}/${outputId}/file`,
      'PUT',
      form,
    );
    if (!output) throw new Error('API did not return the replaced output.');
    const index = outputs.value.findIndex((item) => item.id === outputId);
    if (index !== -1) outputs.value[index] = output;
  }

  async function deleteOutput(profileId: number, workbookId: number, outputId: number): Promise<void> {
    await apiRequest<null>(`${endpoint(profileId, workbookId)}/${outputId}`, 'DELETE');
    outputs.value = outputs.value.filter((output) => output.id !== outputId);
  }

  return { outputs, fetchOutputs, createOutput, readOutput, updateOutput, replaceOutputFile, deleteOutput };
});