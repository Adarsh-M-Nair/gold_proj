import type { ReactNode } from "react";
import { Shield } from "lucide-react";
import { Header } from "./Header";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="shell">
      <Header />
      <main className="page-content">{children}</main>
      <footer className="site-footer">
        <span><Shield size={14} /> GoldSafe · Muthoot Finance AI</span>
        <span>Customer and pledge records are managed through the Django API.</span>
      </footer>
    </div>
  );
}
