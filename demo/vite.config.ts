import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev serves at "/"; production build is mounted at "/app/" by the FastAPI
// StaticFiles mount on the VM. Override with VITE_BASE if deploying elsewhere.
export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === "build" ? "/app/" : "/",
  server: { host: true, port: 5173 },
}));
