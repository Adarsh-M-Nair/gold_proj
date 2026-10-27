import { useState, type FormEvent } from "react";
import { type SelectedImage } from "../../types/jewellery";
import { type Pledge } from "../../types/pledge";
import { uploadImage } from "../../services/imageService";
import { registerCustomer } from "../../services/customerService";
import { errorMessage } from "../../services/apiClient";
import { Link } from "react-router-dom";
import { Check, ArrowRight, X, Camera, Upload, Shield, LoaderCircle } from "lucide-react";
import { ErrorBanner } from "../common/ErrorBanner";
import { useWebcam } from "../../hooks/useWebcam";
import { useImageUpload } from "../../hooks/useImageUpload";
import { KycFields } from "./KycFields";
import { WebcamCapture } from "../jewellery/WebcamCapture";
import { MultiImageUploader } from "../jewellery/MultiImageUploader";
import { ImagePreviewGrid } from "../jewellery/ImagePreviewGrid";

export function CustomerForm() {
  const webcam = useWebcam();
  const { stopCamera, capturePhoto } = webcam;
  const { images, imageError, addImageFiles: addFiles, removeImage, clearImages } = useImageUpload();
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [aadhaar, setAadhaar] = useState("");
  const [category, setCategory] = useState("OTHER");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState<Pledge | null>(null);
  const [mode, setMode] = useState<"camera" | "upload">("camera");

  function addImageFiles(files: FileList | File[], source: SelectedImage["source"]) {
    setError("");
    if (addFiles(files, source)) setSuccess(null);
  }

  async function submitRegistration(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const digits = aadhaar.replace(/\D/g, "");
    if (phone.replace(/\D/g, "").length !== 10) {
      setError("Enter a valid 10-digit phone number.");
      return;
    }
    if (digits.length !== 12) {
      setError("Enter a valid 12-digit Aadhaar number.");
      return;
    }
    if (!images.length) {
      setError("Add at least one jewellery photo before registering.");
      return;
    }
    setSubmitting(true);
    try {
      const uploads = await Promise.all(images.map(({ file }) => uploadImage(file)));
      const pledge = await registerCustomer({
        customer: { full_name: fullName.trim(), phone_number: phone.replace(/\D/g, ""), aadhaar_number: digits },
        jewellery_item: { category },
        images: uploads.map((upload, index) => ({
          object_key: upload.object_key,
          original_filename: upload.original_filename,
          content_type: upload.content_type,
          file_size_bytes: upload.file_size_bytes,
          capture_source: images[index].source,
          image_type: ["FRONT", "SIDE", "BACK", "CLOSEUP"][index] ?? "OTHER",
        })),
      });
      stopCamera();
      setSuccess(pledge);
      setFullName("");
      setPhone("");
      setAadhaar("");
      clearImages();
    } catch (cause: unknown) {
      setError(errorMessage(cause));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      {success && (
        <div className="registration-success">
          <span><Check size={19} /></span>
          <div><strong>Customer registered successfully</strong><p>Pledge {success.pledge_id} is now in the records.</p></div>
          <Link className="text-link" to={`/pledges/${success.id}`}>View pledge <ArrowRight size={15} /></Link>
          <button type="button" aria-label="Dismiss success message" onClick={() => setSuccess(null)}><X size={16} /></button>
        </div>
      )}
      <form className="panel registration-form" onSubmit={(event) => void submitRegistration(event)}>
        <KycFields fullName={fullName} phone={phone} aadhaar={aadhaar} category={category} onFullNameChange={setFullName} onPhoneChange={setPhone} onAadhaarChange={setAadhaar} onCategoryChange={setCategory} />
        <section className="form-section photo-section">
          <div className="section-title"><span className="section-icon gold"><Camera size={18} /></span><div><h2>Pledged jewellery photos</h2><p>Capture different angles or upload existing images. JPG, PNG, and WEBP · max 10 MB each.</p></div></div>
          <div className="segmented-control">
            <button type="button" className={mode === "camera" ? "selected" : ""} onClick={() => setMode("camera")}><Camera size={16} />Webcam capture</button>
            <button type="button" className={mode === "upload" ? "selected" : ""} onClick={() => setMode("upload")}><Upload size={16} />Upload photos</button>
          </div>
          {mode === "camera" ? (
            <WebcamCapture camera={webcam} onCapture={() => capturePhoto((file) => addImageFiles([file], "WEBCAM"))} />
          ) : (
            <MultiImageUploader onFiles={(files) => addImageFiles(files, "UPLOAD")} />
          )}
          <ImagePreviewGrid images={images} onRemove={removeImage} />
        </section>
        {(error || imageError) && <ErrorBanner message={error || imageError} />}
        <div className="form-footer"><p><Shield size={15} /> Aadhaar is masked in the pledge records list.</p><button className="button button-primary" type="submit" disabled={submitting}>{submitting ? <><LoaderCircle className="spin" size={16} />Saving registration…</> : <><Check size={16} />Create pledge record</>}</button></div>
      </form>
    </>
  );
}
