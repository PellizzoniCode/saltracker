import { useEffect, useRef, useState } from "react";
import { api } from "../api/client.js";

// Photo selection, private upload and Bedrock analysis polling for the asset
// form. The three refs guard against stale results: picking a new photo (or
// resetting) invalidates any upload or polling loop still in flight.
//   analysisTimer  - pending poll timeout
//   activePhotoKey - the uploaded key the polling loop is allowed to update
//   uploadToken    - bumped on every selection to cancel an in-flight upload
export function usePhotoAnalysis({ setForm, saving }) {
  const [photo, setPhoto] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [photoMessage, setPhotoMessage] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [analysisMessage, setAnalysisMessage] = useState("");
  const [checkingAnalysis, setCheckingAnalysis] = useState(false);
  const photoInput = useRef(null);
  const analysisTimer = useRef(null);
  const activePhotoKey = useRef(null);
  const uploadToken = useRef(0);

  useEffect(() => {
    return () => {
      if (analysisTimer.current) {
        clearTimeout(analysisTimer.current);
      }
    };
  }, []);

  function selectPhoto(event) {
    const selected = event.target.files?.[0] || null;

    if (analysisTimer.current) {
      clearTimeout(analysisTimer.current);
      analysisTimer.current = null;
    }

    activePhotoKey.current = null;
    uploadToken.current += 1;
    setPhoto(selected);
    setForm((current) => ({ ...current, imageKey: "" }));
    setPhotoMessage("");
    setAnalysis(null);
    setAnalysisMessage("");
    setCheckingAnalysis(false);
  }

  async function checkPhotoAnalysis(photoKey, attempt = 0) {
    if (activePhotoKey.current !== photoKey) return;

    if (attempt === 0) {
      setCheckingAnalysis(true);
      setAnalysis(null);
    }

    try {
      const result = await api(
        `/photo-analysis?key=${encodeURIComponent(photoKey)}`
      );

      if (activePhotoKey.current !== photoKey) return;

      if (result.status === "Processing") {
        if (attempt >= 30) {
          setAnalysisMessage(
            "Analysis is taking longer than expected. You may continue entering the asset details."
          );
          setCheckingAnalysis(false);
          return;
        }

        setAnalysisMessage("Bedrock is analyzing the photograph...");

        analysisTimer.current = setTimeout(() => {
          checkPhotoAnalysis(photoKey, attempt + 1);
        }, 2000);

        return;
      }

      if (result.status === "Ready" && result.suggestion) {
        setAnalysis(result.suggestion);
        setAnalysisMessage(
          "Bedrock analysis is ready. Review the suggestions before applying them."
        );
        setCheckingAnalysis(false);
        return;
      }

      setAnalysisMessage(
        result.message || "The photograph analysis could not be completed."
      );
      setCheckingAnalysis(false);
    } catch (error) {
      if (activePhotoKey.current !== photoKey) return;
      setAnalysisMessage(error.message);
      setCheckingAnalysis(false);
    }
  }

  async function uploadPhoto() {
    if (!photo || uploading || saving) return;

    const token = uploadToken.current;

    if (
      !["image/jpeg", "image/png"].includes(photo.type) ||
      photo.size < 1 ||
      photo.size > 3_750_000
    ) {
      setPhotoMessage(
        "Choose a JPEG or PNG photo between 1 byte and 3.75 MB."
      );
      return;
    }

    setUploading(true);
    setPhotoMessage("");
    setAnalysis(null);
    setAnalysisMessage("");

    try {
      const signed = await api("/photo-uploads", {
        method: "POST",
        body: JSON.stringify({
          contentType: photo.type,
        }),
      });

      if (uploadToken.current !== token) return;

      const data = new FormData();

      Object.entries(signed.fields).forEach(
        ([name, value]) => data.append(name, value)
      );

      data.append("file", photo);

      const upload = await fetch(signed.url, {
        method: "POST",
        body: data,
      });

      if (!upload.ok) {
        throw new Error(
          "Photo upload failed. Please try again."
        );
      }

      if (uploadToken.current !== token) return;

      setForm((current) => ({
        ...current,
        imageKey: signed.key,
      }));

      setPhotoMessage(
        "Photo uploaded privately. Bedrock analysis has started."
      );

      activePhotoKey.current = signed.key;
      await checkPhotoAnalysis(signed.key);
    } catch (error) {
      setPhotoMessage(error.message);
      setCheckingAnalysis(false);
    } finally {
      setUploading(false);
    }
  }

  function applyAnalysis() {
    if (!analysis) return;

    setForm((current) => ({
      ...current,
      category: analysis.category || current.category,
      description: analysis.description || current.description,
      condition: analysis.condition || current.condition,
      manufacturer: analysis.manufacturer || current.manufacturer,
      model: analysis.model || current.model,
      usefulLifeMonths:
        analysis.usefulLifeMonths !== undefined
          ? Number(analysis.usefulLifeMonths)
          : current.usefulLifeMonths,
    }));

    setAnalysisMessage(
      "AI suggestions applied. Review or edit the values before creating the asset."
    );
  }

  function rejectAnalysis() {
    setAnalysis(null);
    setAnalysisMessage(
      "AI suggestions rejected. Enter the asset information manually."
    );
  }

  // Clears the selected photo, analysis and polling after an asset is
  // created. The caller resets the form itself.
  function resetPhoto() {
    setPhoto(null);
    setAnalysis(null);
    setAnalysisMessage("");
    setCheckingAnalysis(false);
    activePhotoKey.current = null;

    if (analysisTimer.current) {
      clearTimeout(analysisTimer.current);
      analysisTimer.current = null;
    }

    if (photoInput.current) photoInput.current.value = "";
    setPhotoMessage("");
  }

  return {
    photo,
    uploading,
    photoMessage,
    setPhotoMessage,
    analysis,
    analysisMessage,
    checkingAnalysis,
    photoInput,
    selectPhoto,
    uploadPhoto,
    applyAnalysis,
    rejectAnalysis,
    resetPhoto,
  };
}
