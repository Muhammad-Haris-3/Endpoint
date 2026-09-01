# Do clinical trials keep the promise they made before they started?

**Endpoint · 1 September 2026 · two pages, no statistics required**

Every clinical trial writes down, before it enrols a single person, the one thing
it will measure. That promise is the entire basis of the evidence: a trial that
picks its outcome *after* seeing the data can find something in almost any
dataset.

ClinicalTrials.gov keeps every edit to that promise, dated, in public. This
project read all of it — **126,760 completed trials**, every version of every
registration — and asked whether the promises were kept.

---

## The finding

**Most trials never report anything at all.**

> **91,495 of 126,760 — 72.2% — posted no results.**

Every trial in that count finished more than three years ago. This is not a
backlog. Of the minority that *did* report, **87% took longer than the twelve
months the rules allow**, with a median of 584 days.

That number is a census, not an estimate. There is no sampling, no model, and
nothing to argue with.

**And it is not who you would guess.**

| Who ran the trial | Never reported |
|---|---|
| Other government | **96%** |
| Universities, hospitals, foundations | **80%** |
| **Industry** | **53%** |
| NIH-funded | **28%** |

**Pharmaceutical companies report their results at roughly twice the rate
universities do.** The public reasonably assumes the opposite. Among Phase 3
trials — the ones that support drug approvals — **44% still reported nothing.**

---

## The number everybody wants, and why it isn't ready

The headline question is *outcome switching*: did the trial quietly change what
it was measuring after it could already see the answer?

The registry appears to answer this directly. It flags which version last edited
the primary outcome, and dating those flags gives:

> **33.6% of trials changed their primary outcome after the data was in.**

**That number is wrong**, and it is wrong in the direction that flatters whoever
publishes it.

Fetching both versions and reading the actual text, more than a third of those
"changes" turn out to be capitalisation passes, reformatted time windows, or
records that are **word-for-word identical** on both sides. The real figure is
**19.9%** — about 25,000 trials.

And even that cannot yet be read as "25,000 trials switched their outcomes".
Here is why:

| | Flagged as switching |
|---|---|
| Trials that **reported** results | **59%** |
| Trials that reported **nothing** | **4.8%** |

A twelvefold gap. The explanation is mundane: **submitting results to
ClinicalTrials.gov requires retyping the outcome into the form's own format**,
and that retyping is filed as a dated edit — always after the trial finished.
Seven in ten flagged changes happen within a month of the results being posted.

So a large share of the 19.9% is paperwork.

**But not obviously all of it.** Filing the results is also precisely the moment a
sponsor *would* switch, because it is when they write up what they found, having
seen it. The innocent retyping and the real thing happen at the same instant, in
the same box. **No amount of date arithmetic separates them.** Only reading
whether the endpoint *means* something different can, and that work — 300
hand-labelled examples — is 60 done.

**The honest position: we can prove 25,000 trials rewrote their promise after
seeing the data. We cannot yet say how many of those rewrites mattered.**

---

## Why that matters more than the number

Four separate times in this project, a clean and striking headline turned out to
be substantially an artefact.

| The number | What it actually was |
|---|---|
| A control group comparing old versions against new | Comparing decade-old records with three-week-old ones. Would have produced a large, clean, entirely false result |
| 33.6% switched their outcomes | A third of it was capitalisation |
| 58.7 million people enrolled in unreported trials | The median such trial has **52** people. One record — a leech-therapy study listing 12.3 million participants — was a fifth of the total on its own |
| 19.9% switched their outcomes | Largely tracks who bothered to file paperwork |

Every one of those would have charted beautifully. Every one was caught only by
asking *what else could produce this number* — and each was caught by fetching a
few hundred extra records, never by thinking harder.

The fourth is the one that should worry anyone using this registry. **A ranking
of "which sponsors switch outcomes most" produces almost exactly the reporting
table, upside down.** NIH looks like the worst offender and is in fact the best
reporter. Published without the check, that chart reads as an integrity ranking
and is a compliance ranking wearing its clothes.

---

## What to do with this

**If you want to know whether trials keep their promises:** the registry answers
the reporting question definitively today. 72% silence is a real, checkable,
census-grade finding, and the sponsor breakdown inverts the public assumption.

**If you want to know about outcome switching:** do not use the registry's change
flag. It overstates by a third before you start, and what survives is entangled
with the act of reporting. Read the endpoint text, or do not make the claim.

**If you are building anything on this data:** assume your first aggregate is an
artefact until you have tried to break it. Four for four here — and the checks
that caught them cost minutes, not weeks.

---

**Everything above is reproducible.** The cohort was fixed and cryptographically
sealed before collection began; the analysis rules were written down and hashed
first; every figure on the public site links to the trial it came from.

**https://muhammad-haris-3.github.io/Endpoint/**

The full working, including every number this project decided *not* to publish
and why, is in [`FINDINGS.md`](FINDINGS.md).
