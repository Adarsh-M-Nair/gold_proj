export interface CustomerSummary {
  id: string;
  full_name: string;
  phone_number: string;
  masked_aadhaar: string;
}

export interface RegisterCustomerPayload {
  customer: {
    full_name: string;
    phone_number: string;
    aadhaar_number: string;
  };
  jewellery_item: { category: string };
  images: Array<{
    object_key: string;
    original_filename: string;
    content_type: string;
    file_size_bytes: number;
    capture_source: "WEBCAM" | "UPLOAD";
    image_type: string;
  }>;
}
