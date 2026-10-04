<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { ApiError } from '@/stores/api';
import { useOutputs, type WorkbookOutput, type WorkbookOutputContent } from '@/stores/useOutputs';
import { useNotifier } from '@/Widgets';
import WButton from '@/Widgets/WButton.vue';
import WDialog from '@/Widgets/WDialog.vue';
import WInput from '@/Widgets/WInput.vue';
import WTextarea from '@/Widgets/WTextarea.vue';
import WIcon from '@/Widgets/WIcon.vue';
import WMenu from '@/Widgets/WMenu.vue';
import WSelect from '@/Widgets/WSelect.vue';
import WOption from '@/Widgets/WOption.vue';
import { useWorkbookSettings } from '@/stores/useWorkbookSettings';
import type { PreviewItem } from '../preview';

const props = defineProps<{ profileId: number; workbookId: number }>();
const emit = defineEmits<{
    openPreview: [item: PreviewItem];
    closePreview: [id: string];
}>();
const outputStore = useOutputs();
const settings = useWorkbookSettings();
const { notify } = useNotifier();
const isLoading = ref(true);
const loadError = ref('');
const filter = ref('');
const selectedOutput = ref<WorkbookOutput | null>(null);
const selectedContent = ref<WorkbookOutputContent | null>(null);
const isEditOpen = ref(false);
const isCreateOpen = ref(false);
const isDeleteOpen = ref(false);
const isSaving = ref(false);
const isCreating = ref(false);
const actionOutputId = ref<number | null>(null);
const name = ref('');
const description = ref('');
const content = ref('');
const replacementFile = ref<File | null>(null);
const newFileName = ref('');
const newFileFolder = ref('');
const newFileContent = ref('');
const expandedPaths = ref(new Set<string>());
const isFolderDialogOpen = ref(false);
const isMoveDialogOpen = ref(false);
const folderName = ref('');
const folderParent = ref('');
const targetFolder = ref('');
const isFolderSaving = ref(false);
let loadGeneration = 0;

interface OutputFolderNode {
    name: string;
    path: string;
    folders: Map<string, OutputFolderNode>;
    outputs: WorkbookOutput[];
}

type OutputTreeRow =
    | { type: 'folder'; label: string; path: string; depth: number }
    | { type: 'output'; output: WorkbookOutput; depth: number };

const filteredOutputs = computed(() => {
    const value = filter.value.trim().toLocaleLowerCase();
    return value ? outputStore.outputs.filter((output) => `${output.name} ${output.description}`.toLocaleLowerCase().includes(value)) : outputStore.outputs;
});
const outputFolderChoices = computed(() => {
    const folders = new Set(settings.outputFolders);
    for (const output of outputStore.outputs) {
        const segments = output.folder.split('/').filter(Boolean);
        for (let index = 1; index <= segments.length; index++) folders.add(segments.slice(0, index).join('/'));
    }
    return [...folders].sort((a, b) => a.localeCompare(b));
});
const outputTreeRows = computed<OutputTreeRow[]>(() => {
    const rows: OutputTreeRow[] = [];
    const rootNode: OutputFolderNode = { name: '', path: '', folders: new Map(), outputs: [] };
    const allPaths = [
        ...settings.outputFolders,
        ...filteredOutputs.value.map((output) => output.folder).filter(Boolean),
    ];
    for (const fullPath of allPaths) {
        let parent = rootNode;
        let path = '';
        for (const segment of fullPath.split('/').filter(Boolean)) {
            path = path ? `${path}/${segment}` : segment;
            let child = parent.folders.get(segment);
            if (!child) {
                child = { name: segment, path, folders: new Map(), outputs: [] };
                parent.folders.set(segment, child);
            }
            parent = child;
        }
    }
    for (const output of filteredOutputs.value) {
        if (!output.folder) rootNode.outputs.push(output);
        else {
            let parent = rootNode;
            for (const segment of output.folder.split('/').filter(Boolean)) {
                const child = parent.folders.get(segment);
                if (!child) break;
                parent = child;
            }
            parent.outputs.push(output);
        }
    }
    const addChildren = (node: OutputFolderNode, depth: number): void => {
        for (const child of [...node.folders.values()].sort((a, b) => a.name.localeCompare(b.name))) {
            rows.push({ type: 'folder', label: child.name, path: child.path, depth });
            if (expandedPaths.value.has(`folder:${child.path}`)) addChildren(child, depth + 1);
        }
        for (const output of [...node.outputs].sort((a, b) => a.name.localeCompare(b.name))) rows.push({ type: 'output', output, depth });
    };
    addChildren(rootNode, 0);
    return rows;
});

function errorMessage(error: unknown): string {
    if (error instanceof ApiError) return error.status === null ? error.message : `${error.message} (HTTP ${error.status})`;
    return error instanceof Error ? error.message : String(error);
}

function formatSize(size: number): string {
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

async function loadOutputs(): Promise<void> {
    const generation = ++loadGeneration;
    isLoading.value = true;
    loadError.value = '';
    try {
        await outputStore.fetchOutputs(props.profileId, props.workbookId);
    } catch (error) {
        if (generation !== loadGeneration) return;
        loadError.value = errorMessage(error);
    } finally {
        if (generation === loadGeneration) isLoading.value = false;
    }
}

async function readOutput(output: WorkbookOutput): Promise<WorkbookOutputContent | null> {
    actionOutputId.value = output.id;
    try {
        const result = await outputStore.readOutput(props.profileId, props.workbookId, output.id);
        selectedOutput.value = output;
        selectedContent.value = result;
        return result;
    } catch (error) {
        notify(`Could not read output: ${errorMessage(error)}`, 'error', 9000);
        return null;
    } finally {
        actionOutputId.value = null;
    }
}

async function openOutput(output: WorkbookOutput): Promise<void> {
    const data = await readOutput(output);
    if (!data) return;
    emit('openPreview', { id: `output-${output.id}`, name: data.name, kind: 'output', mediaType: data.media_type, encoding: data.encoding, content: data.content, contentBase64: data.content_base64 });
}

function downloadContent(data: WorkbookOutputContent): void {
    const fileData = data.encoding === 'base64'
        ? Uint8Array.from(atob(data.content_base64 ?? ''), (character) => character.charCodeAt(0)).buffer
        : data.content ?? '';
    const url = URL.createObjectURL(new Blob([fileData], { type: data.media_type }));
    const link = document.createElement('a');
    link.href = url;
    link.download = data.name;
    link.click();
    URL.revokeObjectURL(url);
}

async function downloadOutput(output: WorkbookOutput): Promise<void> {
    const data = await readOutput(output);
    if (data) downloadContent(data);
}

async function openEditor(output: WorkbookOutput): Promise<void> {
    const data = await readOutput(output);
    if (!data) return;
    name.value = data.name;
    description.value = data.description;
    content.value = data.content ?? '';
    replacementFile.value = null;
    isEditOpen.value = true;
}

function onReplacementFile(event: Event): void {
    replacementFile.value = (event.target as HTMLInputElement).files?.[0] ?? null;
}

async function saveOutput(): Promise<void> {
    if (!selectedOutput.value || !selectedContent.value) return;
    isSaving.value = true;
    try {
        if (selectedContent.value.encoding === 'base64' && replacementFile.value) {
            await outputStore.replaceOutputFile(props.profileId, props.workbookId, selectedOutput.value.id, replacementFile.value);
        }
        await outputStore.updateOutput(props.profileId, props.workbookId, selectedOutput.value.id, {
            name: name.value.trim(),
            description: description.value.trim(),
            ...(selectedContent.value.encoding === 'utf-8' ? { content: content.value } : {}),
        });
        isEditOpen.value = false;
        notify('Output updated.', 'success', 4500);
    } catch (error) {
        notify(`Could not update output: ${errorMessage(error)}`, 'error', 9000);
    } finally {
        isSaving.value = false;
    }
}

async function createOutput(): Promise<void> {
    if (!newFileName.value.trim()) {
        notify('A file name is required.', 'warning', 5000);
        return;
    }
    isCreating.value = true;
    try {
        await outputStore.createOutput(props.profileId, props.workbookId, {
            name: newFileName.value.trim(),
            folder: newFileFolder.value,
            content: newFileContent.value,
        });
        isCreateOpen.value = false;
        newFileName.value = '';
        newFileFolder.value = '';
        newFileContent.value = '';
        notify('File created.', 'success', 4500);
    } catch (error) {
        notify(`Could not create file: ${errorMessage(error)}`, 'error', 9000);
    } finally {
        isCreating.value = false;
    }
}

async function deleteOutput(): Promise<void> {
    if (!selectedOutput.value) return;
    actionOutputId.value = selectedOutput.value.id;
    try {
        await outputStore.deleteOutput(props.profileId, props.workbookId, selectedOutput.value.id);
        emit('closePreview', `output-${selectedOutput.value.id}`);
        isDeleteOpen.value = false;
        selectedContent.value = null;
        notify('Output deleted.', 'success', 4500);
    } catch (error) {
        notify(`Could not delete output: ${errorMessage(error)}`, 'error', 9000);
    } finally {
        actionOutputId.value = null;
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
    const folderSegment = folderName.value.trim();
    if (!folderSegment || folderSegment === '.' || folderSegment === '..' || /[\\/]/.test(folderSegment)) {
        notify('Enter a folder name without path separators.', 'warning', 5000);
        return;
    }
    const path = folderParent.value ? `${folderParent.value}/${folderSegment}` : folderSegment;
    if (outputFolderChoices.value.includes(path)) {
        notify('That folder already exists.', 'warning', 5000);
        return;
    }
    const previous = [...settings.outputFolders];
    settings.outputFolders = [...previous, path].sort((a, b) => a.localeCompare(b));
    isFolderSaving.value = true;
    try {
        await settings.saveSettings(props.profileId, props.workbookId);
        expandedPaths.value = new Set([...expandedPaths.value, ...(folderParent.value ? [`folder:${folderParent.value}`] : []), `folder:${path}`]);
        isFolderDialogOpen.value = false;
        notify('Folder created.', 'success', 4000);
    } catch (error) {
        settings.outputFolders = previous;
        notify(`Could not create folder: ${errorMessage(error)}`, 'error', 8000);
    } finally {
        isFolderSaving.value = false;
    }
}

function openMoveDialog(output: WorkbookOutput): void {
    selectedOutput.value = output;
    targetFolder.value = output.folder;
    isMoveDialogOpen.value = true;
}

async function moveOutput(): Promise<void> {
    if (!selectedOutput.value || selectedOutput.value.folder === targetFolder.value) {
        isMoveDialogOpen.value = false;
        return;
    }
    isFolderSaving.value = true;
    try {
        await outputStore.updateOutput(props.profileId, props.workbookId, selectedOutput.value.id, { folder: targetFolder.value });
        isMoveDialogOpen.value = false;
        notify('Output moved.', 'success', 4000);
    } catch (error) {
        notify(`Could not move output: ${errorMessage(error)}`, 'error', 8000);
    } finally {
        isFolderSaving.value = false;
    }
}

watch(() => [props.profileId, props.workbookId], loadOutputs, { immediate: true });
</script>

<template>
    <section class="tab-content" aria-label="Workbook outputs">
        <header class="tab-toolbar">
            <WInput v-model="filter" type="search" aria-label="Filter outputs" placeholder="Filter outputs" />
            <WButton size="sm" variant="ghost" :disabled="isLoading" aria-label="Refresh outputs" title="Refresh outputs" @click="loadOutputs"><WIcon name="refresh" /></WButton>
            <WButton size="sm" aria-label="Create output file" title="New file" @click="isCreateOpen = true"><WIcon name="note_add" /></WButton>
            <WButton size="sm" variant="secondary" aria-label="Create output folder" title="Create folder" @click="openFolderDialog()"><WIcon name="create_new_folder" /></WButton>
        </header>
        <p v-if="isLoading" class="state-message" role="status">Loading outputs…</p>
        <div v-else-if="loadError" class="state-error" role="alert"><p>{{ loadError }}</p><WButton size="sm" variant="ghost" @click="loadOutputs">Retry</WButton></div>
        <div v-else class="item-list" role="tree" aria-label="Output folders and files">
            <div v-for="row in outputTreeRows" :key="row.type === 'output' ? `output-${row.output.id}` : `folder-${row.path}`" class="tree-row" :style="{ '--tree-depth': row.depth }">
                <template v-if="row.type === 'folder'">
                    <WButton variant="ghost" size="sm" role="treeitem" :aria-expanded="expandedPaths.has(`folder:${row.path}`)" class="tree-label" @click="toggleTreePath(`folder:${row.path}`)">
                        <WIcon :name="expandedPaths.has(`folder:${row.path}`) ? 'folder_open' : 'folder'" :size="16" /><span>{{ row.label }}</span>
                    </WButton>
                    <WMenu :trigger-label="`Actions for ${row.label}`"><template #trigger><WIcon name="more_vert" :size="18" /></template>
                        <WButton variant="ghost" size="sm" role="menuitem" class="menu-item" @click="openFolderDialog(row.path)"><WIcon name="create_new_folder" :size="16" />New subfolder</WButton>
                    </WMenu>
                </template>
                <template v-else>
                    <WButton variant="ghost" size="sm" role="treeitem" class="tree-label tree-file" :disabled="actionOutputId === row.output.id" @click="openOutput(row.output)">
                        <WIcon :name="row.output.media_type.startsWith('image/') ? 'image' : 'draft'" :size="16" /><span>{{ row.output.name }}</span>
                    </WButton>
                    <WMenu :trigger-label="`Actions for ${row.output.name}`"><template #trigger><WIcon name="more_vert" :size="18" /></template>
                        <WButton variant="ghost" size="sm" role="menuitem" class="menu-item" :disabled="actionOutputId === row.output.id" @click="openOutput(row.output)"><WIcon name="open_in_new" :size="16" />Open</WButton>
                        <WButton variant="ghost" size="sm" role="menuitem" class="menu-item" :disabled="actionOutputId === row.output.id" @click="openEditor(row.output)"><WIcon name="edit" :size="16" />Update</WButton>
                        <WButton variant="ghost" size="sm" role="menuitem" class="menu-item" @click="openMoveDialog(row.output)"><WIcon name="drive_file_move" :size="16" />Move to folder</WButton>
                        <WButton variant="ghost" size="sm" role="menuitem" class="menu-item" :disabled="actionOutputId === row.output.id" @click="downloadOutput(row.output)"><WIcon name="download" :size="16" />Download</WButton>
                        <WButton variant="ghost" size="sm" role="menuitem" class="menu-item text-rose-700" :disabled="actionOutputId === row.output.id" @click="selectedOutput = row.output; isDeleteOpen = true"><WIcon name="delete" :size="16" />Delete</WButton>
                    </WMenu>
                </template>
            </div>
        </div>
    </section>

    <WDialog v-model="isCreateOpen" title="New output file" description="Create a text file in this workbook.">
        <div class="grid gap-4">
            <WInput v-model="newFileName" label="File name" placeholder="home.html" maxlength="255" required />
            <WSelect v-model="newFileFolder" label="Folder">
                <WOption value="">Root</WOption>
                <WOption v-for="folder in outputFolderChoices" :key="folder" :value="folder">{{ folder }}</WOption>
            </WSelect>
            <WTextarea v-model="newFileContent" label="Content" />
        </div>
        <template #footer><WButton variant="secondary" :disabled="isCreating" @click="isCreateOpen = false">Cancel</WButton><WButton :loading="isCreating" @click="createOutput">Create file</WButton></template>
    </WDialog>

    <WDialog v-model="isEditOpen" title="Update output" description="Text outputs can be edited here; binary files can be replaced.">
        <div class="grid gap-4">
            <WInput v-model="name" label="File name" maxlength="255" required />
            <WTextarea v-model="description" label="Description" />
            <WTextarea v-if="selectedContent?.encoding === 'utf-8'" v-model="content" label="Text content" />
            <label v-else class="grid gap-2 text-sm font-medium text-neutral-700"><span>Replacement file (optional, up to 50 MB)</span><input type="file" class="w-full text-sm" @change="onReplacementFile" /><span v-if="replacementFile" class="text-xs font-normal text-neutral-500">{{ replacementFile.name }}</span></label>
        </div>
        <template #footer><WButton variant="secondary" :disabled="isSaving" @click="isEditOpen = false">Cancel</WButton><WButton :loading="isSaving" @click="saveOutput">Save changes</WButton></template>
    </WDialog>

    <WDialog v-model="isDeleteOpen" title="Delete output">
        <p class="text-sm text-neutral-700">Delete <strong>{{ selectedOutput?.name }}</strong> and its stored file?</p>
        <template #footer><WButton variant="secondary" :disabled="actionOutputId !== null" @click="isDeleteOpen = false">Cancel</WButton><WButton variant="danger" :loading="actionOutputId !== null" @click="deleteOutput">Delete output</WButton></template>
    </WDialog>

    <WDialog v-model="isFolderDialogOpen" title="Create folder">
        <div class="grid gap-3">
            <p v-if="folderParent" class="text-xs text-neutral-500">Parent: {{ folderParent }}</p>
            <WInput v-model="folderName" label="Folder name" maxlength="120" required />
        </div>
        <template #footer><WButton variant="secondary" :disabled="isFolderSaving" @click="isFolderDialogOpen = false">Cancel</WButton><WButton :loading="isFolderSaving" @click="createFolder">Create folder</WButton></template>
    </WDialog>

    <WDialog v-model="isMoveDialogOpen" title="Move output">
        <p class="mb-3 text-sm text-neutral-600">Choose a folder for <strong>{{ selectedOutput?.name }}</strong>.</p>
        <WSelect v-model="targetFolder" label="Destination">
            <WOption value="">Root</WOption>
            <WOption v-for="folder in outputFolderChoices" :key="folder" :value="folder">{{ folder }}</WOption>
        </WSelect>
        <template #footer><WButton variant="secondary" :disabled="isFolderSaving" @click="isMoveDialogOpen = false">Cancel</WButton><WButton :loading="isFolderSaving" @click="moveOutput">Move output</WButton></template>
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
.tree-file { color: #3f4947; font-weight: 400; }
.menu-item { display: flex; width: 100%; justify-content: flex-start; gap: 8px; border-radius: 2px; padding-inline: 8px; }
.state-message, .state-error { padding: 12px 4px; color: #687573; font-size: 13px; line-height: 1.6; }
.state-error { color: #a32b2b; }
</style>