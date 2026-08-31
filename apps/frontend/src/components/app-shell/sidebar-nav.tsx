import { Link, useRouterState } from "@tanstack/react-router";

import { cn } from "@/lib/utils";
import { NAV_SECTIONS } from "@/lib/nav-items";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

/** Shared between the desktop sidebar and the mobile drawer — the only
 * difference between the two contexts is width/chrome around this list,
 * never the nav logic itself. */
export function SidebarNav({ collapsed = false, onNavigate }: { collapsed?: boolean; onNavigate?: () => void }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <nav className="flex flex-1 flex-col gap-5 overflow-y-auto px-3 py-2">
      {NAV_SECTIONS.map((section, sectionIndex) => (
        <div key={section.label ?? `section-${sectionIndex}`} className="flex flex-col gap-0.5">
          {section.label && !collapsed ? (
            <p className="mb-1 px-2.5 text-[11px] font-semibold uppercase tracking-wider text-sidebar-muted-foreground">
              {section.label}
            </p>
          ) : null}
          {section.items.map((item) => {
            const isActive = pathname === item.to || pathname.startsWith(`${item.to}/`);
            const link = (
              <Link
                key={item.to}
                to={item.to}
                onClick={onNavigate}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "group flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-colors",
                  "text-sidebar-foreground/85 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring",
                  isActive && "bg-sidebar-accent text-sidebar-accent-foreground shadow-clay-inset",
                  collapsed && "justify-center px-2",
                )}
              >
                <item.icon className="size-[18px] shrink-0" aria-hidden="true" />
                {!collapsed && <span className="truncate">{item.label}</span>}
              </Link>
            );

            if (!collapsed) return link;

            return (
              <Tooltip key={item.to} delayDuration={200}>
                <TooltipTrigger asChild>{link}</TooltipTrigger>
                <TooltipContent side="right">{item.label}</TooltipContent>
              </Tooltip>
            );
          })}
        </div>
      ))}
    </nav>
  );
}
