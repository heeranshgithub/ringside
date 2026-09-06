# Attendance for 1,000 people at 100 sites, without smartphones

> *If there were no smartphones but LLMs exist, and you are an HR who has to track attendance of 1,000
> people every day across 100 locations, what would you do?*

Buy biometric punch machines. Fingerprint punch at every site is the boring, proven answer to identity
and presence, and no smartphone is involved. The brief does not constrain budget, so I would spend on
the one piece of hardware that removes the most daily work, and put the LLM on what hardware cannot fix.

## Primary: punch machines

One machine per site, synced over the site's landline or GSM modem. A punch is the source of truth for
"who was here and when". Enrolment happens at joining, and nothing in the daily flow needs literacy or
a personal phone.

## What the machine does not solve

Across 100 sites, every day, something breaks: a machine that did not sync, a power cut, a new joiner
not yet enrolled, a site whose count looks wrong, a worker who forgot to punch out. Today that tail is
100 phone calls made by a clerk and a spreadsheet of hand-typed excuses. That is the job for the LLM.

## Exception loop: a voice agent

Each morning the sync produces a gap list. An agent calls only the supervisors on that list, on the site
landline, in the local language, and turns "the machine was off, everyone was here except Suresh" into a
per-worker record. Landline means the supervisor is on site. The record lands in the same table as the
punches, flagged as a supervisor statement, not a verified punch. This is the screening agent in this
repo, pointed at a roster instead of a job description.

## Fallback: missed call

A site with no working machine falls back to a missed call from each worker's registered number to a
site-specific virtual number, answered with an SMS receipt. Free, works on any handset. It is the
worker's timestamped claim, confirmed by the supervisor call above.

## What HR sees

One page by 09:30: silent sites, gaps the agent could not close, three-day absentees. Every row names its
source, and a punch and a supervisor's word are never shown as the same green tick. Same principle as
the hiring product: evidence over verdict, degrade visibly rather than guess.
