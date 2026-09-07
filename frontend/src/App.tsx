import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { LockProvider, useLock } from "./contexts/LockContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import { Dashboard } from "./pages/Dashboard";
import { CalendarView } from "./pages/CalendarView";
import { LockScreen } from "./pages/LockScreen";
import { Settings } from "./pages/Settings";

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
    <BrowserRouter>
      <div className="flex min-h-screen bg-[var(--bg)]">
        <Sidebar />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Dashboard view="all" />} />
            <Route path="/today" element={<Dashboard view="today" />} />
            <Route path="/upcoming" element={<Dashboard view="upcoming" />} />
            <Route path="/completed" element={<Dashboard view="completed" />} />
            <Route path="/notes" element={<Dashboard view="notes" />} />
            <Route path="/calendar" element={<CalendarView />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
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
