import { DetailList } from "../../components/DetailList.jsx";

export function AnalysisSuggestions({ analysis, onApply, onReject }) {
  return (
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
          onClick={onApply}
        >
          Apply suggestions
        </button>

        <button
          type="button"
          className="secondary"
          onClick={onReject}
        >
          Reject suggestions
        </button>
      </div>
    </div>
  );
}
