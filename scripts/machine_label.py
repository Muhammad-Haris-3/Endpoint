"""Apply machine-produced labels, marked as such and never as a gold set.

GOLDSET_PROTOCOL.md 0 is explicit: Tier 2 is an LLM, so LLM labels cannot be the
reference standard -- precision against them measures agreement between two
models, not accuracy. This script exists because a machine pass is still USEFUL,
provided nothing downstream can mistake it for the thing it is not:

  * it is a REFERENCE pass over all 419 pairs, so Tier 1 can be scored against
    something rather than nothing while human labelling is incomplete;
  * it gives the human a spot-check target (GOLDSET_PROTOCOL.md 5a), so
    machine-vs-human agreement is measured on a subsample instead of assumed.

Every row it writes carries `labeller` containing "MACHINE" and `machine: true`.
gold_eval.py keys off those and refuses to call the result precision or recall.

--dump writes the pairs for reading. --apply ingests a two-column TSV of
`nct<TAB>LABEL`. It will not invent a label: every NCT must appear in the drawn
sample and every label must be one of the five in the codebook, or the whole
batch is rejected. A partially-applied batch would be worse than none, because
nobody would know which half.
"""
import argparse, csv, datetime, glob, gzip, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD = os.path.join(ROOT, 'data', 'gold')
SAMPLE = os.path.join(GOLD, 'sample.tsv')
LABELS = os.path.join(GOLD, 'labels.ndjson')
REGISTER = os.path.join(ROOT, 'data', 'register')

VALID = {'SAME', 'REFINED', 'DIFFERENT', 'SET_CHANGED', 'UNCLEAR'}
SUBSTANTIVE = {'DIFFERENT', 'SET_CHANGED'}
LABELLER = 'claude-opus-5 (MACHINE)'


def load_sample():
    return list(csv.DictReader(open(SAMPLE, encoding='utf-8'), delimiter='\t'))


def load_pairs(batch):
    out = {}
    for path in sorted(glob.glob(os.path.join(REGISTER, batch, '*.versions.ndjson.gz'))):
        with gzip.open(path, 'rt', encoding='utf-8') as fh:
            for line in fh:
                if line.strip():
                    r = json.loads(line)
                    out[r['p']] = r
    return out


def already():
    seen = set()
    if os.path.exists(LABELS):
        for line in open(LABELS, encoding='utf-8'):
            if line.strip():
                r = json.loads(line)
                if 'MACHINE' in str(r.get('labeller', '')):
                    seen.add(r['nct'])
    return seen


def one_line(s, n=210):
    s = ' '.join(str(s or '').split())
    return s if len(s) <= n else s[:n - 1] + '…'


def cmd_dump(args):
    sample = load_sample()
    pairs = load_pairs(args.versions_batch)
    done = already()
    rows = [r for r in sample if r['nct'] not in done] if args.skip_done else sample
    rows = rows[args.offset:args.offset + args.limit] if args.limit else rows[args.offset:]

    out = []
    for r in rows:
        p = pairs.get(r['nct'])
        if not p:
            continue
        out.append('### %s' % r['nct'])
        for side, key in (('B', 'before'), ('A', 'after')):
            outs = p.get(key) or []
            if not outs:
                out.append('  %s: (none)' % side)
            for o in outs:
                tf = one_line(o.get('t'), 90)
                out.append('  %s| %s' % (side, one_line(o.get('m'))))
                if tf:
                    out.append('   tf: %s' % tf)
        sb, sa = p.get('before_sec') or [], p.get('after_sec') or []
        if len(sb) != len(sa):
            out.append('  sec: %d -> %d' % (len(sb), len(sa)))
        out.append('')
    print('\n'.join(out))
    sys.stderr.write('dumped %d pairs (offset %d)\n' % (len(rows), args.offset))
    return 0


def cmd_apply(args):
    sample = {r['nct']: r for r in load_sample()}
    incoming = []
    with open(args.file, encoding='utf-8') as fh:
        for ln, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t') if '\t' in line else line.split(None, 1)
            if len(parts) != 2:
                print('line %d: expected `nct<TAB>LABEL`, got %r' % (ln, line))
                return 1
            nct, label = parts[0].strip(), parts[1].strip().upper()
            if nct not in sample:
                print('line %d: %s is not in the drawn sample' % (ln, nct))
                return 1
            if label not in VALID:
                print('line %d: %r is not one of %s' % (ln, label, sorted(VALID)))
                return 1
            incoming.append((nct, label))

    dupes = [n for n, _ in incoming if list(x for x, _ in incoming).count(n) > 1]
    if dupes:
        print('duplicate NCTs in batch: %s' % sorted(set(dupes))[:5])
        return 1

    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    with open(LABELS, 'a', encoding='utf-8', newline='\n') as fh:
        for nct, label in incoming:
            fh.write(json.dumps({
                'nct': nct,
                'version': int(sample[nct]['version']),
                'label': label,
                'substantive': label in SUBSTANTIVE,
                'unclear': label == 'UNCLEAR',
                'note': '',
                'labeller': LABELLER,
                'machine': True,
                'labelled_utc': now,
            }, separators=(',', ':'), sort_keys=True) + '\n')

    print('applied %d machine labels' % len(incoming))
    print('total machine-labelled: %d of %d' % (len(already()), len(sample)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--versions-batch', default='versions-2026-08-30')
    sub = ap.add_subparsers(dest='cmd', required=True)
    d = sub.add_parser('dump'); d.add_argument('--offset', type=int, default=0)
    d.add_argument('--limit', type=int, default=0)
    d.add_argument('--skip-done', action='store_true')
    a = sub.add_parser('apply'); a.add_argument('file')
    args = ap.parse_args()
    return cmd_dump(args) if args.cmd == 'dump' else cmd_apply(args)


if __name__ == '__main__':
    sys.exit(main())
