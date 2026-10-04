import { defineStore } from 'pinia';
import { ref } from 'vue';
import { apiRequest } from '@/stores/api';

export interface Tool {
  id: number;
  title: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface ToolCreate {
  title: string;
  description: string;
  package: File;
}

export interface ToolUpdate {
  title: string;
  description: string;
  package?: File;
}

export const useTools = defineStore('tools', () => {
  const tools = ref<Tool[]>([]);

  async function fetchTools(profileId: number): Promise<void> {
    tools.value = await apiRequest<Tool[]>(`/profiles/${profileId}/tools`) ?? [];
  }

  async function createTool(profileId: number, payload: ToolCreate): Promise<Tool> {
    const form = new FormData();
    form.set('title', payload.title);
    form.set('description', payload.description);
    form.set('package', payload.package);
    const tool = await apiRequest<Tool, FormData>(`/profiles/${profileId}/tools`, 'POST', form);
    if (!tool) throw new Error('API did not return the created tool.');
    tools.value.push(tool);
    return tool;
  }

  async function updateTool(profileId: number, toolId: number, payload: ToolUpdate): Promise<Tool> {
    const form = new FormData();
    form.set('title', payload.title);
    form.set('description', payload.description);
    if (payload.package) form.set('package', payload.package);
    const tool = await apiRequest<Tool, FormData>(
      `/profiles/${profileId}/tools/${toolId}`,
      'PATCH',
      form,
    );
    if (!tool) throw new Error('API did not return the updated tool.');
    const index = tools.value.findIndex((item) => item.id === toolId);
    if (index !== -1) tools.value[index] = tool;
    return tool;
  }

  async function deleteTool(profileId: number, toolId: number): Promise<void> {
    await apiRequest<null>(`/profiles/${profileId}/tools/${toolId}`, 'DELETE');
    tools.value = tools.value.filter((item) => item.id !== toolId);
  }

  function clear(): void {
    tools.value = [];
  }

  return { tools, fetchTools, createTool, updateTool, deleteTool, clear };
});
