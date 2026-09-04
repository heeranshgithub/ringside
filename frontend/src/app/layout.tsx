import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Toaster } from "sonner";

import { AccessGate } from "@/components/access-gate";
import { AppShell } from "@/components/app-shell";
import { StoreProvider } from "@/store/provider";

import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "Hunar Hiring Assistant", template: "%s · Hunar Hiring" },
  description: "AI hiring assistant and people-search outreach powered by Hunar.AI voice agents.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <StoreProvider>
          <AppShell>
            <AccessGate>{children}</AccessGate>
          </AppShell>
          <Toaster richColors position="top-right" closeButton />
        </StoreProvider>
      </body>
    </html>
  );
}
