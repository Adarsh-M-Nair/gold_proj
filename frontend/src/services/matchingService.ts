import { type MatchResponse } from "../types/matching";
import { request } from "./apiClient";

export async function searchMatches(file: File): Promise<MatchResponse> {
  const form = new FormData();
  form.append("image", file);
  return await request("/matching/search/", { method: "POST", body: form });
}
