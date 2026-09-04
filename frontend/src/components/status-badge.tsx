import { cn } from "@/lib/utils";
import { titleCase } from "@/lib/format";

/**
 * One vocabulary for every asynchronous call state, used everywhere a status appears.
 * A lamp carries the state; the word repeats it, so colour is never the only signal.
 */
type Lamp = "idle" | "live" | "talking" | "done" | "fail";

const LAMP: Record<string, Lamp> = {
  NOT_STARTED: "idle",
  SCHEDULED: "idle",
  INITIATED: "live",
  RINGING: "live",
  IN_PROGRESS: "talking",
  COMPLETED: "done",
  NOT_CONNECTED: "fail",
  CANCELLED: "idle",
  FAILED: "fail",
  ENGAGED: "done",
  NOT_ENGAGED: "idle",
  active: "done",
  draft: "idle",
  closed: "idle",
  strong_yes: "done",
  yes: "done",
  maybe: "live",
  no: "fail",
  insufficient_data: "idle",
};

const TONE: Record<Lamp, string> = {
  idle: "text-muted-foreground",
  live: "text-live-ink",
  talking: "text-live-ink",
  done: "text-done",
  fail: "text-fail",
};

export function StatusBadge({
  status,
  className,
  showLabel = true,
}: {
  status: string | null | undefined;
  className?: string;
  showLabel?: boolean;
}) {
  if (!status) return <span className="text-muted-foreground">—</span>;
  const lamp = LAMP[status] ?? "idle";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 text-[13px] whitespace-nowrap",
        TONE[lamp],
        className,
      )}
    >
      <span className="lamp" data-state={lamp} aria-hidden />
      {showLabel && titleCase(status)}
    </span>
  );
}

export function ScorePill({ score }: { score: number }) {
  const tone =
    score >= 75
      ? "bg-done-bg text-done border-done-line"
      : score >= 50
        ? "bg-live-bg text-live-ink border-live-line"
        : "bg-muted text-muted-foreground border-transparent";
  return (
    <span
      className={cn(
        "inline-block min-w-8 rounded-md border px-2 py-0.5 text-center text-[11.5px] font-semibold tabular-nums",
        tone,
      )}
      title={`Fit score ${score} of 100`}
    >
      {score}
    </span>
  );
}
