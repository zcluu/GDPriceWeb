import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ command }) => {
  const isDev = command === "serve";

  return {
    plugins: [react()],
    build: {
      outDir: "../backend/app/static/frontend",
      emptyOutDir: true
    },
    server: isDev
      ? {
          port: 5173,
          proxy: {
            "/api": {
              target: process.env.VITE_DEV_API_TARGET || "http://127.0.0.1:8000",
              changeOrigin: true,
              ws: true
            }
          }
        }
      : undefined
  };
});
