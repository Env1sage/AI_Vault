import { useNavigate } from "@tanstack/react-router";
import { Search } from "lucide-react";
import { useEffect, useState } from "react";

import { NAV_SECTIONS } from "@/lib/nav-items";
import { useLayoutStore } from "@/stores/layout-store";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";

/** The Cmd/Ctrl+K launcher (redesign brief §7/§29) — doubles as page
 * navigation and a shortcut into the real /search page. Never renders
 * search results itself; it hands the query to the Search route, which
 * is the only place that calls the real /v1/search endpoint. */
export function CommandPalette() {
  const open = useLayoutStore((s) => s.commandPaletteOpen);
  const setOpen = useLayoutStore((s) => s.setCommandPaletteOpen);
  const navigate = useNavigate();
  const [query, setQuery] = useState("");

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen(!open);
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, setOpen]);

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (!next) setQuery("");
  }

  function go(to: string) {
    setOpen(false);
    void navigate({ to });
  }

  function runSearch() {
    if (query.trim().length === 0) return;
    setOpen(false);
    void navigate({ to: "/search", search: { q: query.trim() } });
  }

  const filteredSections = NAV_SECTIONS.map((section) => ({
    ...section,
    items: section.items.filter((item) =>
      item.label.toLowerCase().includes(query.trim().toLowerCase()),
    ),
  })).filter((section) => section.items.length > 0);

  return (
    <CommandDialog open={open} onOpenChange={handleOpenChange}>
      <CommandInput
        placeholder="Search files, or jump to a page…"
        value={query}
        onValueChange={setQuery}
        onKeyDown={(event) => {
          if (event.key === "Enter" && filteredSections.length === 0) runSearch();
        }}
      />
      <CommandList>
        {query.trim().length > 0 && (
          <CommandGroup heading="Search">
            <CommandItem onSelect={runSearch}>
              <Search className="size-4 text-muted-foreground" />
              Search files for "{query.trim()}"
            </CommandItem>
          </CommandGroup>
        )}
        <CommandSeparator />
        {filteredSections.length === 0 && query.trim().length > 0 ? (
          <CommandEmpty>No matching pages.</CommandEmpty>
        ) : (
          filteredSections.map((section) => (
            <CommandGroup key={section.label ?? "primary"} heading={section.label ?? "Go to"}>
              {section.items.map((item) => (
                <CommandItem key={item.to} onSelect={() => go(item.to)}>
                  <item.icon className="size-4 text-muted-foreground" />
                  {item.label}
                </CommandItem>
              ))}
            </CommandGroup>
          ))
        )}
      </CommandList>
    </CommandDialog>
  );
}
