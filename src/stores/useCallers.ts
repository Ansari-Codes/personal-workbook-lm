import { defineStore } from 'pinia';
import { ref } from 'vue';
import { apiRequest } from '@/stores/api';

export interface Caller {
  id: number;
  name: string;
  description: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface CallerCreate {
  name: string;
  description: string;
  content: string;
}

export type CallerUpdate = Partial<CallerCreate>;

export const useCallers = defineStore('callers', () => {
  const callers = ref<Caller[]>([]);

  async function fetchCallers(profileId: number): Promise<void> {
    callers.value = await apiRequest<Caller[]>(`/profiles/${profileId}/callers`) ?? [];
  }

  async function createCaller(profileId: number, payload: CallerCreate): Promise<Caller> {
    const caller = await apiRequest<Caller>(`/profiles/${profileId}/callers`, 'POST', payload);
    if (!caller) throw new Error('API did not return the created caller.');
    callers.value.push(caller);
    return caller;
  }

  async function updateCaller(profileId: number, callerId: number, payload: CallerUpdate): Promise<Caller> {
    const caller = await apiRequest<Caller>(`/profiles/${profileId}/callers/${callerId}`, 'PATCH', payload);
    if (!caller) throw new Error('API did not return the updated caller.');
    const index = callers.value.findIndex((item) => item.id === callerId);
    if (index !== -1) callers.value[index] = caller;
    return caller;
  }

  async function deleteCaller(profileId: number, callerId: number): Promise<void> {
    await apiRequest<null>(`/profiles/${profileId}/callers/${callerId}`, 'DELETE');
    callers.value = callers.value.filter((item) => item.id !== callerId);
  }

  function clear(): void {
    callers.value = [];
  }

  return { callers, fetchCallers, createCaller, updateCaller, deleteCaller, clear };
});
