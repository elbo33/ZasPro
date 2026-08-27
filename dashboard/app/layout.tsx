import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "ZasPro dashboard",
  description: "Review queue, curriculum tree, source pages (SPEC §17).",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <nav className="nav">
          <span className="brand">ZasPro</span>
          <Link href="/">Review queue</Link>
          <Link href="/curriculum">Curriculum</Link>
          <Link href="/sources">Sources</Link>
          <Link href="/calibration">Calibration</Link>
        </nav>
        <main className="wrap">{children}</main>
      </body>
    </html>
  );
}
