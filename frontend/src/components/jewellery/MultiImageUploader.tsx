import { ImagePlus } from "lucide-react";

export function MultiImageUploader({ onFiles }: { onFiles: (files: FileList) => void }) {
  return (
    <label
      className="upload-dropzone"
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault();
        onFiles(event.dataTransfer.files);
      }}
    >
      <input type="file" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp" multiple onChange={(event) => {
        if (event.target.files) onFiles(event.target.files);
        event.target.value = "";
      }} />
      <span className="upload-icon"><ImagePlus size={23} /></span>
      <strong>Choose jewellery photos</strong>
      <span>Drag photos here or browse files · select multiple angles</span>
    </label>
  );
}
