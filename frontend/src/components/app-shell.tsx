"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bot,
  BriefcaseBusiness,
  LayoutDashboard,
  Menu,
  Monitor,
  Moon,
  PhoneCall,
  Search,
  Settings,
  ShieldCheck,
  ShieldOff,
  Sun,
} from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { RingsideLogo } from "@/components/logo";
import { useTheme, type ThemeChoice } from "@/components/theme";
import { useGetConfigQuery } from "@/features/calls/api";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, group: null },
  { href: "/jobs", label: "Jobs", icon: BriefcaseBusiness, group: "Pipeline" },
  { href: "/search", label: "People search", icon: Search, group: null },
  { href: "/agents", label: "Voice agents", icon: Bot, group: "Calling" },
  { href: "/calls", label: "Calls", icon: PhoneCall, group: null },
  { href: "/settings", label: "Settings", icon: Settings, group: "Workspace" },
] as const;

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav className="flex flex-col gap-0.5" aria-label="Primary">
      {NAV.map(({ href, label, icon: Icon, group }) => {
        const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
        return (
          <div key={href} className="contents">
            {group && (
              <div className="text-muted-foreground px-2 pt-3.5 pb-1 text-[10px] font-medium tracking-[0.07em] uppercase">
                {group}
              </div>
            )}
            <Link
              href={href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex items-center gap-2.5 rounded-md border px-2 py-1.5 text-[13px] transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground border-border/60 font-medium shadow-[0_1px_2px_rgb(20_46_50/0.07)] dark:shadow-none"
                  : "text-muted-foreground hover:text-foreground hover:bg-foreground/[0.04] border-transparent",
              )}
            >
              <Icon className="size-3.5" />
              {label}
            </Link>
          </div>
        );
      })}
    </nav>
  );
}

function ThemeToggle() {
  const { choice, setChoice } = useTheme();
  const options: { value: ThemeChoice; icon: typeof Sun; label: string }[] = [
    { value: "light", icon: Sun, label: "Light" },
    { value: "system", icon: Monitor, label: "System" },
    { value: "dark", icon: Moon, label: "Dark" },
  ];
  return (
    <div
      role="radiogroup"
      aria-label="Colour theme"
      className="border-border/70 flex items-center gap-0.5 rounded-lg border p-0.5"
    >
      {options.map(({ value, icon: Icon, label }) => (
        <button
          key={value}
          type="button"
          role="radio"
          aria-checked={choice === value}
          aria-label={label}
          title={label}
          onClick={() => setChoice(value)}
          className={cn(
            "flex flex-1 items-center justify-center rounded-[5px] py-1 transition-colors",
            choice === value
              ? "bg-foreground/[0.07] text-foreground"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          <Icon className="size-3.5" />
        </button>
      ))}
    </div>
  );
}

function SafeDialPill() {
  const { data } = useGetConfigQuery();
  if (!data) return null;
  const safe = data.safeDialMode;
  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-lg border px-2.5 py-2 text-[11px]",
        safe ? "border-done-line bg-done-bg text-done" : "border-fail-line bg-fail-bg text-fail",
      )}
      title={
        safe
          ? "Every call is routed to the configured test number."
          : "Cleared candidates will be dialled on their real number."
      }
    >
      {safe ? (
        <ShieldCheck className="size-3.5 shrink-0" />
      ) : (
        <ShieldOff className="size-3.5 shrink-0" />
      )}
      <span className="font-medium">{safe ? "Safe dial" : "Real dialling"}</span>
      <span className="text-muted-foreground ml-auto truncate font-mono text-[10px]">
        {data.testPhoneNumbersMasked[0] ?? "not set"}
      </span>
    </div>
  );
}

function Brand({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <Link
      href="/"
      onClick={onNavigate}
      aria-label="Ringside, go to the dashboard"
      className="rounded-md px-1.5 pt-1 pb-3"
    >
      <RingsideLogo />
    </Link>
  );
}

function RailContents({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <>
      <Brand onNavigate={onNavigate} />
      <NavLinks onNavigate={onNavigate} />
      <div className="mt-auto space-y-2 pt-4">
        <SafeDialPill />
        <ThemeToggle />
      </div>
    </>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="flex h-[100svh] overflow-hidden">
      <aside className="halo-rail border-border hidden w-56 shrink-0 flex-col overflow-y-auto border-r p-3 lg:flex">
        <RailContents />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-border halo-glass sticky top-0 z-20 flex h-12 shrink-0 items-center gap-2 border-b px-3 lg:hidden">
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
          <SheetContent side="left" className="halo-rail flex w-64 flex-col p-3">
            <SheetTitle className="sr-only">Navigation</SheetTitle>
            <div className="flex flex-1 flex-col pt-6">
              <RailContents onNavigate={() => setOpen(false)} />
            </div>
          </SheetContent>
        </Sheet>

        <main className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-[1400px] px-5 py-7 sm:px-8 lg:px-10">{children}</div>
        </main>
      </div>
    </div>
  );
}
