import { Panel } from "../../components/Panel.jsx";

export function MaintenanceForm({
  form,
  editingId,
  saving,
  onChange,
  onSubmit,
  onCancel,
}) {
  return (
    <Panel>
      <h2>
        {editingId
          ? `Edit maintenance ${editingId}`
          : "Record maintenance"}
      </h2>

      <form
        className="maintenance-form"
        onSubmit={onSubmit}
      >
        <label>
          <span>Maintenance type</span>
          <select
            name="maintenanceType"
            value={form.maintenanceType}
            onChange={onChange}
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
            value={form.performedDate}
            onChange={onChange}
            required
          />
        </label>

        <label>
          <span>Condition after maintenance</span>
          <select
            name="conditionAfter"
            value={form.conditionAfter}
            onChange={onChange}
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
              form.nextMaintenanceDate
            }
            onChange={onChange}
          />
        </label>

        <label>
          <span>Cost</span>
          <input
            type="number"
            min="0"
            step="0.01"
            name="cost"
            value={form.cost}
            onChange={onChange}
          />
        </label>

        <label className="maintenance-description">
          <span>Description</span>
          <textarea
            name="description"
            value={form.description}
            onChange={onChange}
            required
            rows="4"
          />
        </label>

        <button
          type="submit"
          disabled={saving}
        >
          {saving
            ? "Saving..."
            : editingId
              ? "Save changes"
              : "Record maintenance"}
        </button>

        {editingId && (
          <button
            type="button"
            className="secondary"
            onClick={onCancel}
            disabled={saving}
          >
            Cancel
          </button>
        )}
      </form>
    </Panel>
  );
}
