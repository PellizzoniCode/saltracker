import { useCallback, useEffect, useRef, useState } from "react";

const MAINTENANCE_TYPES = ["Cleaning", "Inspection", "Repair", "Preventive", "Upgrade", "Other"];
const CONDITIONS = ["Good", "Fair", "Poor", "Unknown"];

function today() {
  return new Date().toLocaleDateString("en-CA");
}

function emptyRecord() {
  return {
    performedDate: today(),
    maintenanceType: "Cleaning",
    conditionAfterService: "Good",
    cost: "",
    notes: "",
  };
}

export default function MaintenanceHistory({ api, asset, groups, onClose }) {
  const [records, setRecords] = useState([]);
  const [nextToken, setNextToken] = useState(null);
  const [form, setForm] = useState(emptyRecord);
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  const canRecord = groups.includes("Technician") || groups.includes("Administrator");
  const canManage = groups.includes("Administrator");
  const basePath = `/assets/${encodeURIComponent(asset.assetId)}/maintenance`;
  // The asset currently on screen; responses for any other asset are discarded.
  const activePath = useRef(basePath);
  activePath.current = basePath;

  const loadRecords = useCallback(async ({ append = false, token = null } = {}) => {
    try {
      const query = token ? `?nextToken=${encodeURIComponent(token)}` : "";
      const result = await api(`${basePath}${query}`);
      if (activePath.current !== basePath) return;
      setRecords((current) => (append ? [...current, ...result.items] : result.items));
      setNextToken(result.nextToken || null);
    } catch (error) {
      if (activePath.current === basePath) setMessage(error.message);
    }
  }, [api, basePath]);

  useEffect(() => {
    setRecords([]);
    setNextToken(null);
    setForm(emptyRecord());
    setMessage("");
    loadRecords();
  }, [loadRecords]);

  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function recordMaintenance(event) {
    event.preventDefault();
    if (saving) return;
    setSaving(true);

    try {
      // performedBy is never sent: the API takes it from the signed-in identity.
      const payload = Object.fromEntries(
        Object.entries(form).map(([key, value]) => [key, value === "" ? null : value])
      );
      const result = await api(basePath, { method: "POST", body: JSON.stringify(payload) });
      if (activePath.current !== basePath) return;
      setMessage(`${result.message} ID: ${result.maintenanceId}`);
      setForm(emptyRecord());
      await loadRecords();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setSaving(false);
    }
  }

  async function deleteRecord(record) {
    if (!window.confirm(`Delete maintenance record ${record.maintenanceId}?`)) return;

    try {
      const result = await api(`${basePath}/${encodeURIComponent(record.maintenanceId)}`, { method: "DELETE" });
      if (activePath.current !== basePath) return;
      setMessage(result.message);
      await loadRecords();
    } catch (error) {
      setMessage(error.message);
    }
  }

  return (
    <section className="panel">
      <div className="section-heading">
        <h2>Maintenance history — {asset.assetTag}</h2>
        <button className="secondary" onClick={onClose}>Close</button>
      </div>

      {message && <p className="maintenance-message" role="status">{message}</p>}

      {canRecord && (
        <form className="maintenance-form" onSubmit={recordMaintenance}>
          <label>
            <span>Performed date</span>
            <input name="performedDate" type="date" max={today()} value={form.performedDate} onChange={updateField} required />
          </label>
          <label>
            <span>Maintenance type</span>
            <select name="maintenanceType" value={form.maintenanceType} onChange={updateField}>
              {MAINTENANCE_TYPES.map((type) => <option key={type}>{type}</option>)}
            </select>
          </label>
          <label>
            <span>Condition after service</span>
            <select name="conditionAfterService" value={form.conditionAfterService} onChange={updateField}>
              {CONDITIONS.map((condition) => <option key={condition}>{condition}</option>)}
            </select>
          </label>
          <label>
            <span>Cost</span>
            <input name="cost" type="number" min="0" step="0.01" value={form.cost} onChange={updateField} />
          </label>
          <label className="maintenance-notes">
            <span>Notes</span>
            <textarea name="notes" maxLength={2000} rows={2} value={form.notes} onChange={updateField} />
          </label>
          <button type="submit" disabled={saving}>
            {saving ? "Recording..." : "Record maintenance"}
          </button>
        </form>
      )}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Date</th><th>Type</th><th>Condition after</th><th>Cost</th><th>Notes</th><th>Performed by</th>
              {canManage && <th aria-label="Actions" />}
            </tr>
          </thead>
          <tbody>
            {records.map((record) => (
              <tr key={record.maintenanceId}>
                <td>{record.performedDate}</td>
                <td>{record.maintenanceType}</td>
                <td>{record.conditionAfterService || "—"}</td>
                <td>{record.cost ?? "—"}</td>
                <td>{record.notes || "—"}</td>
                <td>{record.performedBy}</td>
                {canManage && (
                  <td><button className="secondary" onClick={() => deleteRecord(record)}>Delete</button></td>
                )}
              </tr>
            ))}
            {records.length === 0 && (
              <tr><td colSpan={canManage ? 7 : 6}>No maintenance has been recorded for this asset.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {nextToken && (
        <button className="secondary" onClick={() => loadRecords({ append: true, token: nextToken })}>
          Load more
        </button>
      )}
    </section>
  );
}
