import { useCallback, useEffect, useRef, useState } from "react";

export function useWebcam() {
  const videoElement = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const generation = useRef(0);
  const starting = useRef(false);
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState("");

  const videoRef = useCallback((element: HTMLVideoElement | null) => {
    videoElement.current = element;
    if (element) element.srcObject = streamRef.current;
  }, []);

  const stopCamera = useCallback(() => {
    generation.current += 1;
    starting.current = false;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setCameraActive(false);
  }, []);

  useEffect(() => () => {
    generation.current += 1;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    starting.current = false;
  }, []);

  async function startCamera() {
    if (starting.current || streamRef.current) return;
    setCameraError("");
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError("Camera access requires HTTPS or localhost and a supported browser.");
      return;
    }
    const requestGeneration = generation.current;
    starting.current = true;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
        audio: false,
      });
      if (requestGeneration !== generation.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      streamRef.current = stream;
      if (videoElement.current) videoElement.current.srcObject = stream;
      setCameraActive(true);
    } catch {
      if (requestGeneration === generation.current) {
        setCameraError("Camera access was denied or no camera is available. You can upload photos instead.");
      }
    } finally {
      if (requestGeneration === generation.current) starting.current = false;
    }
  }

  function capturePhoto(onCapture: (file: File) => void, filenamePrefix = "pledge-photo") {
    const video = videoElement.current;
    if (!video || !video.videoWidth || !video.videoHeight) {
      setCameraError("Wait for the camera preview before taking a photo.");
      return;
    }
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) {
      setCameraError("The camera image could not be captured. Please try uploading a photo.");
      return;
    }
    const captureGeneration = generation.current;
    context.drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      if (captureGeneration !== generation.current) return;
      if (!blob) {
        setCameraError("The camera image could not be captured. Please try again.");
        return;
      }
      onCapture(new File([blob], `${filenamePrefix}-${Date.now()}.jpg`, { type: "image/jpeg" }));
    }, "image/jpeg", 0.92);
  }

  return { videoRef, cameraActive, cameraError, startCamera, stopCamera, capturePhoto };
}
