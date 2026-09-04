"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Field } from "@/components/field";
import { useCreateCandidateMutation, useImportCsvMutation } from "@/features/candidates/api";
import { getErrorMessage } from "@/lib/errors";

const candidateSchema = z.object({
  name: z.string().min(1, "Required").max(120),
  phone: z.string().max(20).optional().or(z.literal("")),
  email: z.string().email("Invalid email").optional().or(z.literal("")),
  currentTitle: z.string().max(120).optional().or(z.literal("")),
  currentCompany: z.string().max(120).optional().or(z.literal("")),
  location: z.string().max(120).optional().or(z.literal("")),
  skills: z.string().optional().or(z.literal("")),
});

type CandidateValues = z.infer<typeof candidateSchema>;

const blank = (v: string | undefined) => (v && v.trim() ? v.trim() : null);

export function AddCandidateDialog({
  jobId,
  open,
  onOpenChange,
}: {
  jobId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [create, { isLoading }] = useCreateCandidateMutation();
  const form = useForm<CandidateValues>({
    resolver: zodResolver(candidateSchema),
    defaultValues: {
      name: "",
      phone: "",
      email: "",
      currentTitle: "",
      currentCompany: "",
      location: "",
      skills: "",
    },
  });
  const { errors } = form.formState;

  const submit = form.handleSubmit(async (v) => {
    try {
      await create({
        jobId,
        name: v.name.trim(),
        phone: blank(v.phone),
        email: blank(v.email),
        currentTitle: blank(v.currentTitle),
        currentCompany: blank(v.currentCompany),
        location: blank(v.location),
        skills: (v.skills ?? "")
          .split(/[,;]/)
          .map((s) => s.trim())
          .filter(Boolean),
      }).unwrap();
      toast.success("Candidate added");
      form.reset();
      onOpenChange(false);
    } catch (e) {
      toast.error(getErrorMessage(e as never));
    }
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Add candidate</DialogTitle>
          <DialogDescription>
            Phone is optional while safe-dial is on; numbers are normalised to E.164 (+91 default).
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field
              label="Name"
              htmlFor="cand-name"
              error={errors.name?.message}
              className="sm:col-span-2"
            >
              <Input id="cand-name" {...form.register("name")} />
            </Field>
            <Field label="Phone" htmlFor="cand-phone" error={errors.phone?.message}>
              <Input id="cand-phone" placeholder="+91 98765 43210" {...form.register("phone")} />
            </Field>
            <Field label="Email" htmlFor="cand-email" error={errors.email?.message}>
              <Input id="cand-email" type="email" {...form.register("email")} />
            </Field>
            <Field label="Current title" htmlFor="cand-title">
              <Input id="cand-title" {...form.register("currentTitle")} />
            </Field>
            <Field label="Company" htmlFor="cand-company">
              <Input id="cand-company" {...form.register("currentCompany")} />
            </Field>
            <Field label="Location" htmlFor="cand-location">
              <Input id="cand-location" {...form.register("location")} />
            </Field>
            <Field label="Skills (comma separated)" htmlFor="cand-skills">
              <Input id="cand-skills" {...form.register("skills")} />
            </Field>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? "Adding…" : "Add candidate"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

const SAMPLE_CSV = `name,phone,email,title,company,location,skills
Ananya Iyer,+91 98765 43210,ananya@example.com,Senior Frontend Engineer,Razorpay,Bengaluru,react;typescript;next.js
Rohan Mehta,9876500001,rohan@example.com,Frontend Developer,Zepto,Mumbai,react;javascript`;

export function ImportCsvDialog({
  jobId,
  open,
  onOpenChange,
}: {
  jobId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [importCsv, { isLoading }] = useImportCsvMutation();
  const [text, setText] = useState("");

  const submit = async () => {
    try {
      const res = await importCsv({ jobId, csvText: text }).unwrap();
      toast.success(
        `Imported ${res.created.length} candidate${res.created.length === 1 ? "" : "s"}`,
      );
      if (res.skipped.length)
        toast.warning(`${res.skipped.length} row(s) skipped: ${res.skipped[0]}`);
      setText("");
      onOpenChange(false);
    } catch (e) {
      toast.error(getErrorMessage(e as never));
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Import candidates from CSV</DialogTitle>
          <DialogDescription>
            Paste CSV with a header row. Recognised columns: name (required), phone, email, title,
            company, location, skills (semicolon separated), linkedin, notes.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Textarea
            aria-label="CSV text"
            rows={10}
            className="font-mono text-xs"
            placeholder={SAMPLE_CSV}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <Button
            type="button"
            variant="link"
            size="sm"
            className="px-0"
            onClick={() => setText(SAMPLE_CSV)}
          >
            Use sample rows
          </Button>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={isLoading || !text.trim()}>
            {isLoading ? "Importing…" : "Import"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
