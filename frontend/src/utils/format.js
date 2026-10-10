export function formatMoney(value) {
  return value === undefined || value === null ? "—" : `$${value}`;
}
