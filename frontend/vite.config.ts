import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies /interact-backend/* to the FastAPI backend (port 5000),
// stripping the prefix the same way the production reverse proxy does.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const target = env.BACKEND_URL || "http://127.0.0.1:5000";
  return {
    plugins: [react()],
    server: {
      port: 5001,
      proxy: {
        "/interact-backend": {
          target,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/interact-backend/, ""),
        },
      },
    },
  };
});
