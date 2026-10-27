import { type Paginated } from "../types/api";
import { type Pledge } from "../types/pledge";
import { request } from "./apiClient";

export function getPledges(params: {
  search?: string;
  page?: number;
  pageSize?: number;
} = {}): Promise<Paginated<Pledge>> {
  const query = new URLSearchParams();
  if (params.search) query.set("search", params.search);
  query.set("page", String(params.page ?? 1));
  query.set("page_size", String(params.pageSize ?? 10));
  return request(`/pledges/?${query.toString()}`);
}

export function getPledge(id: string): Promise<Pledge> {
  return request(`/pledges/${encodeURIComponent(id)}/`);
}

export function deletePledge(id: string): Promise<void> {
  return request(`/pledges/${encodeURIComponent(id)}/`, { method: "DELETE" });
}
