import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { ReliabilityPill } from "./_components/reliability-pill";

export const metadata: Metadata = {
  title: "home-scanner — Greek apartment rental alerts",
  description: "Telegram alerts for new rentals on xe.gr",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col bg-white text-gray-900 antialiased">
        <header className="border-b border-gray-200">
          <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <Link href="/" className="text-lg font-bold">
              🏠 home-scanner
            </Link>
            <div className="flex items-center gap-6 text-sm text-gray-600">
              <Link href="/listings">Browse</Link>
              <Link href="/about">About</Link>
              <a
                href="https://github.com/geokal94/home-scanner"
                target="_blank"
                rel="noreferrer"
                className="hover:text-gray-900"
              >
                GitHub
              </a>
              <a
                href="https://t.me/home_scanner_gr_bot"
                target="_blank"
                rel="noreferrer"
                className="rounded-md bg-sky-600 px-3 py-1.5 text-white hover:bg-sky-700"
              >
                Open Telegram bot
              </a>
            </div>
          </nav>
        </header>

        <main className="flex-1">{children}</main>

        <footer className="border-t border-gray-200">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4 text-xs text-gray-500">
            <span>© home-scanner · open source on GitHub</span>
            <Suspense fallback={<span className="text-gray-400">…</span>}>
              <ReliabilityPill />
            </Suspense>
          </div>
        </footer>
      </body>
    </html>
  );
}
