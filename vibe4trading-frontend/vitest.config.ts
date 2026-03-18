import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    include: ["tests/**/*.{test,spec}.{ts,tsx}", "src/**/*.{test,spec}.{ts,tsx}"],
    exclude: ["e2e/**", "node_modules/**", ".next/**"],
  },
});
