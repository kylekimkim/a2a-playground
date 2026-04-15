import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/__tests__/setup.js",
  },
  server: {
    port: 5173,
    proxy: {
      "/.well-known": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/rooms": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/chat": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/upload": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/download": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
