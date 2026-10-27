import { useCallback, useEffect, useRef, useState } from "react";
import type { SelectedImage } from "../types/jewellery";
import { maxImageBytes, supportedTypes } from "../utils/imageUtils";

export function useImageUpload({ multiple = true } = {}) {
  const [images, setImages] = useState<SelectedImage[]>([]);
  const selectedImages = useRef<SelectedImage[]>([]);
  const [imageError, setImageError] = useState("");
  const previewUrls = useRef(new Set<string>());

  const releasePreview = useCallback((preview: string) => {
    URL.revokeObjectURL(preview);
    previewUrls.current.delete(preview);
  }, []);

  useEffect(() => () => {
    previewUrls.current.forEach((url) => URL.revokeObjectURL(url));
    previewUrls.current.clear();
  }, []);

  function addImageFiles(files: FileList | File[], source: SelectedImage["source"] = "UPLOAD") {
    const valid: SelectedImage[] = [];
    const errors: string[] = [];
    for (const file of Array.from(files)) {
      if (!supportedTypes.includes(file.type)) {
        errors.push(multiple ? `${file.name}: choose a JPG, PNG, or WEBP image.` : "Choose a JPG, PNG, or WEBP image.");
        continue;
      }
      if (file.size > maxImageBytes) {
        errors.push(multiple ? `${file.name}: each image must be 10 MB or smaller.` : "The selected image must be 10 MB or smaller.");
        continue;
      }
      const preview = URL.createObjectURL(file);
      previewUrls.current.add(preview);
      valid.push({ file, preview, source });
      if (!multiple) break;
    }
    if (valid.length) {
      if (!multiple) {
        selectedImages.current.forEach(({ preview }) => releasePreview(preview));
        selectedImages.current = valid;
      } else {
        selectedImages.current = [...selectedImages.current, ...valid];
      }
      setImages(selectedImages.current);
    }
    setImageError(errors.join(" "));
    return valid.length > 0;
  }

  function removeImage(index: number) {
    const selected = selectedImages.current[index];
    if (selected) releasePreview(selected.preview);
    selectedImages.current = selectedImages.current.filter((_, itemIndex) => itemIndex !== index);
    setImages(selectedImages.current);
  }

  function clearImages() {
    selectedImages.current.forEach(({ preview }) => releasePreview(preview));
    selectedImages.current = [];
    setImages([]);
    setImageError("");
  }

  return { images, imageError, addImageFiles, removeImage, clearImages };
}
