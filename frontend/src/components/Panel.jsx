export function Panel({ as: Tag = "section", className, children }) {
  return (
    <Tag className={className ? `panel ${className}` : "panel"}>
      {children}
    </Tag>
  );
}
