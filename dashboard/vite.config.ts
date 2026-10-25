import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const API_PORT = Number(process.env.DASHBOARD_API_PORT ?? 3847);

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": {
        target: `http://127.0.0.1:${API_PORT}`,
        changeOrigin: false,
      },
    },
  },
});
