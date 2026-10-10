import { useState } from "react";
import { api } from "../../api/client.js";
import { Notice } from "../../components/Notice.jsx";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Panel } from "../../components/Panel.jsx";
import { SectionHeading } from "../../components/SectionHeading.jsx";
import { emptyAsset } from "../../constants/asset.js";
import { useAssetGallery } from "../../hooks/useAssetGallery.js";
import { useAssets } from "../../hooks/useAssets.js";
import { usePhotoAnalysis } from "../../hooks/usePhotoAnalysis.js";
import { MaintenancePage } from "../maintenance/MaintenancePage.jsx";
import { AssetForm } from "./AssetForm.jsx";
import { AssetGallery } from "./AssetGallery.jsx";
import { AssetSearch } from "./AssetSearch.jsx";
import { AssetTable } from "./AssetTable.jsx";
import { PhotoUploader } from "./PhotoUploader.jsx";

// Holds the inventory state and also renders the maintenance view for the
// selected asset, so the form, photo and search state survive the round trip.

export function AssetsPage({ signOut, user }) {
  const {
    assets,
    nextToken,
    message,
    setMessage,
    query,
    setQuery,
    loadAssets,
  } = useAssets();
  const { galleryItems, galleryLoading, galleryMessage, loadGallery } =
    useAssetGallery(assets);
  const [maintenanceAsset, setMaintenanceAsset] = useState(null);
  const [form, setForm] = useState(emptyAsset);
  const [saving, setSaving] = useState(false);
  const {
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
  } = usePhotoAnalysis({ setForm, saving });

  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: name === "usefulLifeMonths" ? Number(value) : value }));
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
      resetPhoto();
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

      <AssetForm
        form={form}
        saving={saving}
        uploading={uploading}
        onChange={updateField}
        onSubmit={createAsset}
      >
        <PhotoUploader
          inputRef={photoInput}
          photo={photo}
          uploading={uploading}
          saving={saving}
          photoMessage={photoMessage}
          analysisMessage={analysisMessage}
          checkingAnalysis={checkingAnalysis}
          analysis={analysis}
          onSelect={selectPhoto}
          onUpload={uploadPhoto}
          onApply={applyAnalysis}
          onReject={rejectAnalysis}
        />
      </AssetForm>

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
