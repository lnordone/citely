import { Navigate, Route, Routes } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { WorkspacePage } from "./pages/WorkspacePage";
import { SearchPage } from "./pages/SearchPage";
import { IngestPage } from "./pages/IngestPage";
import { LibraryPage } from "./pages/LibraryPage";

export function App() {
  return (
    <div className="min-h-screen flex bg-surface text-on-surface font-article-body selection:bg-inverse-primary selection:text-primary">
      <Sidebar />
      <main className="flex-1 flex flex-col md:ml-60 min-h-screen pb-16 md:pb-0">
        <Routes>
          <Route path="/" element={<Navigate to="/review" replace />} />
          <Route path="/review" element={<WorkspacePage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/ingest" element={<IngestPage />} />
          <Route path="/library" element={<LibraryPage />} />
          <Route path="*" element={<Navigate to="/review" replace />} />
        </Routes>
      </main>
    </div>
  );
}
