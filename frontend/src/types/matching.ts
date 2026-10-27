export interface PledgeMatch {
  result_id?: string;
  rank?: number;
  similarity_score?: number;
  matched_image_id?: string;
  pledge_uuid?: string;
  pledge_id?: string;
  pledge_status?: string;
  registered_at?: string;
  customer_name?: string;
  phone_number?: string;
  masked_aadhaar?: string;
  jewellery_item_id?: string;
  jewellery_category?: string;
  jewellery_description?: string;
  purity?: string;
  stored_image_url?: string;
  images?: Array<{ id: string; url: string }>;
}

export interface MatchResponse {
  search_id?: string;
  status?: string;
  model_version?: string;
  query_image_url?: string;
  matches?: PledgeMatch[];
}
