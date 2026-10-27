import { useNavigate } from "react-router-dom";
import { useState, type FormEvent } from "react";
import { searchMatches } from "../services/matchingService";
import { errorMessage } from "../services/apiClient";
import { PageHeading } from "../components/common/PageHeading";
import { Sparkles, Upload, Camera, Shield, LoaderCircle } from "lucide-react";
import { ErrorBanner } from "../components/common/ErrorBanner";
import { useWebcam } from "../hooks/useWebcam";
import { useImageUpload } from "../hooks/useImageUpload";
import { WebcamCapture } from "../components/jewellery/WebcamCapture";

export function JewelleryIdentificationPage() {
  const navigate = useNavigate();
  const webcam = useWebcam();
  const { stopCamera, capturePhoto } = webcam;
  const { images, imageError, addImageFiles } = useImageUpload({ multiple: false });
  const file = images[0]?.file;
  const preview = images[0]?.preview ?? "";
  const [mode, setMode] = useState<"upload" | "camera">("upload");
  const [error, setError] = useState("");
  const [processing, setProcessing] = useState(false);
  const [zoom, setZoom] = useState(1);

  function selectFile(selected: File | undefined) {
    if (!selected) return;
    addImageFiles([selected]);
    setError("");
  }

  function captureForSearch() {
    capturePhoto((file) => {
      selectFile(file);
      stopCamera();
    }, "identification");
  }

  async function findMatches(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Choose or capture an image before starting identification.");
      return;
    }
    setProcessing(true);
    setError("");
    try {
      const body = await searchMatches(file);
      const searchId = body.search_id ?? crypto.randomUUID();
      sessionStorage.setItem(`goldsafe-search-${searchId}`, JSON.stringify(body));
      navigate(`/identify/results/${encodeURIComponent(searchId)}`);
    } catch (cause: unknown) {
      setError(errorMessage(cause));
    } finally {
      setProcessing(false);
    }
  }

  return (
    <>
      <PageHeading eyebrow="Vision match engine" title="Jewellery identification" description="Prepare a clear jewellery image for the similarity matching service." />
      <form className="panel identify-panel" onSubmit={(event) => void findMatches(event)}>
        <div className="identify-header">
          <div><span className="engine-badge"><Sparkles size={15} />Vision Match Engine</span><p>Upload an ornament photo or capture a live image to begin.</p></div>
          <span className="availability-badge"><span />Matching API not connected</span>
        </div>
        <div className="segmented-control identify-tabs">
          <button type="button" className={mode === "upload" ? "selected" : ""} onClick={() => setMode("upload")}><Upload size={16} />Image upload</button>
          <button type="button" className={mode === "camera" ? "selected" : ""} onClick={() => setMode("camera")}><Camera size={16} />Live camera</button>
        </div>
        {mode === "upload" ? (
          <label
            className={`identify-dropzone ${preview ? "has-image" : ""}`}
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              selectFile(event.dataTransfer.files[0]);
            }}
          >
            <input type="file" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp" onChange={(event) => { selectFile(event.target.files?.[0]); event.target.value = ""; }} />
            {preview ? <><img src={preview} alt="Jewellery selected for identification" /><span className="preview-overlay"><strong>{file?.name}</strong><small>Choose another image to replace</small></span></> : <><span className="upload-icon"><Upload size={24} /></span><strong>Drop an image here or browse files</strong><span>Supported formats: JPG, PNG, WEBP · maximum 10 MB</span></>}
          </label>
        ) : (
          <WebcamCapture camera={webcam} onCapture={captureForSearch} zoom={zoom} onZoomChange={setZoom} />
        )}
        {(error || imageError) && <ErrorBanner message={error || imageError} />}
        <div className="identify-footer">
          <span><Shield size={15} /> Matching results require a configured ML service.</span>
          <button className="button button-primary" disabled={processing || !file} type="submit">{processing ? <><LoaderCircle className="spin" size={16} />Searching…</> : <><Sparkles size={16} />Find similar items</>}</button>
        </div>
      </form>
    </>
  );
}
