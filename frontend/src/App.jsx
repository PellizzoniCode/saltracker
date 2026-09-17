import { useCallback, useEffect, useState } from "react";
import { Authenticator } from "@aws-amplify/ui-react";
import { fetchAuthSession } from "aws-amplify/auth";

const API_URL = import.meta.env.VITE_API_URL;

const emptyAsset = {
  assetTag: "",
  category: "Laptop",
  description: "",
  manufacturer: "",
  model: "",
  serialNumber: "",
  purchaseDate: "",
  inServiceDate: "",
  purchaseValue: "",
  salvageValue: "0.00",
  usefulLifeMonths: 48,
  department: "",
  assignedUserId: "",
  condition: "Good",
  status: "Available",
};

async function api(path, options = {}) {
  const session = await fetchAuthSession();
  const token = session.tokens?.idToken?.toString();
  const result = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", Authorization: token, ...options.headers },
  });
  const body = await result.json();
  if (!result.ok) throw new Error(body.message || "Request failed");
  return body;
}

function AssetApplication({ signOut, user }) {
  const [assets, setAssets] = useState([]);
  const [form, setForm] = useState(emptyAsset);
  const [message, setMessage] = useState("");
  const [query, setQuery] = useState("");
const [saving, setSaving] = useState(false);

  const loadAssets = useCallback(async () => {
    try {
      const result = await api(`/assets${query ? `?q=${encodeURIComponent(query)}` : ""}`);
      setAssets(result.items);
      setMessage("");
    } catch (error) {
      setMessage(error.message);
    }
  }, [query]);

  useEffect(() => {
    loadAssets();
  }, [loadAssets]);

  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: name === "usefulLifeMonths" ? Number(value) : value }));
  }

  async function createAsset(event) {
    event.preventDefault();
  if (saving) return;
  setSaving(true);
    try {
      const payload = Object.fromEntries(Object.entries(form).map(([key, value]) => [key, value === "" ? null : value]));
      const result = await api("/assets", { method: "POST", body: JSON.stringify(payload) });
      setMessage(`${result.message} ID: ${result.assetId}`);
      setForm(emptyAsset);
      await loadAssets();
    } catch (error) {
      setMessage(error.message);
    } finally {
  setSaving(false);
}
  }

  return (
    <main>
      <header>
        <div>
          <p className="eyebrow">AWS CLOUD SECURITY PORTFOLIO</p>
          <h1>Smart Asset Lifecycle Tracker</h1>
          <p>Signed in as {user?.signInDetails?.loginId}</p>
        </div>
        <button className="secondary" onClick={signOut}>Sign out</button>
      </header>

      {message && <div className="notice" role="status">{message}</div>}

      <section className="panel">
        <h2>Register an asset manually</h2>
        <form onSubmit={createAsset}>
          {Object.entries(form).map(([name, value]) => (
            <label key={name}>
              <span>{name.replace(/([A-Z])/g, " $1")}</span>
              <input
                name={name}
                value={value ?? ""}
                type={name.includes("Date") ? "date" : name === "usefulLifeMonths" ? "number" : "text"}
                onChange={updateField}
                required={["assetTag", "description", "purchaseDate", "inServiceDate", "purchaseValue"].includes(name)}
              />
            </label>
          ))}
          <button type="submit" disabled={saving}>
  {saving ? "Creating..." : "Create asset"}
</button>
        </form>
      </section>

      <section className="panel">
        <div className="section-heading">
          <h2>Authorized inventory</h2>
          <div className="search">
            <input aria-label="Search assets" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search tag or description" />
            <button className="secondary" onClick={loadAssets}>Search</button>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Tag</th><th>Category</th><th>Description</th><th>Department</th><th>Status</th></tr></thead>
            <tbody>
              {assets.map((asset) => (
                <tr key={asset.assetId}><td>{asset.assetTag}</td><td>{asset.category}</td><td>{asset.description}</td><td>{asset.department || "—"}</td><td><span className="status">{asset.status}</span></td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

export default function App() {
  return <Authenticator>{({ signOut, user }) => <AssetApplication signOut={signOut} user={user} />}</Authenticator>;
}

