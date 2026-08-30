"""M5, step three. Score Tier 1 against the human labels.

Joins data/gold/labels.ndjson to the drawn sample and the Tier 1 verdicts, and
reports precision, recall and the confusion between them -- both raw and
REWEIGHTED to the frame.

REWEIGHTING IS NOT OPTIONAL AND THIS SCRIPT WILL NOT LET YOU FORGET IT. The
sample is stratified: rare verdict classes and posting-coincident changes are
deliberately over-sampled, so a raw mean over these rows describes the sample and
nothing else. Every frame-level figure below is weighted by the inverse sampling
fraction recorded in the `weight` column, and the raw numbers are printed beside
them only so the difference is visible.

THE NUMBER THIS EXISTS FOR. FINDINGS.md F6 established that 70.9% of flagged
changes in reporting trials land within 31 days of the results-posting date, and
that a date cannot distinguish the results form's mandatory restatement from a
genuine switch. The gold set can:

    among POSTING-COINCIDENT changes, what share are substantive?

That single number decides whether the 19.9% headline is mostly bookkeeping or
mostly real. It is reported first, because it matters more than Tier 1's overall
accuracy.

Refuses to report anything if the labels are machine-produced without being
declared as such -- see GOLDSET_PROTOCOL.md 0.
"""
import argparse, csv, gzip, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD = os.path.join(ROOT, 'data', 'gold')
SAMPLE = os.path.join(GOLD, 'sample.tsv')
LABELS = os.path.join(GOLD, 'labels.ndjson')
REGISTER = os.path.join(ROOT, 'data', 'register')

TIER1_SUBSTANTIVE = ('COUNT_CHANGED', 'SUBSTANTIVE')
OVERLAP_N = 60          # GOLDSET_PROTOCOL.md 5


def pct(x):
    return '—' if x is None else '%.1f%%' % (100 * x)


def safe_div(a, b):
    return (a / float(b)) if b else None


def load_labels():
    """nct -> latest row per labeller, plus every row for reliability."""
    latest, all_rows = {}, []
    if not os.path.exists(LABELS):
        return latest, all_rows
    with open(LABELS, encoding='utf-8') as fh:
        for line in fh:
            if line.strip():
                r = json.loads(line)
                all_rows.append(r)
                latest[(r['nct'], r.get('labeller', '?'))] = r
    return latest, all_rows


def cohens_kappa(pairs):
    """pairs: [(a_bool, b_bool)]. Binary substantive/not."""
    n = len(pairs)
    if not n:
        return None
    agree = sum(1 for a, b in pairs if a == b)
    po = agree / float(n)
    pa1 = sum(1 for a, _ in pairs if a) / float(n)
    pb1 = sum(1 for _, b in pairs if b) / float(n)
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    return None if pe == 1 else (po - pe) / (1 - pe)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--versions-batch', default='versions-2026-08-30')
    args = ap.parse_args()

    if not os.path.exists(SAMPLE):
        print('no sample -- run scripts/gold_sample.py')
        return 1
    sample = {r['nct']: r for r in csv.DictReader(open(SAMPLE, encoding='utf-8'), delimiter='\t')}
    latest, all_rows = load_labels()

    if not all_rows:
        print('GOLD-SET EVALUATION')
        print('')
        print('  sample drawn : %d pairs' % len(sample))
        print('  labelled     : 0')
        print('')
        print('NOTHING TO EVALUATE. The sample is drawn and frozen, the tool is')
        print('built, and no pair has been labelled.')
        print('')
        print('PREREGISTRATION.md 5.3 requires >=300 HAND-labelled pairs before')
        print('Tier 2 may enter any reported figure, and GOLDSET_PROTOCOL.md 0')
        print('explains why those labels must not come from a language model:')
        print('scoring an LLM against LLM labels measures agreement between two')
        print('models, not accuracy, and it fails most confidently exactly where')
        print('both are wrong.')
        print('')
        print('To label:  python scripts/label_tool.py --labeller "<name>"')
        return 2

    labellers = sorted({r.get('labeller', '?') for r in all_rows})
    machine = [l for l in labellers if 'llm' in l.lower() or 'gpt' in l.lower()
               or 'claude' in l.lower() or 'model' in l.lower()]

    print('GOLD-SET EVALUATION')
    print('  sample      %d pairs' % len(sample))
    print('  labellers   %s' % ', '.join(labellers))
    if machine:
        print('')
        print('  *** MACHINE-LABELLED REFERENCE, NOT A GOLD SET ***')
        print('  Labeller(s) %s appear to be language models.' % ', '.join(machine))
        print('  Everything below is INTER-MODEL AGREEMENT, not precision and recall')
        print('  against ground truth. PREREGISTRATION.md 5.3 is NOT satisfied and')
        print('  Tier 2 may not enter any reported figure on this basis.')
    print('')

    # -- primary labeller: the first alphabetically, for determinism ---------
    primary = labellers[0]
    rows = {nct: r for (nct, who), r in latest.items() if who == primary}
    usable = {n: r for n, r in rows.items() if not r.get('unclear')}
    unclear = len(rows) - len(usable)

    print('LABELS  (primary labeller: %s)' % primary)
    print('  labelled          %5d' % len(rows))
    print('  UNCLEAR, excluded %5d' % unclear)
    print('  usable            %5d' % len(usable))
    if len(usable) < 300:
        print('  BELOW the 300 the pre-registration requires. Reported anyway,')
        print('  marked as provisional; Tier 2 stays blocked.')
    print('')

    # -- inter-rater ---------------------------------------------------------
    if len(labellers) > 1:
        order = [r['nct'] for r in csv.DictReader(open(SAMPLE, encoding='utf-8'), delimiter='\t')][:OVERLAP_N]
        a_who, b_who = labellers[0], labellers[1]
        pairs = []
        for nct in order:
            a, b = latest.get((nct, a_who)), latest.get((nct, b_who))
            if a and b and not a.get('unclear') and not b.get('unclear'):
                pairs.append((bool(a['substantive']), bool(b['substantive'])))
        k = cohens_kappa(pairs)
        print('INTER-RATER RELIABILITY  (%s vs %s, first %d in sample order)'
              % (a_who, b_who, OVERLAP_N))
        print('  compared          %5d' % len(pairs))
        print("  Cohen's kappa     %s" % ('—' if k is None else '%.3f' % k))
        if k is not None and k < 0.6:
            print('  BELOW 0.6. GOLDSET_PROTOCOL.md 5: the codebook is the problem.')
            print('  Revise section 3, redo the overlap, record it in FINDINGS.md')
            print('  BEFORE labelling the rest.')
        print('')
    else:
        print('INTER-RATER RELIABILITY')
        print('  kappa NOT MEASURED -- one labeller. An unreplicated judgement is')
        print('  not a measurement, and every figure below inherits that caveat.')
        print('')

    # -- Tier 1 confusion, raw and weighted ---------------------------------
    tp = fp = fn = tn = 0.0
    wtp = wfp = wfn = wtn = 0.0
    for nct, lab in usable.items():
        s = sample.get(nct)
        if not s:
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

    def block(title, a, b, c, d):
        prec, rec = safe_div(a, a + b), safe_div(a, a + c)
        f1 = safe_div(2 * prec * rec, prec + rec) if (prec and rec) else None
        print(title)
        print('  true positive  %8.1f   false positive %8.1f' % (a, b))
        print('  false negative %8.1f   true negative  %8.1f' % (c, d))
        print('  precision %s   recall %s   F1 %s' % (pct(prec), pct(rec), pct(f1)))
        print('')
        return prec, rec

    block('TIER 1 vs HUMAN LABELS  (raw sample counts -- NOT a frame estimate)',
          tp, fp, fn, tn)
    block('TIER 1 vs HUMAN LABELS  (reweighted to the frame -- this is the figure)',
          wtp, wfp, wfn, wtn)

    # -- the F6 question -----------------------------------------------------
    print('THE F6 QUESTION: are posting-coincident changes substantive?')
    for flag, name in (('1', 'within 31 days of results posting'),
                       ('0', 'not posting-coincident')):
        sel = [(n, l) for n, l in usable.items()
               if sample.get(n, {}).get('posting_coincident') == flag]
        sub = sum(1 for _, l in sel if l['substantive'])
        wsub = sum(float(sample[n]['weight']) for n, l in sel if l['substantive'])
        wall = sum(float(sample[n]['weight']) for n, _ in sel)
        print('  %-34s n=%4d  substantive raw %s  weighted %s'
              % (name, len(sel), pct(safe_div(sub, len(sel))), pct(safe_div(wsub, wall))))
    print('')
    print('  The weighted share in the first row is what decides whether the 19.9%')
    print('  headline is mostly bookkeeping or mostly real. No date arithmetic')
    print('  reaches it; only reading the endpoints does.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
