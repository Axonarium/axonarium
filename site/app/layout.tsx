import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";

import "./globals.css";

const geistSans = Geist({ variable: "--font-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

const REPO = "https://github.com/axonarium/axonarium";

export const metadata: Metadata = {
  metadataBase: new URL("https://axonarium.org"),
  title: { default: "Axonarium", template: "%s · Axonarium" },
  description: "An open, cited map of how the brain and body are wired.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col bg-background text-foreground">
        <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:p-2">
          Skip to content
        </a>
        <header className="border-b">
          <nav aria-label="Main" className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3">
            <Link href="/" className="font-semibold tracking-tight">
              Axonarium
            </Link>
            <Link href="/explore" className="text-sm text-muted-foreground hover:text-foreground">
              Explore
            </Link>
            <Link href="/atlases" className="text-sm text-muted-foreground hover:text-foreground">
              Atlases
            </Link>
            <Link href="/about" className="text-sm text-muted-foreground hover:text-foreground">
              About
            </Link>
            <a href={REPO} className="ml-auto text-sm text-muted-foreground hover:text-foreground">
              GitHub
            </a>
          </nav>
        </header>
        <main id="main" className="mx-auto w-full max-w-5xl flex-1 px-4 py-10">
          {children}
        </main>
        <footer className="border-t">
          <div className="mx-auto flex max-w-5xl flex-wrap gap-x-6 gap-y-2 px-4 py-6 text-sm text-muted-foreground">
            <span>
              Project-curated data:{" "}
              <a href="https://creativecommons.org/licenses/by/4.0/" className="hover:text-foreground">
                CC BY 4.0
              </a>
              ; sources keep their own terms
            </span>
            <span>Code: Apache-2.0</span>
            <span>
              Region names: Allen Institute atlases, via BrainGlobe;{" "}
              <Link href="/atlases" className="hover:text-foreground">
                cited on the Atlases page
              </Link>
            </span>
            <a href={REPO} className="hover:text-foreground">
              Source and data on GitHub
            </a>
          </div>
        </footer>
      </body>
    </html>
  );
}
