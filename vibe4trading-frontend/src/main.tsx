import { StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { HelmetProvider } from "react-helmet-async";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "@/auth";
import App from "@/App";
import "@/app/globals.css";
import "@/styles/fonts.css";
import "@/i18n/config";
import { initJoyID } from "@/lib/joyid";

// Initialize prerender readiness flag before React mounts.
// Prerender service will wait for this to become `true` before capturing.
window.prerenderReady = false;

// Initialize JoyID SDK
initJoyID();

createRoot(document.getElementById("root")!).render(
  <HelmetProvider>
    <StrictMode>
      <BrowserRouter>
        <AuthProvider>
          <Suspense fallback={<div>Loading...</div>}>
            <App />
          </Suspense>
        </AuthProvider>
      </BrowserRouter>
    </StrictMode>
  </HelmetProvider>,
);
