# Endpoint — M8 (Decision Memo) Milestone Summary

Companion to [Endpoint_SRS_v1.0.md](Endpoint_SRS_v1.0.md) (Section 12) and
[DECISION_MEMO.md](DECISION_MEMO.md).

**Status: Complete** — 2026-09-01

---

## 1. Scope (per SRS Section 12)

> Decision memo. Exit criterion: `DECISION_MEMO.md`, two pages, no statistics
> required.

A document for a reader who will open nothing else — a regulator, a journalist, a
hiring manager — that states what was found, what was not, and what to do about
it, without requiring the reader to follow a method.

## 2. What was built

| Area | Delivered |
|---|---|
| **The memo** | [`DECISION_MEMO.md`](DECISION_MEMO.md) — 973 words. Four sections: the finding, the number that is not ready, why that matters more than the number, and what to do with it |
| **Wiring** | Linked as the first row of the README's five-minute table, and as a companion document in the SRS header |

## 3. Artefact change

None. The memo reports figures already computed and committed; it introduces no
new analysis and no new number.

## 4. How it was verified (not just "should work")

1. **Every figure traced to its source before being written down**: 72.2% and the
   sponsor table from `data/figures/reporting.json`; 33.6% and 19.9% from
   `data/register/versions-2026-08-30/verdicts.txt`; the 59.0% / 4.8% split and
   the 70.9% posting-coincidence from `FINDINGS.md` F6; the enrolment
   concentration from F5.
2. **No statistic appears that the repository cannot produce on demand.** There
   is no rounding toward a rounder number and no figure carried over from memory.
3. **Length checked against the exit criterion**: 973 words, which prints as two
   pages.
4. **The confound is in the memo, not a footnote to it.** A reader who stops
   after the second section has still been told the headline is entangled with
   reporting.

## 5. Decisions & notes worth remembering

- **The memo leads with figure 2, not figure 1.** The instinct is to lead with
  outcome switching, because that is the interesting crime. But 72.2%
  non-reporting is a **census** — no sampling, no model, nothing to argue with —
  while 19.9% is confounded (`FINDINGS.md` F6). Leading with the weaker number
  because it is the more exciting one is how a project spends its credibility on
  its worst evidence.
- **"We cannot yet say how many of those rewrites mattered" is stated as the
  position, not buried as a limitation.** A memo that has to be read to the end
  before it admits its central number is entangled is a memo designed to be
  misquoted.
- **The four artefacts are a section, not an appendix.** For a reader deciding
  whether to trust the numbers, the record of four headline figures that did not
  survive checking is stronger evidence of care than any individual result. It is
  also the part of this project that generalises: the checks that caught them
  cost minutes.
- **The sponsor inversion is called out explicitly** — a "which sponsors switch
  most" ranking reproduces the reporting table upside down, with NIH appearing
  worst while being the best reporter. Anyone reusing this data will build that
  chart, and it is wrong.
- **No recommendation is made that the data cannot support.** The memo says the
  registry answers the reporting question today and does not yet answer the
  switching question. It does not call for enforcement, name a sponsor, or imply
  intent.

## 6. Definition of Done (SRS Section 12) — checked

- [x] Two pages, no statistics required
- [x] Every figure traceable to a committed artefact
- [x] The F6 confound stated in the body, not deferred
- [x] Linked from the README and the SRS
- [x] No claim beyond what the data supports; no sponsor named, no intent implied

## 7. Next

**M5 remains the only open milestone**: 240 more hand labels to reach the 300
`PREREGISTRATION.md` §5.3 requires. When it lands, the memo's central caveat
becomes a number, and this document is revised rather than replaced.

The two proposed amendments in [FINDINGS.md](FINDINGS.md) — F5 (the participant
sum) and F6 (stratifying figure 1 by reporting status) — are decisions, not
builds, and both remain open.

---

## Document Control

| Version | Date | Change |
|---|---|---|
| 1.0 | 1 September 2026 | Memo written and wired in; leads with the census figure, states the confound in the body |
