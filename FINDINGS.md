# Endpoint — findings and deviations, accumulating

Discoveries, corrections, and things that turned out otherwise than the design
assumed. Newest first. Each entry says what was believed, what was measured, and
what changed as a result.

Nothing here overrides [`PREREGISTRATION.md`](PREREGISTRATION.md). Where a
finding implies a rule should change, that is recorded as a **proposed
amendment** and stays proposed until it is argued and numbered under §11.

---

## F7 — The codebook had two gaps, and labelling found both in its first minutes

**31 August 2026 · [`GOLDSET_PROTOCOL.md`](GOLDSET_PROTOCOL.md) §3, §6a ·
protocol revision**

The gold-set codebook was written before anyone had labelled a pair. Two rules
were wrong or missing, and both showed up within the first few real examples.

**The very first pair drawn is a reorder** — four primary outcomes, same four
after, listed in a different order, with `2 years` restated as `baseline and 2
years`. The codebook said nothing about ordering at all, so the labeller's first
decision would have been an undocumented judgement call. **Rule 7** now states
that order is not meaning and sets are compared as sets.

**Rule 4 was actively wrong.** It said merging two outcomes into one is `SAME`
"with the same underlying measurements". A worked example — `NCT02622724`,
*"any cause death"* and *"days free of mechanical ventilation"* becoming
*"Composite Endpoint (VFDsurv; All-cause Mortality and Number of Days Free of
Mechanical Ventilation)"* — shows why that is backwards. Judged separately, the
trial needs an effect on one or the other. As a composite it is **one number that
can be positive when neither component would be.** The bar moved. Rule 4 as
written would have classified one of the most consequential changes a trial can
make as tidying.

Corrected: merging is `SAME` only if each resulting measure is still judged on
its own; a composite is `DIFFERENT`.

**Both revisions were made with 3 pairs labelled and no result computed**, so
neither can have been tuned to an outcome. None of the three contradicts the new
rules and none is being relabelled; the reasoning is recorded in
`GOLDSET_PROTOCOL.md` §6a so a reader can disagree with it.

**Worth keeping:** a codebook written in the abstract survived about four real
examples. The instrument had to meet the data before it was right, which is an
argument for labelling a handful of pairs *deliberately* as a codebook shakedown
before committing to a full pass — and for the revision log that makes such
changes visible rather than silent.

---

## F6 — Primary figure 1 cannot separate outcome switching from results posting

**31 August 2026 · `data/register/versions-2026-08-30/verdicts.ndjson.gz` ·
proposed amendment · the most serious issue in the project**

Primary figure 1 is **25,187 of 126,760 trials, 19.9%**, computed exactly as
`PREREGISTRATION.md` §5.1 and §6 specify. The figure stands. **What it means does
not survive the following.**

### The rate depends almost entirely on whether the trial reported

| | Trials | Flagged as switching | Rate |
|---|---|---|---|
| **Posted results** | 35,265 | 20,818 | **59.0%** |
| **Posted nothing** | 91,495 | 4,369 | **4.8%** |

A **12-fold** difference. And it propagates straight into the sponsor breakdown,
which now reads as a near-perfect inversion of the reporting table in F4:

| Lead sponsor | Silent rate (F4) | "Switching" rate |
|---|---|---|
| `NIH` | 27.7% (best) | **56.1%** (worst) |
| `FED` | 35.7% | 39.5% |
| `INDUSTRY` | 52.8% | 32.6% |
| `OTHER` (academic) | 79.8% | 14.7% |
| `OTHER_GOV` | 96.2% (worst) | **7.8%** (best) |

**The sponsors who report best appear to switch most, in near-exact rank order.**
That is not a finding about research integrity. It is the reporting rate,
measured twice.

### The mechanism, verified

Among defensible retrospective changes in trials that posted results:

| | |
|---|---|
| Change within **7 days** of results posting | 19.8% |
| Change within **31 days** | **70.9%** |
| Change within **92 days** | 88.9% |
| Median gap (posting − change) | **24 days** |

ClinicalTrials.gov's results-submission process requires the sponsor to restate
the outcome measures in a structured results format. That restatement is
submitted as a **new record version, dated at posting time** — which is after
primary completion by construction. The registry cannot distinguish it from a
substantive edit, and neither can Tier 1.

**~14,767 of the 25,187 trials in primary figure 1 — 58.6% — changed their
outcome within a month of posting results.**

### What this does and does not license

It would be wrong to conclude the changes are therefore benign. **Results posting
is precisely when genuine outcome switching would occur** — it is the moment the
sponsor writes up what they found, having seen it. The classic form of the
offence and the mechanical artefact of the submission format happen at the same
instant, in the same field, and the timestamp cannot separate them.

So the honest statement is not "19.9% is inflated" and not "19.9% is real". It is:

> **The measure conflates two things that occur simultaneously, and no amount of
> date arithmetic separates them.** Distinguishing them requires reading whether
> the *substance* of the endpoint changed — the semantic tier — against a
> hand-labelled gold set. That is M5, and it is now load-bearing rather than an
> enhancement.

### Consequences, none applied unilaterally

1. **The figure is not withdrawn.** It is computed as pre-registered and reported
   with this caveat attached wherever it appears, including on the site.
2. **Reporting status must be a published stratum**, not a footnote: 59.0% vs
   4.8% is the second-most important number the project holds.
3. **Proposed amendment:** report figure 1 stratified by reporting status, and
   report the posting-coincident share alongside it. Excluding changes within 31
   days of posting would give **10,420 trials, 8.2% of the frame** — still above
   the 5% kill condition, but a different claim. **Not applied**: excluding a
   category after seeing it move the headline by more than half is exactly what
   §11 requires an amendment for.
4. **The sponsor breakdown of figure 1 must not be published** in its current
   form. It reads as a ranking of integrity and is a ranking of compliance.

**This is the fourth time this project has met the same failure mode**, and the
first time it reached a *primary* figure rather than a secondary one. The pattern
is now unmistakable: every naive aggregate over this registry has been
substantially an artefact, and each was caught only by asking what else could
produce the number.

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
