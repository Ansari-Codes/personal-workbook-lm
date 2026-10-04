const allowedThumbnailTypes = new Set(['image/png', 'image/jpeg', 'image/webp']);
const maximumThumbnailSize = 1024 * 1024;

export function readThumbnailFile(file: File): Promise<string> {
  if (!allowedThumbnailTypes.has(file.type)) {
    return Promise.reject(new Error('Choose a PNG, JPEG, or WebP image.'));
  }
  if (file.size > maximumThumbnailSize) {
    return Promise.reject(new Error('Thumbnail images must be 1 MB or smaller.'));
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener('load', () => {
      if (typeof reader.result === 'string') resolve(reader.result);
      else reject(new Error('Could not read this image.'));
    });
    reader.addEventListener('error', () => reject(new Error('Could not read this image.')));
    reader.readAsDataURL(file);
  });
}