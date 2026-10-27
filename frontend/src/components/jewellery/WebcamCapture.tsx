import { AlertCircle, Camera } from "lucide-react";
import type { useWebcam } from "../../hooks/useWebcam";

interface WebcamCaptureProps {
  camera: ReturnType<typeof useWebcam>;
  onCapture: () => void;
  zoom?: number;
  onZoomChange?: (zoom: number) => void;
}

export function WebcamCapture({ camera, onCapture, zoom, onZoomChange }: WebcamCaptureProps) {
  const { videoRef, cameraActive, cameraError, startCamera, stopCamera } = camera;
  const identification = zoom !== undefined;
  return (
    <div className={`camera-card${identification ? " identify-camera" : ""}`}>
      <div className="camera-preview">
        {cameraActive ? (
          <video ref={videoRef} autoPlay playsInline muted style={identification ? { transform: `scale(${zoom})` } : undefined} aria-label="Live camera preview" />
        ) : (
          <div className="camera-placeholder">
            <Camera size={30} />
            <strong>{identification ? "Align the jewellery in the frame" : "Capture clear jewellery photos"}</strong>
            <span>{identification ? "Use clear lighting and a plain background." : "Place the item against a plain background with good lighting."}</span>
          </div>
        )}
        {cameraActive && <div className="camera-reticle" aria-hidden="true" />}
      </div>
      <div className={`camera-actions${identification ? " camera-zoom" : ""}`}>
        {identification && <label>Zoom <input type="range" min="1" max="3" step="0.1" value={zoom} onChange={(event) => onZoomChange?.(Number(event.target.value))} /></label>}
        {cameraActive ? (
          <>
            <button className="button button-quiet" type="button" onClick={stopCamera}>Stop camera</button>
            <button className="button button-primary" type="button" onClick={onCapture}><Camera size={16} />{identification ? "Capture" : "Capture photo"}</button>
          </>
        ) : (
          <button className="button button-primary" type="button" onClick={() => void startCamera()}><Camera size={16} />Start camera</button>
        )}
      </div>
      {cameraError && <p className="field-error"><AlertCircle size={15} />{cameraError}</p>}
    </div>
  );
}
