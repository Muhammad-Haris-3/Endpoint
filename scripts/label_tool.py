"""M5, step two. The labelling instrument. Blind by construction.

Presents one drawn pair at a time -- the primary outcome set at v-1 and at v,
plus the secondary outcomes -- and records a human's judgement under the codebook
in GOLDSET_PROTOCOL.md.

WHAT IT DELIBERATELY DOES NOT SHOW: the Tier 1 verdict, whether the change is
posting-coincident, the sponsor, the phase, whether the trial reported results,
or the days between completion and the change. Every one of those would anchor
the labeller toward the answer the project already has, and the whole point of
the exercise is an independent judgement. GOLDSET_PROTOCOL.md 4.

The secondary outcomes ARE shown, because a secondary promoted to primary is the
classic form of outcome switching and Tier 1 cannot see it (codebook rule 6).

APPEND-ONLY. A changed mind is a second row, never an overwrite. The last row for
a pair wins at evaluation time, and the history of the labelling stays as
inspectable as the history of the trials it is about. Resumable: pairs already
labelled are skipped unless --relabel is given.

This tool does not label anything itself and has no mode in which it can. See
GOLDSET_PROTOCOL.md 0 for why the labeller must not be an LLM.
"""
import argparse, csv, datetime, glob, gzip, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD = os.path.join(ROOT, 'data', 'gold')
SAMPLE = os.path.join(GOLD, 'sample.tsv')
LABELS = os.path.join(GOLD, 'labels.ndjson')
REGISTER = os.path.join(ROOT, 'data', 'register')

CHOICES = {
    '1': ('SAME', 'same quantity, restated (case, punctuation, house style)'),
    '2': ('REFINED', 'same quantity, made more precise; could NOT flip the result'),
    '3': ('DIFFERENT', 'a different quantity is now primary; COULD flip the result'),
    '4': ('SET_CHANGED', 'the set gained or lost a member in substance'),
    '5': ('UNCLEAR', 'the text does not permit a judgement'),
}
SUBSTANTIVE = ('DIFFERENT', 'SET_CHANGED')


def load_sample():
    with open(SAMPLE, encoding='utf-8') as fh:
        return list(csv.DictReader(fh, delimiter='\t'))


def load_pairs(batch):
    out = {}
    for path in sorted(glob.glob(os.path.join(REGISTER, batch, '*.versions.ndjson.gz'))):
        with gzip.open(path, 'rt', encoding='utf-8') as fh:
            for line in fh:
                if line.strip():
                    r = json.loads(line)
                    out[r['p']] = r
    return out


def load_labels():
    """nct -> most recent label row. Append-only file; last row wins."""
    out = {}
    if os.path.exists(LABELS):
        with open(LABELS, encoding='utf-8') as fh:
            for line in fh:
                if line.strip():
                    r = json.loads(line)
                    out[r['nct']] = r
    return out


def wrap(text, width=76, indent='    '):
    words, line, lines = str(text or '').split(), '', []
    for w in words:
        if len(line) + len(w) + 1 > width:
            lines.append(indent + line)
            line = w
        else:
            line = (line + ' ' + w).strip()
    if line:
        lines.append(indent + line)
    return '\n'.join(lines) or (indent + '(empty)')


def show(pair, i, total):
    print('\n' + '=' * 80)
    print('  pair %d of %d' % (i, total))
    print('=' * 80)
    for side, key, label in (('BEFORE', 'before', 'the earlier version'),
                             ('AT THE CHANGE', 'after', 'the version that changed it')):
        print('\n  %s  (%s)' % (side, label))
        print('  ' + '-' * 76)
        outs = pair.get(key) or []
        if not outs:
            print('    (no primary outcome registered at this version)')
        for k, o in enumerate(outs, 1):
            print('    [%d] measure:' % k)
            print(wrap(o.get('m'), indent='        '))
            if o.get('t'):
                print('        time frame:')
                print(wrap(o.get('t'), indent='          '))
    sec_b, sec_a = pair.get('before_sec') or [], pair.get('after_sec') or []
    if sec_b or sec_a:
        print('\n  SECONDARY OUTCOMES  (shown for codebook rule 6: promotion to primary)')
        print('  ' + '-' * 76)
        print('    before: %d' % len(sec_b))
        for m in sec_b[:6]:
            print(wrap('- ' + str(m), indent='      '))
        if len(sec_b) > 6:
            print('      ... %d more' % (len(sec_b) - 6))
        print('    after:  %d' % len(sec_a))
        for m in sec_a[:6]:
            print(wrap('- ' + str(m), indent='      '))
        if len(sec_a) > 6:
            print('      ... %d more' % (len(sec_a) - 6))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--versions-batch', default='versions-2026-08-30')
    ap.add_argument('--labeller', required=True,
                    help='who is labelling. Recorded on every row; required so a '
                         'later reader knows whose judgement this was.')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--relabel', action='store_true',
                    help='revisit pairs already labelled (appends a new row)')
    args = ap.parse_args()

    if not os.path.exists(SAMPLE):
        print('no sample at %s -- run scripts/gold_sample.py first' % SAMPLE)
        return 1

    sample = load_sample()
    pairs = load_pairs(args.versions_batch)
    done = load_labels()
    todo = [r for r in sample if args.relabel or r['nct'] not in done]
    if args.limit:
        todo = todo[:args.limit]

    print('GOLD-SET LABELLING   labeller: %s' % args.labeller)
    print('sample %d, already labelled %d, to do %d' % (len(sample), len(done), len(todo)))
    print('')
    print('Read GOLDSET_PROTOCOL.md 2 and 3 before starting. The question is NOT')
    print('"did the text change" -- it is:')
    print('')
    print('    Would a reader who trusted the earlier version be misled about')
    print('    what this trial pre-specified as its primary outcome?')
    print('')
    print('You are shown the two outcome sets and nothing else. The Tier 1 verdict,')
    print('the dates, the sponsor and the reporting status are deliberately hidden.')
    print('')
    for k, (name, desc) in sorted(CHOICES.items()):
        print('   %s  %-12s %s' % (k, name, desc))
    print('   s  skip        leave unlabelled')
    print('   q  quit        stop here; everything so far is saved')
    print('')

    if not todo:
        print('nothing to label')
        return 0

    # Opened lazily on the first actual label. Opening it up front creates an
    # empty file even when the labeller quits immediately, which would make
    # "labels.ndjson exists" stop meaning "labelling has started".
    out = [None]

    def sink():
        if out[0] is None:
            out[0] = open(LABELS, 'a', encoding='utf-8', newline='\n')
        return out[0]

    n = 0
    try:
        for i, row in enumerate(todo, 1):
            pair = pairs.get(row['nct'])
            if not pair:
                print('  %s: no stored version pair, skipping' % row['nct'])
                continue
            show(pair, i, len(todo))
            while True:
                try:
                    ans = input('\n  label [1-5, s, q]: ').strip().lower()
                except (EOFError, KeyboardInterrupt):
                    ans = 'q'
                if ans == 'q':
                    print('\nstopped. %d labelled this session.' % n)
                    return 0
                if ans == 's':
                    break
                if ans in CHOICES:
                    label = CHOICES[ans][0]
                    note = input('  note (optional): ').strip()
                    sink().write(json.dumps({
                        'nct': row['nct'],
                        'version': int(row['version']),
                        'label': label,
                        'substantive': label in SUBSTANTIVE,
                        'unclear': label == 'UNCLEAR',
                        'note': note,
                        'labeller': args.labeller,
                        'labelled_utc': datetime.datetime.now(datetime.timezone.utc)
                                                .strftime('%Y-%m-%dT%H:%M:%SZ'),
                    }, separators=(',', ':'), sort_keys=True) + '\n')
                    sink().flush()
                    n += 1
                    break
                print('  ? choose 1-5, s to skip, q to quit')
    finally:
        if out[0] is not None:
            out[0].close()

    print('\ndone. %d labelled this session, %d total.' % (n, len(load_labels())))
    return 0


if __name__ == '__main__':
    sys.exit(main())
