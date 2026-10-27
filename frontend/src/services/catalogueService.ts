import { request } from "./apiClient";

export interface CatalogueItemDetails {
  category: string;
  item_id: string;
  images: Array<{
    filename: string;
    url: string;
  }>;
}

export function getCatalogueItem(category: string, itemId: string): Promise<CatalogueItemDetails> {
  return request(
    `/catalogue/${encodeURIComponent(category)}/${encodeURIComponent(itemId)}/`,
  );
}
