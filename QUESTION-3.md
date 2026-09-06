# Attendance for 1,000 people at 100 sites, without smartphones

> *If there were no smartphones but LLMs exist, and you are an HR who has to track attendance of 1,000
> people every day across 100 locations, what would you do?*

Feature phones, landlines, SMS, IVR and LLMs still exist. The phone network reaches all 100 sites, and an
LLM means a phone call no longer needs a human on the other end. Attendance becomes two phone calls a day
and one reconciliation.

## The design

1. **Missed-call check-in.** Each worker registers one number and each site gets a virtual number. A
   missed call inside the shift window is the worker's timestamped claim of presence, answered with an
   SMS receipt. Free, works on any handset, needs no literacy. It proves the claim, not the location.
2. **Voice-AI roll-call.** Twenty minutes after shift start an agent calls each site supervisor on the
   site landline, in the local language, and turns "everyone is here except Suresh, Priya came at 9:30"
   into a per-worker record. The landline proves the supervisor is on site. This is the screening agent
   in this repo, pointed at a roster instead of a job description.
3. **Spot checks.** On a few random calls a day the agent asks the supervisor to put a named worker on
   the line. A worker who is never available gets flagged. Where a site already has a biometric punch
   machine its export is reconciled against the calls. No new machines are bought: they need power, a PC
   and maintenance at every site.
4. **Reconciliation.** By 09:30 an LLM merges missed calls, roll-call and punches into one table with a
   source and a confidence flag per row. HR sees only exceptions: silent sites, a worker's claim that the
   supervisor did not confirm, three-day absentees. Agents call the silent sites back so HR does not have to.

## Why not the alternatives

SMS codes typed on a keypad have a high error rate, so SMS is the receipt channel, not the reporting one.
A human call centre for 100 calls a day is a team of clerks with sick days and inconsistent notes; agents
make the same call at 08:20 sharp and hand back structured data. A site with no signal keeps a signed
sheet and the supervisor reads it out on the next call, flagged low-confidence.

## What makes it trustworthy

Every row can name its source. A present mark backed by a missed call, a supervisor statement and a punch
is not the same fact as one read off a paper sheet, and the table never shows the two as the same green
tick. Same principle as the hiring product: evidence over verdict, degrade visibly rather than guess.
