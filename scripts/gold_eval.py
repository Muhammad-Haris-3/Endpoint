"""M5, step three. Score Tier 1 against the labels, and never overstate what they are.

Joins data/gold/labels.ndjson to the drawn sample and the Tier 1 verdicts, and
reports agreement both raw and REWEIGHTED to the frame.

TWO KINDS OF LABEL, KEPT APART EVERYWHERE.

  HUMAN labels are the reference standard PREREGISTRATION.md 5.3 requires.
  MACHINE labels (labeller contains "MACHINE", or `machine: true`) are a
  reference pass, produced by an LLM.

Tier 2 is itself an LLM, so scoring it against machine labels would measure
agreement between two language models rather than accuracy -- and two systems
sharing a training distribution agree most confidently exactly where both are
wrong (GOLDSET_PROTOCOL.md 0). This program therefore refuses to print the words
precision or recall for any figure derived from machine labels. It prints
AGREEMENT, and says so on every line.

REWEIGHTING IS NOT OPTIONAL. The sample is stratified: rare verdict classes and
posting-coincident changes are deliberately over-sampled, so a raw mean over
these rows describes the sample and nothing else. Frame-level figures are
weighted by the inverse sampling fraction in the `weight` column; raw numbers are
printed beside them only so the difference stays visible.

THE NUMBER THIS EXISTS FOR. FINDINGS.md F6 showed 70.9% of flagged changes in
reporting trials land within 31 days of results posting, and that a date cannot
separate the results form's mandatory restatement from a genuine switch. Labels
can:

    among POSTING-COINCIDENT changes, what share are substantive?

That decides whether the 19.9% headline is mostly bookkeeping or mostly real.
"""
import argparse, csv, gzip, json, os, statistics, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD = os.path.join(ROOT, 'data', 'gold')
SAMPLE = os.path.join(GOLD, 'sample.tsv')
LABELS = os.path.join(GOLD, 'labels.ndjson')

TIER1_SUBSTANTIVE = ('COUNT_CHANGED', 'SUBSTANTIVE')
OVERLAP_N = 60


def pct(x):
    return '-' if x is None else '%.1f%%' % (100 * x)


def div(a, b):
    return (a / float(b)) if b else None


def is_machine(row):
    return bool(row.get('machine')) or 'MACHINE' in str(row.get('labeller', '')).upper()


def load():
    """(machine, human) -> each nct -> latest row for that kind."""
    machine, human = {}, {}
    if not os.path.exists(LABELS):
        return machine, human
    with open(LABELS, encoding='utf-8') as fh:
        for line in fh:
            if line.strip():
                r = json.loads(line)
                (machine if is_machine(r) else human)[r['nct']] = r
    return machine, human


def kappa(pairs):
    n = len(pairs)
    if not n:
        return None
    po = sum(1 for a, b in pairs if a == b) / float(n)
    pa = sum(1 for a, _ in pairs if a) / float(n)
    pb = sum(1 for _, b in pairs if b) / float(n)
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else (po - pe) / (1 - pe)


def confusion(labels, sample, title, kind):
    tp = fp = fn = tn = 0.0
    wtp = wfp = wfn = wtn = 0.0
    for nct, lab in labels.items():
        s = sample.get(nct)
        if not s or lab.get('unclear'):
            continue
        w = float(s['weight'])
        t1 = s['verdict'] in TIER1_SUBSTANTIVE
        truth = bool(lab['substantive'])
        if t1 and truth:
            tp += 1; wtp += w
        elif t1 and not truth:
            fp += 1; wfp += w
        elif not t1 and truth:
            fn += 1; wfn += w
        else:
            tn += 1; wtn += w

    word = 'precision / recall' if kind == 'human' else 'agreement (NOT precision/recall)'
    print(title)
    print('  metric type: %s' % word)
    for tag, a, b, c, d in (('raw sample counts', tp, fp, fn, tn),
                            ('REWEIGHTED to frame', wtp, wfp, wfn, wtn)):
        p, r = div(a, a + b), div(a, a + c)
        f1 = div(2 * p * r, p + r) if (p and r) else None
        print('  %-20s  Tier1+/label+ %7.1f   Tier1+/label- %7.1f' % (tag, a, b))
        print('  %-20s  Tier1-/label+ %7.1f   Tier1-/label- %7.1f' % ('', c, d))
        print('  %-20s  %s %s   %s %s   F1 %s'
              % ('', 'precision' if kind == 'human' else 'pos.agree', pct(p),
                 'recall' if kind == 'human' else 'sensitivity', pct(r), pct(f1)))
    print('')


def main():
    ap = argparse.ArgumentParser()
    ap.parse_args()

    if not os.path.exists(SAMPLE):
        print('no sample -- run scripts/gold_sample.py')
        return 1
    rows = list(csv.DictReader(open(SAMPLE, encoding='utf-8'), delimiter='\t'))
    sample = {r['nct']: r for r in rows}
    order = [r['nct'] for r in rows]
    machine, human = load()

    print('GOLD-SET EVALUATION')
    print('  sample            %5d pairs' % len(sample))
    print('  HUMAN labels      %5d' % len(human))
    print('  MACHINE labels    %5d' % len(machine))
    print('')

    if not machine and not human:
        print('NOTHING LABELLED. python scripts/label_tool.py --labeller "<name>"')
        return 2

    if len(human) < 300:
        print('*** PREREGISTRATION.md 5.3 IS NOT SATISFIED ***')
        print('  It requires >=300 HAND-labelled pairs. There are %d.' % len(human))
        print('  Tier 2 may not enter any reported figure on this basis, and every')
        print('  machine-derived number below is AGREEMENT, not accuracy.')
        print('')

    # ---- the spot check -------------------------------------------------
    both = [n for n in order if n in machine and n in human
            and not machine[n].get('unclear') and not human[n].get('unclear')]
    print('SPOT CHECK: human vs machine, where both labelled')
    print('  compared          %5d' % len(both))
    if both:
        agree = sum(1 for n in both
                    if bool(machine[n]['substantive']) == bool(human[n]['substantive']))
        k = kappa([(bool(machine[n]['substantive']), bool(human[n]['substantive']))
                   for n in both])
        exact = sum(1 for n in both if machine[n]['label'] == human[n]['label'])
        print('  binary agreement  %5d / %d = %s' % (agree, len(both), pct(div(agree, len(both)))))
        print('  exact label match %5d / %d = %s' % (exact, len(both), pct(div(exact, len(both)))))
        print("  Cohen's kappa     %s" % ('-' if k is None else '%.3f' % k))
        print('')
        for n in both:
            if machine[n]['label'] != human[n]['label']:
                print('  DISAGREE %s  human=%-12s machine=%s'
                      % (n, human[n]['label'], machine[n]['label']))
        print('')
        print('  %d compared is far too few to characterise the machine pass.' % len(both))
        print('  GOLDSET_PROTOCOL.md 5 asks for the first 60 in sample order.')
    else:
        print('  none -- no pair carries both a human and a machine label')
    print('')

    ref = machine if len(machine) >= len(human) else human
    kind = 'machine' if ref is machine else 'human'
    lab_counts = {}
    for r in ref.values():
        lab_counts[r['label']] = lab_counts.get(r['label'], 0) + 1
    unclear = sum(1 for r in ref.values() if r.get('unclear'))

    print('LABEL DISTRIBUTION (%s pass, n=%d)' % (kind.upper(), len(ref)))
    for k2 in ('SAME', 'REFINED', 'DIFFERENT', 'SET_CHANGED', 'UNCLEAR'):
        print('  %-12s %5d  %s' % (k2, lab_counts.get(k2, 0), pct(div(lab_counts.get(k2, 0), len(ref)))))
    print('  substantive  %5d  %s'
          % (sum(1 for r in ref.values() if r['substantive']),
             pct(div(sum(1 for r in ref.values() if r['substantive']), len(ref)))))
    print('  UNCLEAR excluded from every figure below: %d' % unclear)
    print('')

    confusion(ref, sample, 'TIER 1 vs %s LABELS' % kind.upper(), kind)

    # ---- the F6 question ------------------------------------------------
    print('THE F6 QUESTION: are posting-coincident changes substantive?')
    print('  (%s labels -- %s)'
          % (kind, 'ground truth' if kind == 'human' else 'AGREEMENT ONLY, not ground truth'))
    for flag, name in (('1', 'within 31d of results posting'),
                       ('0', 'not posting-coincident')):
        sel = [(n, l) for n, l in ref.items()
               if sample.get(n, {}).get('posting_coincident') == flag and not l.get('unclear')]
        if not sel:
            continue
        sub = sum(1 for _, l in sel if l['substantive'])
        wsub = sum(float(sample[n]['weight']) for n, l in sel if l['substantive'])
        wall = sum(float(sample[n]['weight']) for n, _ in sel)
        print('  %-32s n=%4d  raw %s   weighted %s'
              % (name, len(sel), pct(div(sub, len(sel))), pct(div(wsub, wall))))
    print('')
    print('  The weighted share in the first row is what decides whether the 19.9%')
    print('  headline is mostly bookkeeping or mostly real.')
    if kind == 'machine':
        print('')
        print('  IT IS NOT SETTLED BY THIS RUN. These are machine labels; a human')
        print('  pass over the sample is what PREREGISTRATION.md 5.3 requires, and')
        print('  the spot check above is far too small to say how far the machine')
        print('  pass can be trusted.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
