import { cn } from "@/lib/utils";

/**
 * The Ringside mark: a voice waveform bent into a ring.
 *
 * Twelve radial ticks on a 24 grid, inner radius 5.7, round caps. The tick count and
 * weight are load-bearing: the first draft used twenty-two hairlines and fused into a
 * solid disc at favicon size. Do not add ticks or thin the stroke.
 */
const TICKS = [
  "M17.70 12.00L22.10 12.00",
  "M16.94 14.85L19.27 16.20",
  "M14.85 16.94L16.65 20.05",
  "M12.00 17.70L12.00 22.70",
  "M9.15 16.94L7.60 19.62",
  "M7.06 14.85L4.99 16.05",
  "M6.30 12.00L2.10 12.00",
  "M7.06 9.15L2.82 6.70",
  "M9.15 7.06L7.70 4.55",
  "M12.00 6.30L12.00 2.50",
  "M14.85 7.06L17.40 2.65",
  "M16.94 9.15L19.19 7.85",
];

export function RingsideMark({ className, title }: { className?: string; title?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.95}
      strokeLinecap="round"
      className={cn("size-6", className)}
      role={title ? "img" : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
    >
      {TICKS.map((d) => (
        <path key={d} d={d} />
      ))}
    </svg>
  );
}

/** Mark plus wordmark, as it appears in the rail and anywhere the product signs its name. */
export function RingsideLogo({
  className,
  markClassName,
  wordClassName,
}: {
  className?: string;
  markClassName?: string;
  wordClassName?: string;
}) {
  return (
    <span className={cn("flex items-center gap-1.5", className)}>
      <RingsideMark className={cn("text-tint size-[22px] shrink-0", markClassName)} />
      <span className={cn("text-[15px] font-medium tracking-[-0.032em] lowercase", wordClassName)}>
        ringside
      </span>
    </span>
  );
}
