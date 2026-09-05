import type { Metadata } from "next";
import { Geist_Mono, Onest } from "next/font/google";
import { Toaster } from "sonner";

import { AccessGate } from "@/components/access-gate";
import { AppShell } from "@/components/app-shell";
import { ThemeProvider, themeScript } from "@/components/theme";
import { StoreProvider } from "@/store/provider";

import "./globals.css";

const onest = Onest({ variable: "--font-onest", subsets: ["latin"], display: "swap" });
const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  // The favicon carries the brand; the tab text carries the screen you are on,
  // because tab titles truncate and "ringside | …" spends the space on what you know.
  title: "ringside",
  description:
    "Voice-first hiring assistant. Screen candidates and reach out to sourced talent with Hunar.AI voice agents.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${onest.variable} ${geistMono.variable}`}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="antialiased">
        <ThemeProvider>
          <StoreProvider>
            <AppShell>
              <AccessGate>{children}</AccessGate>
            </AppShell>
            <Toaster
              position="top-right"
              closeButton
              toastOptions={{
                classNames: {
                  toast:
                    "!bg-popover !text-popover-foreground !border-border !rounded-lg backdrop-blur-xl",
                },
              }}
            />
          </StoreProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
