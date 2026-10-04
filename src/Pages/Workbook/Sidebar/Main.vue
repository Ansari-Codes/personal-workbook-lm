<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { ApiError } from '@/stores/api';
import { useAPIKeys } from '@/stores/useAPIKeys';
import { useTools } from '@/stores/useTools';
import { useWorkbookSettings } from '@/stores/useWorkbookSettings';
import { useWorkbooksStore, type Workbook } from '@/stores/useWorkbooks';
import { useNotifier } from '@/Widgets';
import WButton from '@/Widgets/WButton.vue';
import WIcon from '@/Widgets/WIcon.vue';
import TabApiKeys from './TabApiKeys.vue';
import TabOutputs from './TabOutputs.vue';
import TabSettings from './TabSettings.vue';
import TabSources from './TabSources.vue';
import TabTools from './TabTools.vue';
import type { PreviewItem } from '../preview';

const props = defineProps<{
    profileId: number;
    workbookId: number;
    profileName: string;
    workbookName: string;
    narrow?: boolean;
}>();
const emit = defineEmits<{
    openPreview: [item: PreviewItem];
    closePreview: [id: string];
    workbookUpdated: [workbook: Workbook];
}>();

type TabId = 'sources' | 'outputs' | 'api-keys' | 'tools' | 'settings';
const tabs: Array<{ id: TabId; label: string; icon: string; detail: string }> = [
    { id: 'sources', label: 'Sources', icon: 'source', detail: 'Workbook references' },
    { id: 'outputs', label: 'Outputs', icon: 'folder_open', detail: 'Generated files and media' },
    { id: 'api-keys', label: 'API Keys', icon: 'key', detail: 'Credentials enabled for chat' },
    { id: 'tools', label: 'Tools', icon: 'handyman', detail: 'Functions available to the model' },
    { id: 'settings', label: 'Settings', icon: 'tune', detail: 'Workbook details and behavior' },
];
const activeTab = ref<TabId>('sources');
const mobileOpen = ref(false);
const isLoading = ref(true);
const loadError = ref('');
const apiKeyStore = useAPIKeys();
const toolStore = useTools();
const settings = useWorkbookSettings();
const workbookStore = useWorkbooksStore();
const { notify } = useNotifier();
const workbook = computed(() => workbookStore.workbooks.find((item) => item.id === props.workbookId));
const workbookDescription = computed(() => workbook.value?.description ?? '');
const workbookThumbnail = computed(() => workbook.value?.thumbnail ?? null);
let loadGeneration = 0;

function errorMessage(error: unknown): string {
    if (error instanceof ApiError) return error.status === null ? error.message : `${error.message} (HTTP ${error.status})`;
    return error instanceof Error ? error.message : String(error);
}

async function loadSettings(): Promise<void> {
    const generation = ++loadGeneration;
    isLoading.value = true;
    loadError.value = '';
    try {
        await Promise.all([
            apiKeyStore.fetchAPIKeys(props.profileId),
            toolStore.fetchTools(props.profileId),
            settings.fetchSettings(props.profileId, props.workbookId),
        ]);
        if (generation !== loadGeneration) return;
        settings.selectedApiKeyIds = settings.selectedApiKeyIds.filter((id) => apiKeyStore.apiKeys.some((item) => item.id === id));
        settings.selectedToolIds = settings.selectedToolIds.filter((id) => toolStore.tools.some((item) => item.id === id));
    } catch (error) {
        if (generation !== loadGeneration) return;
        loadError.value = errorMessage(error);
        notify(`Could not load workbook settings: ${loadError.value}`, 'error', 9000);
    } finally {
        if (generation === loadGeneration) isLoading.value = false;
    }
}

function selectTab(tab: TabId): void {
    activeTab.value = tab;
    if (props.narrow) mobileOpen.value = true;
}

watch(() => [props.profileId, props.workbookId], loadSettings, { immediate: true });
</script>

<template>
    <aside class="sidebar-shell" :class="{ 'sidebar-shell-narrow': narrow, 'sidebar-shell-mobile-open': mobileOpen }"
        aria-label="Workbook sidebar">
        <nav class="sidebar-rail" role="tablist" aria-label="Workbook sections" aria-orientation="vertical">
            <WButton v-for="tab in tabs" :key="tab.id" type="button" variant="ghost" size="sm" role="tab"
                :aria-selected="activeTab === tab.id" :aria-label="tab.label" :title="tab.label" class="sidebar-tab"
                :class="activeTab === tab.id ? 'sidebar-tab-active' : ''" @click="selectTab(tab.id)">
                <WIcon :name="tab.icon" :size="21" />
                <span>{{ tab.label }}</span>
            </WButton>
        </nav>

        <section class="sidebar-pane" :aria-label="tabs.find((tab) => tab.id === activeTab)?.label">
            <header class="sidebar-pane-header">
                <div class="min-w-0">
                    <h2>{{tabs.find((tab) => tab.id === activeTab)?.label}}</h2>
                    <p>{{tabs.find((tab) => tab.id === activeTab)?.detail}}</p>
                </div>
                <WButton v-if="narrow" variant="ghost" size="sm" aria-label="Close sidebar" title="Close sidebar"
                    @click="mobileOpen = false">
                    <WIcon name="close" />
                </WButton>
            </header>

            <div v-if="loadError && !isLoading" class="sidebar-error" role="alert">
                <p>{{ loadError }}</p>
                <WButton variant="ghost" size="sm" @click="loadSettings">Retry</WButton>
            </div>

            <div class="sidebar-tab-content">
                <TabSources v-if="activeTab === 'sources'" :profile-id="profileId" :workbook-id="workbookId"
                    @open-preview="emit('openPreview', $event)" @close-preview="emit('closePreview', $event)" />
                <TabOutputs v-else-if="activeTab === 'outputs'" :profile-id="profileId" :workbook-id="workbookId"
                    @open-preview="emit('openPreview', $event)" @close-preview="emit('closePreview', $event)" />
                <TabApiKeys v-else-if="activeTab === 'api-keys'" :profile-id="profileId" :workbook-id="workbookId"
                    :profile-name="profileName" :is-loading="isLoading" />
                <TabTools v-else-if="activeTab === 'tools'" :profile-id="profileId" :workbook-id="workbookId"
                    :profile-name="profileName" :is-loading="isLoading" />
                <TabSettings v-else :profile-id="profileId" :workbook-id="workbookId"
                    :workbook-name="workbook?.title ?? workbookName" :workbook-description="workbookDescription"
                    :workbook-thumbnail="workbookThumbnail"
                    :is-loading="isLoading" :load-error="loadError"
                    @workbook-updated="emit('workbookUpdated', $event)" />
            </div>
        </section>
    </aside>
</template>

<style scoped>
.sidebar-shell {
    position: relative;
    display: flex;
    width: 100%;
    min-width: 0;
    height: 100%;
    min-height: 0;
    /* important for flex overflow */
    background: #fff;
    color: #17212b;
    overflow: hidden;
    /* prevent the shell itself from growing */
}

.sidebar-rail {
    display: flex;
    width: 76px;
    flex: 0 0 76px;
    flex-direction: column;
    gap: 5px;
    border-right: 1px solid #e3e8e8;
    background: #fff;
    padding: 10px 6px;
    overflow-y: auto;
}

.sidebar-tab {
    display: flex;
    min-height: 64px;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 5px;
    border: 0;
    background: transparent;
    color: #53605f;
    cursor: pointer;
    font-size: 10px;
    font-weight: 600;
}

.sidebar-tab-active,
.sidebar-tab:hover {
    background: #dcfce7;
    color: #166534;
}

.sidebar-pane {
    display: flex;
    min-width: 0;
    min-height: 0;
    /* allow child overflow */
    flex: 1;
    flex-direction: column;
    overflow: hidden;
}

.sidebar-pane-header {
    display: flex;
    min-height: 66px;
    flex: 0 0 auto;
    /* don't shrink/grow */
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    border-bottom: 1px solid #e7ebea;
    padding: 10px 14px;
}

.sidebar-pane-header h2 {
    overflow: hidden;
    font-size: 14px;
    font-weight: 700;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.sidebar-pane-header p {
    margin-top: 2px;
    color: #687573;
    font-size: 11px;
}

.sidebar-tab-content {
    flex: 1 1 auto;
    min-height: 0;
    /* critical: allows child to scroll instead of expanding parent */
    overflow-y: auto;
    /* scroll here */
    overflow-x: hidden;
}

.sidebar-tab-content> :deep(section) {
    height: 100%;
    min-height: 0;
}

.sidebar-error {
    padding: 16px;
    color: #a32b2b;
    font-size: 13px;
}

.sidebar-error button {
    margin-top: 8px;
    font-weight: 650;
    text-decoration: underline;
}

.icon-button {
    display: grid;
    width: 36px;
    height: 36px;
    flex: 0 0 36px;
    place-items: center;
    border: 0;
    background: transparent;
    color: #44514f;
    cursor: pointer;
}

.icon-button:hover {
    background: #f0fdf4;
    color: #166534;
}

@media (max-width: 1099px) {
    .sidebar-shell-narrow {
        width: 68px;
        overflow: visible;
    }

    .sidebar-rail {
        width: 68px;
        flex-basis: 68px;
        padding-inline: 4px;
    }

    .sidebar-pane {
        position: absolute;
        z-index: 30;
        inset: 0 auto 0 68px;
        display: none;
        width: min(360px, calc(100vw - 68px));
        border: 1px solid #dce3e1;
        background: white;
        box-shadow: 0 4px 14px #12201d20;
        overflow: hidden;
        /* keep the pane from expanding; inner content scrolls */
    }

    .sidebar-shell-mobile-open .sidebar-pane {
        display: flex;
    }
}
</style>
