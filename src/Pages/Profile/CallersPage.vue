<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { ApiError } from '@/stores/api';
import { useProfilesStore, type Profile } from '@/stores/useProfiles';
import { useCallers, type Caller, type CallerCreate } from '@/stores/useCallers';
import { useNotifier } from '@/Widgets';
import WButton from '@/Widgets/WButton.vue';
import WDialog from '@/Widgets/WDialog.vue';
import WTable from '@/Widgets/WTable.vue';
import WInput from '@/Widgets/WInput.vue';
import CallerDialog from '@/Comps/Profile/CallerDialog.vue';

const route = useRoute();
const profileStore = useProfilesStore();
const callerStore = useCallers();
const { notify } = useNotifier();
const profile = ref<Profile | null>(null);
const isLoading = ref(true);
const isSaving = ref(false);
const isDeleting = ref(false);
const loadError = ref('');
const isDialogOpen = ref(false);
const isDeleteOpen = ref(false);
const selectedCaller = ref<Caller | null>(null);
const pendingDelete = ref<Caller | null>(null);
const query = ref('');
const filteredCallers = computed(() => {
    const search = query.value.trim().toLocaleLowerCase();
    if (!search) return callerStore.callers;
    return callerStore.callers.filter((caller) =>
        `${caller.name} ${caller.description}`.toLocaleLowerCase().includes(search),
    );
});
let loadRequest = 0;

const groqTtsCaller = `from uuid import uuid4

import requests


def endpoint_url(base_url, endpoint):
    if not isinstance(base_url, str) or not isinstance(endpoint, str):
        raise ValueError("base_url and endpoint are required")
    return f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"


def INVOKE(**kwargs):
    settings = kwargs
    try:
        endpoint = endpoint_url(settings["base_url"], settings["endpoint"])
        key = settings.get("key", settings.get("api_key"))
        extra = settings.get("additional_parameters") or {}
        response_format = extra.get("response_format", "wav")
        response = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": settings["model"],
                "voice": extra.get("voice", "troy"),
                "input": settings["prompt"],
                "response_format": response_format,
                **{name: value for name, value in extra.items() if name not in ("voice", "response_format")},
            },
            timeout=90,
        )
        response.raise_for_status()
        suffix = response_format if response_format in ("wav", "mp3") else "wav"
        return {
            "success": True,
            "model": settings["model"],
            "message": {"role": "assistant", "content": "Audio generated."},
            "usage": {},
            "media": [{
                "name": f"audio-{uuid4().hex[:12]}.{suffix}",
                "folder": "audio",
                "media_type": "audio/wav" if suffix == "wav" else "audio/mpeg",
                "content": response.content,
            }],
            "raw": {},
        }
    except Exception as error:
        return {"success": False, "error": str(error)}


def MODEL(**kwargs):
    settings = kwargs
    try:
        response = requests.get(
            endpoint_url(settings["base_url"], settings["endpoint"]),
            headers={"Authorization": f"Bearer {settings.get('key', settings.get('api_key'))}"},
            timeout=15,
        )
        response.raise_for_status()
        raw = response.json()
        models = [
            {**item, "id": item["id"], "name": item.get("name", item["id"])}
            for item in raw.get("data", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        ]
        return {"success": True, "models": models, "raw": raw}
    except Exception as error:
        return {"success": False, "models": [], "error": str(error)}
`;

const columns = [
    { key: 'name', label: 'Name', cellClass: 'font-medium text-neutral-950' },
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
    callerStore.clear();
    try {
        if (!name) throw new Error('Profile name is missing from the route.');
        await profileStore.fetchProfiles();
        if (request !== loadRequest) return;
        const found = profileStore.profiles.find((item) => item.name === name);
        if (!found) throw new Error(`Profile "${name}" was not found.`);
        profile.value = found;
        await callerStore.fetchCallers(found.id);
    } catch (error) {
        if (request !== loadRequest) return;
        loadError.value = errorMessage(error);
        notify(`Failed to load callers: ${loadError.value}`, 'error', 10000);
    } finally {
        if (request === loadRequest) isLoading.value = false;
    }
}

function openCreate(): void {
    selectedCaller.value = null;
    isDialogOpen.value = true;
}

function openEdit(caller: Caller): void {
    selectedCaller.value = caller;
    isDialogOpen.value = true;
}

async function saveCaller(payload: CallerCreate): Promise<void> {
    if (!profile.value) return;
    isSaving.value = true;
    try {
        if (selectedCaller.value) {
            await callerStore.updateCaller(profile.value.id, selectedCaller.value.id, payload);
            notify('Caller updated.', 'success', 5000);
        } else {
            await callerStore.createCaller(profile.value.id, payload);
            notify('Caller created.', 'success', 5000);
        }
        selectedCaller.value = null;
        isDialogOpen.value = false;
    } catch (error) {
        notify(`Could not save caller: ${errorMessage(error)}`, 'error', 10000);
    } finally {
        isSaving.value = false;
    }
}

async function createGroqTtsCaller(): Promise<void> {
    if (!profile.value) return;
    isSaving.value = true;
    try {
        await callerStore.createCaller(profile.value.id, {
            name: 'Groq TTS',
            description: 'Groq text-to-speech through the unified INVOKE interface.',
            content: groqTtsCaller,
        });
        notify('Groq TTS caller added.', 'success', 5000);
    } catch (error) {
        notify(`Could not add Groq TTS caller: ${errorMessage(error)}`, 'error', 10000);
    } finally {
        isSaving.value = false;
    }
}

function askDelete(caller: Caller): void {
    pendingDelete.value = caller;
    isDeleteOpen.value = true;
}

async function deleteCaller(): Promise<void> {
    if (!profile.value || !pendingDelete.value) return;
    isDeleting.value = true;
    try {
        await callerStore.deleteCaller(profile.value.id, pendingDelete.value.id);
        notify('Caller deleted.', 'success', 5000);
        pendingDelete.value = null;
        isDeleteOpen.value = false;
    } catch (error) {
        notify(`Could not delete caller: ${errorMessage(error)}`, 'error', 10000);
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
                    <h2 class="mt-1 text-2xl font-semibold text-neutral-950">Callers</h2>
                </div>
                <div class="flex flex-wrap gap-2">
                    <WButton variant="secondary" :disabled="!profile || isLoading || isSaving" @click="createGroqTtsCaller">Add Groq TTS caller</WButton>
                    <WButton :disabled="!profile || isLoading" @click="openCreate">Add caller</WButton>
                </div>
            </section>

            <WInput v-if="callerStore.callers.length" v-model="query" label="Search callers" type="search" placeholder="Name or description" class="mt-5 max-w-md" />

            <div v-if="isLoading" class="py-16 text-center text-sm text-neutral-500" role="status">Loading callers…
            </div>
            <section v-else-if="loadError" class="py-16 text-center" role="alert">
                <p class="text-sm text-rose-700">{{ loadError }}</p>
                <WButton class="mt-4" variant="secondary" @click="load(route.params.name)">Retry</WButton>
            </section>
            <section v-else-if="callerStore.callers.length === 0" class="flex flex-col items-center py-20 text-center">
                <h3 class="text-base font-semibold text-neutral-950">No callers yet</h3>
                <p class="mt-1 max-w-md text-sm text-neutral-600">Add a caller to define how this profile invokes
                    external services.</p>
                <WButton class="mt-5" @click="openCreate">Add caller</WButton>
            </section>
            <section v-else class="py-6">
                <WTable :data="filteredCallers" :columns="columns" row-key="id" empty-message="No callers match your search.">
                    <template #actions="{ row }">
                        <div class="flex justify-end gap-2">
                            <WButton size="sm" variant="secondary" @click="openEdit(row)">Edit</WButton>
                            <WButton size="sm" variant="danger" @click="askDelete(row)">Delete</WButton>
                        </div>
                    </template>
                </WTable>
            </section>
        </main>

        <CallerDialog v-model="isDialogOpen" :caller="selectedCaller" :loading="isSaving" @submit="saveCaller" />
        <WDialog v-model="isDeleteOpen" title="Delete caller"
            description="API keys linked to this caller will no longer be able to invoke it.">
            <p class="text-sm text-neutral-700">Delete <strong>{{ pendingDelete?.name }}</strong>?</p>
            <template #footer>
                <WButton variant="secondary" :disabled="isDeleting" @click="isDeleteOpen = false">Cancel</WButton>
                <WButton variant="danger" :loading="isDeleting" @click="deleteCaller">Delete caller</WButton>
            </template>
        </WDialog>
    </div>
</template>
