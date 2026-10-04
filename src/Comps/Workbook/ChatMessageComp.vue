<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { renderMarkdown } from '@/utils/markdown';
import { useNotifier } from '@/Widgets';
import WIcon from '@/Widgets/WIcon.vue';
import type { ChatMessage } from '@/stores/useWorkbooks';

const props = defineProps<{ message: ChatMessage; allowHtmlPreview?: boolean; mediaUrls?: Record<string, string> }>();
const emit = defineEmits<{ openFileLink: [href: string] }>();
const { notify } = useNotifier();
const isCopying = ref(false);
const htmlFrame = ref<HTMLIFrameElement | null>(null);
const renderedContent = computed(() => renderMarkdown(props.message.content, props.mediaUrls));
const htmlSnippet = computed(() => props.message.content.match(/```html\s*\n([\s\S]*?)```/i)?.[1]?.trim() ?? '');
const previewDocument = computed(() => {
  if (!htmlSnippet.value) return '';
  const policy = '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src data: blob: https:; media-src data: blob: https:; style-src \'unsafe-inline\' https:; script-src \'unsafe-inline\' https:; font-src data: https:; connect-src \'none\'">';
  const bridge = '<scr' + 'ipt>document.addEventListener(\'click\',function(event){var link=event.target.closest(\'a[href]\');if(!link)return;var href=link.getAttribute(\'href\');if(!href||/^(?:[a-z][a-z\\d+.-]*:|\\/\\/|#)/i.test(href))return;event.preventDefault();parent.postMessage({type:\'pawm-chat-link\',href:href},\'*\')});</scr' + 'ipt>';
  const source = htmlSnippet.value;
  let document = source;
  if (/<head\b[^>]*>/i.test(document)) document = document.replace(/<head\b[^>]*>/i, (head) => `${head}${policy}`);
  else if (/<html\b[^>]*>/i.test(document)) document = document.replace(/<html\b[^>]*>/i, (html) => `${html}<head>${policy}</head>`);
  else document = `<!doctype html><html><head>${policy}</head><body>${document}</body></html>`;
  return /<\/body\s*>/i.test(document)
    ? document.replace(/<\/body\s*>/i, `${bridge}</body>`)
    : document.replace(/<\/html\s*>/i, `${bridge}</html>`);
});

const roleLabels: Record<ChatMessage['role'], string> = {
  tool_call: 'Tool call',
  tool_output: 'Tool output',
  thinking: 'Thinking',
  reasoning: 'Reasoning',
  assistant: 'Assistant',
  system: 'System',
  user: 'You',
  error: 'Error',
};

function formatTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? ''
    : new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(date);
}

async function copyResponse(): Promise<void> {
  if (isCopying.value) return;
  isCopying.value = true;
  try {
    await navigator.clipboard.writeText(props.message.content);
    notify('Response copied.', 'success', 3000);
  } catch {
    notify('Could not copy response. Check clipboard permissions.', 'error', 5000);
  } finally {
    isCopying.value = false;
  }
}

function onMarkdownClick(event: MouseEvent): void {
  if (!(event.target instanceof Element)) return;
  const link = event.target.closest<HTMLAnchorElement>('a[href]');
  const href = link?.getAttribute('href');
  if (!href || /^(?:[a-z][a-z\d+.-]*:|\/\/|#)/i.test(href)) return;
  event.preventDefault();
  emit('openFileLink', href);
}

function onPreviewMessage(event: MessageEvent): void {
  if (event.source !== htmlFrame.value?.contentWindow || event.data?.type !== 'pawm-chat-link') return;
  if (typeof event.data.href === 'string') emit('openFileLink', event.data.href);
}

onMounted(() => window.addEventListener('message', onPreviewMessage));
onUnmounted(() => window.removeEventListener('message', onPreviewMessage));
</script>

<template>
  <article
    :data-role="message.role"
    :class="[
      'border px-3 py-2.5',
      message.role === 'user' ? 'ml-auto border-neutral-300 bg-neutral-100 text-neutral-950' : '',
      message.role === 'assistant' ? 'mx-auto w-full max-w-5xl border-neutral-200 bg-white text-neutral-900' : '',
      message.role === 'user' ? 'max-w-[92%] sm:max-w-[85%]' : '',
      message.role === 'system' || message.role === 'thinking' || message.role === 'reasoning' ? 'mx-auto border-transparent bg-transparent text-neutral-500' : '',
      message.role === 'tool_call' ? 'ml-4 border-amber-200 bg-amber-50 text-amber-950' : '',
      message.role === 'tool_output' ? 'ml-4 border-neutral-200 bg-neutral-100 text-neutral-800' : '',
      message.role === 'error' ? 'mr-auto border-rose-200 bg-rose-50 text-rose-900' : '',
    ]"
  >
    <header class="mb-1 flex items-center justify-between gap-4 text-[11px] font-semibold uppercase text-neutral-500">
      <span class="flex items-center gap-1.5">
        <span v-if="message.role === 'thinking'" class="size-1.5 animate-pulse rounded-full bg-green-700" aria-hidden="true" />
        {{ roleLabels[message.role] }}
      </span>
      <span class="flex shrink-0 items-center gap-2 font-normal normal-case">
        <time v-if="message.role !== 'thinking'">{{ formatTime(message.createdAt) }}</time>
        <button
          v-if="message.role === 'assistant' && message.content"
          type="button"
          class="font-semibold text-green-800 hover:text-green-950 focus-visible:outline-none focus-visible:underline disabled:opacity-50"
          :disabled="isCopying"
          title="Copy response"
          aria-label="Copy response"
          @click="copyResponse"
        >Copy</button>
      </span>
    </header>
    <iframe
      v-if="message.role === 'assistant' && allowHtmlPreview && previewDocument"
      ref="htmlFrame"
      :srcdoc="previewDocument"
      :title="`Sandboxed HTML preview: ${message.createdAt}`"
      sandbox="allow-scripts allow-forms allow-popups allow-modals"
      referrerpolicy="no-referrer"
      class="html-response-preview"
    />
    <div v-else class="rich-markdown wrap-break-word text-sm leading-6" v-html="renderedContent" @click="onMarkdownClick" />
    <p v-if="message.metadata?.model" class="mt-2 text-[11px] text-neutral-500">{{ message.metadata.model }}</p>
  </article>
</template>

<style scoped>
.html-response-preview { width: 100%; min-height: 280px; border: 1px solid #dce4e1; background: white; }
.rich-markdown :deep(img), .rich-markdown :deep(video), .rich-markdown :deep(audio) { display: block; max-width: 100%; margin-block: 8px; }
.rich-markdown :deep(img) { max-height: 420px; object-fit: contain; }
</style>
