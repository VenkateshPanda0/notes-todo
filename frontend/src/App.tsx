import { BrowserRouter, Route, Routes } from "react-router-dom";
import { CommandPalette } from "./components/CommandPalette";
import { ToastHost } from "./components/ToastHost";
import { Sidebar } from "./components/Sidebar";
import { AiProvider } from "./contexts/AiProvider";
import { LockProvider, useLock } from "./contexts/LockContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import { Dashboard } from "./pages/Dashboard";
import { AskView } from "./pages/AskView";
import { CalendarView } from "./pages/CalendarView";
import { GraphView } from "./pages/GraphView";
import { LockScreen } from "./pages/LockScreen";
import { Settings } from "./pages/Settings";
import { TrashView } from "./pages/TrashView";

function AppShell() {
  const { loading, unlocked } = useLock();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg)]">
        <p className="text-sm text-[var(--text-secondary)]">Loading...</p>
      </div>
    );
  }

  if (!unlocked) {
    return <LockScreen />;
  }

  return (
    <AiProvider>
      <BrowserRouter>
        <div className="flex min-h-screen bg-[var(--bg)]">
          <a
            href="#main"
            className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[60] focus:rounded-lg focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:text-white"
          >
            Skip to content
          </a>
          <Sidebar />
          <CommandPalette />
          <ToastHost />
          <main id="main" tabIndex={-1} className="flex-1 focus:outline-none">
            <Routes>
              <Route path="/" element={<Dashboard view="all" />} />
              <Route path="/today" element={<Dashboard view="today" />} />
              <Route path="/upcoming" element={<Dashboard view="upcoming" />} />
              <Route path="/completed" element={<Dashboard view="completed" />} />
              <Route path="/notes" element={<Dashboard view="notes" />} />
              <Route path="/calendar" element={<CalendarView />} />
              <Route path="/ask" element={<AskView />} />
              <Route path="/graph" element={<GraphView />} />
              <Route path="/trash" element={<TrashView />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </AiProvider>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <LockProvider>
        <AppShell />
      </LockProvider>
    </ThemeProvider>
  );
}
