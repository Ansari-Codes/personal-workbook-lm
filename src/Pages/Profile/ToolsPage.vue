<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { ApiError } from '@/stores/api';
import { useProfilesStore, type Profile } from '@/stores/useProfiles';
import { useTools, type Tool, type ToolUpdate } from '@/stores/useTools';
import { useNotifier } from '@/Widgets';
import WButton from '@/Widgets/WButton.vue';
import WDialog from '@/Widgets/WDialog.vue';
import WTable from '@/Widgets/WTable.vue';
import WInput from '@/Widgets/WInput.vue';
import ToolDialog, { type ToolFormData } from '@/Comps/Profile/ToolDialog.vue';

const route = useRoute();
const profileStore = useProfilesStore();
const toolStore = useTools();
const { notify } = useNotifier();
const profile = ref<Profile | null>(null);
const isLoading = ref(true);
const isSaving = ref(false);
const isDeleting = ref(false);
const loadError = ref('');
const isDialogOpen = ref(false);
const isDeleteOpen = ref(false);
const selectedTool = ref<Tool | null>(null);
const pendingDelete = ref<Tool | null>(null);
const query = ref('');
const filteredTools = computed(() => {
    const search = query.value.trim().toLocaleLowerCase();
    if (!search) return toolStore.tools;
    return toolStore.tools.filter((tool) =>
        `${tool.title} ${tool.description}`.toLocaleLowerCase().includes(search),
    );
});
let loadRequest = 0;

const columns = [
    { key: 'title', label: 'Title', cellClass: 'font-medium text-neutral-950' },
    { key: 'description', label: 'Description' },
    { key: 'updated_at', label: 'Updated' },
] as const;

function errorMessage(error: unknown): string {
    if (error instanceof ApiError) return error.status === null ? error.message : `${error.message} (HTTP ${error.status})`;
    return error instanceof Error ? error.message : String(error);
}

async function load(routeName: string | string[] | undefined): Promise<void> {
    const request = ++loadRequest;
    const name = Array.isArray(routeName) ? routeName[0] : routeName;
    isLoading.value = true;
    profile.value = null;
    loadError.value = '';
    toolStore.clear();
    try {
        if (!name) throw new Error('Profile name is missing from the route.');
        await profileStore.fetchProfiles();
        if (request !== loadRequest) return;
        const found = profileStore.profiles.find((item) => item.name === name);
        if (!found) throw new Error(`Profile "${name}" was not found.`);
        profile.value = found;
        await toolStore.fetchTools(found.id);
    } catch (error) {
        if (request !== loadRequest) return;
        loadError.value = errorMessage(error);
        notify(`Failed to load tools: ${loadError.value}`, 'error', 10000);
    } finally {
        if (request === loadRequest) isLoading.value = false;
    }
}

function openCreate(): void {
    selectedTool.value = null;
    isDialogOpen.value = true;
}

function openEdit(tool: Tool): void {
    selectedTool.value = tool;
    isDialogOpen.value = true;
}

async function saveTool(payload: ToolFormData): Promise<void> {
    if (!profile.value) return;
    isSaving.value = true;
    try {
        if (selectedTool.value) {
            const updates: ToolUpdate = {
                title: payload.title,
                description: payload.description,
                ...(payload.package ? { package: payload.package } : {}),
            };
            await toolStore.updateTool(profile.value.id, selectedTool.value.id, updates);
            notify('Tool updated.', 'success', 5000);
        } else {
            if (!payload.package) throw new Error('Choose a ZIP package.');
            await toolStore.createTool(profile.value.id, {
                title: payload.title,
                description: payload.description,
                package: payload.package,
            });
            notify('Tool uploaded.', 'success', 5000);
        }
        selectedTool.value = null;
        isDialogOpen.value = false;
    } catch (error) {
        notify(`Could not save tool: ${errorMessage(error)}`, 'error', 10000);
    } finally {
        isSaving.value = false;
    }
}

function askDelete(tool: Tool): void {
    pendingDelete.value = tool;
    isDeleteOpen.value = true;
}

async function deleteTool(): Promise<void> {
    if (!profile.value || !pendingDelete.value) return;
    isDeleting.value = true;
    try {
        await toolStore.deleteTool(profile.value.id, pendingDelete.value.id);
        notify('Tool deleted.', 'success', 5000);
        pendingDelete.value = null;
        isDeleteOpen.value = false;
    } catch (error) {
        notify(`Could not delete tool: ${errorMessage(error)}`, 'error', 10000);
    } finally {
        isDeleting.value = false;
    }
}

watch(() => route.params.name, load, { immediate: true });
</script>

<template>
    <div class="min-h-screen bg-neutral-50">
        <main class="mx-auto max-w-6xl px-5 py-4 sm:px-8">
            <section class="flex flex-wrap items-end justify-between gap-4">
                <div>
                    <h2 class="mt-1 text-2xl font-semibold text-neutral-950">Tools</h2>
                </div>
                <WButton :disabled="!profile || isLoading" @click="openCreate">Upload tool ZIP</WButton>
            </section>

            <WInput v-if="toolStore.tools.length" v-model="query" label="Search tools" type="search" placeholder="Title or description" class="mt-5 max-w-md" />

            <div v-if="isLoading" class="py-16 text-center text-sm text-neutral-500" role="status">Loading tools…</div>
            <section v-else-if="loadError" class="py-16 text-center" role="alert">
                <p class="text-sm text-rose-700">{{ loadError }}</p>
                <WButton class="mt-4" variant="secondary" @click="load(route.params.name)">Retry</WButton>
            </section>
            <section v-else-if="toolStore.tools.length === 0" class="flex flex-col items-center py-20 text-center">
                <h3 class="text-base font-semibold text-neutral-950">No tools installed</h3>
                <p class="mt-1 max-w-md text-sm text-neutral-600">Upload a ZIP containing non-empty main.py, README.md,
                    and schema.json files.</p>
                <WButton class="mt-5" @click="openCreate">Upload tool ZIP</WButton>
            </section>
            <section v-else class="py-6">
                <WTable :data="filteredTools" :columns="columns" row-key="id" empty-message="No tools match your search.">
                    <template #actions="{ row }">
                        <div class="flex justify-end gap-2">
                            <WButton size="sm" variant="secondary" @click="openEdit(row)">Edit</WButton>
                            <WButton size="sm" variant="danger" @click="askDelete(row)">Delete</WButton>
                        </div>
                    </template>
                </WTable>
            </section>
        </main>

        <ToolDialog v-model="isDialogOpen" :tool="selectedTool" :loading="isSaving" @submit="saveTool" />
        <WDialog v-model="isDeleteOpen" title="Delete tool"
            description="The package files will be removed from this profile.">
            <p class="text-sm text-neutral-700">Delete <strong>{{ pendingDelete?.title }}</strong>?</p>
            <template #footer>
                <WButton variant="secondary" :disabled="isDeleting" @click="isDeleteOpen = false">Cancel</WButton>
                <WButton variant="danger" :loading="isDeleting" @click="deleteTool">Delete tool</WButton>
            </template>
        </WDialog>
    </div>
</template>
