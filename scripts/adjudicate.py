"""How much of the naive signal survives reading the actual text?

WHY THIS EXISTS. `pilot.py` flags a trial when `history.lastUpdateVersions`
reports the primary outcome was last modified at a version dated after primary
completion. That flag is an UPPER BOUND and treating it as a finding would be
the project's first serious error.

The counter-example was found by hand before this script was written.
NCT02895035, flagged as a retrospective primary-outcome change 386 days after
completion. Fetching the two versions and reading them:

  v4  "the mean area under the curve change from baseline in pupil diameter
       over time to the end of cataract surgery"
      timeFrame: "N/A (during cataract surgery)"

  v5  "Mean Area Under the Curve Change From Baseline in Pupil Diameter Over
       Time to the End of Cataract Surgery"
      timeFrame: "During cataract surgery, with maximum end time of 20 minutes"

That is a capitalisation pass and a timeframe restatement applied when results
were attached. It is not outcome switching. The registry's change flag cannot
tell the two apart, because it is computed on the field, not on the meaning.

A headline built on the unadjudicated flag would be large, clean, and pointed in
exactly the direction this project hopes to find. That is the failure mode
Halflife's FEASIBILITY.md 4 describes: the naive comparison does not fail
loudly, it fails by returning the answer you wanted.

WHAT THIS MEASURES. For every flagged change, fetch the version before and the
version at the change, and classify what actually happened to the primary
outcome set:

  COUNT_CHANGED   a primary outcome was added or removed. Unambiguous.
  SUBSTANTIVE     the measure text differs beyond rewording.
  REWORDED        same measure, heavily overlapping tokens, different phrasing.
  TIMEFRAME_ONLY  same measure, different timeframe. Sometimes substantive.
  COSMETIC        identical after normalising case, entities and punctuation.
  IDENTICAL       byte-identical. The flag fired on a field this does not read.

Only the first two are defensible as outcome switching without a human reading
them. The gap between the flagged rate and the COUNT_CHANGED+SUBSTANTIVE rate is
the size of the artefact, and it is the number that decides whether the project
is worth building.

This is a lexical adjudicator, deliberately. It is the floor, not the ceiling:
it cannot tell that "HbA1c at 12 weeks" and "glycated haemoglobin at 3 months"
are the same endpoint, nor that a promoted secondary outcome is a switch. That
is the semantic layer the SRS specifies, and its value is measured against this
floor rather than asserted.
"""
import argparse, html, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch                                                    # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'pilot')
VERSION = 'https://clinicaltrials.gov/api/int/studies/%s/history/%d'

REWORD_JACCARD = 0.80       # token overlap above which a text change is "rewording"


def norm(s):
    """Case, HTML entities, punctuation and whitespace all removed.

    ClinicalTrials.gov double-escapes: the JSON carries `&#x2F;` for a slash.
    Unescaping twice is deliberate, not a mistake.
    """
    if not s:
        return ''
    s = html.unescape(html.unescape(s))
    s = s.lower()
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return ' '.join(s.split())


def jaccard(a, b):
    sa, sb = set(a.split()), set(b.split())
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / float(len(sa | sb))


def outcomes_of(doc):
    """[(measure, timeFrame)] for the primary outcomes of one version document."""
    study = doc.get('study', doc)
    om = (study.get('protocolSection') or {}).get('outcomesModule') or {}
    return [(o.get('measure') or '', o.get('timeFrame') or '')
            for o in (om.get('primaryOutcomes') or [])]


def classify(before, after):
    """Compare two primary-outcome sets. Returns (label, detail)."""
    if len(before) != len(after):
        return 'COUNT_CHANGED', '%d -> %d primary outcomes' % (len(before), len(after))

    if before == after:
        return 'IDENTICAL', 'byte-identical primary outcome set'

    # Order within the set is not meaningful, so compare as sorted normalised sets.
    nb = sorted(norm(m) for m, _ in before)
    na = sorted(norm(m) for m, _ in after)
    tb = sorted(norm(t) for _, t in before)
    ta = sorted(norm(t) for _, t in after)

    if nb == na and tb == ta:
        return 'COSMETIC', 'identical after normalisation'
    if nb == na:
        return 'TIMEFRAME_ONLY', '%s -> %s' % (tb[0][:60], ta[0][:60])

    sims = [jaccard(x, y) for x, y in zip(nb, na)]
    worst = min(sims) if sims else 0.0
    if worst >= REWORD_JACCARD:
        return 'REWORDED', 'min token jaccard %.2f' % worst
    return 'SUBSTANTIVE', 'min token jaccard %.2f' % worst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rows', default=os.path.join(OUT, 'history_pilot.json'))
    ap.add_argument('--out', default=os.path.join(OUT, 'adjudication'))
    ap.add_argument('--rate', type=float, default=2.0)
    ap.add_argument('--limit', type=int, default=0, help='0 = every flagged trial')
    args = ap.parse_args()

    rows = json.load(open(args.rows, encoding='utf-8'))
    flagged = [r for r in rows
               if isinstance(r.get('po_last_change_version'), int)
               and r['po_last_change_version'] >= 1]
    if args.limit:
        flagged = flagged[:args.limit]

    lines = []

    def log(msg):
        print(msg, flush=True)
        lines.append(msg)

    pacer = fetch.Pacer(args.rate)
    log('ADJUDICATION OF FLAGGED PRIMARY-OUTCOME CHANGES')
    log('flagged trials in pilot sample: %d of %d' % (len(flagged), len(rows)))
    log('fetching 2 versions each (before, at-change)')
    log('')

    verdicts, failures = [], 0
    for i, r in enumerate(flagged, 1):
        v = r['po_last_change_version']
        a, ra = fetch.get_json(VERSION % (r['nct'], v - 1), pacer=pacer)
        b, rb = fetch.get_json(VERSION % (r['nct'], v), pacer=pacer)
        if a is None or b is None:
            failures += 1
            continue
        before, after = outcomes_of(a), outcomes_of(b)
        label, detail = classify(before, after)
        verdicts.append({
            'nct': r['nct'],
            'version': v,
            'retrospective': (r.get('po_days_after_pc') or 0) > 0,
            'days_after_pc': r.get('po_days_after_pc'),
            'label': label,
            'detail': detail,
            'before': [m for m, _ in before],
            'after': [m for m, _ in after],
            'has_results': r.get('has_results'),
        })
        if i % 25 == 0:
            log('  %d/%d adjudicated' % (i, len(flagged)))

    log('  adjudicated %d, failed %d' % (len(verdicts), failures))
    log('')

    order = ['COUNT_CHANGED', 'SUBSTANTIVE', 'REWORDED', 'TIMEFRAME_ONLY',
             'COSMETIC', 'IDENTICAL']
    retro = [v for v in verdicts if v['retrospective']]

    def table(title, subset):
        log(title + '   (n=%d)' % len(subset))
        log('   %-16s %6s  %7s' % ('verdict', 'count', 'share'))
        log('   ' + '-' * 34)
        for label in order:
            c = sum(1 for v in subset if v['label'] == label)
            share = ('%.1f%%' % (100.0 * c / len(subset))) if subset else 'n/a'
            log('   %-16s %6d  %7s' % (label, c, share))
        real = sum(1 for v in subset if v['label'] in ('COUNT_CHANGED', 'SUBSTANTIVE'))
        log('   ' + '-' * 34)
        log('   %-16s %6d  %7s' % ('defensible', real,
                                   ('%.1f%%' % (100.0 * real / len(subset))) if subset else 'n/a'))
        log('')
        return real

    table('ALL FLAGGED CHANGES', verdicts)
    real_retro = table('RETROSPECTIVE ONLY (changed after primary completion)', retro)

    log('THE NUMBER THAT MATTERS')
    log('   naive retrospective rate     %d / %d trials sampled = %s'
        % (len(retro), len(rows), '%.1f%%' % (100.0 * len(retro) / len(rows)) if rows else 'n/a'))
    log('   adjudicated retrospective    %d / %d trials sampled = %s'
        % (real_retro, len(rows), '%.1f%%' % (100.0 * real_retro / len(rows)) if rows else 'n/a'))
    if len(retro):
        log('   share of the naive signal that survives reading the text: %.1f%%'
            % (100.0 * real_retro / len(retro)))
    log('')

    log('WORKED EXAMPLES  (defensible retrospective changes)')
    shown = 0
    for v in sorted([v for v in retro if v['label'] in ('COUNT_CHANGED', 'SUBSTANTIVE')],
                    key=lambda v: -(v['days_after_pc'] or 0)):
        log('   %s  +%sd  %s  (%s)' % (v['nct'], v['days_after_pc'], v['label'], v['detail']))
        for m in v['before'][:2]:
            log('       before: %s' % m[:110])
        for m in v['after'][:2]:
            log('       after : %s' % m[:110])
        shown += 1
        if shown >= 6:
            break
    if not shown:
        log('   none in this sample')

    with open(args.out + '.txt', 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(lines) + '\n')
    with open(args.out + '.json', 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(verdicts, fh, indent=1, sort_keys=True)
    print('\nwrote %s.txt and %s.json' % (args.out, args.out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
