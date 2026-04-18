import "bootstrap/dist/css/bootstrap.min.css";
import "./globals.css";

import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Damah_noshem",
  description: "Internal reconciliation workspace",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return children;
}
