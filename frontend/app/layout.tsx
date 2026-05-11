import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "home-scanner — Greek apartment rental alerts",
  description: "Telegram alerts for new rentals on xe.gr",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-white text-gray-900 antialiased">{children}</body>
    </html>
  );
}
