import { StatusBadge } from "../../components/StatusBadge.jsx";

export function AssetTable({ assets, onViewMaintenance }) {
  return (
            <div className="table-wrap">
              <table>
      <thead>
        <tr>
          <th>Tag</th>
          <th>Category</th>
          <th>Description</th>
          <th>Department</th>
          <th>Location</th>
          <th>Status</th>
          <th>Maintenance</th>
        </tr>
      </thead>

      <tbody>
        {assets.map((asset) => (
          <tr key={asset.assetId}>
            <td>{asset.assetTag}</td>
            <td>{asset.category}</td>
            <td>{asset.description}</td>
            <td>{asset.department || "—"}</td>
            <td>{asset.location || "—"}</td>
            <td>
              <StatusBadge>{asset.status}</StatusBadge>
            </td>
            <td>
              <button
                type="button"
                className="secondary table-action"
                onClick={() => onViewMaintenance(asset)}
              >
                View maintenance
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
            </div>
  );
}
