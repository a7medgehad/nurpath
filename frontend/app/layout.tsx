import type { Metadata } from "next";
import { Cairo, Literata } from "next/font/google";
import "./globals.css";

const cairo = Cairo({
  subsets: ["arabic", "latin"],
  variable: "--font-cairo",
  weight: ["400", "600", "700"],
});

const literata = Literata({
  subsets: ["latin"],
  variable: "--font-literata",
  weight: ["500", "700"],
});

export const metadata: Metadata = {
  title: "NurPath",
  description: "Ikhtilaf-aware Arabic-English Islamic learning tutor",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${cairo.variable} ${literata.variable}`}>{children}</body>
    </html>
  );
}
