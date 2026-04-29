import { NavLink } from "react-router-dom";

import { cn } from "../../lib/utils";
import { navItems } from "./nav-items";

export function Sidebar() {
  return (
    <aside className="hidden w-64 shrink-0 border-r border-border bg-card lg:block">
      <div className="flex h-16 items-center gap-3 border-b border-border px-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
          MR
        </div>
        <div>
          <div className="text-sm font-semibold">Medical RAG Console</div>
          <div className="text-xs text-muted-foreground">MinerU-ready KB Platform</div>
        </div>
      </div>
      <nav className="space-y-1 p-3">
        {navItems.slice(0, 7).map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )
            }
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="mx-3 mt-4 rounded-lg border border-border bg-muted/40 p-4">
        <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Product Focus
        </div>
        <div className="mt-2 text-sm font-medium">可溯源医疗文献知识库</div>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          复杂版式解析、医疗语义切分、向量索引与证据引用统一管理。
        </p>
      </div>
    </aside>
  );
}
