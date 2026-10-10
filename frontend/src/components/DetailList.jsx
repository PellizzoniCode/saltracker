import { Fragment } from "react";

// Renders label/value pairs as a <dl>. Values are rendered as given, so
// callers decide their own empty-value fallback.
//   grouped=false: flat <dt><dd> pairs (recommendation-details, gallery)
//   grouped=true:  each pair wrapped in a <div> (asset-summary)
export function DetailList({ items, className, grouped = false }) {
  return (
    <dl className={className}>
      {items.map(({ label, value }) => {
        const pair = (
          <>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </>
        );

        return grouped ? (
          <div key={label}>{pair}</div>
        ) : (
          <Fragment key={label}>{pair}</Fragment>
        );
      })}
    </dl>
  );
}
