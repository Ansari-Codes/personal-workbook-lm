import { defineStore } from 'pinia';
import { ref } from 'vue';
import { apiRequest, apiStreamRequest } from '@/stores/api';

export interface Workbook {
  id: number;
  title: string;
  description: string;
  thumbnail?: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkbookCreate {
  title: string;
  description?: string;
  thumbnail?: string | null;
}

export type WorkbookUpdate = Partial<WorkbookCreate>;

export type ChatRole = 'tool_call' | 'tool_output' | 'thinking' | 'reasoning' | 'assistant' | 'system' | 'user' | 'error';

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
  metadata?: Record<string, unknown>;
}

export interface ChatConfiguration {
  callerId: number | null;
  model: string;
  apiKeyId: number | null;
  endpointName: string;
  temperature: number;
  topP: number;
  contextLength: number;
  stream: boolean;
  allowHtml: boolean;
  maxToolCalls: number | null;
  additionalParameters: string;
}

export interface ChatSendPayload extends ChatConfiguration {
  prompt: string;
}

interface ChatTurn {
  role: 'user' | 'assistant';
  content: string;
}

interface ChatCompletionResponse {
  role: 'assistant';
  content: string;
  model: string;
  usage: Record<string, unknown>;
  events: Array<{ role: 'tool_call' | 'tool_output' | 'thinking' | 'reasoning'; content: string; name: string }>;
}

interface ChatStreamEvent {
  type: 'token' | 'tool_call' | 'tool_output' | 'thinking' | 'reasoning' | 'done' | 'error';
  content?: string;
  role?: 'tool_call' | 'tool_output' | 'thinking' | 'reasoning';
  name?: string;
  model?: string;
  usage?: Record<string, unknown>;
  status?: number;
  message?: string;
}

interface StoredChatMessage {
  role: ChatRole;
  content: string;
  meta?: Record<string, unknown>;
  created_at: string;
}

const defaultChatConfiguration = (): ChatConfiguration => ({
  callerId: null,
  model: 'gpt-4o-mini',
  apiKeyId: null,
  endpointName: 'chat',
  temperature: 0.7,
  topP: 1,
  contextLength: 20,
  stream: false,
  allowHtml: false,
  maxToolCalls: 4,
  additionalParameters: '{}',
});

function sortableMessageId(createdAt: string, sequence: number): string {
  const timestamp = Date.parse(createdAt);
  const timeKey = String(Number.isNaN(timestamp) ? Date.now() : timestamp).padStart(13, '0');
  return `${timeKey}-${String(sequence).padStart(8, '0')}`;
}

export const useWorkbooksStore = defineStore('workbooks', () => {
  const workbooks = ref<Workbook[]>([]);
  const chats = ref<Record<string, ChatMessage[]>>({});
  const chatConfigurations = ref<Record<string, ChatConfiguration>>({});
  const hydratedChats = new Set<string>();
  let nextMessageId = 1;

  function chatKey(profileId: number, workbookId: number): string {
    return `${profileId}:${workbookId}`;
  }

  function storageKey(key: string): string {
    return `pawm.workbook-chat.${key}`;
  }

  function ensureChat(profileId: number, workbookId: number): string {
    const key = chatKey(profileId, workbookId);
    if (hydratedChats.has(key)) return key;
    hydratedChats.add(key);

    if (typeof localStorage !== 'undefined') {
      try {
        const saved = localStorage.getItem(storageKey(key));
        if (saved) {
          const parsed = JSON.parse(saved) as {
            messages?: ChatMessage[];
            configuration?: Partial<ChatConfiguration>;
          };
          chats.value[key] = Array.isArray(parsed.messages)
            ? parsed.messages.map((message, index) => ({
              ...message,
              id: sortableMessageId(message.createdAt, index),
            }))
            : [];
          const savedConfiguration = { ...parsed.configuration };
          delete (savedConfiguration as Partial<ChatConfiguration> & { topK?: number }).topK;
          const defaults = defaultChatConfiguration();
          const savedHistoryCount = savedConfiguration.contextLength;
          const savedMaxToolCalls = savedConfiguration.maxToolCalls;
          chatConfigurations.value[key] = {
            ...defaults,
            ...savedConfiguration,
            contextLength: typeof savedHistoryCount === 'number'
              ? Math.min(100, Math.max(0, Math.floor(savedHistoryCount)))
              : defaults.contextLength,
            maxToolCalls: savedMaxToolCalls === null
              ? null
              : typeof savedMaxToolCalls === 'number' && Number.isSafeInteger(savedMaxToolCalls) && savedMaxToolCalls > 0
                ? savedMaxToolCalls
                : defaults.maxToolCalls,
          };
          return key;
        }
      } catch {
        localStorage.removeItem(storageKey(key));
      }
    }

    chats.value[key] ??= [];
    chatConfigurations.value[key] ??= defaultChatConfiguration();
    return key;
  }

  function persistChat(key: string): void {
    if (typeof localStorage === 'undefined') return;
    try {
      localStorage.setItem(storageKey(key), JSON.stringify({
        messages: chats.value[key] ?? [],
        configuration: chatConfigurations.value[key] ?? defaultChatConfiguration(),
      }));
    } catch {
      // Keep the active chat usable if browser storage is unavailable or full.
    }
  }

  function chatMessagesFor(profileId: number, workbookId: number): ChatMessage[] {
    return chats.value[ensureChat(profileId, workbookId)]!;
  }

  function chatConfigurationFor(profileId: number, workbookId: number): ChatConfiguration {
    return chatConfigurations.value[ensureChat(profileId, workbookId)]!;
  }

  function saveChatConfiguration(
    profileId: number,
    workbookId: number,
    configuration: ChatConfiguration,
  ): void {
    const key = ensureChat(profileId, workbookId);
    Object.assign(chatConfigurations.value[key]!, configuration);
    persistChat(key);
  }

  function addChatMessage(
    profileId: number,
    workbookId: number,
    role: ChatRole,
    content: string,
    metadata?: Record<string, unknown>,
  ): ChatMessage {
    const key = ensureChat(profileId, workbookId);
    const createdAt = new Date().toISOString();
    const message: ChatMessage = {
      id: sortableMessageId(createdAt, nextMessageId++),
      role,
      content,
      createdAt,
      ...(metadata ? { metadata } : {}),
    };
    chats.value[key]!.push(message);
    persistChat(key);
    return chats.value[key]![chats.value[key]!.length - 1]!;
  }

  async function fetchChatHistory(profileId: number, workbookId: number): Promise<void> {
    const key = ensureChat(profileId, workbookId);
    const history = await apiRequest<StoredChatMessage[]>(
      `/profiles/${profileId}/workbooks/${workbookId}/chat`,
    );
    chats.value[key] = (history ?? []).map((message, index) => ({
      id: sortableMessageId(message.created_at, index),
      role: message.role,
      content: message.content,
      createdAt: message.created_at,
      ...(message.meta ? { metadata: message.meta } : {}),
    }));
    persistChat(key);
  }

  async function clearChat(profileId: number, workbookId: number): Promise<void> {
    const key = ensureChat(profileId, workbookId);
    await apiRequest<null>(`/profiles/${profileId}/workbooks/${workbookId}/chat`, 'DELETE');
    chats.value[key] = [];
    persistChat(key);
  }

  async function fetchWorkbooks(profileId: number): Promise<void> {
    const data = await apiRequest<Workbook[]>(`/profiles/${profileId}/workbooks`);
    workbooks.value = data ?? [];
  }

  async function createWorkbook(
    profileId: number,
    payload: WorkbookCreate,
  ): Promise<Workbook | null> {
    const workbook = await apiRequest<Workbook>(
      `/profiles/${profileId}/workbooks`,
      'POST',
      payload,
    );
    if (workbook) workbooks.value.push(workbook);
    return workbook;
  }

  async function updateWorkbook(
    profileId: number,
    workbookId: number,
    payload: WorkbookUpdate,
  ): Promise<Workbook | null> {
    const workbook = await apiRequest<Workbook>(
      `/profiles/${profileId}/workbooks/${workbookId}`,
      'PATCH',
      payload,
    );
    if (workbook) {
      const index = workbooks.value.findIndex((item) => item.id === workbookId);
      if (index !== -1) workbooks.value[index] = workbook;
    }
    return workbook;
  }

  async function deleteWorkbook(profileId: number, workbookId: number): Promise<void> {
    await apiRequest<null>(`/profiles/${profileId}/workbooks/${workbookId}`, 'DELETE');
    workbooks.value = workbooks.value.filter((item) => item.id !== workbookId);
  }

  function clearWorkbooks(): void {
    workbooks.value = [];
  }

  async function sendChatMessage(
    profileId: number,
    workbookId: number,
    payload: ChatSendPayload,
    signal?: AbortSignal,
  ): Promise<void> {
    const key = ensureChat(profileId, workbookId);
    const recentMessages: ChatTurn[] = chats.value[key]!
      .filter((message): message is ChatMessage & { role: 'user' | 'assistant' } =>
        (message.role === 'user' || message.role === 'assistant') && Boolean(message.content.trim()),
      )
      .slice(-100)
      .map(({ role, content }) => ({ role, content }));
    const historyLimit = Math.min(100, Math.max(0, Math.floor(payload.contextLength)));
    const history = historyLimit === 0 ? [] : recentMessages.slice(-historyLimit);
    addChatMessage(profileId, workbookId, 'user', payload.prompt, {
      model: payload.model,
      apiKeyId: payload.apiKeyId,
      temperature: payload.temperature,
      topP: payload.topP,
      contextLength: payload.contextLength,
      stream: payload.stream,
      maxToolCalls: payload.maxToolCalls,
    });

    const url = `/profiles/${profileId}/workbooks/${workbookId}/chat`;
    let assistantMessage: ChatMessage | null = null;
    try {
      const additionalParameters = JSON.parse(payload.additionalParameters || '{}') as Record<string, unknown>;
      const requestBody = {
        model: payload.model,
        api_key_id: payload.apiKeyId,
        endpoint_name: payload.endpointName,
        caller_id: payload.callerId,
        temperature: payload.temperature,
        top_p: payload.topP,
        context_length: payload.contextLength,
        max_tool_calls: payload.maxToolCalls,
        stream: payload.stream,
        prompt: payload.prompt,
        ...(Object.keys(additionalParameters).length
          ? { additional_parameters: additionalParameters }
          : {}),
        history,
      };
      if (!payload.stream) {
        const response = await apiRequest<ChatCompletionResponse, typeof requestBody>(
          url,
          'POST',
          requestBody,
          {},
          signal,
          null,
        );
        if (!response) throw new Error('The chat response was empty.');
        for (const event of response.events) {
          addChatMessage(profileId, workbookId, event.role, event.content, { name: event.name });
        }
        addChatMessage(profileId, workbookId, 'assistant', response.content, {
          model: response.model,
          usage: response.usage,
          apiKeyId: payload.apiKeyId,
        });
        return;
      }
      assistantMessage = payload.stream
        ? addChatMessage(profileId, workbookId, 'assistant', '', {
          model: payload.model,
          apiKeyId: payload.apiKeyId,
          streaming: true,
        })
        : null;
      const bufferedEvents: ChatStreamEvent[] = [];
      let fullAnswer = '';
      let receivedDone = false;
      let reasoningMessage: ChatMessage | null = null;
      await apiStreamRequest<ChatStreamEvent, typeof requestBody>(url, {
          ...requestBody,
          stream: true,
        }, (event) => {
          if (event.type === 'token' && event.content) {
            fullAnswer += event.content;
            if (!assistantMessage) return;
            assistantMessage.content += event.content;
            persistChat(key);
          } else if ((event.type === 'thinking' || event.type === 'reasoning') && event.content) {
            if (!assistantMessage) {
              bufferedEvents.push(event);
              return;
            }
            reasoningMessage ??= addChatMessage(profileId, workbookId, event.type, '', { name: event.name ?? 'Reasoning' });
            reasoningMessage.content += event.content;
            persistChat(key);
          } else if ((event.type === 'tool_call' || event.type === 'tool_output') && event.role && event.content) {
            if (!assistantMessage) {
              bufferedEvents.push(event);
              return;
            }
            addChatMessage(profileId, workbookId, event.role, event.content, { name: event.name });
          } else if (event.type === 'done') {
            receivedDone = true;
            if (assistantMessage) {
              assistantMessage.metadata = {
                ...assistantMessage.metadata,
                model: event.model ?? payload.model,
                usage: event.usage ?? {},
                streaming: false,
              };
              persistChat(key);
            } else {
              for (const bufferedEvent of bufferedEvents) {
                if ((bufferedEvent.type === 'tool_call' || bufferedEvent.type === 'tool_output') && bufferedEvent.role && bufferedEvent.content) {
                  addChatMessage(profileId, workbookId, bufferedEvent.role, bufferedEvent.content, { name: bufferedEvent.name });
                } else if ((bufferedEvent.type === 'thinking' || bufferedEvent.type === 'reasoning') && bufferedEvent.content) {
                  reasoningMessage ??= addChatMessage(profileId, workbookId, bufferedEvent.type, '', { name: bufferedEvent.name ?? 'Reasoning' });
                  reasoningMessage.content += bufferedEvent.content;
                }
              }
              addChatMessage(profileId, workbookId, 'assistant', fullAnswer, {
                model: event.model ?? payload.model,
                usage: event.usage ?? {},
                apiKeyId: payload.apiKeyId,
              });
            }
          } else if (event.type === 'error') {
            throw new Error(event.message ?? `Chat stream failed (HTTP ${event.status ?? 502})`);
          }
        }, signal);
      if (!receivedDone) throw new Error('The chat stream ended before completion.');
    } catch (error) {
      if (signal?.aborted) {
        if (assistantMessage) {
          assistantMessage.metadata = { ...assistantMessage.metadata, streaming: false, stopped: true };
          persistChat(key);
        }
        addChatMessage(profileId, workbookId, 'system', 'Generation stopped.');
        return;
      }
      const message = error instanceof Error ? error.message : String(error);
      addChatMessage(profileId, workbookId, 'error', message);
      throw error;
    }
  }

  return {
    workbooks,
    chats,
    chatConfigurations,
    chatMessagesFor,
    chatConfigurationFor,
    saveChatConfiguration,
    addChatMessage,
    fetchWorkbooks,
    createWorkbook,
    updateWorkbook,
    deleteWorkbook,
    clearWorkbooks,
    fetchChatHistory,
    clearChat,
    sendChatMessage,
  };
});
