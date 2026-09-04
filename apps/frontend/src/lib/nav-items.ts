import {
  Bell,
  BrainCircuit,
  Building2,
  ClipboardCheck,
  ClipboardList,
  Cloud,
  FolderOpen,
  HardDrive,
  Layers,
  LayoutDashboard,
  LayoutTemplate,
  Lightbulb,
  MessageCircle,
  PlayCircle,
  ScanLine,
  Search,
  Workflow,
  Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
}

export interface NavSection {
  label: string | null;
  items: NavItem[];
}

/** Central nav config — the sidebar, the mobile drawer, and the command
 * palette's "Go to…" group all read from this one list so a new page never
 * needs to be wired into three places by hand. */
export const NAV_SECTIONS: NavSection[] = [
  {
    label: null,
    items: [
      { label: "Dashboard", to: "/dashboard", icon: LayoutDashboard },
      { label: "Files", to: "/files", icon: FolderOpen },
      { label: "Search", to: "/search", icon: Search },
      { label: "Ask Vault", to: "/chat", icon: MessageCircle },
      { label: "Recommendations", to: "/recommendations", icon: Lightbulb },
      { label: "Approvals", to: "/approvals", icon: ClipboardCheck },
    ],
  },
  {
    label: "Automation",
    items: [
      { label: "Workflows", to: "/workflows", icon: Workflow },
      { label: "Automation", to: "/automation", icon: Zap },
      { label: "Templates", to: "/automation-templates", icon: LayoutTemplate },
      { label: "Notifications", to: "/notifications", icon: Bell },
    ],
  },
  {
    label: "Execution",
    items: [
      { label: "Execution Plans", to: "/execution-plans", icon: ClipboardList },
      { label: "Execution Jobs", to: "/execution-jobs", icon: PlayCircle },
    ],
  },
  {
    label: "Storage",
    items: [
      { label: "Connections", to: "/storage-connections", icon: Cloud },
      { label: "Scans", to: "/scans", icon: ScanLine },
      { label: "Storage Intelligence", to: "/storage-intelligence", icon: HardDrive },
    ],
  },
  {
    label: "Organization",
    items: [
      { label: "Organization", to: "/organization", icon: Building2 },
    ],
  },
];

export const AI_ACCENT_ICON: LucideIcon = BrainCircuit;
export const LAYERS_ICON: LucideIcon = Layers;
