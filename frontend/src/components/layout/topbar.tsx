import { Moon, Search, Sun } from "lucide-react";
import { useLocation } from "react-router-dom";

import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { navItems } from "./nav-items";

type TopbarProps = {
  theme: "light" | "dark";
  onToggleTheme: () => void;
};

export function Topbar({ theme, onToggleTheme }: TopbarProps) {
  const location = useLocation();
  const current = navItems.find((item) => item.path === location.pathname);

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-border bg-background/95 px-4 backdrop-blur md:px-6">
      <div>
        <div className="text-sm text-muted-foreground">MinerU Medical RAG</div>
        <h1 className="text-lg font-semibold">{current?.label ?? "控制台"}</h1>
      </div>
      <div className="flex items-center gap-2">
        <div className="relative hidden md:block">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input className="w-72 pl-9" placeholder="搜索知识库、文档、章节..." />
        </div>
        <Button variant="outline" size="icon" onClick={onToggleTheme} title="切换主题">
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
      </div>
    </header>
  );
}

