import { DetailList } from "../../components/DetailList.jsx";
import { Panel } from "../../components/Panel.jsx";
import { SectionHeading } from "../../components/SectionHeading.jsx";

export function SchedulePanel({ schedule, loading }) {
  return (
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
  );
}
