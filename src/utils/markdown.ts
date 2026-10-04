import DOMPurify from 'dompurify';
import { marked, Renderer, type Tokens } from 'marked';

export function normalizeWorkbookFilePath(href: string): string | null {
  if (/^(?:[a-z][a-z\d+.-]*:|\/\/|#)/i.test(href)) return null;
  let path = href.split(/[?#]/, 1)[0] ?? '';
  try {
    path = decodeURIComponent(path);
  } catch {
    return null;
  }
  path = path.replace(/^\.\//, '').replace(/^\/+/, '').replace(/^(?:outputs?|files?)\//i, '');
  return path.split('/').some((part) => !part || part === '.' || part === '..') ? null : path;
}

function mediaUrl(href: string, mediaUrls: Record<string, string>): string {
  const path = normalizeWorkbookFilePath(href);
  return mediaUrls[href] ?? (path ? mediaUrls[path] : undefined) ?? href;
}

function escapeAttribute(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[character] ?? character);
}

export function renderMarkdown(source: string, mediaUrls: Record<string, string> = {}): string {
  const renderer = new Renderer();
  renderer.image = ({ href, title, text }: Tokens.Image) => {
    const titleAttribute = title ? ` title="${escapeAttribute(title)}"` : '';
    const image = `<img src="${escapeAttribute(mediaUrl(href, mediaUrls))}" alt="${escapeAttribute(text)}"${titleAttribute}>`;
    return normalizeWorkbookFilePath(href)
      ? `<a href="${escapeAttribute(href)}">${image}</a>`
      : image;
  };
  renderer.link = function ({ href, title, tokens }: Tokens.Link) {
    const sourceUrl = mediaUrl(href, mediaUrls);
    const extension = href.split(/[?#]/, 1)[0]?.split('.').pop()?.toLowerCase() ?? '';
    if (/^(png|jpe?g|gif|webp|avif|svg)$/.test(extension)) {
      const image = `<img src="${escapeAttribute(sourceUrl)}" alt=""${title ? ` title="${escapeAttribute(title)}"` : ''}>`;
      return normalizeWorkbookFilePath(href) ? `<a href="${escapeAttribute(href)}">${image}</a>` : image;
    }
    if (/^(mp3|wav|ogg|oga|m4a|aac|flac)$/.test(extension)) {
      return `<audio controls preload="metadata" src="${escapeAttribute(sourceUrl)}"></audio>`;
    }
    if (/^(mp4|webm|ogv|mov|m4v)$/.test(extension)) {
      return `<video controls preload="metadata" src="${escapeAttribute(sourceUrl)}"></video>`;
    }
    const titleAttribute = title ? ` title="${escapeAttribute(title)}"` : '';
    const externalAttributes = /^(?:[a-z][a-z\d+.-]*:|\/\/)/i.test(href) ? ' target="_blank" rel="noopener noreferrer"' : '';
    return `<a href="${escapeAttribute(href)}"${titleAttribute}${externalAttributes}>${this.parser.parseInline(tokens)}</a>`;
  };
  return DOMPurify.sanitize(marked.parse(source, {
    async: false,
    breaks: true,
    gfm: true,
    renderer,
  }), {
    ALLOWED_URI_REGEXP: /^(?:(?:(?:f|ht)tps?|mailto|tel|callto|sms|cid|xmpp|matrix|blob):|[^a-z]|[a-z+.-]+(?:[^a-z+.-:]|$))/i,
  });
}
