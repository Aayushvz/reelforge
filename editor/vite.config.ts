import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { reelforgeApi } from "./server/api";

export default defineConfig({
  plugins: [react(), reelforgeApi()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: { port: 5190, strictPort: true },
});
