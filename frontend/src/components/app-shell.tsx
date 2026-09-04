"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bot,
  BriefcaseBusiness,
  ClipboardCheck,
  LayoutDashboard,
  Menu,
  PhoneCall,
  Search,
  Settings,
  ShieldCheck,
  ShieldOff,
} from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { useGetConfigQuery } from "@/features/calls/api";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/jobs", label: "Jobs", icon: BriefcaseBusiness },
  { href: "/search", label: "People search", icon: Search },
  { href: "/agents", label: "Voice agents", icon: Bot },
  { href: "/calls", label: "Calls", icon: PhoneCall },
  { href: "/attendance", label: "Attendance (Q3)", icon: ClipboardCheck },
  { href: "/settings", label: "Settings", icon: Settings },
] as const;

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav className="flex flex-col gap-1" aria-label="Primary">
      {NAV.map(({ href, label, icon: Icon }) => {
        const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors",
              active
                ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground",
            )}
          >
            <Icon className="size-4" />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

function SafeDialPill() {
  const { data } = useGetConfigQuery();
  if (!data) return null;
  const safe = data.safeDialMode;
  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-lg border px-2.5 py-2 text-xs",
        safe
          ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
          : "border-destructive/30 bg-destructive/10 text-destructive",
      )}
      title={
        safe
          ? "Every call is routed to the configured test number."
          : "Cleared candidates will be dialled on their real number."
      }
    >
      {safe ? <ShieldCheck className="size-3.5" /> : <ShieldOff className="size-3.5" />}
      <span className="font-medium">{safe ? "Safe dial on" : "Real dialling"}</span>
      <span className="text-muted-foreground ml-auto truncate">
        {data.testPhoneNumbersMasked[0] ?? "no test number"}
      </span>
    </div>
  );
}

function Brand() {
  return (
    <Link href="/" className="flex items-center gap-2 px-1">
      <span className="bg-primary text-primary-foreground flex size-7 items-center justify-center rounded-lg text-xs font-bold">
        R
      </span>
      <div className="leading-tight">
        <div className="text-sm font-semibold">Ringside</div>
        <div className="text-muted-foreground text-[11px]">Voice AI assistant</div>
      </div>
    </Link>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="bg-background flex min-h-screen">
      <aside className="bg-sidebar text-sidebar-foreground hidden w-60 shrink-0 flex-col gap-6 border-r p-3 lg:flex">
        <Brand />
        <NavLinks />
        <div className="mt-auto space-y-2">
          <SafeDialPill />
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-12 items-center gap-2 border-b px-3 lg:hidden">
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="Open navigation"
            onClick={() => setOpen(true)}
          >
            <Menu />
          </Button>
          <Brand />
        </header>
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetContent side="left" className="w-64 p-3">
            <SheetTitle className="sr-only">Navigation</SheetTitle>
            <div className="space-y-6 pt-6">
              <Brand />
              <NavLinks onNavigate={() => setOpen(false)} />
              <SafeDialPill />
            </div>
          </SheetContent>
        </Sheet>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 lg:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}
