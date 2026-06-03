// TODO(phase 10): render cited markdown with clickable [S?] citation markers.
export function ReviewView({ markdown }: { markdown: string }) {
  if (!markdown) return null;
  return (
    <section>
      <h2>Review</h2>
      <pre style={{ whiteSpace: "pre-wrap" }}>{markdown}</pre>
    </section>
  );
}
