import type { Metadata, Viewport } from "next";
import { SwRegister } from "./sw-register";
import "./globals.css";

export const metadata: Metadata = {
  title: "HavenID",
  description: "Private identity and phone hub",
  manifest: "/manifest.webmanifest",
  icons: { icon: "/icon.svg" },
};

export const viewport: Viewport = {
  themeColor: "#141310",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark">
      <body>
        <SwRegister />
        {children}
      </body>
    </html>
  );
}
