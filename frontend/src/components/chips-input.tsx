"use client";

import { X } from "lucide-react";
import { useState } from "react";

import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export function ChipsInput({
  value,
  onChange,
  placeholder,
  id,
  className,
}: {
  value: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
  id?: string;
  className?: string;
}) {
  const [draft, setDraft] = useState("");

  const commit = () => {
    const parts = draft
      .split(/[,\n]/)
      .map((s) => s.trim())
      .filter(Boolean);
    if (parts.length) onChange([...value, ...parts.filter((p) => !value.includes(p))]);
    setDraft("");
  };

  return (
    <div className={cn("flex flex-wrap items-center gap-1.5 rounded-lg border p-1.5", className)}>
      {value.map((chip) => (
        <span
          key={chip}
          className="bg-secondary text-secondary-foreground inline-flex h-6 items-center gap-1 rounded-md pr-1 pl-2 text-xs"
        >
          {chip}
          <button
            type="button"
            aria-label={`Remove ${chip}`}
            className="hover:bg-foreground/10 rounded p-0.5"
            onClick={() => onChange(value.filter((v) => v !== chip))}
          >
            <X className="size-3" />
          </button>
        </span>
      ))}
      <Input
        id={id}
        value={draft}
        placeholder={value.length ? "" : placeholder}
        className="h-6 min-w-32 flex-1 border-0 bg-transparent px-1 shadow-none focus-visible:ring-0"
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === ",") {
            e.preventDefault();
            commit();
          } else if (e.key === "Backspace" && !draft && value.length) {
            onChange(value.slice(0, -1));
          }
        }}
      />
    </div>
  );
}
