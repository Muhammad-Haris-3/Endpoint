"""M5, step one. Draw the gold-set sample, and freeze it before anyone labels it.

PREREGISTRATION.md 5.3 requires a hand-labelled sample of >=300 version pairs,
labelled BEFORE Tier 2 is run over the frame. This draws that sample under a
fixed rule and hashes it, so the set cannot be quietly reshaped later to one that
flatters whatever Tier 2 turns out to do.

THE SAMPLE IS NOT UNIFORM, DELIBERATELY. A uniform draw from 54,203 pairs would
spend most of its labelling budget on the easy cases and leave the ambiguous ones
with a handful of examples each. The strata are the two axes that actually decide
whether this project's headline means anything:

  * Tier 1 verdict. The interesting error is not "did Tier 1 fire" but "was it
    right when it fired and right when it stayed silent", so every verdict
    category needs enough examples to estimate both directions.

  * Whether the change is POSTING-COINCIDENT -- within 31 days of the results
    first-posted date. FINDINGS.md F6 established that 70.9% of flagged changes
    in reporting trials land in that window, and that the mechanical restatement
    required by the results form is indistinguishable by date from a genuine
    switch. If the gold set does not deliberately over-sample that window, it
    cannot measure the one thing the project most needs measured.

Because the strata are unequal, ESTIMATES OVER THE FRAME MUST BE REWEIGHTED by
the inverse of each stratum's sampling fraction. The weights are written into the
sample file so that a later analysis cannot forget them.

Output:
  data/gold/sample.tsv       the drawn pairs, sorted, with stratum and weight
  data/gold/SAMPLE_MANIFEST  SHA-256, seed, stratum sizes, draw date
"""
import argparse, calendar, csv, datetime, gzip, hashlib, json, os, random, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUDIES = os.path.join(ROOT, 'frame', 'studies.tsv')
REGISTER = os.path.join(ROOT, 'data', 'register')
GOLD = os.path.join(ROOT, 'data', 'gold')

VERDICTS = ['COUNT_CHANGED', 'SUBSTANTIVE', 'REWORDED',
            'TIMEFRAME_ONLY', 'COSMETIC', 'IDENTICAL']
POSTING_WINDOW_DAYS = 31

SEED = 20260831          # fixed and recorded; the draw is reproducible
MIN_PER_CELL = 25
TARGET = 420             # >= the 300 the pre-registration requires

COLUMNS = ['nct', 'version', 'verdict', 'retrospective', 'days_after_pc',
           'posting_coincident', 'stratum', 'weight']


def parse_date(s):
    if not s:
        return None
    p = s.split('-')
    try:
        if len(p) == 3:
            return datetime.date(int(p[0]), int(p[1]), int(p[2]))
        if len(p) == 2:
            y, m = int(p[0]), int(p[1])
            return datetime.date(y, m, calendar.monthrange(y, m)[1])
        if len(p) == 1:
            return datetime.date(int(p[0]), 12, 31)
    except ValueError:
        return None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--versions-batch', default='versions-2026-08-30')
    ap.add_argument('--history-batch', default='history-2026-08-30')
    args = ap.parse_args()

    manifest = os.path.join(GOLD, 'SAMPLE_MANIFEST')
    if os.path.exists(manifest):
        print('REFUSING TO DRAW: %s already exists.' % os.path.relpath(manifest, ROOT))
        print('The gold sample is drawn once. Redrawing after seeing how Tier 1 or')
        print('Tier 2 performs on it would make the set a function of the result.')
        return 1

    frame = {}
    with open(STUDIES, encoding='utf-8') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            frame[r['nct']] = r

    change_date = {}
    hp = os.path.join(REGISTER, args.history_batch, 'records.ndjson.gz')
    with gzip.open(hp, 'rt', encoding='utf-8') as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            v = (r.get('luv') or {}).get('primaryOutcomes')
            d = r.get('d') or []
            if isinstance(v, int) and 0 <= v < len(d):
                change_date[r['p']] = d[v]

    pool = []
    vp = os.path.join(REGISTER, args.versions_batch, 'verdicts.ndjson.gz')
    with gzip.open(vp, 'rt', encoding='utf-8') as fh:
        for line in fh:
            if not line.strip():
                continue
            v = json.loads(line)
            fr = frame.get(v['p']) or {}
            cd = parse_date(change_date.get(v['p']))
            rp = parse_date(fr.get('results_first_post'))
            coincident = bool(cd and rp and abs((rp - cd).days) <= POSTING_WINDOW_DAYS)
            pool.append({
                'nct': v['p'],
                'version': v['v'],
                'verdict': v['label'],
                'retrospective': '1' if v.get('retrospective') else '0',
                'days_after_pc': '' if v.get('days_after_pc') is None else str(v['days_after_pc']),
                'posting_coincident': '1' if coincident else '0',
            })

    # -- strata -------------------------------------------------------------
    cells = {}
    for r in pool:
        cells.setdefault((r['verdict'], r['posting_coincident']), []).append(r)

    print('POOL: %d adjudicated pairs' % len(pool))
    print('')
    print('%-16s %-10s %9s' % ('verdict', 'posting', 'pool'))
    print('-' * 38)
    for k in sorted(cells, key=lambda k: (VERDICTS.index(k[0]) if k[0] in VERDICTS else 9, k[1])):
        print('%-16s %-10s %9d' % (k[0], 'within 31d' if k[1] == '1' else 'not', len(cells[k])))
    print('')

    # Proportional above a floor, so no cell is too small to estimate from and
    # no cell swallows the budget.
    nonempty = {k: v for k, v in cells.items() if v}
    floor_total = MIN_PER_CELL * len(nonempty)
    spare = max(TARGET - floor_total, 0)
    total_pool = sum(len(v) for v in nonempty.values())

    rng = random.Random(SEED)
    drawn = []
    for k in sorted(nonempty):
        cell = nonempty[k]
        want = MIN_PER_CELL + int(round(spare * len(cell) / float(total_pool)))
        want = min(want, len(cell))
        picked = rng.sample(cell, want)
        frac = want / float(len(cell))
        for r in picked:
            r = dict(r)
            r['stratum'] = '%s|%s' % k
            r['weight'] = '%.6f' % (1.0 / frac)     # inverse sampling fraction
            drawn.append(r)

    drawn.sort(key=lambda r: r['nct'])
    os.makedirs(GOLD, exist_ok=True)
    path = os.path.join(GOLD, 'sample.tsv')
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\t'.join(COLUMNS) + '\n')
        for r in drawn:
            fh.write('\t'.join(str(r[c]) for c in COLUMNS) + '\n')

    h = hashlib.sha256(open(path, 'rb').read()).hexdigest()
    counts = {}
    for r in drawn:
        counts[r['stratum']] = counts.get(r['stratum'], 0) + 1

    lines = [
        '# Endpoint gold-set sample manifest',
        '#',
        '# Drawn once, before any labelling, under a fixed seed. PREREGISTRATION.md',
        '# 5.3 requires >=300 hand-labelled pairs labelled BEFORE Tier 2 runs.',
        '#',
        '# The sample is STRATIFIED and therefore UNEQUALLY WEIGHTED. Any estimate',
        '# over the frame must reweight by the `weight` column (inverse sampling',
        '# fraction). A raw mean over these rows is not a frame estimate.',
        '',
        'drawn_utc         %s' % datetime.datetime.now(datetime.timezone.utc)
                                          .strftime('%Y-%m-%dT%H:%M:%SZ'),
        'seed              %d' % SEED,
        'pool              %d' % len(pool),
        'sample_size       %d' % len(drawn),
        'posting_window_d  %d' % POSTING_WINDOW_DAYS,
        'sample_sha256     %s' % h,
        '',
        '# stratum (verdict|posting_coincident)   drawn',
    ]
    for k in sorted(counts):
        lines.append('%-42s %5d' % (k, counts[k]))
    lines.append('')
    with open(manifest, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(lines))

    print('DRAWN %d pairs' % len(drawn))
    for k in sorted(counts):
        print('  %-40s %5d' % (k, counts[k]))
    print('')
    print('sample sha256 %s' % h)
    print('wrote data/gold/sample.tsv and data/gold/SAMPLE_MANIFEST')
    print('')
    print('NOT LABELLED. See GOLDSET_PROTOCOL.md before labelling anything.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
