import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true,            // listen on 0.0.0.0 so the VPS IP can reach it
    allowedHosts: true,    // accept requests via the public IP host header
    proxy: {
      // Forward API calls to the FastAPI backend during development.
      "/chat": "http://localhost:8000",
      "/health": "http://localhost:8000",
      "/cv": "http://localhost:8000",
    },
  },
});
