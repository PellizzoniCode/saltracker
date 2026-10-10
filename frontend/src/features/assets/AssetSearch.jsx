export function AssetSearch({ query, onQueryChange, onSearch }) {
  return (
    <div className="search">
      <input aria-label="Search assets" value={query} onChange={(event) => onQueryChange(event.target.value)} placeholder="Search tag or description" />
      <button className="secondary" onClick={onSearch}>Search</button>
    </div>
  );
}
