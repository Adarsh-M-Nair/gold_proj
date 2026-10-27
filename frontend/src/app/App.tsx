import { AppShell } from "../components/layout/AppShell";
import { AppRouter } from "./router";

export function App() {
  return (
    <div className="app-backdrop">
      <div className="ambient ambient-red" />
      <div className="ambient ambient-gold" />
      <AppShell>
        <AppRouter />
      </AppShell>
    </div>
  );
}
