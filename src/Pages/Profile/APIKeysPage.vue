<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useProfilesStore, type Profile } from '@/stores/useProfiles';
import { ApiError } from '@/stores/api';
import { useAPIKeys, type APIKey, type APIKeyCreate } from '@/stores/useAPIKeys';
import { useNotifier } from '@/Widgets';
import WButton from '@/Widgets/WButton.vue';
import WDialog from '@/Widgets/WDialog.vue';
import WTable from '@/Widgets/WTable.vue';
import WInput from '@/Widgets/WInput.vue';
import APIKeyDialog, { type APIKeyFormData } from '@/Comps/Profile/APIKeyDialog.vue';

const route = useRoute();
const profileStore = useProfilesStore();
const apiKeyStore = useAPIKeys();
const { notify } = useNotifier();

const profile = ref<Profile | null>(null);
const isLoading = ref(true);
const isSaving = ref(false);
const isDeleting = ref(false);
const loadError = ref('');
const isDialogOpen = ref(false);
const isDeleteDialogOpen = ref(false);
const isViewDialogOpen = ref(false);
const selectedApiKey = ref<APIKey | null>(null);
const viewedApiKey = ref<APIKey | null>(null);
const pendingDelete = ref<APIKey | null>(null);
const query = ref('');
const filteredApiKeys = computed(() => {
    const search = query.value.trim().toLocaleLowerCase();
    if (!search) return apiKeyStore.apiKeys;
    return apiKeyStore.apiKeys.filter((apiKey) =>
        `${apiKey.name} ${apiKey.description} ${apiKey.base_url} ${apiKey.key_preview}`.toLocaleLowerCase().includes(search),
    );
});
let loadRequest = 0;

const metadataEntries = computed(() => Object.entries(viewedApiKey.value?.meta ?? {}));

function formatMetadataValue(value: unknown): string {
    if (typeof value === 'string') return value;
    try {
        return JSON.stringify(value, null, 2);
    } catch {
        return String(value);
    }
}

const columns = [
    { key: 'name', label: 'Name', cellClass: 'font-medium text-neutral-950' },
    { key: 'key_preview', label: 'Key', cellClass: 'font-mono text-xs' },
    { key: 'base_url', label: 'Base URL', cellClass: 'max-w-64 wrap-break-word' },
    { key: 'description', label: 'Description', cellClass: 'max-w-56 wrap-break-word' },
] as const;

function errorMessage(error: unknown): string {
    if (error instanceof ApiError) {
        return error.status === null ? error.message : `${error.message} (HTTP ${error.status})`;
    }
    return error instanceof Error ? error.message : String(error);
}

async function loadProfile(routeName: string | string[] | undefined): Promise<void> {
    const request = ++loadRequest;
    const name = Array.isArray(routeName) ? routeName[0] : routeName;
    profile.value = null;
    loadError.value = '';
    apiKeyStore.clear();
    isLoading.value = true;

    try {
        if (!name) throw new Error('Profile name is missing from the route.');
        await profileStore.fetchProfiles();
        if (request !== loadRequest) return;
        const found = profileStore.profiles.find((item) => item.name === name);
        if (!found) throw new Error(`Profile "${name}" was not found.`);
        profile.value = found;
        await apiKeyStore.fetchAPIKeys(found.id);
    } catch (error) {
        if (request !== loadRequest) return;
        loadError.value = errorMessage(error);
        notify(`Failed to load API keys: ${loadError.value}`, 'error', 10000);
    } finally {
        if (request === loadRequest) isLoading.value = false;
    }
}

function openCreateDialog(): void {
    selectedApiKey.value = null;
    isDialogOpen.value = true;
}

function openEditDialog(apiKey: APIKey): void {
    selectedApiKey.value = apiKey;
    isDialogOpen.value = true;
}

function openViewDialog(apiKey: APIKey): void {
    viewedApiKey.value = apiKey;
    isViewDialogOpen.value = true;
}

async function saveApiKey(payload: APIKeyFormData): Promise<void> {
    if (!profile.value) return;
    isSaving.value = true;
    try {
        if (selectedApiKey.value) {
            const { secret, ...updates } = payload;
            await apiKeyStore.updateAPIKey(profile.value.id, selectedApiKey.value.id, secret ? { ...updates, secret } : updates);
            notify('API key updated.', 'success', 5000);
        } else {
            if (!payload.secret) throw new Error('An API key is required.');
            await apiKeyStore.createAPIKey(profile.value.id, payload as APIKeyCreate);
            notify('API key added.', 'success', 5000);
        }
        isDialogOpen.value = false;
        selectedApiKey.value = null;
    } catch (error) {
        notify(`Could not save API key: ${errorMessage(error)}`, 'error', 10000);
    } finally {
        isSaving.value = false;
    }
}

function askDelete(apiKey: APIKey): void {
    pendingDelete.value = apiKey;
    isDeleteDialogOpen.value = true;
}

async function deleteApiKey(): Promise<void> {
    if (!profile.value || !pendingDelete.value) return;
    isDeleting.value = true;
    try {
        await apiKeyStore.deleteAPIKey(profile.value.id, pendingDelete.value.id);
        notify('API key deleted.', 'success', 5000);
        pendingDelete.value = null;
        isDeleteDialogOpen.value = false;
    } catch (error) {
        notify(`Could not delete API key: ${errorMessage(error)}`, 'error', 10000);
    } finally {
        isDeleting.value = false;
    }
}

watch(() => route.params.name, loadProfile, { immediate: true });
</script>

<template>
    <div class="min-h-screen bg-neutral-50">

        <main class="mx-auto max-w-6xl px-5 py-4 sm:px-8">
            <section class="flex flex-wrap items-end justify-between gap-4">
                <div>
                    <h2 class="mt-1 text-2xl font-semibold text-neutral-950">API keys</h2>
                </div>
                <WButton :disabled="!profile || isLoading" @click="openCreateDialog">
                    Add API key
                </WButton>
            </section>

            <WInput v-if="apiKeyStore.apiKeys.length" v-model="query" label="Search API keys" type="search" placeholder="Name, URL, or key preview" class="mt-5 max-w-md" />

            <div v-if="isLoading" class="py-16 text-center text-sm text-neutral-500" role="status">
                Loading API keys…
            </div>

            <section v-else-if="loadError" class="py-16 text-center" role="alert">
                <p class="text-sm text-rose-700">{{ loadError }}</p>
                <WButton class="mt-4" variant="secondary" @click="loadProfile(route.params.name)">Retry</WButton>
            </section>

            <section v-else-if="apiKeyStore.apiKeys.length === 0" class="flex flex-col items-center py-20 text-center">
                <span class="grid size-12 place-items-center rounded-md bg-green-50 text-xl text-green-800"
                    aria-hidden="true">&#128272;</span>
                <h3 class="mt-4 text-base font-semibold text-neutral-950">No API keys yet</h3>
                <p class="mt-1 max-w-sm text-sm text-neutral-600">Add a credential, base URL, and named endpoints for your provider.</p>
                <WButton class="mt-5" @click="openCreateDialog">Add API key</WButton>
            </section>

            <section v-else class="py-6">
                <WTable :data="filteredApiKeys" :columns="columns" row-key="id" empty-message="No API keys match your search.">
                    <template #actions="{ row }">
                        <div class="flex justify-end gap-2">
                            <WButton size="sm" variant="ghost" @click="openViewDialog(row)">View</WButton>
                            <WButton size="sm" variant="secondary" @click="openEditDialog(row)">Edit</WButton>
                            <WButton size="sm" variant="danger" @click="askDelete(row)">Delete</WButton>
                        </div>
                    </template>
                </WTable>
            </section>
        </main>

        <APIKeyDialog v-model="isDialogOpen" :api-key="selectedApiKey"
            :loading="isSaving" @submit="saveApiKey" />

        <WDialog v-model="isViewDialogOpen" :title="viewedApiKey?.name ?? 'API key details'">
            <dl v-if="viewedApiKey" class="grid gap-3 text-sm">
                <div class="grid grid-cols-[7rem_minmax(0,1fr)] gap-3">
                    <dt class="font-medium text-neutral-500">Base URL</dt>
                    <dd class="wrap-break-word text-neutral-900">{{ viewedApiKey.base_url }}</dd>
                </div>
                <div class="grid grid-cols-[7rem_minmax(0,1fr)] gap-3">
                    <dt class="font-medium text-neutral-500">Endpoints</dt>
                    <dd class="grid gap-2">
                        <div v-for="[name, path] in Object.entries(viewedApiKey.endpoints)" :key="name" class="grid grid-cols-[5rem_minmax(0,1fr)] gap-2">
                            <span class="font-medium text-neutral-700">{{ name }}</span>
                            <span class="wrap-break-word font-mono text-xs text-neutral-700">{{ path }}</span>
                        </div>
                    </dd>
                </div>
                <div class="grid grid-cols-[7rem_minmax(0,1fr)] gap-3">
                    <dt class="font-medium text-neutral-500">Key</dt>
                    <dd class="font-mono text-neutral-900">{{ viewedApiKey.key_preview }}</dd>
                </div>
                <div class="grid grid-cols-[7rem_minmax(0,1fr)] gap-3">
                    <dt class="font-medium text-neutral-500">Description</dt>
                    <dd class="wrap-break-word text-neutral-900">{{ viewedApiKey.description || '—' }}</dd>
                </div>
                <div class="border-t border-neutral-200 pt-3">
                    <dt class="mb-2 font-semibold text-neutral-900">Metadata</dt>
                    <dd v-if="metadataEntries.length === 0" class="text-neutral-500">No metadata configured.</dd>
                    <dl v-else class="grid gap-2">
                        <div v-for="[key, value] in metadataEntries" :key="key"
                            class="grid grid-cols-[7rem_minmax(0,1fr)] gap-3 border-b border-neutral-100 pb-2 last:border-0">
                            <dt class="break-all font-medium text-neutral-600">{{ key }}</dt>
                            <dd class="min-w-0 wrap-break-word text-neutral-800">
                                <pre class="whitespace-pre-wrap wrap-break-word font-sans">{{ formatMetadataValue(value) }}</pre>
                            </dd>
                        </div>
                    </dl>
                </div>
            </dl>
            <template #footer>
                <WButton variant="secondary" @click="isViewDialogOpen = false">Close</WButton>
            </template>
        </WDialog>

        <WDialog v-model="isDeleteDialogOpen" title="Delete API key" description="This cannot be undone.">
            <p class="text-sm text-neutral-700">
                Delete <strong>{{ pendingDelete?.name }}</strong> from this profile?
            </p>
            <template #footer>
                <WButton variant="secondary" :disabled="isDeleting" @click="isDeleteDialogOpen = false">Cancel</WButton>
                <WButton variant="danger" :loading="isDeleting" @click="deleteApiKey">Delete key</WButton>
            </template>
        </WDialog>
    </div>
</template>
