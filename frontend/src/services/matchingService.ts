import { type MatchResponse } from "../types/matching";
import { ApiError, request } from "./apiClient";

export async function searchMatches(file: File): Promise<MatchResponse> {
  const form = new FormData();
  form.append("image", file);
  try {
    return await request("/matching/search/", { method: "POST", body: form });
  } catch (cause: unknown) {
    if (cause instanceof ApiError && cause.status === 404) {
      throw new ApiError("The matching API is not available in this backend yet. The Phase 4 ML service must be connected before similarity results can be shown.", 404);
    }
    throw cause;
  }
}
