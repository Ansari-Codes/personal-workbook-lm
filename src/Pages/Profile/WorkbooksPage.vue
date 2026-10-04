<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useProfilesStore, type Profile } from '@/stores/useProfiles';
import { ApiError } from '@/stores/api';
import { useWorkbooksStore, type WorkbookCreate } from '@/stores/useWorkbooks';
import { useNotifier } from '@/Widgets';
import WButton from '@/Widgets/WButton.vue';
import WDialog from '@/Widgets/WDialog.vue';
import WInput from '@/Widgets/WInput.vue';
import WorkbookCard from '@/Comps/Profile/WorkbookCard.vue';
import WorkbookCreateDialog from '@/Comps/Profile/WorkbookCreateDialog.vue';

const route = useRoute();
const profileStore = useProfilesStore();
const workbookStore = useWorkbooksStore();
const { notify } = useNotifier();

const profile = ref<Profile | null>(null);
const isCreateOpen = ref(false);
const isLoading = ref(true);
const isCreating = ref(false);
const isDeleteOpen = ref(false);
const isDeleting = ref(false);
const query = ref('');
const pendingDelete = ref<{ id: number; title: string } | null>(null);
const loadError = ref('');
let loadRequest = 0;
const filteredWorkbooks = computed(() => {
    const search = query.value.trim().toLocaleLowerCase();
    if (!search) return workbookStore.workbooks;
    return workbookStore.workbooks.filter((workbook) =>
        `${workbook.title} ${workbook.description}`.toLocaleLowerCase().includes(search),
    );
});

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
    workbookStore.clearWorkbooks();
    isLoading.value = true;

    try {
        if (!name) throw new Error('Profile name is missing from the route.');
        await profileStore.fetchProfiles();
        if (request !== loadRequest) return;

        const found = profileStore.profiles.find((item) => item.name === name);
        if (!found) throw new Error(`Profile "${name}" was not found.`);
        profile.value = found;
        await workbookStore.fetchWorkbooks(found.id);
    } catch (error) {
        if (request !== loadRequest) return;
        loadError.value = errorMessage(error);
        notify(`Failed to load profile: ${loadError.value}`, 'error', 10000);
    } finally {
        if (request === loadRequest) isLoading.value = false;
    }
}

async function createWorkbook(data: WorkbookCreate): Promise<void> {
    if (!profile.value) return;
    isCreating.value = true;
    try {
        await workbookStore.createWorkbook(profile.value.id, data);
        isCreateOpen.value = false;
        notify('Workbook created successfully.', 'success', 5000);
    } catch (error) {
        notify(`Failed to create workbook: ${errorMessage(error)}`, 'error', 10000);
    } finally {
        isCreating.value = false;
    }
}

async function deleteWorkbook(): Promise<void> {
    if (!profile.value || !pendingDelete.value) return;
    isDeleting.value = true;
    try {
        await workbookStore.deleteWorkbook(profile.value.id, pendingDelete.value.id);
        pendingDelete.value = null;
        isDeleteOpen.value = false;
        notify('Workbook deleted.', 'success', 5000);
    } catch (error) {
        notify(`Could not delete workbook: ${errorMessage(error)}`, 'error', 10000);
    } finally {
        isDeleting.value = false;
    }
}

watch(() => route.params.name, loadProfile, { immediate: true });
</script>

<template>
    <div class="min-h-screen bg-neutral-50">

        <main class="mx-auto max-w-6xl px-5 py-4 sm:px-8">
            <section>
                <div class="flex flex-wrap items-end justify-between gap-4">
                    <div>
                        <h2 class="mt-1 text-2xl font-semibold text-neutral-950">Workbooks</h2>
                    </div>
                    <WButton :disabled="!profile || isLoading" @click="isCreateOpen = true">
                        Create workbook
                    </WButton>
                </div>
            </section>

            <WInput v-if="workbookStore.workbooks.length" v-model="query" label="Search workbooks" type="search" placeholder="Title or description" class="mt-5 max-w-md" />

            <div v-if="isLoading" class="py-16 text-center text-sm text-neutral-500" role="status">
                Loading workbooks...
            </div>

            <div v-else-if="loadError" class="py-16 text-center">
                <p class="text-sm text-rose-700">{{ loadError }}</p>
            </div>

            <div v-else-if="filteredWorkbooks.length"
                class="grid grid-cols-1 gap-4 py-6 sm:grid-cols-2 lg:grid-cols-3">
                <WorkbookCard
                    v-for="workbook in filteredWorkbooks"
                    :key="workbook.id"
                    :workbook="workbook"
                    :profile-name="profile?.name ?? ''"
                    @delete="pendingDelete = $event; isDeleteOpen = true"
                />
            </div>

            <div v-else-if="workbookStore.workbooks.length && query" class="py-16 text-center text-sm text-neutral-500">
                No workbooks match “{{ query }}”.
            </div>

            <div v-else class="flex flex-col items-center justify-center py-20 text-center">
                <h3 class="text-base font-semibold text-neutral-900">No workbooks yet</h3>
                <p class="mt-1 max-w-sm text-sm text-neutral-500">
                    Create a workbook to start organizing this profile's work.
                </p>
                <WButton class="mt-5" :disabled="!profile" @click="isCreateOpen = true">
                    Create workbook
                </WButton>
            </div>
        </main>

        <WorkbookCreateDialog v-model="isCreateOpen" :loading="isCreating" @create="createWorkbook" />
        <WDialog v-model="isDeleteOpen" title="Delete workbook" description="This permanently removes the workbook and its associated content.">
            <p class="text-sm text-neutral-700">Delete <strong>{{ pendingDelete?.title }}</strong>?</p>
            <template #footer>
                <WButton variant="secondary" :disabled="isDeleting" @click="isDeleteOpen = false">Cancel</WButton>
                <WButton variant="danger" :loading="isDeleting" @click="deleteWorkbook">Delete workbook</WButton>
            </template>
        </WDialog>
    </div>
</template>
