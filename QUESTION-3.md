# Attendance for 1,000 people at 100 sites, without smartphones

> *If there were no smartphones but LLMs exist, and you are an HR who has to track attendance of 1,000
> people every day across 100 locations, what would you do?*

No apps, but feature phones, landlines, SMS, IVR, biometric punch machines and LLMs all exist.
Attendance is a daily fact-collection problem with three hard parts: identity, presence and exceptions.
The cheapest reliable channel at all 100 sites is the phone network, and an LLM means a phone call no
longer needs a human on the other end.

## The design

1. **Missed-call check-in, free.** Each worker registers one number and each site gets a virtual number.
   A missed call inside the shift window marks you present and triggers an SMS receipt. It costs nothing,
   works on the cheapest handset, and needs no literacy.
2. **Voice-AI roll-call.** Twenty minutes after shift start an agent calls each site supervisor on the
   site landline, in the local language, and turns "everyone is here except Suresh, Priya came at 9:30"
   into a structured per-worker record. That is the screening agent in this repo, pointed at a roster
   instead of a job description.
3. **Verification.** Landline calls prove the supervisor is on site. Random spot-check calls to workers
   ask questions only someone actually there could answer. Biometric exports, where the machines already
   exist, are reconciled against the calls. An LLM flags the anomalies: the supervisor whose site is
   always full, the number checking in from the wrong district, the worker who is never spot-checkable.
4. **Reconciliation.** By 09:30 an LLM merges the streams into one table with a confidence flag per row.
   HR opens one page showing silent sites, three-day absentees and unapproved replacements. Agents call
   the silent sites so HR does not have to.

## Why not the alternatives

**Not SMS-only.** Typing structured codes on a keypad has a high error rate and proves nothing about
location, so SMS stays the receipt channel rather than the reporting one.

**Not biometrics everywhere.** The machines cost money, break, and need power and a PC at every site.
Use them where they already exist and never depend on them.

**Not a human call centre.** A hundred supervisor calls a day is a small team of clerks with sick days
and inconsistent notes. Agents make the same call the same way at 08:20 sharp and hand back JSON.

**Paper is the last fallback.** A site with no signal keeps a signed sheet, and a photo of it is read by
a vision model into the same table, flagged low-confidence so nobody mistakes it for a verified record.

## What makes it trustworthy

Every row in the final table can name its source and its confidence. A present mark backed by a missed
call, a supervisor statement and a biometric punch is not the same fact as one backed by a photo of a
sheet, and the system never flattens the two into the same green tick. That is the same principle the
hiring product runs on: evidence over verdict, and degrade visibly rather than quietly guess.
