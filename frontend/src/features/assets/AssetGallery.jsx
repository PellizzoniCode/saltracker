import { Notice } from "../../components/Notice.jsx";
import { Panel } from "../../components/Panel.jsx";
import { SectionHeading } from "../../components/SectionHeading.jsx";
import { AssetPhotoCard } from "./AssetPhotoCard.jsx";

export function AssetGallery({ items, loading, message, onRefresh }) {
  return (
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
          disabled={loading}
          onClick={onRefresh}
        >
          {loading
            ? "Loading..."
            : "Refresh gallery"}
        </button>
      </SectionHeading>

      {message && <Notice>{message}</Notice>}

      {!loading && !items.length && (
        <p className="gallery-empty">
          No authorized assets with photographs were found.
        </p>
      )}

      <div
        className="asset-gallery"
        aria-busy={loading}
      >
        {items.map((asset) => (
          <AssetPhotoCard key={asset.assetId} asset={asset} />
        ))}
      </div>
    </Panel>
  );
}
