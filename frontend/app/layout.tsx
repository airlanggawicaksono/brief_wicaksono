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
      <body className="h-screen bg-gray-50 text-gray-900">
        {children}
      </body>
    </html>
  );
}
