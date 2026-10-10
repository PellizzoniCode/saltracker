import { Panel } from "../../components/Panel.jsx";
import { SectionHeading } from "../../components/SectionHeading.jsx";

export function MaintenanceHistoryTable({
  history,
  loading,
  showActions,
  canEdit,
  isAdministrator,
  onEdit,
  onDelete,
  onRefresh,
}) {
  return (
    <Panel>
      <SectionHeading title="Maintenance history">
        <button
          type="button"
          className="secondary"
          onClick={onRefresh}
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
              {showActions && <th>Actions</th>}
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
                  {showActions && (
                    <td>
                      {canEdit(item) && (
                        <button
                          type="button"
                          className="secondary table-action"
                          onClick={() => onEdit(item)}
                        >
                          Edit
                        </button>
                      )}{" "}
                      {isAdministrator && (
                        <button
                          type="button"
                          className="secondary table-action"
                          onClick={() => onDelete(item)}
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
                <td colSpan={showActions ? 8 : 7}>
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
  );
}
