// `children` are the header actions (sign-out button, or a .header-actions
// group) and are rendered as a sibling of the title block.
export function PageHeader({ eyebrow, title, user, children }) {
  return (
    <header>
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p>Signed in as {user?.signInDetails?.loginId}</p>
      </div>

      {children}
    </header>
  );
}
