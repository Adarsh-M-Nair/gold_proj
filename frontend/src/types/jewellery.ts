export interface SelectedImage {
  file: File;
  preview: string;
  source: "WEBCAM" | "UPLOAD";
}

export interface PledgeImage {
  id: string;
  object_key: string;
  thumbnail_object_key: string;
  original_filename: string;
  content_type: string;
  file_size_bytes: number;
  capture_source: "WEBCAM" | "UPLOAD";
  image_type: string;
  embedding_status: string;
  created_at: string;
}

export interface JewelleryItem {
  id: string;
  category: string;
  description: string;
  weight_grams: string | null;
  purity: string;
  status: string;
  images: PledgeImage[];
}

export interface UploadedImage {
  object_key: string;
  url: string;
  original_filename: string;
  content_type: string;
  file_size_bytes: number;
}
