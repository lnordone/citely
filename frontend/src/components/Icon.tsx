// Thin wrapper over Google Material Symbols (loaded via index.html).
export function Icon({
  name,
  className = "",
  filled = false,
}: {
  name: string;
  className?: string;
  filled?: boolean;
}) {
  return (
    <span className={`material-symbols-outlined${filled ? " filled" : ""} ${className}`} aria-hidden>
      {name}
    </span>
  );
}
