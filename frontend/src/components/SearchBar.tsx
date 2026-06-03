import { useState } from "react";

// TODO(phase 10): styling + loading state.
export function SearchBar({ onSubmit }: { onSubmit: (q: string) => void }) {
  const [value, setValue] = useState("");
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (value.trim()) onSubmit(value.trim());
      }}
      style={{ display: "flex", gap: 8 }}
    >
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Ask a research question..."
        style={{ flex: 1, padding: 8 }}
      />
      <button type="submit">Search</button>
    </form>
  );
}
