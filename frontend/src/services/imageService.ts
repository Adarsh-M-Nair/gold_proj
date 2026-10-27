import { type UploadedImage } from "../types/jewellery";
import { request } from "./apiClient";

export async function uploadImage(file: File): Promise<UploadedImage> {
  const form = new FormData();
  form.append("image", file);
  return request("/uploads/", { method: "POST", body: form });
}
