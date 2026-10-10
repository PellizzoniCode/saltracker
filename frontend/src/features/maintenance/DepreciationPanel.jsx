import { DetailList } from "../../components/DetailList.jsx";
import { Panel } from "../../components/Panel.jsx";
import { formatMoney } from "../../utils/format.js";

export function DepreciationPanel({ depreciation }) {
  return (
    <Panel>
      <h2>Depreciation</h2>

      {depreciation ? (
        <DetailList
          className="asset-summary"
          grouped
          items={[
            {
              label: "Original purchase value",
              value: formatMoney(
                depreciation.originalPurchaseValue
              ),
            },
            {
              label: "Annual depreciation",
              value: formatMoney(
                depreciation.annualDepreciation
              ),
            },
            {
              label: "Accumulated depreciation",
              value: formatMoney(
                depreciation.accumulatedDepreciation
              ),
            },
            {
              label: "Current book value",
              value: formatMoney(
                depreciation.currentBookValue
              ),
            },
            {
              label: "Useful life consumed",
              value: `${depreciation.usefulLifeConsumedPercent}%`,
            },
            {
              label: "Estimated replacement date",
              value: depreciation.estimatedReplacementDate,
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
  );
}
