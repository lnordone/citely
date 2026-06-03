import { useState } from "react";
import { SearchBar } from "./components/SearchBar";
import { ResultsList } from "./components/ResultsList";
import { ReviewView } from "./components/ReviewView";
import { search, streamReview, SourceOut } from "./api";

// TODO(phase 10): query box + results + streamed review view. Minimal scaffold below.
export function App() {
  const [sources, setSources] = useState<SourceOut[]>([]);
  const [review, setReview] = useState("");

  async function onSubmit(query: string) {
    setReview("");
    const res = await search(query);
    setSources(res.sources);
    await streamReview(query, (chunk) => setReview((prev) => prev + chunk));
  }

  return (
    <main style={{ maxWidth: 820, margin: "2rem auto", fontFamily: "system-ui" }}>
      <h1>Citely</h1>
      <SearchBar onSubmit={onSubmit} />
      <ResultsList sources={sources} />
      <ReviewView markdown={review} />
    </main>
  );
}
