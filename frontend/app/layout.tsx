import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { Header } from "@/components/Header";
import { Sidebar } from "@/components/Sidebar";

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
        <div className="app-layout">
          <Sidebar />
          <div className="main-column">
            <Header />
            <main className="content">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
