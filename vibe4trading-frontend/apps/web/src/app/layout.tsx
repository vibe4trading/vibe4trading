import type { Metadata } from "next";
import { DotGothic16 } from "next/font/google";
import "./globals.css";

import { RouteWrapper } from "@/app/components/RouteWrapper";
import { SessionProvider } from "next-auth/react";

const dotGothic = DotGothic16({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-dot-gothic",
});

export const metadata: Metadata = {
  title: "vibe4trading",
  description: "LLM trading benchmark dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={dotGothic.variable}>
        <SessionProvider>
          <RouteWrapper>
            {children}
          </RouteWrapper>
        </SessionProvider>
      </body>
    </html>
  );
}
