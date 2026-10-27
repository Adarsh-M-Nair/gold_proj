import { X } from "lucide-react";
import type { SelectedImage } from "../../types/jewellery";

export function ImagePreviewGrid({ images, onRemove }: { images: SelectedImage[]; onRemove: (index: number) => void }) {
  if (!images.length) return null;
  return (
    <div className="image-preview-section">
      <div className="preview-heading"><strong>Selected photos</strong><span>{images.length} {images.length === 1 ? "image" : "images"}</span></div>
      <div className="preview-grid">
        {images.map((image, index) => (
          <div className="preview-card" key={`${image.preview}-${index}`}>
            <img src={image.preview} alt={`Jewellery angle ${index + 1}`} />
            <span className="preview-label">{image.source === "WEBCAM" ? "Camera" : image.file.name}</span>
            <button type="button" aria-label={`Remove photo ${index + 1}`} onClick={() => onRemove(index)}><X size={15} /></button>
          </div>
        ))}
      </div>
    </div>
  );
}
