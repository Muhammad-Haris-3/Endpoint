# Endpoint — findings and deviations, accumulating

Discoveries, corrections, and things that turned out otherwise than the design
assumed. Newest first. Each entry says what was believed, what was measured, and
what changed as a result.

Nothing here overrides [`PREREGISTRATION.md`](PREREGISTRATION.md). Where a
finding implies a rule should change, that is recorded as a **proposed
amendment** and stays proposed until it is argued and numbered under §11.

---

## F10 — The codebook revision worked: kappa 0.402 to 0.609

**31 August 2026 · `data/gold/labels.ndjson` · §5 clause resolved, with one
limitation I cannot now remove**

The human relabelled all 60 overlap pairs under the revised codebook (Rules 8–10,
§6a revision 2). Everything improved:

| | Before revision | **After** |
|---|---|---|
| Binary agreement | 72.9% | **81.7%** |
| Exact label match | 52.5% | **70.0%** |
| **Cohen's κ** | 0.402 | **0.609** |
| Boundary-crossing disagreements | 16 | **11** |

**κ = 0.609 clears the 0.6 floor `GOLDSET_PROTOCOL.md` §5 set before any
labelling began.** The clause fired on data, the codebook was revised, and the
revision is measurably the fix rather than assertedly so. Exact-match agreement
rising 17.5 points says the labellers now mean the same things by the same words,
not merely that they land on the same side.

On the same 60 pairs the two passes are now within **1.6 points**: human 36.7%
substantive, machine 38.3%.

### It clears the threshold, but not decisively

κ = 0.609 with an approximate 95% CI of **0.400 to 0.818**. The point estimate is
over the line; the interval is not. At n = 60 that is unavoidable, and it is the
reason §5.3 asks for ≥300 rather than 60. **This licenses continuing, not
concluding.**

### The limitation, and why it stays

The human's 60 were relabelled under the revised codebook. **The machine's 419
were labelled before Rules 8–10 existed.** κ is therefore measured across a
codebook mismatch, and §5 asks that *both* labellers redo the overlap.

**I have not relabelled, and will not.** I have now seen the human's labels and
the disagreement list. Relabelling under that knowledge would move the reference
pass toward agreement by exactly the mechanism the pre-registration exists to
prevent, and would inflate κ while appearing to validate it. **An uncorrectable
limitation honestly recorded is worth more than a clean number obtained by
contamination.**

What follows from that:

1. **κ = 0.609 is a floor, not a clean measurement.** A machine pass made under
   the current codebook would plausibly agree better; that cannot now be
   established without a fresh, blind pass.
2. **Any future machine pass must be made blind** to the human labels and under
   the codebook current at the time, with both recorded.
3. **The human labels are the reference**; the machine pass remains a stale
   reference pass and is not a gold set.

### Status

Labelling may continue toward the 300 that `PREREGISTRATION.md` §5.3 requires.
Tier 2 stays blocked until it gets there. No published figure changes.

---

## F9 — kappa 0.402 on 59 pairs: the codebook, not the labellers

**31 August 2026 · `data/gold/labels.ndjson` · supersedes F8's kappa · triggers
`GOLDSET_PROTOCOL.md` §5**

The spot check reached the 60 pairs §5 asks for. F8's κ = 0.000 was an artefact
of n = 10 and is superseded.

| | n=10 (F8) | **n=59** |
|---|---|---|
| Binary agreement | 50.0% | **72.9%** |
| Exact label match | 40.0% | **52.5%** |
| **Cohen's κ** | 0.000 | **0.402** |

κ = 0.402 is fair-to-moderate. **It is below the 0.6 floor `GOLDSET_PROTOCOL.md`
§5 sets**, and §5 is explicit about what that means: *the codebook is the problem,
not the labellers.* That clause now fires on its own terms.

### The aggregate agrees while the cases do not

| | Substantive share |
|---|---|
| Human (n=60) | **28.3%** |
| Machine (n=419) | **31.0%** |

Within three points. **That is not reassurance.** Two labellers can disagree on
half the individual pairs and still land on the same total, because the errors run
in both directions and cancel. Endpoint publishes a per-trial explorer where every
figure drills through to a specific trial, so **per-case accuracy is the product,
not the aggregate.** A site that is right on average and wrong on the row you
happen to open is not right.

### Where the disagreements actually are

Of 28 disagreements, only **16 cross the substantive boundary** — the rest are
`SAME` vs `REFINED` or `DIFFERENT` vs `SET_CHANGED`, which land on the same side
and cannot move any figure.

Of those 16, **seven are one shape**: the human chose `REFINED` where the machine
chose `DIFFERENT`, on a vague endpoint replaced by a specific one, or a changed
timeframe.

| Trial | Human | Machine |
|---|---|---|
| `NCT00669877`, `NCT00715273`, `NCT00942890` | `REFINED` | `DIFFERENT` |
| `NCT01573507`, `NCT01591746`, `NCT01610414`, `NCT01930682` | `REFINED` | `DIFFERENT` |

**That is precisely the gap the drafted Rule 8 addresses**, and it was drafted
before these labels existed. Nearly half the consequential disagreement is one
undefined boundary.

A second, harmless pattern: the human labelled `REFINED` where the machine
labelled `SAME` eight times, often on pure capitalisation. Both are
non-substantive, so no figure moves — but it says the `SAME`/`REFINED` line is
also underspecified, and a labeller reading the codebook cannot tell which to use.

### What happens next, per §5

1. **Commit Rules 8–10** (vague→specific, inverse framing, component dropped from
   a stated combination), logged in §6a with the label count at the time.
2. **Redo the 60-pair overlap** under the revised codebook. The tool appends, so
   both judgements stay in the record and the revision's effect is measurable
   rather than asserted.
3. **Recompute κ.** If it clears 0.6, labelling continues toward the 300 §5.3
   requires. If not, the codebook is still wrong and more labelling is waste.

**No figure changes on the basis of this run**, and the machine pass remains a
reference pass, not a gold set.

---

## F8 — The machine label pass agrees with the human at chance (kappa = 0.000)

> **Superseded by F9.** This entry's κ was computed on n = 10. At n = 59 the
> figure is 0.402. The systematic pattern it identified stands; the κ does not.

**31 August 2026 · `data/gold/labels.ndjson` · blocking for Tier 2**

All 419 sampled pairs were labelled by an LLM as a **reference pass**, explicitly
not as a gold set (`GOLDSET_PROTOCOL.md` §0). Ten of them also carry a human
label. On those ten:

| | |
|---|---|
| Binary agreement (substantive / not) | **5 / 10 = 50.0%** |
| Exact label match | 4 / 10 = 40.0% |
| **Cohen's κ** | **0.000** |

κ = 0 is agreement at exactly the rate chance predicts. **n = 10 is far too small
to estimate κ**, and the confidence interval on it spans nearly the whole range —
so this is not evidence that the machine pass is worthless. It is, however,
entirely absent of evidence that it is any good, which is the same thing for a
figure that would otherwise be published.

### The disagreements are systematic, which is more informative than the κ

| Trial | Human | Machine |
|---|---|---|
| `NCT00669877` | `REFINED` | `DIFFERENT` |
| `NCT00715273` | `REFINED` | `DIFFERENT` |
| `NCT00942890` | `REFINED` | `DIFFERENT` |
| `NCT00816062` | `REFINED` | `SAME` |

Four of the six disagreements are the human choosing **`REFINED`** where the
machine chose something substantive, and all four are the same shape: a **vague
earlier outcome replaced by a specific later one** — *"lower extremity muscle
strength and mobility"* becoming six named measures, or *"changes in carotid
plaque composition"* becoming two named volumetric endpoints.

`GOLDSET_PROTOCOL.md` §2 already names this as "the hard boundary and the reason
a domain labeller matters". It is not merely hard — **the codebook does not
adjudicate it at all.** Rule 3 covers adding a *threshold*; nothing covers
replacing a vague endpoint with a specific one, which is one of the most common
shapes in the data.

**This is a defect in the instrument, not in either labeller.** Two careful
readers applying the written rules can reach opposite verdicts on the same pair,
which means the rules are underdetermined.

### What the machine pass says about F6, and why it cannot be believed yet

Using the machine labels, weighted to the frame:

| | Substantive share |
|---|---|
| Changes **within 31 days** of results posting | **35.8%** |
| Changes **not** posting-coincident | **39.1%** |

If that held, it would substantially **defuse F6**: posting-coincident changes
would be barely less substantive than any other kind, so the results-form
restatement would not be quietly inflating the headline after all.

**It cannot be believed on this basis.** The labels producing it agree with the
only human check at chance. A number that would weaken the project's most serious
caveat is precisely the number to distrust when its source is unvalidated — and
it is exactly the direction an LLM asked to judge its own kind of output would be
expected to err.

### Consequences

1. **Tier 2 remains blocked.** `PREREGISTRATION.md` §5.3 requires ≥300 hand
   labels; there are 10.
2. **The F6 answer above is not published on the site** and does not modify the
   19.9% headline or its caveat.
3. **The codebook needs a rule for vague → specific**, argued and written down
   *before* more labelling, and recorded in §6a like the others.
4. **The spot check needs to reach 60**, per `GOLDSET_PROTOCOL.md` §5, before κ
   means anything at all.

Tier 1 vs the machine pass, for completeness and with the same caveat: positive
agreement **56.9%**, sensitivity **84.2%** (frame-weighted). Tier 1 flags
substantially more than the machine pass calls substantive — consistent in
direction with `FEASIBILITY.md` §4, and equally unvalidated.

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
