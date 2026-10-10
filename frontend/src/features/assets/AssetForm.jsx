import { Panel } from "../../components/Panel.jsx";

// `children` is the photo uploader, rendered between the fields and the
// submit button.
export function AssetForm({
  form,
  saving,
  uploading,
  onChange,
  onSubmit,
  children,
}) {
  return (
    <Panel>
      <h2>Register an asset manually</h2>
      <form onSubmit={onSubmit}>
        {Object.entries(form).filter(([name]) => name !== "imageKey").map(([name, value]) => (
          <label key={name}>
            <span>{name.replace(/([A-Z])/g, " $1")}</span>
            <input
              name={name}
              value={value ?? ""}
              type={name.includes("Date") ? "date" : name === "usefulLifeMonths" ? "number" : "text"}
              onChange={onChange}
              required={["assetTag", "description", "purchaseDate", "inServiceDate", "purchaseValue"].includes(name)}
            />
          </label>
        ))}
        {children}
        <button type="submit" disabled={saving || uploading}>
          {saving ? "Creating..." : "Create asset"}
        </button>
      </form>
    </Panel>
  );
}
