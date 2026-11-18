import path from "node:path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Every FastAPI path the UI calls; the dev server forwards them to the server on :8000.
const api = ["/health", "/campaigns", "/state", "/log", "/action", "/roll", "/session", "/inventory", "/events"];

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  server: { proxy: Object.fromEntries(api.map((p) => [p, "http://localhost:8000"])) },
  test: { environment: "jsdom" },
});
