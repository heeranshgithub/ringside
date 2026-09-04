"use client";

import { Search, UserPlus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ChipsInput } from "@/components/chips-input";
import { Field } from "@/components/field";
import { EmptyState } from "@/components/states";
import {
  useGetProvidersQuery,
  useImportPeopleMutation,
  useSearchPeopleMutation,
} from "@/features/candidates/api";
import { getErrorMessage } from "@/lib/errors";
import { maskPhone } from "@/lib/format";
import type { Person } from "@/types/candidate";
import type { SearchCriteria } from "@/types/job";

export function PeopleSearchPanel({
  jobId,
  initialCriteria,
  onImported,
}: {
  jobId: string;
  initialCriteria: SearchCriteria;
  onImported?: (count: number) => void;
}) {
  const { data: providers } = useGetProvidersQuery();
  const [search, searchState] = useSearchPeopleMutation();
  const [importPeople, importState] = useImportPeopleMutation();
  const [provider, setProvider] = useState("mock");
  const [criteria, setCriteria] = useState<SearchCriteria>(initialCriteria);
  const [limit, setLimit] = useState("10");
  const [results, setResults] = useState<Person[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const runSearch = async () => {
    try {
      const res = await search({
        provider,
        criteria: { ...criteria, limit: Number(limit) },
      }).unwrap();
      setResults(res.results);
      setSelected(new Set(res.results.map((p) => p.sourceRef)));
      if (!res.results.length) toast.info("No matches. Loosen the titles or skills.");
    } catch (e) {
      toast.error(getErrorMessage(e as never));
    }
  };

  const runImport = async () => {
    const people = results.filter((p) => selected.has(p.sourceRef));
    try {
      const created = await importPeople({ jobId, people }).unwrap();
      toast.success(
        `Added ${created.length} candidate${created.length === 1 ? "" : "s"} to this job`,
      );
      onImported?.(created.length);
      setSelected(new Set());
    } catch (e) {
      toast.error(getErrorMessage(e as never));
    }
  };

  const toggle = (ref: string, on: boolean) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (on) next.add(ref);
      else next.delete(ref);
      return next;
    });

  const allSelected = results.length > 0 && selected.size === results.length;
  const providerInfo = providers?.find((p) => p.name === provider);

  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <Field label="Job titles" htmlFor="ps-titles">
          <ChipsInput
            id="ps-titles"
            value={criteria.titles}
            onChange={(titles) => setCriteria({ ...criteria, titles })}
            placeholder="Frontend Engineer, React Developer…"
          />
        </Field>
        <Field label="Locations" htmlFor="ps-locations">
          <ChipsInput
            id="ps-locations"
            value={criteria.locations}
            onChange={(locations) => setCriteria({ ...criteria, locations })}
            placeholder="Bengaluru, Mumbai…"
          />
        </Field>
        <Field label="Skills" htmlFor="ps-skills">
          <ChipsInput
            id="ps-skills"
            value={criteria.skills}
            onChange={(skills) => setCriteria({ ...criteria, skills })}
            placeholder="react, typescript…"
          />
        </Field>
        <Field label="Keywords" htmlFor="ps-keywords">
          <Input
            id="ps-keywords"
            value={criteria.keywords}
            onChange={(e) => setCriteria({ ...criteria, keywords: e.target.value })}
          />
        </Field>
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <Field label="Provider" htmlFor="ps-provider" hint={providerInfo?.note}>
          <Select value={provider} onValueChange={(v) => setProvider(v ?? "mock")}>
            <SelectTrigger id="ps-provider" className="w-56">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(
                providers ?? [{ name: "mock", label: "Demo dataset", configured: true, note: "" }]
              ).map((p) => (
                <SelectItem key={p.name} value={p.name} disabled={!p.configured}>
                  {p.label}
                  {!p.configured && " (no key)"}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        <Field label="Max results" htmlFor="ps-limit">
          <Select value={limit} onValueChange={(v) => setLimit(v ?? "10")}>
            <SelectTrigger id="ps-limit" className="w-24">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {["5", "10", "20", "50"].map((n) => (
                <SelectItem key={n} value={n}>
                  {n}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        <Button onClick={runSearch} disabled={searchState.isLoading} className="mb-[1px]">
          <Search data-icon="inline-start" />
          {searchState.isLoading ? "Searching…" : "Search people"}
        </Button>
      </div>

      {results.length === 0 ? (
        <EmptyState
          icon={<Search className="size-5" />}
          title="No results yet"
          description="Search runs against the selected provider and normalises every profile to the same shape."
        />
      ) : (
        <div className="space-y-3">
          <div className="overflow-x-auto rounded-xl border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-8">
                    <Checkbox
                      aria-label="Select all"
                      checked={allSelected}
                      onCheckedChange={(on) =>
                        setSelected(on ? new Set(results.map((p) => p.sourceRef)) : new Set())
                      }
                    />
                  </TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Title</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead>Skills</TableHead>
                  <TableHead>Contact</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {results.map((p) => (
                  <TableRow key={p.sourceRef}>
                    <TableCell>
                      <Checkbox
                        aria-label={`Select ${p.name}`}
                        checked={selected.has(p.sourceRef)}
                        onCheckedChange={(on) => toggle(p.sourceRef, on)}
                      />
                    </TableCell>
                    <TableCell>
                      <div className="font-medium">{p.name}</div>
                      {p.linkedinUrl && (
                        <a
                          href={p.linkedinUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="text-primary text-xs underline-offset-2 hover:underline"
                        >
                          LinkedIn
                        </a>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">{p.currentTitle ?? "—"}</div>
                      <div className="text-muted-foreground text-xs">{p.currentCompany ?? ""}</div>
                    </TableCell>
                    <TableCell className="text-xs">{p.location ?? "—"}</TableCell>
                    <TableCell className="text-muted-foreground max-w-56 truncate text-xs">
                      {p.skills.slice(0, 6).join(", ") || "—"}
                    </TableCell>
                    <TableCell className="text-xs">
                      <div>
                        {p.phone ? (
                          maskPhone(p.phone)
                        ) : (
                          <span className="text-muted-foreground">no phone</span>
                        )}
                      </div>
                      <div className="text-muted-foreground truncate">{p.email ?? ""}</div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <div className="flex items-center justify-between gap-3">
            <p className="text-muted-foreground text-xs">
              {selected.size} of {results.length} selected · source:{" "}
              {providerInfo?.label ?? provider}
            </p>
            <Button onClick={runImport} disabled={importState.isLoading || selected.size === 0}>
              <UserPlus data-icon="inline-start" />
              {importState.isLoading ? "Adding…" : `Add ${selected.size} to job`}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
