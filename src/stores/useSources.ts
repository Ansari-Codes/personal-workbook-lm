import { defineStore } from 'pinia';
import { ref } from 'vue';
import { apiRequest } from '@/stores/api';

export interface Source {
  id: number;
  name: string;
  description: string;
  folder: string;
  kind: 'link' | 'local';
  source_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface SourceCreate {
  name: string;
  description: string;
  folder?: string;
}

export interface SourcePreview {
  id: number;
  name: string;
  content: string;
  truncated: boolean;
}

export type SourceUpdate = Partial<SourceCreate>;

export const useSources = defineStore('sources', () => {
  const sources = ref<Source[]>([]);

  function endpoint(profileId: number, workbookId: number): string {
    return `/profiles/${profileId}/workbooks/${workbookId}/sources`;
  }

  async function fetchSources(profileId: number, workbookId: number): Promise<void> {
    sources.value = await apiRequest<Source[]>(endpoint(profileId, workbookId)) ?? [];
  }

  async function uploadSource(
    profileId: number,
    workbookId: number,
    payload: SourceCreate & { file: File },
  ): Promise<Source> {
    const form = new FormData();
    form.set('name', payload.name);
    form.set('description', payload.description);
    form.set('folder', payload.folder ?? '');
    form.set('file', payload.file);
    const source = await apiRequest<Source, FormData>(`${endpoint(profileId, workbookId)}/upload`, 'POST', form);
    if (!source) throw new Error('API did not return the uploaded source.');
    sources.value.unshift(source);
    return source;
  }

  async function addContentSource(
    profileId: number,
    workbookId: number,
    payload: SourceCreate & { content: string },
  ): Promise<Source> {
    const source = await apiRequest<Source>(`${endpoint(profileId, workbookId)}/content`, 'POST', payload);
    if (!source) throw new Error('API did not return the created source.');
    sources.value.unshift(source);
    return source;
  }

  async function addUrlSource(
    profileId: number,
    workbookId: number,
    payload: SourceCreate & { url: string; download: boolean },
  ): Promise<Source> {
    const source = await apiRequest<Source>(`${endpoint(profileId, workbookId)}/url`, 'POST', payload);
    if (!source) throw new Error('API did not return the created source.');
    sources.value.unshift(source);
    return source;
  }

  async function previewSource(profileId: number, workbookId: number, sourceId: number): Promise<SourcePreview> {
    const preview = await apiRequest<SourcePreview>(`${endpoint(profileId, workbookId)}/${sourceId}/content`);
    if (!preview) throw new Error('API did not return source content.');
    return preview;
  }

  async function updateSource(
    profileId: number,
    workbookId: number,
    sourceId: number,
    updates: SourceUpdate,
  ): Promise<Source> {
    const source = await apiRequest<Source>(`${endpoint(profileId, workbookId)}/${sourceId}`, 'PATCH', updates);
    if (!source) throw new Error('API did not return the updated source.');
    const index = sources.value.findIndex((item) => item.id === sourceId);
    if (index !== -1) sources.value[index] = source;
    return source;
  }

  async function redownloadSource(profileId: number, workbookId: number, sourceId: number): Promise<Source> {
    const source = await apiRequest<Source>(`${endpoint(profileId, workbookId)}/${sourceId}/redownload`, 'POST');
    if (!source) throw new Error('API did not return the updated source.');
    const index = sources.value.findIndex((item) => item.id === sourceId);
    if (index !== -1) sources.value[index] = source;
    return source;
  }

  async function deleteSource(profileId: number, workbookId: number, sourceId: number): Promise<void> {
    await apiRequest<null>(`${endpoint(profileId, workbookId)}/${sourceId}`, 'DELETE');
    sources.value = sources.value.filter((item) => item.id !== sourceId);
  }

  function clear(): void {
    sources.value = [];
  }

  return {
    sources,
    fetchSources,
    uploadSource,
    addContentSource,
    addUrlSource,
    previewSource,
    updateSource,
    redownloadSource,
    deleteSource,
    clear,
  };
});
