import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HelmetProvider } from "react-helmet-async";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "@/auth";
import App from "@/App";
import "@/app/globals.css";

// Initialize prerender readiness flag before React mounts.
// Prerender service will wait for this to become `true` before capturing.
window.prerenderReady = false;

createRoot(document.getElementById("root")!).render(
  <HelmetProvider>
    <StrictMode>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </StrictMode>
  </HelmetProvider>,
);
