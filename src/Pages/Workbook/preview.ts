export interface PreviewItem {
  id: string;
  name: string;
  kind: 'source' | 'output';
  mediaType: string;
  encoding: 'utf-8' | 'base64';
  content: string | null;
  contentBase64: string | null;
  truncated?: boolean;
}