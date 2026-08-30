"""M4, part two. Apply the frozen rules to every stored version pair.

Pure and deterministic: reads what collect_versions.py stored, classifies with
verdict.classify, joins to the frozen frame for dates and sponsor class, and
writes verdicts plus a report. It touches no network, so it can be re-run for
free whenever the rules change by amendment.

PRIMARY FIGURE 1 (PREREGISTRATION.md 6):

    trials with a COUNT_CHANGED or SUBSTANTIVE verdict dated strictly after
    primary completion, over trials admitted under 3

A DISTINCTION THE FROZEN RULES DO NOT DRAW, REPORTED SEPARATELY BECAUSE OF IT.

PREREGISTRATION.md 5.1 defines COUNT_CHANGED as "the number of primary outcomes
differs". Some trials have NO registered primary outcome in the earlier version
and gain one in the later -- an empty-to-populated transition. That satisfies the
frozen rule and counts as COUNT_CHANGED, but it is not the same act as replacing
four declared outcomes with one. It is a registration being completed, and on an
old record it may say nothing about the sponsor's intent at all.

The rule is frozen and this program does not quietly reinterpret it: those
trials ARE counted in primary figure 1, exactly as 5.1 requires. But they are
also counted separately and printed on their own line, so a reader can see how
much of the figure rests on them, and so an amendment can be argued from a
measured number rather than from a suspicion. Changing the rule to exclude them
would be a post-hoc narrowing made after seeing which way it moved the headline,
which is the thing the pre-registration exists to prevent.

Also reported, for the same reason: populated-to-empty transitions, where a trial
that once declared a primary outcome later declares none.
"""
import argparse, calendar, datetime, glob, gzip, json, os, statistics, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verdict import classify, ORDER, DEFENSIBLE, REWORD_JACCARD   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUDIES = os.path.join(ROOT, 'frame', 'studies.tsv')
REGISTER = os.path.join(ROOT, 'data', 'register')


def parse_date(s):
    """PREREGISTRATION.md 4.1."""
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


def load_frame():
    frame = {}
    with open(STUDIES, encoding='utf-8') as fh:
        cols = fh.readline().rstrip('\n').split('\t')
        for line in fh:
            if line.strip():
                r = dict(zip(cols, line.rstrip('\n').split('\t')))
                frame[r['nct']] = r
    return frame


def load_change_dates(history_batch):
    """nct -> ISO date of the version at which the primary outcome last changed."""
    path = os.path.join(REGISTER, history_batch, 'records.ndjson.gz')
    out = {}
    with gzip.open(path, 'rt', encoding='utf-8') as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            v = (r.get('luv') or {}).get('primaryOutcomes')
            d = r.get('d') or []
            if isinstance(v, int) and 0 <= v < len(d):
                out[r['p']] = d[v]
    return out


def flagged_count(history_batch):
    """How many pairs collect_versions.py was supposed to produce."""
    path = os.path.join(REGISTER, history_batch, 'records.ndjson.gz')
    seen = set()
    with gzip.open(path, 'rt', encoding='utf-8') as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            v = (r.get('luv') or {}).get('primaryOutcomes')
            if isinstance(v, int) and v >= 1:
                seen.add(r['p'])
    return seen


def iter_versions(batch):
    pattern = os.path.join(REGISTER, batch, '*.versions.ndjson.gz')
    for path in sorted(glob.glob(pattern)):
        with gzip.open(path, 'rt', encoding='utf-8') as fh:
            for line in fh:
                if line.strip():
                    yield json.loads(line)


def pct(a, b):
    return '%.1f%%' % (100.0 * a / b) if b else 'n/a'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch', required=True, help='versions batch')
    ap.add_argument('--history-batch', default='history-2026-08-30')
    ap.add_argument('--out', default=None)
    args = ap.parse_args()

    frame = load_frame()
    change_dates = load_change_dates(args.history_batch)
    lines = []

    def log(m):
        print(m, flush=True)
        lines.append(m)

    log('FRAME ADJUDICATION  (M4)')
    log('versions batch: %s   history batch: %s' % (args.batch, args.history_batch))
    log('frame: %d trials    Jaccard threshold: %.2f (PREREG 5.1)'
        % (len(frame), REWORD_JACCARD))
    log('')

    verdicts = []
    counts = {k: 0 for k in ORDER}
    retro_counts = {k: 0 for k in ORDER}
    empty_before = empty_after = 0
    retro_empty_before = 0
    undatable = 0
    retro_days = []
    by_sponsor = {}

    for row in iter_versions(args.batch):
        nct = row['p']
        before = [(o['m'], o['t']) for o in row['before']]
        after = [(o['m'], o['t']) for o in row['after']]
        label, detail = classify(before, after)
        counts[label] += 1

        if not before and after:
            empty_before += 1
        if before and not after:
            empty_after += 1

        fr = frame.get(nct) or {}
        pc = parse_date(fr.get('primary_completion'))
        cd = parse_date(change_dates.get(nct))
        days = (cd - pc).days if (pc and cd) else None
        if days is None:
            undatable += 1
        retro = days is not None and days > 0        # PREREG 4.2: strictly after
        if retro:
            retro_counts[label] += 1
            if not before and after:
                retro_empty_before += 1
            if label in DEFENSIBLE:
                retro_days.append(days)
                sc = fr.get('sponsor_class') or '(none)'
                by_sponsor[sc] = by_sponsor.get(sc, 0) + 1

        verdicts.append({
            'p': nct, 'v': row['v'], 'label': label, 'detail': detail,
            'days_after_pc': days, 'retrospective': retro,
            'empty_before': (not before) and bool(after),
            'sponsor_class': fr.get('sponsor_class'),
            'status': fr.get('status'),
            'has_results': fr.get('has_results') == '1',
            'enrollment': fr.get('enrollment'),
        })

    n = len(verdicts)
    if not n:
        log('NO VERSION PAIRS FOUND. Run collect_versions.py first.')
        return 1

    frame_n = len(frame)

    # Reconciliation. Adjudicating whatever happened to arrive, and reporting a
    # rate over that, would silently rescale the denominator to whatever the
    # crawl managed to fetch.
    expected = flagged_count(args.history_batch)
    got = {v['p'] for v in verdicts}
    missing = sorted(expected - got)
    extra = sorted(got - expected)
    complete = not missing and not extra
    log('RECONCILIATION')
    log('   flagged by the history register           %8d' % len(expected))
    log('   adjudicated pairs                         %8d' % n)
    log('   MISSING pairs                             %8d' % len(missing))
    log('   adjudicated but not flagged               %8d' % len(extra))
    if missing:
        mp = os.path.join(REGISTER, args.batch, 'missing_pairs.txt')
        with open(mp, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write('\n'.join(missing) + '\n')
        log('   named in missing_pairs.txt, EXCLUDED from every figure below')
        log('   and never imputed (PREREGISTRATION.md 3).')
    if extra:
        log('   ERROR: pairs adjudicated that the history register did not flag.')
        log('   The version crawl read a different flagged list. Refusing.')
        return 1
    log('')

    def table(title, cmap, total):
        log('%s   (n=%d)' % (title, total))
        log('   %-16s %8s  %8s' % ('verdict', 'count', 'share'))
        log('   ' + '-' * 38)
        for k in ORDER:
            log('   %-16s %8d  %8s' % (k, cmap[k], pct(cmap[k], total)))
        d = sum(cmap[k] for k in DEFENSIBLE)
        log('   ' + '-' * 38)
        log('   %-16s %8d  %8s' % ('defensible', d, pct(d, total)))
        log('')
        return d

    all_def = table('ALL ADJUDICATED PAIRS', counts, n)
    retro_n = sum(retro_counts.values())
    retro_def = table('RETROSPECTIVE ONLY (change dated after primary completion)',
                      retro_counts, retro_n)

    log('PRIMARY FIGURE 1  (PREREGISTRATION.md 6)')
    log('   frame                                    %8d' % frame_n)
    log('   flagged and adjudicated                  %8d  %s of frame' % (n, pct(n, frame_n)))
    log('   retrospective (any verdict)              %8d  %s of frame' % (retro_n, pct(retro_n, frame_n)))
    log('   >>> DEFENSIBLE RETROSPECTIVE CHANGE      %8d  %s of frame <<<'
        % (retro_def, pct(retro_def, frame_n)))
    log('   share of retrospective flags surviving   %8s' % pct(retro_def, retro_n))
    if retro_days:
        log('   median days after completion             %8s' % statistics.median(retro_days))
        log('   max days after completion                %8d' % max(retro_days))
    if undatable:
        log('   undatable pairs (excluded, not imputed)  %8d' % undatable)
    log('')

    log('THE EMPTY-BEFORE CAVEAT  (see module docstring)')
    log('   pairs where the earlier version had NO primary outcome  %8d  %s of pairs'
        % (empty_before, pct(empty_before, n)))
    log('   ...of those, retrospective                              %8d' % retro_empty_before)
    log('   ...as a share of the defensible retrospective figure    %8s'
        % pct(retro_empty_before, retro_def))
    log('   pairs where the later version has NO primary outcome    %8d' % empty_after)
    log('')
    log('   These satisfy the frozen COUNT_CHANGED rule and ARE counted above.')
    log('   They are broken out because "a registration was completed" is not the')
    log('   same act as "four declared outcomes became one", and a reader should be')
    log('   able to see how much of the figure rests on them. Excluding them now,')
    log('   after seeing which way it moves the headline, is exactly what')
    log('   PREREGISTRATION.md 11 requires an amendment for.')
    log('')

    if by_sponsor:
        log('DEFENSIBLE RETROSPECTIVE CHANGES by lead sponsor class')
        for k, v in sorted(by_sponsor.items(), key=lambda kv: -kv[1]):
            log('   %-14s %8d  %s' % (k, v, pct(v, retro_def)))
        log('')

    out = args.out or os.path.join(REGISTER, args.batch, 'verdicts')
    with gzip.GzipFile(out + '.ndjson.gz', 'wb', compresslevel=9, mtime=0) as fh:
        for v in sorted(verdicts, key=lambda r: r['p']):
            fh.write((json.dumps(v, separators=(',', ':'), sort_keys=True) + '\n').encode())
    with open(out + '.txt', 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('wrote %s.ndjson.gz and %s.txt' % (out, out))
    print('')
    print('BATCH COMPLETE: %s' % complete)
    return 0 if complete else 2


if __name__ == '__main__':
    sys.exit(main())
