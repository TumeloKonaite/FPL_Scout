import type { Metadata } from "next";
import { Suspense, type ReactNode } from "react";
import "./globals.css";
import "@/components/kasifpl/styles/kasifpl.css";
import { Header } from "@/components/Header";
import { KasiFplFooter } from "@/components/kasifpl";
import { ReportSelectionProvider } from "@/components/useSelectedReport";

export const metadata: Metadata = {
  title: { default: "kasifpl", template: "%s · kasifpl" },
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
        <Suspense fallback={<div className="kasifpl-shell"><main className="kasifpl-shell__main">Loading reports…</main></div>}>
          <ReportSelectionProvider>
            <div className="kasifpl-shell">
              <Header />
              <main className="kasifpl-shell__main">{children}</main>
              <KasiFplFooter>Public, read-only FPL decision support · Recommendations remain tied to their published gameweek.</KasiFplFooter>
            </div>
          </ReportSelectionProvider>
        </Suspense>
      </body>
    </html>
  );
}
