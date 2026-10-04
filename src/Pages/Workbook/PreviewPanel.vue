<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { renderMarkdown } from '@/utils/markdown';
import WIcon from '@/Widgets/WIcon.vue';
import WButton from '@/Widgets/WButton.vue';
import type { PreviewItem } from './preview';

const props = defineProps<{
    tabs: PreviewItem[];
    activeTabId: string | null;
    collapsed: boolean;
    narrow?: boolean;
}>();
const emit = defineEmits<{
    activate: [id: string];
    close: [id: string];
    toggle: [];
    openFileLink: [href: string, basePath: string];
}>();
const htmlFrame = ref<HTMLIFrameElement | null>(null);

const activeItem = computed(
    () => props.tabs.find((item) => item.id === props.activeTabId) ?? null,
);

/* ── Data URL for base64 items (used by img/audio/video/pdf iframe) ── */
const dataUrl = computed(() => {
    const item = activeItem.value;
    if (!item || item.encoding !== 'base64') return '';
    return `data:${item.mediaType};base64,${item.contentBase64 ?? ''}`;
});

/* ── Type detection ── */
const isImage = computed(() => activeItem.value?.mediaType.startsWith('image/') ?? false);
const isAudio = computed(() => activeItem.value?.mediaType.startsWith('audio/') ?? false);
const isVideo = computed(() => activeItem.value?.mediaType.startsWith('video/') ?? false);
const isPdf   = computed(() => activeItem.value?.mediaType === 'application/pdf');

/* ── Code vs Markdown vs plain text ── */
const CODE_MIME = /(?:^|\/)(?:x-)?(?:python|javascript|typescript|jsx|tsx|java|c\+\+|csharp|go|rust|ruby|php|swift|kotlin|sql|shell|bash|sh|yaml|yml|toml|xml|json|css|scss|less|html?)$/i;
const isCode = computed(() => {
    const m = activeItem.value?.mediaType ?? '';
    return CODE_MIME.test(m) || /\.(ts|tsx|js|jsx|py|rb|go|rs|java|c|cpp|h|hpp|cs|php|swift|kt|sql|sh|bash|zsh|yml|yaml|toml|json|css|scss|less)$/i.test(activeItem.value?.name ?? '');
});

/* Map mime/extension → highlight.js language */
const hlLang = computed(() => {
    const item = activeItem.value;
    if (!item) return 'plaintext';
    const name = item.name.toLowerCase();
    const extMap: Record<string, string> = {
        py: 'python', js: 'javascript', mjs: 'javascript', cjs: 'javascript',
        ts: 'typescript', tsx: 'typescript', jsx: 'javascript',
        rb: 'ruby', go: 'go', rs: 'rust', java: 'java',
        c: 'c', h: 'c', cpp: 'cpp', hpp: 'cpp', cc: 'cpp',
        cs: 'csharp', php: 'php', swift: 'swift', kt: 'kotlin',
        sql: 'sql', sh: 'bash', bash: 'bash', zsh: 'bash',
        yml: 'yaml', yaml: 'yaml', toml: 'ini', json: 'json',
        css: 'css', scss: 'scss', less: 'less',
        html: 'xml', htm: 'xml', xml: 'xml', svg: 'xml',
    };
    const ext = name.split('.').pop() ?? '';
    return extMap[ext] ?? 'plaintext';
});

/* ── HTML live preview (iframe srcdoc) ── */
const isHtml = computed(
    () => activeItem.value?.mediaType === 'text/html'
        || /\.html?$/i.test(activeItem.value?.name ?? ''),
);

/* ── Render helpers ── */
const activeText = computed(() => {
    const item = activeItem.value;
    if (!item || item.encoding !== 'utf-8' || item.content == null) return '';
    // Markdown files → markdown renderer
    if (item.mediaType === 'text/markdown' || /\.md$/i.test(item.name)) {
        return renderMarkdown(item.content);
    }
    // Code files → highlighted code block
    if (isCode.value) {
        try {
            // highlight.js is loaded globally
            const hljs = (window as any).hljs;
            if (hljs) {
                const highlighted = hljs.getLanguage(hlLang.value)
                    ? hljs.highlight(item.content, { language: hlLang.value }).value
                    : hljs.highlightAuto(item.content).value;
                return `<pre class="code-block"><code class="hljs language-${hlLang.value}">${highlighted}</code></pre>`;
            }
        } catch { /* fall through */ }
        return `<pre class="code-block"><code>${escapeHtml(item.content)}</code></pre>`;
    }
    // Plain text / anything else → markdown (safe, renders line breaks)
    return renderMarkdown(item.content);
});

function escapeHtml(s: string) {
    return s.replace(/[&<>"']/g, (c) =>
        ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] as string),
    );
}

/* ── HTML srcDoc — wrap in a minimal doc so styles/scripts run ── */
const htmlSrcDoc = computed(() => {
    const item = activeItem.value;
    if (!item || item.encoding !== 'utf-8' || item.content == null) return '';
    // If the user already supplied a full HTML document, use it as-is.
    const bridge = '<scr' + 'ipt>document.addEventListener(\'click\',function(event){var link=event.target.closest(\'a[href]\');if(!link)return;var href=link.getAttribute(\'href\');if(!href||/^(?:[a-z][a-z\\d+.-]*:|\\/\\/|#)/i.test(href))return;event.preventDefault();parent.postMessage({type:\'pawm-preview-link\',href:href},\'*\')});</scr' + 'ipt>';
    if (/<\/body\s*>/i.test(item.content)) return item.content.replace(/<\/body\s*>/i, `${bridge}</body>`);
    if (/<html[\s>]/i.test(item.content)) return item.content.replace(/<\/html\s*>/i, `${bridge}</html>`);
    return `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
        body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;padding:16px;color:#17212b;}
        a{color:#15803d}
    </style></head><body>${item.content}${bridge}</body></html>`;
});

function onPreviewMessage(event: MessageEvent): void {
    if (event.source !== htmlFrame.value?.contentWindow || event.data?.type !== 'pawm-preview-link') return;
    if (typeof event.data.href === 'string' && activeItem.value) emit('openFileLink', event.data.href, activeItem.value.name);
}

function onDocumentClick(event: MouseEvent): void {
    if (!(event.target instanceof Element)) return;
    const link = event.target.closest<HTMLAnchorElement>('a[href]');
    const href = link?.getAttribute('href');
    if (!href || /^(?:[a-z][a-z\d+.-]*:|\/\/|#)/i.test(href)) return;
    event.preventDefault();
    if (activeItem.value) emit('openFileLink', href, activeItem.value.name);
}

onMounted(() => window.addEventListener('message', onPreviewMessage));
onUnmounted(() => window.removeEventListener('message', onPreviewMessage));
</script>

<template>
    <aside
        class="preview-panel"
        :class="{ 'preview-panel-collapsed': collapsed, 'preview-panel-narrow': narrow }"
        aria-label="File preview panel"
    >
        <!-- Collapsed state -->
        <template v-if="collapsed">
            <WButton
                type="button" variant="ghost" size="sm"
                class="preview-expand"
                aria-label="Expand preview panel"
                title="Expand preview panel"
                @click="emit('toggle')"
            >
                <WIcon name="left_panel_open" :size="21" />
                <span v-if="tabs.length" class="preview-count">{{ tabs.length }}</span>
            </WButton>
        </template>

        <!-- Expanded state -->
        <template v-else>
            <header class="preview-header">
                <div class="min-w-0">
                    <h2>Preview</h2>
                    <p>
                        {{ tabs.length
                            ? `${tabs.length} open ${tabs.length === 1 ? 'file' : 'files'}`
                            : 'Files and resources' }}
                    </p>
                </div>
                <WButton
                    type="button" variant="ghost" size="sm" class="icon-button"
                    :aria-label="narrow ? 'Close preview panel' : 'Collapse preview panel'"
                    :title="narrow ? 'Close preview panel' : 'Collapse preview panel'"
                    @click="emit('toggle')"
                >
                    <WIcon :name="narrow ? 'close' : 'right_panel_close'" />
                </WButton>
            </header>

            <div v-if="tabs.length" class="preview-tabs" role="tablist" aria-label="Open previews">
                <div
                    v-for="item in tabs"
                    :key="item.id"
                    class="preview-tab-wrap"
                    :class="activeTabId === item.id ? 'preview-tab-active' : ''"
                >
                    <WButton
                        type="button" variant="ghost" size="sm" role="tab"
                        :aria-selected="activeTabId === item.id"
                        class="preview-tab"
                        :title="item.name"
                        @click="emit('activate', item.id)"
                    >
                        <WIcon :name="item.kind === 'source' ? 'description' : 'draft'" :size="16" />
                        <span>{{ item.name }}</span>
                    </WButton>
                    <WButton
                        type="button" variant="ghost" size="sm"
                        class="preview-tab-close"
                        :aria-label="`Close ${item.name}`"
                        @click="emit('close', item.id)"
                    >
                        <WIcon name="close" :size="15" />
                    </WButton>
                </div>
            </div>

            <section v-if="activeItem" class="preview-body" role="tabpanel">
                <div class="preview-item-heading">
                    <div class="min-w-0">
                        <h3 :title="activeItem.name">{{ activeItem.name }}</h3>
                        <p>
                            {{ activeItem.mediaType }}
                            <span v-if="activeItem.truncated"> · Preview limited to 1 MB</span>
                        </p>
                    </div>
                    <a
                        v-if="activeItem.encoding === 'base64'"
                        :href="dataUrl"
                        :download="activeItem.name"
                        class="icon-button"
                        :aria-label="`Download ${activeItem.name}`"
                        title="Download"
                    >
                        <WIcon name="download" />
                    </a>
                </div>

                <!-- HTML live preview (sandboxed, CSS/JS enabled) -->
                <iframe
                    v-if="activeItem.encoding === 'utf-8' && isHtml"
                    ref="htmlFrame"
                    :srcdoc="htmlSrcDoc"
                    :title="activeItem.name"
                    class="preview-html"
                    sandbox="allow-scripts allow-forms allow-popups allow-modals"
                />

                <!-- Code / Markdown / plain text -->
                <div
                    v-else-if="activeItem.encoding === 'utf-8'"
                    class="preview-document rich-markdown"
                    v-html="activeText"
                    @click="onDocumentClick"
                />

                <!-- Image -->
                <div v-else-if="isImage" class="preview-media">
                    <img :src="dataUrl" :alt="activeItem.name" />
                </div>

                <!-- Audio -->
                <div v-else-if="isAudio" class="preview-media">
                    <audio :src="dataUrl" controls />
                </div>

                <!-- Video -->
                <div v-else-if="isVideo" class="preview-media">
                    <video :src="dataUrl" controls />
                </div>

                <!-- PDF -->
                <object
                    v-else-if="isPdf"
                    :data="dataUrl"
                    :title="activeItem.name"
                    type="application/pdf"
                    class="preview-pdf"
                >
                    <iframe :src="dataUrl" :title="activeItem.name" class="preview-pdf" />
            </object>

                <!-- Unknown binary -->
                <div v-else class="preview-empty">
                    <WIcon name="draft" :size="32" />
                    <p>This file type cannot be previewed here.</p>
                    <a
                        v-if="activeItem.encoding === 'base64'"
                        :href="dataUrl"
                        :download="activeItem.name"
                    >Download file</a>
                </div>
            </section>

            <div v-else class="preview-empty preview-empty-start">
                <WIcon name="preview" :size="32" />
                <p>Open a source or output to preview it here.</p>
            </div>
        </template>
    </aside>
</template>

<style scoped>
.preview-panel {
    display: flex;
    min-width: 0;
    height: 100%;
    flex-direction: column;
    overflow: hidden;
    background: #fff;
    color: #17212b;
}

.preview-panel-collapsed {
    align-items: center;
    background: #f4f7f5;
}

.preview-expand {
    position: relative;
    display: grid;
    width: 44px;
    height: 48px;
    place-items: center;
    border: 0;
    background: transparent;
    color: #43514f;
    cursor: pointer;
}

.preview-expand:hover,
.icon-button:hover {
    background: #edf2f0;
    color: #166534;
}

.preview-count {
    position: absolute;
    top: 5px;
    right: 3px;
    display: grid;
    min-width: 16px;
    height: 16px;
    place-items: center;
    background: #15803d;
    color: white;
    font-size: 9px;
}

.preview-header {
    display: flex;
    min-height: 66px;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    border-bottom: 1px solid #e7ebea;
    padding: 10px 14px;
}

.preview-header h2 { font-size: 14px; font-weight: 700; }
.preview-header p { margin-top: 2px; color: #687573; font-size: 11px; }

.icon-button {
    display: grid;
    width: 34px;
    height: 34px;
    flex: 0 0 34px;
    place-items: center;
    border: 0;
    background: transparent;
    color: #44514f;
    cursor: pointer;
    border-radius: 6px;
}

.preview-tabs {
    display: flex;
    min-height: 42px;
    gap: 2px;
    overflow-x: auto;
    border-bottom: 1px solid #e5e9e8;
    padding: 4px 6px 0;
}

.preview-tab-wrap {
    display: flex;
    max-width: 190px;
    min-width: 100px;
    align-items: center;
    border-bottom: 2px solid transparent;
    background: #f5f7f6;
}

.preview-tab-active {
    border-bottom-color: #15803d;
    background: #fff;
}

.preview-tab {
    display: flex;
    min-width: 0;
    flex: 1;
    align-items: center;
    gap: 6px;
    padding: 0 8px;
    border: 0;
    background: transparent;
    color: #4d5a58;
    cursor: pointer;
    font-size: 11px;
}

.preview-tab span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.preview-tab-close {
    display: grid;
    width: 26px;
    height: 30px;
    flex: 0 0 26px;
    place-items: center;
    border: 0;
    background: transparent;
    color: #697573;
    cursor: pointer;
}

.preview-tab-close:hover { background: #edf2f0; }

.preview-body {
    display: flex;
    min-height: 0;
    flex: 1;
    flex-direction: column;
    overflow: hidden;
}

.preview-item-heading {
    display: flex;
    min-height: 54px;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    border-bottom: 1px solid #eff1f0;
    padding: 8px 12px;
}

.preview-item-heading h3 {
    overflow: hidden;
    font-size: 12px;
    font-weight: 650;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.preview-item-heading p {
    margin-top: 2px;
    color: #74807e;
    font-size: 10px;
}

.preview-document {
    min-height: 0;
    flex: 1;
    overflow: auto;
    padding: 16px;
    font-size: 13px;
    line-height: 1.65;
    background: #fff;
}

/* Code block styling */
.preview-document :deep(.code-block) {
    margin: 0;
    padding: 14px 16px;
    border-radius: 8px;
    background: #f6f8fa;
    border: 1px solid #e2e8e6;
    overflow: auto;
    font-size: 12px;
    line-height: 1.55;
}
.preview-document :deep(.code-block code) {
    font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', ui-monospace, monospace;
    background: none;
    padding: 0;
    font-size: 12px;
}

.preview-media {
    display: grid;
    min-height: 0;
    flex: 1;
    place-items: center;
    overflow: auto;
    background: #f1f4f3;
    padding: 12px;
}

.preview-media img,
.preview-media video {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
}

.preview-media audio {
    width: min(100%, 420px);
}

/* PDF — both object and fallback iframe */
.preview-pdf {
    width: 100%;
    min-height: 0;
    flex: 1;
    border: 0;
    background: #f1f4f3;
    display: block;
}

/* HTML live preview */
.preview-html {
    width: 100%;
    min-height: 0;
    flex: 1;
    border: 0;
    background: #fff;
}

.preview-empty {
    display: flex;
    min-height: 180px;
    flex: 1;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 9px;
    padding: 24px;
    color: #77817f;
    text-align: center;
    font-size: 12px;
}

.preview-empty a {
    color: #166534;
    font-weight: 650;
    text-decoration: underline;
}

.preview-empty-start { min-height: 0; }

@media (max-width: 1099px) {
    .preview-panel-narrow:not(.preview-panel-collapsed) {
        position: fixed;
        z-index: 24;
        top: 0;
        right: 0;
        bottom: 0;
        width: min(380px, calc(100vw - 68px));
        box-shadow: 0 4px 14px #12201d20;
    }
}
</style>