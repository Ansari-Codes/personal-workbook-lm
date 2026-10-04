<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from 'vue';
import { ApiError } from '@/stores/api';
import { useAPIKeys } from '@/stores/useAPIKeys';
import { useCallers } from '@/stores/useCallers';
import { useWorkbooksStore, type ChatConfiguration, type ChatSendPayload } from '@/stores/useWorkbooks';
import { useOutputs } from '@/stores/useOutputs';
import { useWorkbookSettings } from '@/stores/useWorkbookSettings';
import { useNotifier } from '@/Widgets';
import WButton from '@/Widgets/WButton.vue';
import ChatMessageBoxComp from '@/Comps/Workbook/ChatMessageBoxComp.vue';
import ChatMessageComp from '@/Comps/Workbook/ChatMessageComp.vue';
import type { ChatMessage } from '@/stores/useWorkbooks';
import ToolCallBadge from '@/Comps/Workbook/ToolCallBadge.vue'; // or wherever you put it
import ReasoningTimeline from '@/Comps/Workbook/ReasoningTimeline.vue';
import { normalizeWorkbookFilePath } from '@/utils/markdown';

type ChatDisplayEntry =
    | { kind: 'message'; key: string; message: ChatMessage }
    | { kind: 'tools' | 'reasoning'; key: string; messages: ChatMessage[] };

const props = defineProps<{
    profileId: number;
    workbookId: number;
    profileName: string;
    workbookName: string;
}>();
const emit = defineEmits<{
    openFileLink: [href: string, basePath?: string];
}>();

const workbookStore = useWorkbooksStore();
const outputStore = useOutputs();
const apiKeyStore = useAPIKeys();
const callerStore = useCallers();
const workbookSettings = useWorkbookSettings();
const { notify } = useNotifier();
const messages = computed(() => workbookStore.chatMessagesFor(props.profileId, props.workbookId));
const displayEntries = computed<ChatDisplayEntry[]>(() => {
    const turns: ChatMessage[][] = [];
    let currentTurn: ChatMessage[] = [];
    const orderedMessages = [...messages.value].sort((left, right) => left.id.localeCompare(right.id));
    for (const message of orderedMessages) {
        if (message.role === 'user' && currentTurn.length > 0) {
            turns.push(currentTurn);
            currentTurn = [];
        }
        currentTurn.push(message);
    }
    if (currentTurn.length > 0) turns.push(currentTurn);

    return turns.flatMap((turn, index) => {
        const turnKey = turn.find((message) => message.role === 'user')?.id ?? `turn-${index}`;
        const entries: ChatDisplayEntry[] = [];
        const users = turn.filter((message) => message.role === 'user');
        const toolGroups: ChatMessage[][] = [];
        let currentToolGroup: ChatMessage[] = [];
        for (const message of turn) {
            if (message.role === 'tool_call' || message.role === 'tool_output') {
                currentToolGroup.push(message);
            } else if (currentToolGroup.length > 0) {
                toolGroups.push(currentToolGroup);
                currentToolGroup = [];
            }
        }
        if (currentToolGroup.length > 0) toolGroups.push(currentToolGroup);
        const reasoning = turn.filter((message) => message.role === 'thinking' || message.role === 'reasoning');
        const remaining = turn.filter((message) =>
            message.role !== 'user'
            && message.role !== 'tool_call'
            && message.role !== 'tool_output'
            && message.role !== 'thinking'
            && message.role !== 'reasoning',
        );

        users.forEach((message) => entries.push({ kind: 'message', key: message.id, message }));
        toolGroups.forEach((group, groupIndex) => entries.push({
            kind: 'tools',
            key: `${turnKey}-tools-${groupIndex}`,
            messages: group,
        }));
        if (reasoning.length) entries.push({ kind: 'reasoning', key: `${turnKey}-reasoning`, messages: reasoning });
        remaining.forEach((message) => entries.push({ kind: 'message', key: message.id, message }));
        return entries;
    });
});
const configuration = ref<ChatConfiguration>(workbookStore.chatConfigurationFor(props.profileId, props.workbookId));
const isLoading = ref(true);
const isGenerating = ref(false);
const isReady = ref(false);
const loadError = ref('');
const scrollContainer = ref<HTMLElement | null>(null);
const mediaUrls = ref<Record<string, string>>({});
const objectUrls = new Map<number, string>();
let loadGeneration = 0;
let mediaLoadGeneration = 0;
let activeChatController: AbortController | null = null;

const apiKeysForMessage = computed(() => apiKeyStore.apiKeys.filter((key) =>
    workbookSettings.selectedApiKeyIds.includes(key.id),
));

const modelSelectionKey = computed(() => {
    const { apiKeyId, callerId, endpointName } = configuration.value;
    return apiKeyId === null || callerId === null ? '' : `${apiKeyId}:${callerId}:${endpointName}`;
});
const modelOptions = computed(() =>
    (apiKeyStore.modelsBySelection[modelSelectionKey.value] ?? []).map((model) => model.id),
);

function errorMessage(error: unknown): string {
    if (error instanceof ApiError) {
        return error.status === null ? error.message : `${error.message} (HTTP ${error.status})`;
    }
    return error instanceof Error ? error.message : String(error);
}

async function loadChat(): Promise<void> {
    const generation = ++loadGeneration;
    isLoading.value = true;
    isReady.value = false;
    loadError.value = '';
    try {
        await Promise.all([
            apiKeyStore.fetchAPIKeys(props.profileId),
            callerStore.fetchCallers(props.profileId),
            workbookSettings.fetchSettings(props.profileId, props.workbookId),
            workbookStore.fetchChatHistory(props.profileId, props.workbookId),
        ]);
        if (generation !== loadGeneration) return;
        try {
            await outputStore.fetchOutputs(props.profileId, props.workbookId);
        } catch (error) {
            notify(`Could not load workbook media: ${errorMessage(error)}`, 'warning', 7000);
        }
        if (generation !== loadGeneration) return;
        configuration.value = workbookStore.chatConfigurationFor(props.profileId, props.workbookId);
        if (!workbookSettings.selectedApiKeyIds.includes(configuration.value.apiKeyId ?? -1)) {
            configuration.value.apiKeyId = workbookSettings.selectedApiKeyIds[0] ?? null;
        }
        const selectedKey = apiKeyStore.apiKeys.find((key) => key.id === configuration.value.apiKeyId);
        const endpointNames = Object.keys(selectedKey?.endpoints ?? {});
        if (!endpointNames.includes(configuration.value.endpointName)) {
            configuration.value.endpointName = endpointNames.includes('chat') ? 'chat' : endpointNames[0] ?? '';
        }
        if (!callerStore.callers.some((caller) => caller.id === configuration.value.callerId)) {
            configuration.value.callerId = callerStore.callers.some((caller) => caller.id === workbookSettings.selectedCallerId)
                ? workbookSettings.selectedCallerId
                : callerStore.callers[0]?.id ?? null;
        }
        if (configuration.value.apiKeyId !== null && configuration.value.callerId !== null) {
            try {
                const models = await apiKeyStore.fetchModels(
                    props.profileId,
                    configuration.value.apiKeyId,
                    configuration.value.callerId,
                    configuration.value.endpointName,
                );
                if (!models.some((model) => model.id === configuration.value.model)) {
                    configuration.value.model = models[0]?.id ?? '';
                }
            } catch (error) {
                notify(`Could not load model list: ${errorMessage(error)}`, 'error', 7000);
            }
        }
        isReady.value = true;
    } catch (error) {
        if (generation !== loadGeneration) return;
        loadError.value = errorMessage(error);
        notify(`Could not load chat settings: ${loadError.value}`, 'error', 9000);
        configuration.value = workbookStore.chatConfigurationFor(props.profileId, props.workbookId);
        isReady.value = true;
    } finally {
        if (generation === loadGeneration) isLoading.value = false;
    }
}

async function handleSend(payload: ChatSendPayload): Promise<void> {
    if (!isReady.value || isGenerating.value) return;
    if (payload.apiKeyId === null) {
        notify('Select an API key for this workbook before sending a message.', 'error', 7000);
        return;
    }
    workbookStore.saveChatConfiguration(props.profileId, props.workbookId, {
        model: payload.model,
        apiKeyId: payload.apiKeyId,
        endpointName: payload.endpointName,
        temperature: payload.temperature,
        topP: payload.topP,
        contextLength: payload.contextLength,
        stream: payload.stream,
        allowHtml: payload.allowHtml,
        maxToolCalls: payload.maxToolCalls,
        additionalParameters: payload.additionalParameters,
        callerId: payload.callerId,
    });
    const controller = new AbortController();
    activeChatController = controller;
    isGenerating.value = true;
    try {
        await workbookStore.sendChatMessage(props.profileId, props.workbookId, payload, controller.signal);
        try {
            await outputStore.fetchOutputs(props.profileId, props.workbookId);
        } catch (error) {
            notify(`Could not refresh outputs: ${errorMessage(error)}`, 'warning', 7000);
        }
    } catch (error) {
        notify(`Could not generate a response: ${errorMessage(error)}`, 'error', 9000);
    } finally {
        if (activeChatController === controller) activeChatController = null;
        isGenerating.value = false;
    }
}

async function refreshResponseMedia(): Promise<void> {
    const generation = ++mediaLoadGeneration;
    const hrefs = new Set<string>();
    for (const message of messages.value) {
        if (message.role !== 'assistant') continue;
        const pattern = /!?\[[^\]]*\]\((?:<([^>]+)>|([^\s)]+))/g;
        for (const match of message.content.matchAll(pattern)) {
            const href = match[1] ?? match[2];
            if (href) hrefs.add(href);
        }
    }
    if (!hrefs.size) {
        mediaUrls.value = {};
        return;
    }
    if (props.profileId === undefined || props.workbookId === undefined) return;
    if (outputStore.outputs.length === 0) {
        try {
            await outputStore.fetchOutputs(props.profileId, props.workbookId);
        } catch {
            return;
        }
    }
    const resolved: Record<string, string> = {};
    for (const href of hrefs) {
        const path = normalizeWorkbookFilePath(href);
        if (!path) continue;
        const output = outputStore.outputs.find((item) => (item.folder ? `${item.folder}/${item.name}` : item.name) === path);
        if (!output || !/^(?:image|audio|video)\//.test(output.media_type)) continue;
        let url = objectUrls.get(output.id);
        if (!url) {
            try {
                const content = await outputStore.readOutput(props.profileId, props.workbookId, output.id);
                const blob = content.encoding === 'base64'
                    ? new Blob([Uint8Array.from(atob(content.content_base64 ?? ''), (character) => character.charCodeAt(0))], { type: content.media_type })
                    : new Blob([content.content ?? ''], { type: content.media_type });
                url = URL.createObjectURL(blob);
                objectUrls.set(output.id, url);
            } catch {
                continue;
            }
        }
        resolved[href] = url;
        resolved[path] = url;
    }
    if (generation === mediaLoadGeneration) mediaUrls.value = resolved;
}

function stopGeneration(): void {
    activeChatController?.abort();
}

async function clearChat(): Promise<void> {
    try {
        await workbookStore.clearChat(props.profileId, props.workbookId);
    } catch (error) {
        notify(`Could not clear chat: ${errorMessage(error)}`, 'error', 7000);
    }
}

watch(() => [configuration.value.apiKeyId, configuration.value.callerId, configuration.value.endpointName] as const, async ([apiKeyId, callerId, endpointName]) => {
    if (apiKeyId === null || callerId === null || !endpointName || !isReady.value) return;
    try {
        const models = await apiKeyStore.fetchModels(props.profileId, apiKeyId, callerId, endpointName);
        if (!models.some((model) => model.id === configuration.value.model)) {
            configuration.value.model = models[0]?.id ?? '';
        }
    } catch (error) {
        notify(`Could not load model list: ${errorMessage(error)}`, 'error', 7000);
    }
});

watch(configuration, (value) => {
    if (isReady.value) workbookStore.saveChatConfiguration(props.profileId, props.workbookId, value);
}, { deep: true });

watch(() => [props.profileId, props.workbookId], loadChat, { immediate: true });
watch(() => messages.value.map((message) => `${message.role}:${message.content}`).join('\n'), refreshResponseMedia, { immediate: true });
watch(() => outputStore.outputs.map((output) => `${output.id}:${output.updated_at}`).join(','), refreshResponseMedia);
watch(() => messages.value.map((message) => message.content.length), async () => {
    await nextTick();
    if (scrollContainer.value) scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight;
});

onUnmounted(() => {
    loadGeneration++;
    mediaLoadGeneration++;
    for (const url of objectUrls.values()) URL.revokeObjectURL(url);
    objectUrls.clear();
    activeChatController?.abort();
});
</script>

<template>
    <section class="flex h-full min-h-88 min-w-0 flex-col bg-neutral-50" aria-label="Chat panel">
        <header class="flex items-center justify-between gap-3 border-b border-neutral-200 bg-white px-4 py-3">
            <div class="min-w-0">
                <h2 class="truncate text-sm font-semibold text-neutral-950">{{ workbookName }}</h2>
                <p class="truncate text-xs text-neutral-500">{{ profileName }} · Chat</p>
            </div>
            <WButton size="sm" variant="ghost" :disabled="messages.length === 0 || isGenerating" @click="clearChat">Clear chat</WButton>
        </header>
        
        <!-- Remove the debug strip when done -->
        
        <div ref="scrollContainer" class="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-4" aria-live="polite">
            <div v-if="isLoading" class="m-auto text-sm text-neutral-500" role="status">Loading workbook chat…</div>
            <div v-else-if="loadError" class="m-auto text-sm text-rose-700" role="alert">{{ loadError }}</div>
            <div v-else-if="messages.length === 0" class="m-auto max-w-sm text-center">
                <p class="text-sm font-medium text-neutral-800">Start a conversation</p>
                <p class="mt-1 text-xs leading-5 text-neutral-500">Choose an API key, endpoint, caller, and model, then enter a prompt below.</p>
            </div>
            
            <template v-for="entry in displayEntries" :key="entry.key">
                <ChatMessageComp v-if="entry.kind === 'message'" :message="entry.message" :allow-html-preview="configuration.allowHtml" :media-urls="mediaUrls" @open-file-link="emit('openFileLink', $event)" />
                
                <!-- Replace WCollapsible with badges -->
                <ToolCallBadge v-else-if="entry.kind === 'tools'" :messages="entry.messages" />
                
                <!-- Replace WCollapsible with timeline -->
                <ReasoningTimeline v-else :messages="entry.messages" />
            </template>
        </div>

        <ChatMessageBoxComp
            v-model:configuration="configuration"
            :api-keys="apiKeysForMessage"
            :callers="callerStore.callers"
            :allowed-api-key-ids="workbookSettings.selectedApiKeyIds"
            :models="modelOptions"
            :is-generating="isGenerating"
            :disabled="isLoading || !isReady || isGenerating"
            @send="handleSend"
            @stop="stopGeneration"
        />
    </section>
</template>
