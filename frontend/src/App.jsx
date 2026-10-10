import { useCallback, useEffect, useRef, useState } from "react";
import { Authenticator } from "@aws-amplify/ui-react";
import { api } from "./api/client.js";
import { DetailList } from "./components/DetailList.jsx";
import { Notice } from "./components/Notice.jsx";
import { PageHeader } from "./components/PageHeader.jsx";
import { Panel } from "./components/Panel.jsx";
import { SectionHeading } from "./components/SectionHeading.jsx";
import { StatusBadge } from "./components/StatusBadge.jsx";
import { emptyAsset } from "./constants/asset.js";
import { emptyMaintenance } from "./constants/maintenance.js";
import { useIdentity } from "./hooks/useIdentity.js";
import { formatMoney } from "./utils/format.js";

function MaintenancePage({
  asset,
  onBack,
  signOut,
  user,
}) {
  const [history, setHistory] = useState([]);
  const [schedule, setSchedule] = useState(null);
  const [aiRecommendation, setAiRecommendation] =
    useState(null);
  const [maintenanceForm, setMaintenanceForm] =
    useState(emptyMaintenance);
  const [loading, setLoading] = useState(true);
  const [savingMaintenance, setSavingMaintenance] =
    useState(false);
  const [generatingAi, setGeneratingAi] =
    useState(false);
  const [maintenanceMessage, setMaintenanceMessage] =
    useState("");
  const [editingMaintenance, setEditingMaintenance] =
    useState(null);
  const editingMaintenanceId =
    editingMaintenance?.maintenanceId ?? null;
  const identity = useIdentity();
  const isAdministrator =
    identity?.groups.has("Administrator") ?? false;

  function canEditMaintenance(item) {
    if (isAdministrator) return true;

    return Boolean(
      identity?.groups.has("Technician") &&
        identity.sub &&
        item.performedBy === identity.sub &&
        identity.department &&
        identity.department === asset.department
    );
  }

  const showMaintenanceActions =
    isAdministrator || history.some(canEditMaintenance);

  const loadMaintenance = useCallback(async () => {
    setLoading(true);

    try {
      const result = await api(
        `/assets/${encodeURIComponent(
          asset.assetId
        )}/maintenance`
      );

      setHistory(result.items || []);
      setSchedule(result.recommendation || null);
      setMaintenanceMessage("");
    } catch (error) {
      setMaintenanceMessage(error.message);
    } finally {
      setLoading(false);
    }
  }, [asset.assetId]);

  useEffect(() => {
    loadMaintenance();
  }, [loadMaintenance]);

  function updateMaintenanceField(event) {
    const { name, value } = event.target;

    setMaintenanceForm((current) => ({
      ...current,
      [name]: value,
    }));
  }

  function maintenancePath(maintenanceId) {
    const base = `/assets/${encodeURIComponent(
      asset.assetId
    )}/maintenance`;

    return maintenanceId
      ? `${base}/${encodeURIComponent(maintenanceId)}`
      : base;
  }

  function editMaintenance(item) {
    setEditingMaintenance(item);
    setMaintenanceForm(
      Object.fromEntries(
        Object.keys(emptyMaintenance).map((key) => [
          key,
          item[key] ?? "",
        ])
      )
    );
    setMaintenanceMessage("");
  }

  function cancelEditMaintenance() {
    setEditingMaintenance(null);
    setMaintenanceForm(emptyMaintenance);
  }

  async function deleteMaintenance(item) {
    if (
      !window.confirm(
        `Delete the ${item.maintenanceType} record from ${item.performedDate}?`
      )
    ) {
      return;
    }

    setMaintenanceMessage("");

    try {
      const result = await api(
        maintenancePath(item.maintenanceId),
        { method: "DELETE" }
      );

      if (editingMaintenanceId === item.maintenanceId) {
        cancelEditMaintenance();
      }

      setMaintenanceMessage(result.message);
      await loadMaintenance();
    } catch (error) {
      setMaintenanceMessage(error.message);
    }
  }

  async function recordMaintenance(event) {
    event.preventDefault();

    if (savingMaintenance) return;

    setSavingMaintenance(true);
    setMaintenanceMessage("");

    try {
      const payload = Object.fromEntries(
        Object.entries(maintenanceForm).map(
          ([key, value]) => [
            key,
            value === "" ? null : value,
          ]
        )
      );

      if (editingMaintenance) {
        payload.expectedUpdatedAt =
          editingMaintenance.updatedAt ?? null;
      }

      const result = await api(
        maintenancePath(editingMaintenanceId),
        {
          method: editingMaintenanceId ? "PUT" : "POST",
          body: JSON.stringify(payload),
        }
      );

      setMaintenanceMessage(result.message);
      setMaintenanceForm(emptyMaintenance);
      setEditingMaintenance(null);
      setAiRecommendation(null);
      await loadMaintenance();
    } catch (error) {
      setMaintenanceMessage(error.message);
    } finally {
      setSavingMaintenance(false);
    }
  }

  async function generateAiRecommendation() {
    if (generatingAi) return;

    setGeneratingAi(true);
    setMaintenanceMessage("");

    try {
      const result = await api(
        `/assets/${encodeURIComponent(
          asset.assetId
        )}/maintenance-recommendation`,
        {
          method: "POST",
        }
      );

      setSchedule(result.schedule || null);
      setAiRecommendation(
        result.aiRecommendation || null
      );
      setMaintenanceMessage( "" );
    } catch (error) {
      setMaintenanceMessage(error.message);
    } finally {
      setGeneratingAi(false);
    }
  }

  return (
    <main>
      <PageHeader
        eyebrow="MAINTENANCE INTELLIGENCE"
        title="Maintenance history and recommendations"
        user={user}
      >
        <div className="header-actions">
          <button
            type="button"
            className="secondary"
            onClick={onBack}
          >
            Back to inventory
          </button>

          <button
            type="button"
            className="secondary"
            onClick={signOut}
          >
            Sign out
          </button>
        </div>
      </PageHeader>

      {maintenanceMessage && (
        <Notice>{maintenanceMessage}</Notice>
      )}

      <Panel>
        <SectionHeading
          title={asset.assetTag}
          description={<p>{asset.description}</p>}
        >
          <StatusBadge>{asset.status || "Unknown"}</StatusBadge>
        </SectionHeading>

        <DetailList
          className="asset-summary"
          grouped
          items={[
            { label: "Asset ID", value: asset.assetId },
            { label: "Category", value: asset.category || "—" },
            { label: "Condition", value: asset.condition || "—" },
            { label: "Location", value: asset.location || "—" },
            {
              label: "In-service date",
              value: asset.inServiceDate || "—",
            },
          ]}
        />
      </Panel>

      <Panel>
        <h2>Depreciation</h2>

        {asset.depreciation ? (
          <DetailList
            className="asset-summary"
            grouped
            items={[
              {
                label: "Original purchase value",
                value: formatMoney(
                  asset.depreciation.originalPurchaseValue
                ),
              },
              {
                label: "Annual depreciation",
                value: formatMoney(
                  asset.depreciation.annualDepreciation
                ),
              },
              {
                label: "Accumulated depreciation",
                value: formatMoney(
                  asset.depreciation.accumulatedDepreciation
                ),
              },
              {
                label: "Current book value",
                value: formatMoney(
                  asset.depreciation.currentBookValue
                ),
              },
              {
                label: "Useful life consumed",
                value: `${asset.depreciation.usefulLifeConsumedPercent}%`,
              },
              {
                label: "Estimated replacement date",
                value: asset.depreciation.estimatedReplacementDate,
              },
            ]}
          />
        ) : (
          <p>
            Depreciation is unavailable because the asset is
            missing financial or in-service information.
          </p>
        )}
      </Panel>

      <section className="maintenance-grid">
        <Panel as="article">
          <SectionHeading title="Calculated schedule">
            {schedule?.maintenanceStatus && (
              <span
                className={`maintenance-status maintenance-${schedule.maintenanceStatus.toLowerCase()}`}
              >
                {schedule.maintenanceStatus}
              </span>
            )}
          </SectionHeading>

          {loading ? (
            <p>Loading maintenance schedule...</p>
          ) : schedule ? (
            <DetailList
              className="recommendation-details"
              items={[
                {
                  label: "Priority",
                  value: schedule.priority || "—",
                },
                {
                  label: "Recommended cleaning",
                  value: schedule.recommendedCleaningDate || "—",
                },
                {
                  label: "Recommended maintenance",
                  value: schedule.recommendedMaintenanceDate || "—",
                },
                {
                  label: "Days until maintenance",
                  value: schedule.daysUntilMaintenance ?? "—",
                },
                {
                  label: "Recommendation",
                  value:
                    schedule.recommendation ||
                    schedule.message ||
                    "—",
                },
              ]}
            />
          ) : (
            <p>No schedule is available.</p>
          )}
        </Panel>

        <Panel as="article">
          <SectionHeading title="Bedrock recommendation">
            <button
              type="button"
              onClick={generateAiRecommendation}
              disabled={generatingAi}
            >
              {generatingAi
                ? "Generating..."
                : "Generate recommendation"}
            </button>
          </SectionHeading>

          {aiRecommendation ? (
            <div className="ai-maintenance-result">
              <DetailList
                className="recommendation-details"
                items={[
                  {
                    label: "Risk level",
                    value: aiRecommendation.riskLevel,
                  },
                  {
                    label: "Review status",
                    value: aiRecommendation.reviewStatus,
                  },
                  {
                    label: "Rationale",
                    value: aiRecommendation.rationale,
                  },
                ]}
              />

              <h3>Recommended actions</h3>

              <ol>
                {aiRecommendation.recommendedActions.map(
                  (action) => (
                    <li key={action}>{action}</li>
                  )
                )}
              </ol>


            </div>
          ) : (
            <p>
              Generate an AI-assisted recommendation using
              the asset condition, maintenance history, and
              calculated schedule.
            </p>
          )}
        </Panel>
      </section>

      <Panel>
        <h2>
          {editingMaintenanceId
            ? `Edit maintenance ${editingMaintenanceId}`
            : "Record maintenance"}
        </h2>

        <form
          className="maintenance-form"
          onSubmit={recordMaintenance}
        >
          <label>
            <span>Maintenance type</span>
            <select
              name="maintenanceType"
              value={maintenanceForm.maintenanceType}
              onChange={updateMaintenanceField}
            >
              <option>Preventive</option>
              <option>Corrective</option>
              <option>Inspection</option>
              <option>Cleaning</option>
              <option>Repair</option>
            </select>
          </label>

          <label>
            <span>Performed date</span>
            <input
              type="date"
              name="performedDate"
              value={maintenanceForm.performedDate}
              onChange={updateMaintenanceField}
              required
            />
          </label>

          <label>
            <span>Condition after maintenance</span>
            <select
              name="conditionAfter"
              value={maintenanceForm.conditionAfter}
              onChange={updateMaintenanceField}
            >
              <option value="">Not recorded</option>
              <option>Excellent</option>
              <option>Good</option>
              <option>Fair</option>
              <option>Poor</option>
              <option>Damaged</option>
            </select>
          </label>

          <label>
            <span>Next maintenance date</span>
            <input
              type="date"
              name="nextMaintenanceDate"
              value={
                maintenanceForm.nextMaintenanceDate
              }
              onChange={updateMaintenanceField}
            />
          </label>

          <label>
            <span>Cost</span>
            <input
              type="number"
              min="0"
              step="0.01"
              name="cost"
              value={maintenanceForm.cost}
              onChange={updateMaintenanceField}
            />
          </label>

          <label className="maintenance-description">
            <span>Description</span>
            <textarea
              name="description"
              value={maintenanceForm.description}
              onChange={updateMaintenanceField}
              required
              rows="4"
            />
          </label>

          <button
            type="submit"
            disabled={savingMaintenance}
          >
            {savingMaintenance
              ? "Saving..."
              : editingMaintenanceId
                ? "Save changes"
                : "Record maintenance"}
          </button>

          {editingMaintenanceId && (
            <button
              type="button"
              className="secondary"
              onClick={cancelEditMaintenance}
              disabled={savingMaintenance}
            >
              Cancel
            </button>
          )}
        </form>
      </Panel>

      <Panel>
        <SectionHeading title="Maintenance history">
          <button
            type="button"
            className="secondary"
            onClick={loadMaintenance}
            disabled={loading}
          >
            Refresh
          </button>
        </SectionHeading>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Type</th>
                <th>Description</th>
                <th>Condition after</th>
                <th>Next maintenance</th>
                <th>Cost</th>
                <th>Performed by</th>
                {showMaintenanceActions && <th>Actions</th>}
              </tr>
            </thead>

            <tbody>
              {history.length ? (
                history.map((item) => (
                  <tr key={item.maintenanceId}>
                    <td>{item.performedDate || "—"}</td>
                    <td>
                      {item.maintenanceType || "—"}
                    </td>
                    <td>{item.description || "—"}</td>
                    <td>
                      {item.conditionAfter || "—"}
                    </td>
                    <td>
                      {item.nextMaintenanceDate || "—"}
                    </td>
                    <td>
                      {item.cost !== undefined
                        ? `$${item.cost}`
                        : "—"}
                    </td>
                    <td>
                      {item.performedByEmail ||
                        item.performedBy ||
                        "—"}
                    </td>
                    {showMaintenanceActions && (
                      <td>
                        {canEditMaintenance(item) && (
                          <button
                            type="button"
                            className="secondary table-action"
                            onClick={() => editMaintenance(item)}
                          >
                            Edit
                          </button>
                        )}{" "}
                        {isAdministrator && (
                          <button
                            type="button"
                            className="secondary table-action"
                            onClick={() => deleteMaintenance(item)}
                          >
                            Delete
                          </button>
                        )}
                      </td>
                    )}
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={showMaintenanceActions ? 8 : 7}>
                    {loading
                      ? "Loading maintenance history..."
                      : "No maintenance history has been recorded."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>
    </main>
  );
}

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
  <div className="analysis-result">
    <h3>Bedrock suggestions</h3>

    <DetailList
      items={[
        { label: "Category", value: analysis.category || "—" },
        { label: "Description", value: analysis.description || "—" },
        { label: "Condition", value: analysis.condition || "—" },
        { label: "Manufacturer", value: analysis.manufacturer || "—" },
        { label: "Model", value: analysis.model || "—" },
        {
          label: "Useful life",
          value: analysis.usefulLifeMonths
            ? `${analysis.usefulLifeMonths} months`
            : "—",
        },
        {
          label: "Maintenance category",
          value: analysis.maintenanceCategory || "—",
        },
        {
          label: "Review status",
          value: analysis.reviewStatus || "Needs review",
        },
      ]}
    />

    <div className="analysis-actions">
      <button
        type="button"
        onClick={applyAnalysis}
      >
        Apply suggestions
      </button>

      <button
        type="button"
        className="secondary"
        onClick={rejectAnalysis}
      >
        Reject suggestions
      </button>
    </div>
  </div>
)}
          </div>
          <button type="submit" disabled={saving || uploading}>
            {saving ? "Creating..." : "Create asset"}
          </button>
        </form>
      </Panel>

      <Panel className="gallery-panel">
        <SectionHeading
          title="Asset photo gallery"
          description={
            <p className="gallery-intro">
              Only photographs for assets authorized by your Cognito
              role are shown.
            </p>
          }
        >
          <button
            type="button"
            className="secondary gallery-refresh"
            disabled={galleryLoading}
            onClick={loadGallery}
          >
            {galleryLoading
              ? "Loading..."
              : "Refresh gallery"}
          </button>
        </SectionHeading>

        {galleryMessage && <Notice>{galleryMessage}</Notice>}

        {!galleryLoading && !galleryItems.length && (
          <p className="gallery-empty">
            No authorized assets with photographs were found.
          </p>
        )}

        <div
          className="asset-gallery"
          aria-busy={galleryLoading}
        >
          {galleryItems.map((asset) => {
            const suggestion = asset.suggestion;

            return (
              <article
                className="asset-photo-card"
                key={asset.assetId}
              >
                <img
                  className="asset-gallery-image"
                  src={asset.photoUrl}
                  alt={`${asset.assetTag} ${
                    asset.category || "asset"
                  }`}
                  loading="lazy"
                />

                <div className="asset-photo-content">
                  <div className="asset-photo-title">
                    <div>
                      <p className="asset-photo-tag">
                        {asset.assetTag}
                      </p>
                      <h3>
                        {asset.category ||
                          "Uncategorized asset"}
                      </h3>
                    </div>

                    <StatusBadge>{asset.status}</StatusBadge>
                  </div>

                  <p>
                    {asset.description ||
                      "No description provided."}
                  </p>

                  <DetailList
                    className="asset-photo-meta"
                    items={[
                      {
                        label: "Department",
                        value: asset.department || "—",
                      },
                      {
                        label: "Condition",
                        value: asset.condition || "—",
                      },
                    ]}
                  />

                  <div className="gallery-analysis">
                    <div className="gallery-analysis-heading">
                      <h4>Bedrock insight</h4>
                      <span className="analysis-badge">
                        {asset.analysisStatus ||
                          "Processing"}
                      </span>
                    </div>

                    {suggestion ? (
                      <DetailList
                        items={[
                          {
                            label: "Detected category",
                            value: suggestion.category || "—",
                          },
                          {
                            label: "Description",
                            value: suggestion.description || "—",
                          },
                          {
                            label: "Maintenance",
                            value:
                              suggestion.maintenanceCategory || "—",
                          },
                          {
                            label: "Review",
                            value:
                              suggestion.reviewStatus ||
                              "Needs review",
                          },
                        ]}
                      />
                    ) : (
                      <p>
                        The AI analysis is still processing or
                        has no suggestion.
                      </p>
                    )}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </Panel>

      <Panel>
        <SectionHeading title="Authorized inventory">
          <div className="search">
            <input aria-label="Search assets" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search tag or description" />
            <button className="secondary" onClick={loadAssets}>Search</button>
          </div>
        </SectionHeading>
        <div className="table-wrap">
          <table>
  <thead>
    <tr>
      <th>Tag</th>
      <th>Category</th>
      <th>Description</th>
      <th>Department</th>
      <th>Location</th>
      <th>Status</th>
      <th>Maintenance</th>
    </tr>
  </thead>

  <tbody>
    {assets.map((asset) => (
      <tr key={asset.assetId}>
        <td>{asset.assetTag}</td>
        <td>{asset.category}</td>
        <td>{asset.description}</td>
        <td>{asset.department || "—"}</td>
        <td>{asset.location || "—"}</td>
        <td>
          <StatusBadge>{asset.status}</StatusBadge>
        </td>
        <td>
          <button
            type="button"
            className="secondary table-action"
            onClick={() => setMaintenanceAsset(asset)}
          >
            View maintenance
          </button>
        </td>
      </tr>
    ))}
  </tbody>
</table>
        </div>

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
