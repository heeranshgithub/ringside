import { cn } from "@/lib/utils";
import { titleCase } from "@/lib/format";

const STATUS_STYLES: Record<string, string> = {
  NOT_STARTED: "bg-muted text-muted-foreground",
  SCHEDULED: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
  INITIATED: "bg-sky-500/15 text-sky-700 dark:text-sky-300",
  RINGING: "bg-sky-500/15 text-sky-700 dark:text-sky-300",
  IN_PROGRESS: "bg-sky-500/15 text-sky-700 dark:text-sky-300",
  COMPLETED: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  NOT_CONNECTED: "bg-orange-500/15 text-orange-700 dark:text-orange-300",
  CANCELLED: "bg-muted text-muted-foreground",
  FAILED: "bg-destructive/10 text-destructive",
  ENGAGED: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  NOT_ENGAGED: "bg-muted text-muted-foreground",
  active: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  draft: "bg-muted text-muted-foreground",
  closed: "bg-muted text-muted-foreground",
  strong_yes: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  yes: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  maybe: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
  no: "bg-destructive/10 text-destructive",
  insufficient_data: "bg-muted text-muted-foreground",
};

const LIVE = new Set(["INITIATED", "RINGING", "IN_PROGRESS"]);

export function StatusBadge({
  status,
  className,
}: {
  status: string | null | undefined;
  className?: string;
}) {
  if (!status) return <span className="text-muted-foreground">—</span>;
  return (
    <span
      className={cn(
        "inline-flex h-5 items-center gap-1.5 rounded-full px-2 text-xs font-medium whitespace-nowrap",
        STATUS_STYLES[status] ?? "bg-muted text-muted-foreground",
        className,
      )}
    >
      {LIVE.has(status) && (
        <span className="relative flex size-1.5">
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-current opacity-75" />
          <span className="relative inline-flex size-1.5 rounded-full bg-current" />
        </span>
      )}
      {titleCase(status)}
    </span>
  );
}

export function ScorePill({ score }: { score: number }) {
  const tone =
    score >= 75
      ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
      : score >= 50
        ? "bg-amber-500/15 text-amber-700 dark:text-amber-300"
        : "bg-muted text-muted-foreground";
  return (
    <span
      className={cn("inline-flex h-5 items-center rounded-full px-2 text-xs font-semibold", tone)}
    >
      {score}
    </span>
  );
}
