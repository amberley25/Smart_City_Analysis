import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const target = process.env.VITE_PROXY_TARGET ?? "http://127.0.0.1:5000";

// In development and preview the SPA talks to the API through a same-origin /api proxy,
// so the browser needs no CORS handling and the code uses relative URLs.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": target } },
  preview: { proxy: { "/api": target } },
});
