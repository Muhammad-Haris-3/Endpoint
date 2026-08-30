# Endpoint — gold-set labelling protocol

**Drafted 31 August 2026, after `data/gold/sample.tsv` was drawn and hashed, and
before any pair was labelled.**

Companion to [`PREREGISTRATION.md`](PREREGISTRATION.md) §5.3, which requires a
hand-labelled sample of **≥300 version pairs, labelled before Tier 2 is run over
the frame**, with published precision and recall for both tiers.

The sample is **419 pairs**, drawn under seed `20260831`, hashed in
`data/gold/SAMPLE_MANIFEST`. It is drawn once. Redrawing after seeing how either
tier performs would make the set a function of the result.

---

## 0. Who labels this, and why it cannot be me

**This document was drafted by an AI assistant. The labels must not be.**

Tier 2 — the semantic adjudicator this gold set exists to evaluate — is an LLM.
If an LLM also produces the reference labels, then precision and recall computed
against them measure **agreement between two language models, not accuracy**.
Two systems sharing a training distribution, a tokenizer, and a family of failure
modes will agree most confidently exactly where they are both wrong. A validation
step built that way does not catch the errors it exists to catch; it launders
them, and it does so while producing a reassuring number.

That would be the fifth instance of this project's recurring failure — a clean,
publishable figure that is substantially an artefact — and the first one
deliberately constructed rather than stumbled into.

So:

| | |
|---|---|
| **Required** | A human labeller applying §2–§4, blind to the Tier 1 verdict |
| **Strongly preferred** | A second human on the overlap subset (§5), so agreement is measured rather than assumed |
| **Ideal** | At least one labeller with clinical-trials or systematic-review experience. §3's hard cases are domain judgements, not reading comprehension |
| **Not acceptable as the gold set** | Any LLM, including the one that drafted this file |

**If an LLM is used anyway** — because no human is available and a number is
wanted — then every figure derived from it must be labelled *"machine-labelled
reference, not a gold set"*, and the published metric must be described as
**inter-model agreement**. It may not be called precision or recall against
ground truth, and `PREREGISTRATION.md` §5.3 is then **not** satisfied, so Tier 2
still may not enter any reported figure.

---

## 1. The question being asked

For each pair, the labeller sees the primary outcome set as it stood at version
*v−1* and at version *v*, and answers one question:

> **Would a reader who trusted the earlier version be misled about what this
> trial pre-specified as its primary outcome?**

Not "did the text change" — the classifier already answers that, and gets it
wrong in both directions. The question is whether **the thing being measured**
changed.

---

## 2. The label set

| Label | Meaning | Substantive? |
|---|---|---|
| `SAME` | The same quantity, restated. Capitalisation, punctuation, house style, expanding an abbreviation | **No** |
| `REFINED` | The same quantity, made more precise. A timepoint that was implicit is now written out; units are added; a vague phrase is specified without changing what is measured | **No** |
| `DIFFERENT` | A different quantity is now primary. A different endpoint, a different population, a different timepoint that changes what the result would be | **Yes** |
| `SET_CHANGED` | The set of primary outcomes gained or lost a member in substance — not merely split, merged, or reworded | **Yes** |
| `UNCLEAR` | The text does not permit a judgement | *excluded from metrics, reported as a count* |

`REFINED` is the hard boundary and the reason a domain labeller matters. **The
test is counterfactual: could this change flip whether the trial reports a
positive result?** If yes, it is `DIFFERENT`, however small the edit looks.

---

## 3. Codebook — the cases that will actually come up

**Rule 1 — read the timeframe as part of the endpoint.** *"Pain score"* at 6
weeks and *"Pain score"* at 12 months are different endpoints. A change to
`timeFrame` alone can be `DIFFERENT`.

**Rule 2 — a units or reporting-format change is `SAME`.** *"Percent of
participants with X"* → *"Number of Participants With X"* measures the same
thing, reported differently. This is a very common results-form restatement.

**Rule 3 — adding a threshold is `DIFFERENT`, not `REFINED`.** *"Clearance of
warts"* → *"**Complete** clearance of warts **at or before week 12**"* changes
which participants count as successes. It could flip the result.

**Rule 4 — splitting or merging is `SAME` only if each resulting measure is
still judged on its own.** Presenting the same measurements as two rows instead
of one, or one instead of two, is a formatting artefact even though the count
changed — Tier 1 calls it `COUNT_CHANGED`, and quantifying that error is part of
why this gold set exists.

**But combining separate outcomes into a single `COMPOSITE` score is
`DIFFERENT`.** *"All-cause death"* and *"ventilator-free days"* judged separately
require an effect on one or the other; a composite of the two is one number that
**can come out positive when neither component would**. That moves the bar, so it
fails the counterfactual test and is a substantive change however much it looks
like tidying.

**Rule 5 — an empty earlier version is `UNCLEAR`, not `SET_CHANGED`,** unless the
later version's outcome contradicts something the trial stated elsewhere. A
registration that had no primary outcome and later has one may be a registration
being completed, not a promise being changed. (`FINDINGS.md` and
`adjudicate_frame.py` already report these separately; here they are labelled
honestly rather than assumed.)

**Rule 6 — a secondary outcome promoted to primary is `DIFFERENT`.** This is the
classic form of outcome switching and Tier 1 cannot see it at all. The labelling
tool shows the secondary outcomes for exactly this reason.

**Rule 7 — order is not meaning.** Compare the outcome sets as *sets*. The
results form reorders outcomes routinely. If the same measures appear in both
versions with only their positions changed, that is `SAME`; judge only whether a
measure was added, dropped, or altered.

**Rule 8 — when genuinely torn, label `UNCLEAR`.** A forced guess is worse than a
recorded uncertainty: `UNCLEAR` is reported as a count and excluded from the
metrics, so it costs coverage rather than corrupting accuracy.

---

## 4. Blinding

The labelling tool (`scripts/label_tool.py`) **does not show**:

- the Tier 1 verdict,
- whether the change is posting-coincident,
- the sponsor, the phase, or whether the trial reported results,
- the number of days between completion and the change.

All of these would anchor the judgement toward the answer the project already
has. The labeller sees the two outcome sets, the secondary outcomes, and nothing
else. The join back to Tier 1 happens in `gold_eval.py`, after labelling.

Labels are written **append-only** with a timestamp per decision. A changed mind
is recorded as a second row, not an overwrite, so the history of the labelling is
as inspectable as the history of the trials.

---

## 5. Inter-rater reliability

The **first 60 pairs in sample order** are the overlap subset. If a second
labeller is available they label those 60 independently, and **Cohen's κ on the
binary substantive/not collapse is published** with the metrics.

If κ < 0.6 the codebook is the problem, not the labellers: §3 is revised, both
labellers redo the overlap, and **the revision is recorded in `FINDINGS.md`
before the full set is labelled**. A codebook tuned after seeing the full results
is not a codebook.

Single-labeller sets are acceptable but must publish **"κ not measured, one
labeller"** beside every metric. An unreplicated judgement is not a measurement.

---

## 6. What the labels are used for

1. **Tier 1's precision and recall**, per verdict class and reweighted to the
   frame by the `weight` column. This is publishable on its own and does not
   depend on Tier 2 existing.
2. **The F6 question**, which is now the most important thing the gold set can
   answer: *among posting-coincident changes, what share are substantive?* That
   single number decides whether the 19.9% headline is mostly bookkeeping or
   mostly real, and no amount of date arithmetic can reach it.
3. **Tier 2's precision and recall**, if and only if §0 is satisfied.

**Reweighting is mandatory.** The sample is stratified and unequally weighted; a
raw mean over these 419 rows is not a frame estimate, and `gold_eval.py` refuses
to report one.

---

## 6a. Codebook revision log

A codebook tuned after seeing results is not a codebook (§5). Revisions are
therefore recorded here with what had been labelled when they were made.

| # | Date | Change | Labels existing at the time |
|---|---|---|---|
| 1 | 31 Aug 2026 | **Rule 7 added** (order is not meaning) and **Rule 4 corrected** (merging is `SAME` only if the parts are still judged separately; a *composite* is `DIFFERENT`). Both gaps surfaced on first contact with real pairs — the very first pair drawn is a reorder, and a worked example was a two-endpoint→composite merge that Rule 4 as written would have waved through. | **3** (`NCT00329706`, `NCT00475982`, `NCT00508794`) |

**On revision 1 and those three labels.** None contradicts the new rules.
`NCT00329706` is a reorder already labelled `SAME`, which is what Rule 8 now
states; the other two are one-to-one changes untouched by either rule. They were
made under an undocumented judgement that the revision has since formalised, and
they are **not** being relabelled. This note exists so a reader can see that and
disagree, rather than having to reconstruct it from timestamps.

No result had been computed when this revision was made. The revision cannot
have been tuned to one.

---

## 7. Status

| | |
|---|---|
| Sample drawn and hashed | ✅ 419 pairs, seed 20260831 |
| Protocol written before labelling | ✅ this document |
| Labelling tool built | ✅ `scripts/label_tool.py` |
| Evaluation harness built | ✅ `scripts/gold_eval.py` |
| **Pairs labelled** | **3 of 419** — labelling under way |
| Tier 2 built | ❌ and may not be, until the above is non-zero |
