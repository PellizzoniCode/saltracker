import { DetailList } from "../../components/DetailList.jsx";
import { StatusBadge } from "../../components/StatusBadge.jsx";

export function AssetPhotoCard({ asset }) {
  const suggestion = asset.suggestion;

  return (
    <article className="asset-photo-card">
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
}
