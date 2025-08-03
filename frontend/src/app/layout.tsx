import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Swift Package Android Support Tracking",
  description: "Linux-compatible Swift packages that lack Android support - migration recommendations for Swift Android Working Group",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
