# Endpoint — findings and deviations, accumulating

Discoveries, corrections, and things that turned out otherwise than the design
assumed. Newest first. Each entry says what was believed, what was measured, and
what changed as a result.

Nothing here overrides [`PREREGISTRATION.md`](PREREGISTRATION.md). Where a
finding implies a rule should change, that is recorded as a **proposed
amendment** and stays proposed until it is argued and numbered under §11.

---

## F5 — Primary figure 3's raw sum is not reportable as written

**31 August 2026 · [`data/figures/reporting.txt`](data/figures/reporting.txt) ·
proposed amendment**

`PREREGISTRATION.md` §6 fixes figure 3 as *the sum of `enrollmentInfo.count` over
trials with no posted results*. Computed on the census that sum is **58,650,765
participants**, and it was going to be the landing figure (UI-1) precisely
because it is a count rather than an estimate.

It is dominated by a small number of records, and by at least one that is wrong.

| | |
|---|---|
| Median silent trial | **52 participants** |
| Mean silent trial | 641 participants |
| Largest single trial's share of the total | **21.0%** |
| Top 10 trials' share | **38.8%** |
| Top 100 trials' share | **63.2%** |

The largest contributor is `NCT05438901`, *"Investigation of Oxidant-antioxidant
Status in Patients Treated With Hirudotherapy"* — a **single-group before/after
study of leech therapy**, recorded as `ACTUAL` enrolment of **12,317,546**. That
is not a plausible count for that design. One probable data-entry error is over a
fifth of the pre-registered headline.

Most of the remaining top contributors are legitimate but are **behavioural
megastudies** — SMS nudges, online health advertisements, vaccine-booking
reminders. They genuinely enrolled millions. But "enrolled in a clinical trial
that never reported its results" invites a reader to picture a person taking an
experimental drug, not a person receiving a text message.

**Measured alternatives, none pre-registered:**

| Estimator | Value | vs raw sum |
|---|---|---|
| Raw sum (**pre-registered**) | 58,650,765 | 100% |
| Dropping the single largest trial | 46,333,219 | 79.0% |
| Each trial capped at 100,000 | 30,681,187 | 52.3% |
| Median × number of silent trials | 4,754,984 | 8.1% |
| Excluding `phase = NA` | 7,291,573 | 12.4% |

**Status: the frozen figure is computed and reported unmodified.** No estimator
has been substituted. Choosing one after seeing which reads better is exactly the
move the pre-registration exists to prevent, and the spread above — 8% to 100%
depending on the choice — is why.

**Proposed amendment**, to be argued from the table rather than the hunch: report
figure 3 as *the number of silent trials* (91,495, robust) with the participant
sum shown beside its median and top-10 concentration, never alone.

**This is the third time this project has met the same failure mode**, after the
control arm that never was and the change flag that overstated by 38%. A large,
clean, striking aggregate that is substantially an artefact, pointing in the
direction the project hoped to find. It is beginning to look like the default
outcome of any naive aggregate over this registry rather than bad luck.

---

## F4 — Non-reporting is a census, and it varies enormously by sponsor

**31 August 2026 · [`data/figures/reporting.txt`](data/figures/reporting.txt) ·
result**

`hasResults` is carried in the frozen frame, so figure 2 needs no crawl and is a
**census, not a sample**. Every trial in the denominator is more than three years
past the 12-month deadline, so an absent result is settled rather than pending.

**91,495 of 126,760 trials — 72.2% — have no results posted.**

Among the 35,265 that did post, **87.2% were later than 365 days**, median 584
days, 90th percentile 1,522 days.

The variation by sponsor is larger than the headline:

| Lead sponsor class | Trials | Silent | Rate |
|---|---|---|---|
| `OTHER_GOV` | 2,586 | 2,487 | **96.2%** |
| `OTHER` (academic, hospital, foundation) | 88,403 | 70,572 | **79.8%** |
| `INDUSTRY` | 32,449 | 17,125 | **52.8%** |
| `FED` | 1,187 | 424 | 35.7% |
| `NIH` | 1,265 | 351 | **27.7%** |

**Industry reports at roughly twice the rate of academia**, which inverts the
direction most readers would guess. NIH-sponsored trials are the best in the
frame by a wide margin.

By phase, `PHASE3` — the trials that support approvals — is **43.7% silent**.

These are rates, not sums, so they are not vulnerable to the outlier problem in
F5. They are the most defensible numbers the project currently holds.

**Not a claim of illegality.** FDAAA applicability is not exposed by the API and
is not adjudicated here (`PREREGISTRATION.md` §10).

---

## F3 — The §5.4 blind spot is 21.8%, measured

**30 August 2026 · history register · accepted limitation**

`lastUpdateVersions.primaryOutcomes` reports only the **last** primary-outcome
change, so a trial changed retrospectively and then again prospectively is
invisible to the primary figure. `PREREGISTRATION.md` §5.4 accepted this without
knowing its size.

The history crawl records every version whose `moduleLabels` mention
`Outcome Measures`, so the size is now known: **27,612 trials — 21.8% — have more
than one outcome-touching version.**

This biases the reported rate **downward**, which is the direction the
pre-registration accepts. Fixing it means fetching every outcome-touching version
rather than two per trial, which is uncosted.

---

## F2 — The archive gate is a handshake profile, not a TLS library

**30 August 2026 · [`FEASIBILITY.md`](FEASIBILITY.md) §7.1 · correction**

`FEASIBILITY.md` predicted a Linux CI runner might be refused by the archive
endpoints because its curl links OpenSSL where the development machine's links
Schannel. Both runners were served, so M1 passed — but the stated reason was
wrong.

On `ubuntu-latest`, Python's `ssl` reports **OpenSSL 3.0.13** and curl links
**OpenSSL/3.0.13** — same library, same version, same machine — and curl is
served 200 while `urllib` is refused 403. The discriminator is the handshake
profile each client presents, not the library underneath.

Visible only because the probe ran on **both** operating systems rather than the
one in doubt. A single-OS run would have returned a passing result with a false
explanation attached, and the error would have surfaced years later as "the
collector stopped working and nobody knows which property mattered."

---

## F1 — The registry's change flag overstates outcome switching by 37.7%

**30 August 2026 · [`FEASIBILITY.md`](FEASIBILITY.md) §4 · design change**

The project was pitched on reading
`history.lastUpdateVersions.primaryOutcomes`, dating it against primary
completion, and reporting the share of trials that edited their promise after the
fact. On the pilot that gives **30.5%**.

Fetching both versions and diffing the actual text gives **19.0%**. For one
flagged trial in seven, the primary outcome set is **byte-identical** across the
change the registry flagged.

The flag is computed on the field, not on the meaning. Adjudication became a
requirement rather than a refinement, and the frame-wide adjudicated figure is
what M4 produces.

The frame-wide **flagged** rate is **33.6%**, close to the pilot's 30.5%. The
survival ratio is deliberately **not** applied to it: whether a flag survives is a
property of the text, not of the sample.
