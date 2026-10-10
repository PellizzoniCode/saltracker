// `description` is rendered next to the title inside a wrapper <div>; without
// it the <h2> sits directly in the heading. `children` is the trailing
// content (badge, button, search box).
export function SectionHeading({ title, description, children }) {
  return (
    <div className="section-heading">
      {description ? (
        <div>
          <h2>{title}</h2>
          {description}
        </div>
      ) : (
        <h2>{title}</h2>
      )}

      {children}
    </div>
  );
}
