import { Outlet } from "react-router-dom";

import { useTheme } from "../../hooks/useTheme";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";

export function AppLayout() {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="min-h-screen bg-background">
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="min-w-0 flex-1">
          <Topbar theme={theme} onToggleTheme={toggleTheme} />
          <main className="mx-auto w-full max-w-7xl px-4 py-6 md:px-6">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}

