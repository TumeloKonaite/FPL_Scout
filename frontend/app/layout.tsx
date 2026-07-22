import type { Metadata } from "next";
import { Suspense, type ReactNode } from "react";
import "./globals.css";
import { Header } from "@/components/Header";
import { Sidebar } from "@/components/Sidebar";
import { ReportSelectionProvider } from "@/components/useSelectedReport";

export const metadata: Metadata = {
  title: { default: "FPL Technocrat", template: "%s · FPL Technocrat" },
  description: "Fantasy Premier League reporting and decision support"
};

export default function RootLayout({
  children
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <Suspense fallback={<div className="app-layout"><div className="main-column"><main className="content">Loading reports…</main></div></div>}>
          <ReportSelectionProvider>
            <div className="app-layout">
              <Sidebar />
              <div className="main-column">
                <Header />
                <main className="content">{children}</main>
              </div>
            </div>
          </ReportSelectionProvider>
        </Suspense>
      </body>
    </html>
  );
}
