import { useNavigate } from "react-router-dom";
import { Icon } from "../components/Icon";

// NOTE(pending-backend): there is no endpoint to list the ingested corpus
// (GET /papers or /papers/{id}). This screen is intentionally a placeholder until the
// backend exposes paper listing; the search and review flows are fully wired.
export function LibraryPage() {
  const navigate = useNavigate();
  return (
    <div className="max-w-article-width mx-auto px-margin-mobile md:px-8 py-10 md:py-16 w-full">
      <div className="mb-12">
        <h1 className="font-display-lg text-display-lg text-on-surface mb-2">Local Library</h1>
        <p className="font-article-body text-article-body text-on-surface-variant">
          Browse and manage your ingested research corpus.
        </p>
      </div>

      <div className="border border-dashed border-outline-variant rounded-xl p-10 flex flex-col items-center text-center bg-surface-container-lowest">
        <Icon name="menu_book" className="text-[40px] text-outline mb-4" />
        <h2 className="font-headline-lg text-[20px] text-on-surface mb-2">Corpus browsing coming soon</h2>
        <p className="font-ui-label-md text-ui-label-md text-on-surface-variant max-w-md mb-6">
          Listing stored papers needs a backend endpoint (e.g. <code>GET /papers</code>) that
          isn’t implemented yet. In the meantime, search retrieves passages directly and the
          workspace synthesizes cited reviews.
        </p>
        <div className="flex gap-3">
          <button
            onClick={() => navigate("/search")}
            className="bg-primary text-on-primary font-ui-label-md text-ui-label-md px-5 py-2 rounded flex items-center gap-2 hover:opacity-90 transition-opacity"
          >
            <Icon name="search" className="text-[18px]" /> Go to Search
          </button>
          <button
            onClick={() => navigate("/ingest")}
            className="border border-outline-variant text-on-surface font-ui-label-md text-ui-label-md px-5 py-2 rounded flex items-center gap-2 hover:bg-surface-variant transition-colors"
          >
            <Icon name="upload_file" className="text-[18px]" /> Ingest Papers
          </button>
        </div>
      </div>
    </div>
  );
}
