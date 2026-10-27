export const supportedTypes = ["image/jpeg", "image/png", "image/webp"];

export const maxImageBytes = 10 * 1024 * 1024;

export function imageUrl(objectKey: string): string {
  if (/^https?:\/\//i.test(objectKey)) return objectKey;
  const normalized = objectKey.replace(/^\/+/, "");
  if (normalized.startsWith("media/")) return `/${normalized}`;
  if (normalized.startsWith("static/uploads/")) {
    return `/${normalized}`;
  }
  return `/media/${normalized}`;
}
