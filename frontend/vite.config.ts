import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// TODO(phase 10): tune proxy/build. Proxy /api to the FastAPI backend in dev.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/health": "http://localhost:8000",
      "/ingest": "http://localhost:8000",
      "/models": "http://localhost:8000",
      "/papers": "http://localhost:8000",
      "/search": "http://localhost:8000",
      "/review": "http://localhost:8000",
    },
  },
});
