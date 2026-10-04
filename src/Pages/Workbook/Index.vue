<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { ApiError } from '@/stores/api';
import { useProfilesStore } from '@/stores/useProfiles';
import { useWorkbooksStore } from '@/stores/useWorkbooks';
import { useOutputs, type WorkbookOutput } from '@/stores/useOutputs';
import { useNotifier } from '@/Widgets';
import Chat from './Chat.vue';
import SidebarMain from './Sidebar/Main.vue';
import PreviewPanel from './PreviewPanel.vue';
import type { PreviewItem } from './preview';

const props = defineProps<{
    profileName: string;
    workbookName: string;
}>();

const profiles = useProfilesStore();
const workbooks = useWorkbooksStore();
const outputs = useOutputs();
const { notify } = useNotifier();
const profileId = ref<number | null>(null);
const workbookId = ref<number | null>(null);
const loading = ref(true);
const loadError = ref('');
const narrowLayout = ref(false);
const leftWidth = ref(330);
const rightWidth = ref(360);
const rightCollapsed = ref(false);
const resizing = ref<'left' | 'right' | null>(null);
const previewTabs = ref<PreviewItem[]>([]);
const activePreviewId = ref<string | null>(null);
const displayWorkbookName = ref(props.workbookName);
const gridColumns = computed(() => narrowLayout.value
    ? `68px minmax(0, 1fr) ${rightCollapsed.value ? '44px' : '0px'}`
    : `${leftWidth.value}px 6px minmax(340px, 1fr) 6px ${rightCollapsed.value ? '44px' : `${rightWidth.value}px`}`);
let loadGeneration = 0;

function errorMessage(error: unknown): string {
    if (error instanceof ApiError) {
        return error.status === null ? error.message : `${error.message} (HTTP ${error.status})`;
    }
    return error instanceof Error ? error.message : String(error);
}

async function loadContext(): Promise<void> {
    const generation = ++loadGeneration;
    loading.value = true;
    loadError.value = '';
    profileId.value = null;
    workbookId.value = null;
    try {
        await profiles.fetchProfiles();
        if (generation !== loadGeneration) return;
        const profile = profiles.profiles.find((item) => item.name === props.profileName);
        if (!profile) throw new Error(`Profile "${props.profileName}" was not found.`);
        profileId.value = profile.id;
        await workbooks.fetchWorkbooks(profile.id);
        if (generation !== loadGeneration) return;
        const workbook = workbooks.workbooks.find((item) => item.title === props.workbookName);
        if (!workbook) throw new Error(`Workbook "${props.workbookName}" was not found.`);
        workbookId.value = workbook.id;
    } catch (error) {
        if (generation !== loadGeneration) return;
        loadError.value = errorMessage(error);
        notify(`Could not open workbook: ${loadError.value}`, 'error', 9000);
    } finally {
        if (generation === loadGeneration) loading.value = false;
    }
}

function updateLayout(): void {
    const previousNarrow = narrowLayout.value;
    narrowLayout.value = window.innerWidth < 1100;
    if (narrowLayout.value && !previousNarrow) rightCollapsed.value = true;
}

function startResize(panel: 'left' | 'right', event: PointerEvent): void {
    if (narrowLayout.value) return;
    resizing.value = panel;
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
    event.preventDefault();
}

function resizePanels(event: PointerEvent): void {
    if (!resizing.value) return;
    const centerMin = 360;
    if (resizing.value === 'left') {
        const max = Math.min(520, window.innerWidth - (rightCollapsed.value ? 44 : rightWidth.value) - centerMin - 24);
        leftWidth.value = Math.max(260, Math.min(max, event.clientX));
    } else {
        const max = Math.min(560, window.innerWidth - leftWidth.value - centerMin - 24);
        rightWidth.value = Math.max(260, Math.min(max, window.innerWidth - event.clientX));
    }
}

function stopResize(): void {
    resizing.value = null;
}

function resizeByKeyboard(panel: 'left' | 'right', event: KeyboardEvent): void {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
    event.preventDefault();
    const delta = event.key === 'ArrowRight' ? 16 : -16;
    if (panel === 'left') leftWidth.value = Math.max(260, Math.min(520, leftWidth.value + delta));
    else rightWidth.value = Math.max(260, Math.min(560, rightWidth.value - delta));
}

async function hydratePreviewMedia(item: PreviewItem): Promise<PreviewItem> {
    if (item.encoding !== 'utf-8' || item.content === null || !/\.html?$/i.test(item.name)) return item;
    if (outputs.outputs.length === 0 && profileId.value !== null && workbookId.value !== null) {
        await outputs.fetchOutputs(profileId.value, workbookId.value);
    }
    const document = new DOMParser().parseFromString(item.content, 'text/html');
    const mediaElements = document.querySelectorAll<HTMLImageElement | HTMLAudioElement | HTMLVideoElement | HTMLSourceElement>(
        'img[src], audio[src], video[src], source[src], video[poster]',
    );
    for (const element of mediaElements) {
        const attribute = element.hasAttribute('poster') ? 'poster' : 'src';
        const href = element.getAttribute(attribute);
        if (!href || /^(?:[a-z][a-z\d+.-]*:|\/\/|#|data:|blob:)/i.test(href)) continue;
        const path = normalizeLinkedPath(href, item.name);
        if (!path) continue;
        const output = outputs.outputs.find((candidate) => outputPath(candidate) === path);
        if (!output) continue;
        try {
            const content = await outputs.readOutput(profileId.value!, workbookId.value!, output.id);
            const url = content.encoding === 'base64'
                ? `data:${content.media_type};base64,${content.content_base64 ?? ''}`
                : `data:${content.media_type};charset=utf-8,${encodeURIComponent(content.content ?? '')}`;
            element.setAttribute(attribute, url);
        } catch {
            continue;
        }
    }
    return { ...item, content: document.documentElement.outerHTML };
}

async function openPreview(item: PreviewItem): Promise<void> {
    const previewItem = await hydratePreviewMedia(item);
    const index = previewTabs.value.findIndex((tab) => tab.id === previewItem.id);
    if (index === -1) previewTabs.value.push(previewItem);
    else previewTabs.value[index] = previewItem;
    activePreviewId.value = previewItem.id;
    rightCollapsed.value = false;
}

function outputPath(output: WorkbookOutput): string {
    return output.folder ? `${output.folder}/${output.name}` : output.name;
}

function normalizeLinkedPath(href: string, basePath = ''): string | null {
    if (/^(?:[a-z][a-z\d+.-]*:|\/\/|#)/i.test(href)) return null;
    let path = href.split(/[?#]/, 1)[0] ?? '';
    try {
        path = decodeURIComponent(path);
    } catch {
        return null;
    }
    const parts = path.startsWith('/') ? [] : basePath.split('/').slice(0, -1).filter(Boolean);
    for (const segment of path.replace(/^\/+/, '').split('/')) {
        if (!segment || segment === '.') continue;
        if (segment === '..') {
            if (!parts.length) return null;
            parts.pop();
        } else parts.push(segment);
    }
    const normalized = parts.join('/').replace(/^(?:outputs?|files?)\//i, '');
    return normalized || null;
}

async function openFileLink(href: string, basePath?: string): Promise<void> {
    const path = normalizeLinkedPath(href, basePath);
    if (!path || profileId.value === null || workbookId.value === null) return;
    try {
        await outputs.fetchOutputs(profileId.value, workbookId.value);
        const output = outputs.outputs.find((item) => outputPath(item) === path);
        if (!output) {
            notify(`No workbook output exists at ${path}.`, 'warning', 6000);
            return;
        }
        const content = await outputs.readOutput(profileId.value, workbookId.value, output.id);
        openPreview({
            id: `output-${output.id}`,
            name: outputPath(output),
            kind: 'output',
            mediaType: content.media_type,
            encoding: content.encoding,
            content: content.content,
            contentBase64: content.content_base64,
        });
    } catch (error) {
        notify(`Could not open ${path}: ${errorMessage(error)}`, 'error', 8000);
    }
}

function closePreview(id: string): void {
    const index = previewTabs.value.findIndex((tab) => tab.id === id);
    if (index === -1) return;
    previewTabs.value.splice(index, 1);
    if (activePreviewId.value === id) activePreviewId.value = previewTabs.value[Math.min(index, previewTabs.value.length - 1)]?.id ?? null;
}

function updateWorkbookName(title: string): void {
    displayWorkbookName.value = title;
}

watch(() => [props.profileName, props.workbookName], loadContext, { immediate: true });
watch(() => props.workbookName, (name) => { displayWorkbookName.value = name; });
onMounted(() => {
    updateLayout();
    window.addEventListener('resize', updateLayout);
    window.addEventListener('pointermove', resizePanels);
    window.addEventListener('pointerup', stopResize);
});
onUnmounted(() => {
    window.removeEventListener('resize', updateLayout);
    window.removeEventListener('pointermove', resizePanels);
    window.removeEventListener('pointerup', stopResize);
});

</script>

<template>
    <main class="workbook-grid" :class="{ 'workbook-grid-narrow': narrowLayout }" :style="{ gridTemplateColumns: gridColumns }">
        <SidebarMain
            v-if="profileId !== null && workbookId !== null"
            :profile-id="profileId"
            :workbook-id="workbookId"
            :profile-name="props.profileName"
            :workbook-name="displayWorkbookName"
            :narrow="narrowLayout"
            @open-preview="openPreview"
            @close-preview="closePreview"
            @workbook-updated="updateWorkbookName($event.title)"
        />
        <section v-else class="workspace-loading" aria-label="Workbook sections">
            <p role="status">{{ loading ? 'Resolving workbook…' : loadError }}</p>
        </section>

        <button v-if="!narrowLayout" type="button" role="separator" aria-orientation="vertical"
            aria-label="Resize workbook sidebar" :aria-valuenow="leftWidth" aria-valuemin="260" aria-valuemax="520"
            class="workbook-resizer" @pointerdown="startResize('left', $event)" @keydown="resizeByKeyboard('left', $event)" />

        <Chat
            v-if="profileId !== null && workbookId !== null"
            :profile-id="profileId"
            :workbook-id="workbookId"
            :profile-name="props.profileName"
            :workbook-name="displayWorkbookName"
            @open-file-link="openFileLink"
        />
        <section v-else class="workspace-loading" aria-label="Chat panel">
            <p role="status">{{ loading ? 'Resolving workbook…' : loadError }}</p>
        </section>

        <button v-if="!narrowLayout" type="button" role="separator" aria-orientation="vertical"
            aria-label="Resize preview panel" :aria-valuenow="rightWidth" aria-valuemin="260" aria-valuemax="560"
            class="workbook-resizer" @pointerdown="startResize('right', $event)" @keydown="resizeByKeyboard('right', $event)" />

        <PreviewPanel
            :tabs="previewTabs"
            :active-tab-id="activePreviewId"
            :collapsed="rightCollapsed"
            :narrow="narrowLayout"
            @activate="activePreviewId = $event"
            @close="closePreview"
            @toggle="rightCollapsed = !rightCollapsed"
            @open-file-link="openFileLink"
        />
    </main>
</template>

<style scoped>
.workbook-grid {
    display: grid;
    width: 100%;
    height: 100dvh;
    min-height: 500px;
    overflow: hidden;
    background: #eef2f0;
    gap: 1px;
}
.workbook-resizer { width: 6px; height: 100%; border: 0; background: #eef2f0; cursor: col-resize; touch-action: none; outline: none; }
.workbook-resizer:hover, .workbook-resizer:focus-visible { background: #74a59b; }
.workspace-loading {
    display: grid;
    min-width: 0;
    place-items: center;
    background: #fff;
    color: #677472;
    font-size: 13px;
}

@media (max-width: 1099px) {
    .workbook-grid { height: 100dvh; min-height: 0; }
}
</style>
