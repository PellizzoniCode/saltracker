import { DetailList } from "../../components/DetailList.jsx";
import { Panel } from "../../components/Panel.jsx";
import { SectionHeading } from "../../components/SectionHeading.jsx";

export function AiRecommendationPanel({
  recommendation,
  generating,
  onGenerate,
}) {
  return (
    <Panel as="article">
      <SectionHeading title="Bedrock recommendation">
        <button
          type="button"
          onClick={onGenerate}
          disabled={generating}
        >
          {generating
            ? "Generating..."
            : "Generate recommendation"}
        </button>
      </SectionHeading>

      {recommendation ? (
        <div className="ai-maintenance-result">
          <DetailList
            className="recommendation-details"
            items={[
              {
                label: "Risk level",
                value: recommendation.riskLevel,
              },
              {
                label: "Review status",
                value: recommendation.reviewStatus,
              },
              {
                label: "Rationale",
                value: recommendation.rationale,
              },
            ]}
          />

          <h3>Recommended actions</h3>

          <ol>
            {recommendation.recommendedActions.map(
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
  );
}
