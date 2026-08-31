import * as DialogPrimitive from "@radix-ui/react-dialog";
import { Link } from "@tanstack/react-router";
import { X } from "lucide-react";

import { useLayoutStore } from "@/stores/layout-store";
import { SidebarNav } from "@/components/app-shell/sidebar-nav";

export function MobileNav() {
  const open = useLayoutStore((s) => s.mobileNavOpen);
  const setOpen = useLayoutStore((s) => s.setMobileNavOpen);

  return (
    <DialogPrimitive.Root open={open} onOpenChange={setOpen}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-foreground/40 backdrop-blur-[1px] md:hidden" />
        <DialogPrimitive.Content
          className="fixed inset-y-0 left-0 z-50 flex w-72 animate-slide-in-right flex-col bg-sidebar shadow-clay-lg md:hidden"
          aria-describedby={undefined}
        >
          <DialogPrimitive.Title className="sr-only">Navigation</DialogPrimitive.Title>
          <div className="flex h-14 items-center justify-between px-4">
            <Link
              to="/dashboard"
              onClick={() => setOpen(false)}
              className="flex items-center gap-2 text-sm font-semibold text-sidebar-foreground"
            >
              <span className="flex size-7 items-center justify-center rounded-lg bg-primary text-sm font-bold text-primary-foreground">
                V
              </span>
              AI Project Vault
            </Link>
            <DialogPrimitive.Close className="rounded-md p-1.5 text-sidebar-foreground/70 hover:bg-sidebar-accent">
              <X className="size-4" />
              <span className="sr-only">Close menu</span>
            </DialogPrimitive.Close>
          </div>
          <SidebarNav onNavigate={() => setOpen(false)} />
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
