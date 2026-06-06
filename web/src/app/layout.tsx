import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "InternRadar AI",
  description:
    "Verified internship listings for undergraduate CS students — official links, freshness checks, and evidence-based tags.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
