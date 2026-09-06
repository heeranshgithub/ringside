import type { ReactNode } from "react";

import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export function Field({
  label,
  htmlFor,
  hint,
  error,
  children,
  className,
}: {
  label: ReactNode;
  htmlFor?: string;
  hint?: ReactNode;
  error?: string | undefined;
  children: ReactNode;
  className?: string;
}) {
  return (
    // `flex flex-col gap-1.5`, not `space-y-1.5`: Base UI renders a `position: fixed` input as
    // the last child of a Select for form integration, and `space-y` targets it as a sibling
    // (`:not([hidden]) ~ :not([hidden])`), adding its margin to this box even though the element
    // is out of flow. The wrapper then sits 6px below its own control, and any row that aligns
    // on it — `items-end` toolbars — pushes plain buttons out of line. Flex gap only applies
    // between real flex items, so the box hugs the visible control.
    <div className={cn("flex flex-col gap-1.5", className)}>
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
      {error ? (
        <p className="text-destructive text-xs" role="alert">
          {error}
        </p>
      ) : hint ? (
        <p className="text-muted-foreground text-xs">{hint}</p>
      ) : null}
    </div>
  );
}
