import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AudioNet",
  description: "Send text between laptops using sound.",
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
