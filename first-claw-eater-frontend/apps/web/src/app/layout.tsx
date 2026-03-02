import type { Metadata } from "next";
import { DM_Serif_Display, IBM_Plex_Mono, Space_Grotesk } from "next/font/google";
import "./globals.css";

import { SiteHeader } from "@/app/components/SiteHeader";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space",
  subsets: ["latin"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  weight: ["400", "500"],
  subsets: ["latin"],
});

const dmSerif = DM_Serif_Display({
  variable: "--font-display",
  weight: ["400"],
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "First Claw Eater",
  description: "LLM trading benchmark dashboard (MVP)",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${spaceGrotesk.variable} ${plexMono.variable} ${dmSerif.variable} antialiased`}
      >
        <div className="min-h-dvh bg-[color:var(--bg)] text-[color:var(--ink)]">
          <div className="pointer-events-none fixed inset-0 -z-10 opacity-100">
            <div className="absolute -left-40 -top-40 h-[480px] w-[480px] rounded-full bg-[radial-gradient(circle_at_center,rgba(20,184,166,0.18),transparent_60%)]" />
            <div className="absolute -right-56 top-16 h-[560px] w-[560px] rounded-full bg-[radial-gradient(circle_at_center,rgba(249,115,22,0.14),transparent_60%)]" />
            <div className="absolute left-1/2 top-[60vh] h-[520px] w-[520px] -translate-x-1/2 rounded-full bg-[radial-gradient(circle_at_center,rgba(15,23,42,0.10),transparent_62%)]" />
          </div>

          <SiteHeader />
          <main className="mx-auto w-full max-w-6xl px-5 py-10">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
