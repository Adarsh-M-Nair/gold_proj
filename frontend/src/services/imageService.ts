import { type UploadedImage } from "../types/jewellery";
import { request } from "./apiClient";

export async function uploadImage(file: File): Promise<UploadedImage> {
  const upload = await request<{
    method: "POST" | "LOCAL";
    upload_url: string;
    object_key: string;
    fields: Record<string, string>;
    original_filename: string;
    content_type: string;
    file_size_bytes: number;
  }>("/uploads/presign/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filename: file.name,
      content_type: file.type,
      file_size_bytes: file.size,
    }),
  });

  if (upload.method === "LOCAL") {
    const form = new FormData();
    form.append("image", file);
    return request("/uploads/", { method: "POST", body: form });
  }

  const form = new FormData();
  for (const [name, value] of Object.entries(upload.fields)) {
    form.append(name, value);
  }
  form.append("file", file);
  const response = await fetch(upload.upload_url, {
    method: upload.method,
    body: form,
  });
  if (!response.ok) {
    throw new Error("The image could not be uploaded to private storage. Please try again.");
  }
  return {
    object_key: upload.object_key,
    original_filename: upload.original_filename,
    content_type: upload.content_type,
    file_size_bytes: upload.file_size_bytes,
  };
}
