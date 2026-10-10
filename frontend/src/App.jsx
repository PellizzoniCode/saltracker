import { useCallback, useEffect, useRef, useState } from "react";
import { Authenticator } from "@aws-amplify/ui-react";
import { api } from "./api/client.js";
import { Notice } from "./components/Notice.jsx";
import { PageHeader } from "./components/PageHeader.jsx";
import { Panel } from "./components/Panel.jsx";
import { SectionHeading } from "./components/SectionHeading.jsx";
import { emptyAsset } from "./constants/asset.js";
import { AnalysisSuggestions } from "./features/assets/AnalysisSuggestions.jsx";
import { AssetGallery } from "./features/assets/AssetGallery.jsx";
import { AssetSearch } from "./features/assets/AssetSearch.jsx";
import { AssetTable } from "./features/assets/AssetTable.jsx";
import { MaintenancePage } from "./features/maintenance/MaintenancePage.jsx";

function AssetApplication({ signOut, user }) {
  const [assets, setAssets] = useState([]);
  const [nextToken, setNextToken] = useState(null);
  const [maintenanceAsset, setMaintenanceAsset] = useState(null);
  const [form, setForm] = useState(emptyAsset);
  const [message, setMessage] = useState("");
  const [query, setQuery] = useState("");
  const [saving, setSaving] = useState(false);
  const [photo, setPhoto] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [photoMessage, setPhotoMessage] = useState("");
    const [galleryItems, setGalleryItems] = useState([]);
  const [galleryLoading, setGalleryLoading] = useState(false);
  const [galleryMessage, setGalleryMessage] = useState("");
  const photoInput = useRef(null);
  const [analysis, setAnalysis] = useState(null);
  const [analysisMessage, setAnalysisMessage] = useState("");
  const [checkingAnalysis, setCheckingAnalysis] = useState(false);
  const analysisTimer = useRef(null);
  const activePhotoKey = useRef(null);
  const uploadToken = useRef(0);

  const loadAssets = useCallback(async ({
    append = false,
    token = null,
  } = {}) => {
    try {
      const params = new URLSearchParams();

      if (query) {
        params.set("q", query);
      }

      if (token) {
        params.set("nextToken", token);
      }

      const queryString = params.toString();
      const result = await api(
        `/assets${queryString ? `?${queryString}` : ""}`
      );

      setAssets((current) =>
        append ? [...current, ...result.items] : result.items
      );
      setNextToken(result.nextToken || null);
      setMessage("");
    } catch (error) {
      setMessage(error.message);
    }
  }, [query]);

    useEffect(() => {
    loadAssets();
  }, [loadAssets]);

    const loadGallery = useCallback(async () => {
    const photoAssets = assets.filter((asset) => asset.imageKey);

    if (!photoAssets.length) {
      setGalleryItems([]);
      setGalleryMessage("");
      return;
    }

    setGalleryLoading(true);
    setGalleryMessage("");

    const results = await Promise.allSettled(
      photoAssets.map(async (asset) => {
        const photoDetails = await api(
          `/assets/${encodeURIComponent(asset.assetId)}/photo`
        );

        return {
          ...asset,
          ...photoDetails,
        };
      })
    );

    const visibleItems = results
      .filter((result) => result.status === "fulfilled")
      .map((result) => result.value);

    const failedCount =
      results.length - visibleItems.length;

    setGalleryItems(visibleItems);

    if (failedCount) {
      setGalleryMessage(
        `${failedCount} photograph${
          failedCount === 1 ? "" : "s"
        } could not be loaded. Refresh the gallery to try again.`
      );
    }

    setGalleryLoading(false);
  }, [assets]);

  useEffect(() => {
    loadGallery();
  }, [loadGallery]);

  useEffect(() => {
    return () => {
      if (analysisTimer.current) {
        clearTimeout(analysisTimer.current);
      }
    };
  }, []);

  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: name === "usefulLifeMonths" ? Number(value) : value }));
  }

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
  async function createAsset(event) {
    event.preventDefault();
    if (saving || uploading) return;
    if (photo && !form.imageKey) {
      setPhotoMessage("Upload the selected photo first, or remove it to create the asset without a photo.");
      return;
    }
    setSaving(true);

    try {
      const payload = Object.fromEntries(Object.entries(form).map(([key, value]) => [key, value === "" ? null : value]));
      const result = await api("/assets", { method: "POST", body: JSON.stringify(payload) });
      setMessage(`${result.message} ID: ${result.assetId}`);
      setForm(emptyAsset);
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
      await loadAssets();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setSaving(false);
    }
  }
if (maintenanceAsset) {
    return (
      <MaintenancePage
        asset={maintenanceAsset}
        user={user}
        signOut={signOut}
        onBack={() => setMaintenanceAsset(null)}
      />
    );
  }

  return (
    <main>
      <PageHeader
        eyebrow="AWS CLOUD SECURITY PORTFOLIO"
        title="Smart Asset Lifecycle Tracker"
        user={user}
      >
        <button className="secondary" onClick={signOut}>Sign out</button>
      </PageHeader>

      {message && <Notice>{message}</Notice>}

      <Panel>
        <h2>Register an asset manually</h2>
        <form onSubmit={createAsset}>
          {Object.entries(form).filter(([name]) => name !== "imageKey").map(([name, value]) => (
            <label key={name}>
              <span>{name.replace(/([A-Z])/g, " $1")}</span>
              <input
                name={name}
                value={value ?? ""}
                type={name.includes("Date") ? "date" : name === "usefulLifeMonths" ? "number" : "text"}
                onChange={updateField}
                required={["assetTag", "description", "purchaseDate", "inServiceDate", "purchaseValue"].includes(name)}
              />
            </label>
          ))}
          <div className="photo-upload">
            <label htmlFor="asset-photo"><span>Asset photo (optional)</span></label>
            <input id="asset-photo" ref={photoInput} type="file" accept="image/jpeg,image/png" disabled={uploading || saving} onChange={selectPhoto} />
            <button type="button" className="secondary" disabled={!photo || uploading || saving} onClick={uploadPhoto}>
              {uploading ? "Uploading..." : "Upload photo"}
            </button>
            {photoMessage && <p role="status">{photoMessage}</p>}
            {analysisMessage && (
  <p role="status">{analysisMessage}</p>
)}

{checkingAnalysis && (
  <p className="analysis-status">
    Analyzing photograph...
  </p>
)}

{analysis && (
  <AnalysisSuggestions
    analysis={analysis}
    onApply={applyAnalysis}
    onReject={rejectAnalysis}
  />
)}
          </div>
          <button type="submit" disabled={saving || uploading}>
            {saving ? "Creating..." : "Create asset"}
          </button>
        </form>
      </Panel>

      <AssetGallery
        items={galleryItems}
        loading={galleryLoading}
        message={galleryMessage}
        onRefresh={loadGallery}
      />

      <Panel>
        <SectionHeading title="Authorized inventory">
          <AssetSearch
            query={query}
            onQueryChange={setQuery}
            onSearch={loadAssets}
          />
        </SectionHeading>
        <AssetTable
          assets={assets}
          onViewMaintenance={setMaintenanceAsset}
        />

        {nextToken && (
          <button
            className="secondary"
            onClick={() =>
              loadAssets({
                append: true,
                token: nextToken,
              })
            }
          >
            Load more
          </button>
        )}
      </Panel>
    </main>
  );
}

export default function App() {
  return <Authenticator>{({ signOut, user }) => <AssetApplication signOut={signOut} user={user} />}</Authenticator>;
}
