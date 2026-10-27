export interface MatchResponse {
  search_id?: string;
  status?: string;
  query_image_url?: string;
  matches?: Array<{
    result_id?: string;
    rank?: number;
    similarity_score?: number;
    pledge_id?: string;
    customer_name?: string;
    phone_number?: string;
    masked_aadhaar?: string;
    registered_at?: string;
    stored_image_url?: string;
    jewellery_description?: string;
  }>;
}
