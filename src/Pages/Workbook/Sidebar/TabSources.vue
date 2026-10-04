<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { ApiError } from '@/stores/api';
import { useSources, type Source } from '@/stores/useSources';
import { useNotifier } from '@/Widgets';
import WButton from '@/Widgets/WButton.vue';
import WDialog from '@/Widgets/WDialog.vue';
import WInput from '@/Widgets/WInput.vue';
import WTextarea from '@/Widgets/WTextarea.vue';
import WIcon from '@/Widgets/WIcon.vue';
import WMenu from '@/Widgets/WMenu.vue';
import WCheck from '@/Widgets/WCheck.vue';
import WSelect from '@/Widgets/WSelect.vue';
import WOption from '@/Widgets/WOption.vue';
import { useWorkbookSettings } from '@/stores/useWorkbookSettings';
import type { PreviewItem } from '../preview';

const props = defineProps<{ profileId: number; workbookId: number }>();
const emit = defineEmits<{
    openPreview: [item: PreviewItem];
    closePreview: [id: string];
}>();

type SourceMode = 'file' | 'url' | 'content';
const sourceStore = useSources();
const settings = useWorkbookSettings();
const { notify } = useNotifier();
const mode = ref<SourceMode>('file');
const query = ref('');
const isLoading = ref(true);
const isAdding = ref(false);
const loadError = ref('');
const dialogError = ref('');
const isAddOpen = ref(false);
const isEditOpen = ref(false);
const isDeleteOpen = ref(false);
const name = ref('');
const description = ref('');
const url = ref('');
const content = ref('');
const file = ref<File | null>(null);
const downloadUrl = ref(true);
const selectedSourceFolder = ref('');
const selectedSource = ref<Source | null>(null);
const actionSourceId = ref<number | null>(null);
const expandedPaths = ref(new Set(['root:Sources']));
const isFolderDialogOpen = ref(false);
const isMoveDialogOpen = ref(false);
const folderName = ref('');
const folderParent = ref('');
const targetFolder = ref('');
const isFolderSaving = ref(false);
let loadRequest = 0;

interface SourceFolderNode {
    name: string;
    path: string;
    folders: Map<string, SourceFolderNode>;
    sources: Source[];
}

type SourceTreeRow =
    | { type: 'root'; root: string; label: string; count: number; depth: number }
    | { type: 'folder'; root: string; label: string; path: string; depth: number }
    | { type: 'source'; root: string; source: Source; depth: number };

const filteredSources = computed(() => {
    const value = query.value.trim().toLocaleLowerCase();
    return value
        ? sourceStore.sources.filter((source) => `${source.name} ${source.description} ${source.kind} ${source.source_url ?? ''}`.toLocaleLowerCase().includes(value))
        : sourceStore.sources;
});
const knownSourceFolders = computed(() => {
    const folders = new Set(settings.sourceFolders);
    for (const source of sourceStore.sources) {
        const segments = source.folder.split('/').filter(Boolean);
        for (let index = 1; index <= segments.length; index++) folders.add(segments.slice(0, index).join('/'));
    }
    return [...folders].sort((a, b) => a.localeCompare(b));
});
const creationFolderOptions = computed(() => ['', ...knownSourceFolders.value]);
const moveFolderOptions = computed(() => ['', ...knownSourceFolders.value]);
const sourceTreeRows = computed<SourceTreeRow[]>(() => {
    const rows: SourceTreeRow[] = [];
    const rootNode: SourceFolderNode = { name: 'Sources', path: 'Sources', folders: new Map(), sources: [] };
    const allPaths = [
        ...settings.sourceFolders,
        ...filteredSources.value.map((source) => source.folder).filter(Boolean),
    ];

    for (const fullPath of allPaths) {
        let parent = rootNode;
        let path = '';
        for (const segment of fullPath.split('/').filter(Boolean)) {
            path = path ? `${path}/${segment}` : segment;
            let child = parent.folders.get(segment);
            if (!child) {
                child = { name: segment, path, folders: new Map(), sources: [] };
                parent.folders.set(segment, child);
            }
            parent = child;
        }
    }

    for (const source of filteredSources.value) {
        if (!source.folder) rootNode.sources.push(source);
        else {
            let parent = rootNode;
            for (const segment of source.folder.split('/').filter(Boolean)) {
                const child = parent.folders.get(segment);
                if (!child) break;
                parent = child;
            }
            parent.sources.push(source);
        }
    }

    rows.push({ type: 'root', root: 'Sources', label: 'Sources', count: filteredSources.value.length, depth: 0 });
    if (!expandedPaths.value.has('root:Sources')) return rows;

    const addChildren = (node: SourceFolderNode, depth: number): void => {
        for (const child of [...node.folders.values()].sort((a, b) => a.name.localeCompare(b.name))) {
            rows.push({ type: 'folder', root: 'Sources', label: child.name, path: child.path, depth });
            if (expandedPaths.value.has(`folder:${child.path}`)) addChildren(child, depth + 1);
        }
        for (const source of [...node.sources].sort((a, b) => a.name.localeCompare(b.name))) {
            rows.push({ type: 'source', root: 'Sources', source, depth });
        }
    };
    addChildren(rootNode, 1);
    return rows;
});

function errorMessage(error: unknown): string {
    if (error instanceof ApiError) return error.status === null ? error.message : `${error.message} (HTTP ${error.status})`;
    return error instanceof Error ? error.message : String(error);
}

async function loadSources(): Promise<void> {
    const request = ++loadRequest;
    isLoading.value = true;
    loadError.value = '';
    try {
        await sourceStore.fetchSources(props.profileId, props.workbookId);
    } catch (error) {
        if (request !== loadRequest) return;
        loadError.value = errorMessage(error);
        notify(`Could not load sources: ${loadError.value}`, 'error', 9000);
    } finally {
        if (request === loadRequest) isLoading.value = false;
    }
}

function resetAddForm(): void {
    name.value = '';
    description.value = '';
    url.value = '';
    content.value = '';
    file.value = null;
    downloadUrl.value = true;
    selectedSourceFolder.value = '';
    dialogError.value = '';
    mode.value = 'file';
}

function onFileChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    file.value = input.files?.[0] ?? null;
    if (file.value && !name.value.trim()) name.value = file.value.name;
    if (file.value && file.value.size > 10 * 1024 * 1024) {
        dialogError.value = 'Files must be 10 MB or smaller.';
        file.value = null;
        input.value = '';
    } else dialogError.value = '';
}

async function addSource(): Promise<void> {
    const cleanName = name.value.trim();
    if (!cleanName) {
        dialogError.value = 'A source name is required.';
        return;
    }
    isAdding.value = true;
    dialogError.value = '';
    try {
        if (mode.value === 'file') {
            if (!file.value) throw new Error('Choose a local file first.');
            await sourceStore.uploadSource(props.profileId, props.workbookId, { name: cleanName, description: description.value.trim(), file: file.value, folder: selectedSourceFolder.value });
        } else if (mode.value === 'url') {
            const cleanUrl = url.value.trim();
            if (!/^https?:\/\//i.test(cleanUrl)) throw new Error('Enter a valid HTTP or HTTPS URL.');
            await sourceStore.addUrlSource(props.profileId, props.workbookId, { name: cleanName, description: description.value.trim(), url: cleanUrl, download: downloadUrl.value, folder: selectedSourceFolder.value });
        } else {
            if (!content.value.trim()) throw new Error('Source text cannot be empty.');
            await sourceStore.addContentSource(props.profileId, props.workbookId, { name: cleanName, description: description.value.trim(), content: content.value, folder: selectedSourceFolder.value });
        }
        isAddOpen.value = false;
        resetAddForm();
        notify('Source added.', 'success', 4500);
    } catch (error) {
        dialogError.value = errorMessage(error);
    } finally {
        isAdding.value = false;
    }
}

function openEdit(source: Source): void {
    selectedSource.value = source;
    name.value = source.name;
    description.value = source.description;
    dialogError.value = '';
    isEditOpen.value = true;
}

async function saveSource(): Promise<void> {
    if (!selectedSource.value) return;
    isAdding.value = true;
    try {
        await sourceStore.updateSource(props.profileId, props.workbookId, selectedSource.value.id, { name: name.value.trim(), description: description.value.trim() });
        isEditOpen.value = false;
        notify('Source updated.', 'success', 4500);
    } catch (error) {
        dialogError.value = errorMessage(error);
    } finally {
        isAdding.value = false;
    }
}

async function openPreview(source: Source): Promise<void> {
    actionSourceId.value = source.id;
    try {
        const result = await sourceStore.previewSource(props.profileId, props.workbookId, source.id);
        emit('openPreview', { id: `source-${source.id}`, name: result.name, kind: 'source', mediaType: 'text/plain', encoding: 'utf-8', content: result.content, contentBase64: null, truncated: result.truncated });
    } catch (error) {
        notify(`Could not read source: ${errorMessage(error)}`, 'error', 9000);
    } finally {
        actionSourceId.value = null;
    }
}

async function redownload(source: Source): Promise<void> {
    actionSourceId.value = source.id;
    try {
        await sourceStore.redownloadSource(props.profileId, props.workbookId, source.id);
        notify('Source downloaded again.', 'success', 4500);
    } catch (error) {
        notify(`Could not download source: ${errorMessage(error)}`, 'error', 9000);
    } finally {
        actionSourceId.value = null;
    }
}

function askDelete(source: Source): void {
    selectedSource.value = source;
    isDeleteOpen.value = true;
}

async function deleteSource(): Promise<void> {
    if (!selectedSource.value) return;
    actionSourceId.value = selectedSource.value.id;
    try {
        await sourceStore.deleteSource(props.profileId, props.workbookId, selectedSource.value.id);
        emit('closePreview', `source-${selectedSource.value.id}`);
        isDeleteOpen.value = false;
        notify('Source removed.', 'success', 4500);
    } catch (error) {
        notify(`Could not remove source: ${errorMessage(error)}`, 'error', 9000);
    } finally {
        actionSourceId.value = null;
    }
}

function toggleTreePath(key: string): void {
    const next = new Set(expandedPaths.value);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    expandedPaths.value = next;
}

function openFolderDialog(parent = ''): void {
    folderParent.value = parent;
    folderName.value = '';
    isFolderDialogOpen.value = true;
}

async function createFolder(): Promise<void> {
    const name = folderName.value.trim();
    if (!name || name === '.' || name === '..' || /[\\/]/.test(name)) {
        notify('Enter a folder name without path separators.', 'warning', 5000);
        return;
    }
    const path = folderParent.value ? `${folderParent.value}/${name}` : name;
    if (knownSourceFolders.value.includes(path)) {
        notify('That folder already exists.', 'warning', 5000);
        return;
    }
    const previous = [...settings.sourceFolders];
    settings.sourceFolders = [...previous, path].sort((a, b) => a.localeCompare(b));
    isFolderSaving.value = true;
    try {
        await settings.saveSettings(props.profileId, props.workbookId);
        expandedPaths.value = new Set([...expandedPaths.value, 'root:Sources', ...(folderParent.value ? [`folder:${folderParent.value}`] : []), `folder:${path}`]);
        isFolderDialogOpen.value = false;
        notify('Folder created.', 'success', 4000);
    } catch (error) {
        settings.sourceFolders = previous;
        notify(`Could not create folder: ${errorMessage(error)}`, 'error', 8000);
    } finally {
        isFolderSaving.value = false;
    }
}

function openMoveDialog(source: Source): void {
    selectedSource.value = source;
    targetFolder.value = source.folder;
    isMoveDialogOpen.value = true;
}

async function moveSource(): Promise<void> {
    if (!selectedSource.value || selectedSource.value.folder === targetFolder.value) {
        isMoveDialogOpen.value = false;
        return;
    }
    isFolderSaving.value = true;
    try {
        await sourceStore.updateSource(props.profileId, props.workbookId, selectedSource.value.id, { folder: targetFolder.value });
        isMoveDialogOpen.value = false;
        notify('Source moved.', 'success', 4000);
    } catch (error) {
        notify(`Could not move source: ${errorMessage(error)}`, 'error', 8000);
    } finally {
        isFolderSaving.value = false;
    }
}

watch(() => [props.profileId, props.workbookId], loadSources, { immediate: true });
</script>

<template>
    <section class="tab-content" aria-label="Workbook sources">
        <header class="tab-toolbar">
            <WInput v-model="query" type="search" aria-label="Filter sources" placeholder="Filter sources" />
            <WButton size="sm" :disabled="isLoading" aria-label="Add source" title="Add source" @click="isAddOpen = true"><WIcon name="add" /></WButton>
            <WButton size="sm" variant="secondary" aria-label="Create source folder" title="Create folder" @click="openFolderDialog()"><WIcon name="create_new_folder" /></WButton>
        </header>
        <div v-if="isLoading" class="state-message" role="status">Loading sources…</div>
        <div v-else-if="loadError" class="state-error" role="alert">{{ loadError }} <WButton variant="ghost" size="sm" @click="loadSources">Retry</WButton></div>
        <div v-else class="item-list" role="tree" aria-label="Source folders and files">
            <div v-for="row in sourceTreeRows" :key="row.type === 'source' ? `source-${row.source.id}` : `${row.type}-${row.type === 'root' ? row.root : row.path}`" class="tree-row" :style="{ '--tree-depth': row.depth }">
                <template v-if="row.type === 'root'">
                    <WButton variant="ghost" size="sm" role="treeitem" :aria-expanded="expandedPaths.has(`root:${row.root}`)" class="tree-label tree-root" @click="toggleTreePath(`root:${row.root}`)">
                        <WIcon :name="expandedPaths.has(`root:${row.root}`) ? 'folder_open' : 'folder'" :size="17" />
                        <span>{{ row.label }}</span><small>{{ row.count }}</small>
                    </WButton>
                    <WMenu :trigger-label="`Actions for ${row.label}`"><template #trigger><WIcon name="more_vert" :size="18" /></template>
                        <WButton variant="ghost" size="sm" role="menuitem" class="menu-item" @click="openFolderDialog()"><WIcon name="create_new_folder" :size="16" />New folder</WButton>
                    </WMenu>
                </template>
                <template v-else-if="row.type === 'folder'">
                    <WButton variant="ghost" size="sm" role="treeitem" :aria-expanded="expandedPaths.has(`folder:${row.path}`)" class="tree-label" @click="toggleTreePath(`folder:${row.path}`)">
                        <WIcon :name="expandedPaths.has(`folder:${row.path}`) ? 'folder_open' : 'folder'" :size="16" /><span>{{ row.label }}</span>
                    </WButton>
                    <WMenu :trigger-label="`Actions for ${row.label}`"><template #trigger><WIcon name="more_vert" :size="18" /></template>
                        <WButton variant="ghost" size="sm" role="menuitem" class="menu-item" @click="openFolderDialog(row.path)"><WIcon name="create_new_folder" :size="16" />New subfolder</WButton>
                    </WMenu>
                </template>
                <template v-else>
                    <WButton variant="ghost" size="sm" role="treeitem" class="tree-label tree-file" :disabled="actionSourceId === row.source.id" @click="openPreview(row.source)">
                        <WIcon :name="row.source.kind === 'link' ? 'link' : 'description'" :size="16" /><span>{{ row.source.name }}</span>
                    </WButton>
                    <WMenu :trigger-label="`Actions for ${row.source.name}`"><template #trigger><WIcon name="more_vert" :size="18" /></template>
                        <WButton variant="ghost" size="sm" role="menuitem" class="menu-item" :disabled="actionSourceId === row.source.id" @click="openPreview(row.source)"><WIcon name="open_in_new" :size="16" />Open</WButton>
                        <WButton variant="ghost" size="sm" role="menuitem" class="menu-item" @click="openEdit(row.source)"><WIcon name="edit" :size="16" />Update</WButton>
                        <WButton variant="ghost" size="sm" role="menuitem" class="menu-item" @click="openMoveDialog(row.source)"><WIcon name="drive_file_move" :size="16" />Move to folder</WButton>
                        <WButton v-if="row.source.kind === 'link'" variant="ghost" size="sm" role="menuitem" class="menu-item" :disabled="actionSourceId === row.source.id" @click="redownload(row.source)"><WIcon name="download" :size="16" />Download again</WButton>
                        <WButton variant="ghost" size="sm" role="menuitem" class="menu-item text-rose-700" @click="askDelete(row.source)"><WIcon name="delete" :size="16" />Delete</WButton>
                    </WMenu>
                </template>
            </div>
        </div>
    </section>

    <WDialog v-model="isAddOpen" title="Add source" description="Add a file, URL, or text to this workbook.">
        <div class="grid gap-4">
            <div class="grid grid-cols-3 border border-neutral-200 p-1" role="group" aria-label="Source type">
                <WButton v-for="option in (['file', 'url', 'content'] as const)" :key="option" size="sm" :variant="mode === option ? 'primary' : 'ghost'" :aria-pressed="mode === option" @click="mode = option">{{ option === 'content' ? 'Text' : option }}</WButton>
            </div>
            <WInput v-model="name" label="Name" maxlength="255" required />
            <WTextarea v-model="description" label="Description" />
            <WSelect v-model="selectedSourceFolder" label="Folder">
                <WOption v-for="folder in creationFolderOptions" :key="folder || 'root'" :value="folder">{{ folder || 'Sources (root)' }}</WOption>
            </WSelect>
            <label v-if="mode === 'file'" class="grid gap-2 text-sm font-medium text-neutral-700">
                <span>File (up to 10 MB)</span><input type="file" class="w-full text-sm" @change="onFileChange" />
                <span v-if="file" class="text-xs font-normal text-neutral-500">{{ file.name }}</span>
            </label>
            <template v-else-if="mode === 'url'">
                <WInput v-model="url" label="HTTP or HTTPS URL" type="url" placeholder="https://example.com/source" />
                <WCheck v-model="downloadUrl">Download a local copy now</WCheck>
            </template>
            <WTextarea v-else v-model="content" label="Text content" />
            <p v-if="dialogError" role="alert" class="text-sm text-rose-700">{{ dialogError }}</p>
        </div>
        <template #footer>
            <WButton variant="secondary" :disabled="isAdding" @click="isAddOpen = false">Cancel</WButton>
            <WButton :loading="isAdding" @click="addSource">Add source</WButton>
        </template>
    </WDialog>

    <WDialog v-model="isFolderDialogOpen" title="Create folder">
        <div class="grid gap-3">
            <p v-if="folderParent" class="text-xs text-neutral-500">Parent: {{ folderParent }}</p>
            <p v-else class="text-xs text-neutral-500">In Sources</p>
            <WInput v-model="folderName" label="Folder name" maxlength="120" required />
        </div>
        <template #footer><WButton variant="secondary" :disabled="isFolderSaving" @click="isFolderDialogOpen = false">Cancel</WButton><WButton :loading="isFolderSaving" @click="createFolder">Create folder</WButton></template>
    </WDialog>

    <WDialog v-model="isMoveDialogOpen" title="Move source">
        <p class="mb-3 text-sm text-neutral-600">Choose a folder for <strong>{{ selectedSource?.name }}</strong>.</p>
        <WSelect v-model="targetFolder" label="Destination">
            <WOption value="">Sources (root)</WOption>
            <WOption v-for="folder in moveFolderOptions.slice(1)" :key="folder" :value="folder">{{ folder }}</WOption>
        </WSelect>
        <template #footer><WButton variant="secondary" :disabled="isFolderSaving" @click="isMoveDialogOpen = false">Cancel</WButton><WButton :loading="isFolderSaving" @click="moveSource">Move source</WButton></template>
    </WDialog>

    <WDialog v-model="isEditOpen" title="Update source">
        <div class="grid gap-4"><WInput v-model="name" label="Name" maxlength="255" /><WTextarea v-model="description" label="Description" /><p v-if="dialogError" role="alert" class="text-sm text-rose-700">{{ dialogError }}</p></div>
        <template #footer><WButton variant="secondary" :disabled="isAdding" @click="isEditOpen = false">Cancel</WButton><WButton :loading="isAdding" @click="saveSource">Save</WButton></template>
    </WDialog>

    <WDialog v-model="isDeleteOpen" title="Delete source" description="This also deletes its stored local copy.">
        <p class="text-sm text-neutral-700">Delete <strong>{{ selectedSource?.name }}</strong> from this workbook?</p>
        <template #footer><WButton variant="secondary" :disabled="actionSourceId !== null" @click="isDeleteOpen = false">Cancel</WButton><WButton variant="danger" :loading="actionSourceId !== null" @click="deleteSource">Delete source</WButton></template>
    </WDialog>
</template>

<style scoped>
.tab-content { display: flex; height: 100%; min-height: 0; flex-direction: column; gap: 10px; overflow: hidden; padding: 12px; }
.tab-toolbar { display: flex; align-items: center; gap: 8px; }
.tab-toolbar :deep(label) { min-width: 0; flex: 1; }
.item-list { min-height: 0; flex: 1; overflow: auto; border-top: 1px solid #e7ebea; padding: 4px 0; }
.tree-row { display: flex; min-width: 0; align-items: center; gap: 2px; padding-left: calc(var(--tree-depth) * 14px); }
.tree-label { min-width: 0; min-height: 32px; flex: 1; justify-content: flex-start; gap: 7px; overflow: hidden; border: 0; padding-inline: 6px; text-align: left; }
.tree-label > span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tree-root { font-weight: 650; }
.tree-root small { margin-left: auto; color: #737d7b; font-size: 10px; font-weight: 400; }
.tree-file { color: #3f4947; font-weight: 400; }
.menu-item { display: flex; width: 100%; justify-content: flex-start; gap: 8px; border-radius: 2px; padding-inline: 8px; }
.empty-state, .state-message, .state-error { padding: 16px 4px; color: #687573; font-size: 13px; line-height: 1.6; }
.empty-state p { color: #273331; font-weight: 600; }
.empty-state small { color: #687573; }
.state-error { color: #a32b2b; }
</style>