"""The adjudication rules, in one place because PREREGISTRATION.md 5.1 fixes them.

These rules were frozen on 30 August 2026. They are reproduced here verbatim from
the pilot implementation so that the pilot in data/pilot/adjudication.json and the
frame-wide run in M4 are produced by the SAME code rather than by two copies that
agree until one is edited.

    COUNT_CHANGED   the number of primary outcomes differs
    SUBSTANTIVE     measure text differs, min pairwise token Jaccard < 0.80
    REWORDED        measure text differs, min Jaccard >= 0.80
    TIMEFRAME_ONLY  measures normalise equal, timeframes differ
    COSMETIC        equal after normalising case, entities and punctuation
    IDENTICAL       byte-identical

Only COUNT_CHANGED and SUBSTANTIVE enter primary figure 1.

Changing any threshold or rule here changes a pre-registered analysis and needs a
numbered amendment under PREREGISTRATION.md 11, not an edit. Run --selftest after
touching anything: it re-derives the pilot's committed verdicts from the pilot's
committed texts and fails if any of them move.
"""
import html, re, sys

# PREREGISTRATION.md 5.1. Fixed at freeze. Sensitivity at 0.70 and 0.90 is
# published alongside the primary figure whatever it shows.
REWORD_JACCARD = 0.80

ORDER = ['COUNT_CHANGED', 'SUBSTANTIVE', 'REWORDED', 'TIMEFRAME_ONLY',
         'COSMETIC', 'IDENTICAL']

DEFENSIBLE = ('COUNT_CHANGED', 'SUBSTANTIVE')


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


def classify(before, after):
    """Compare two primary-outcome sets. Each is [(measure, timeFrame), ...].

    Returns (label, detail).
    """
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


def _selftest():
    """Re-derive the pilot's committed verdicts and fail if any moved.

    data/pilot/adjudication.json stores the before/after MEASURE lists but not
    the timeframes, so verdicts that turn on a timeframe cannot be reproduced
    from it. Those are skipped and counted rather than quietly passed: a self-test
    that reports 100% while silently skipping a category is worse than none.
    """
    import json, os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, 'data', 'pilot', 'adjudication.json')
    if not os.path.exists(path):
        print('selftest: %s not found' % path)
        return 1

    rows = json.load(open(path, encoding='utf-8'))
    checked = skipped = failed = 0
    for r in rows:
        # Without timeframes, only these verdicts are decidable from the stored
        # measures alone. The rest depend on data the pilot output did not keep.
        if r['label'] in ('TIMEFRAME_ONLY', 'COSMETIC', 'IDENTICAL'):
            skipped += 1
            continue
        before = [(m, '') for m in r['before']]
        after = [(m, '') for m in r['after']]
        label, _ = classify(before, after)
        checked += 1
        if label != r['label']:
            failed += 1
            print('  MISMATCH %s: committed %s, recomputed %s'
                  % (r['nct'], r['label'], label))

    print('selftest: %d re-derived, %d matched, %d moved, %d skipped '
          '(timeframe-dependent, not decidable from stored measures)'
          % (checked, checked - failed, failed, skipped))
    if failed:
        print('RULES HAVE CHANGED. This is a pre-registered analysis '
              '(PREREGISTRATION.md 5.1) and needs a numbered amendment.')
        return 1
    print('rules unchanged')
    return 0


if __name__ == '__main__':
    sys.exit(_selftest() if '--selftest' in sys.argv else 0)
