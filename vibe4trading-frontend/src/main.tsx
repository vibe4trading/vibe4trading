import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HelmetProvider } from "react-helmet-async";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "@/auth";
import App from "@/App";
import "@/app/globals.css";

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
