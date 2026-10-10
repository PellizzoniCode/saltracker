import { DetailList } from "../../components/DetailList.jsx";
import { Panel } from "../../components/Panel.jsx";
import { SectionHeading } from "../../components/SectionHeading.jsx";
import { StatusBadge } from "../../components/StatusBadge.jsx";

export function AssetSummaryPanel({ asset }) {
  return (
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
  );
}
