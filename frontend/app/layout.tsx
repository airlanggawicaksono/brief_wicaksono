import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "WPP",
  description: "AI-powered text to structured data",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900">
        <main className="mx-auto max-w-2xl px-4 py-12">{children}</main>
      </body>
    </html>
  );
}
