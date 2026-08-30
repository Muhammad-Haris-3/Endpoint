/* UI-2 — the version diff viewer.
 *
 * Shows the primary outcome as it stood at version v-1 and at version v, with a
 * word-level diff and a timeline placing the change relative to primary
 * completion. This is the interaction the whole project exists to support: the
 * claim "this trial rewrote its promise after it could see the answer" is only
 * worth making if a reader can open the two versions and check it.
 *
 * Loaded before app.js. It uses `$`, `load` and `fmt` from app.js, but only
 * inside function bodies, which run after app.js has defined them.
 */
'use strict';

const diffs = { index: null, loaded: new Map() };

const esc = (t) => String(t).replace(/[&<>"]/g,
  (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

/* A real word-level LCS diff, not a token-set difference.
 *
 * Set difference would mark a moved word as both added and removed, and would
 * render an insertion like "at or Before Week 12" as though the entire measure
 * had changed. LCS preserves word order, so what the reader sees matches what
 * actually changed. */
function wordDiff(before, after) {
  const A = String(before || '').split(/(\s+)/).filter((x) => x !== '');
  const B = String(after || '').split(/(\s+)/).filter((x) => x !== '');
  const n = A.length, m = B.length;

  // LCS is O(n*m). Outcome text is short, but one pathological record should
  // degrade to "wholly replaced" rather than lock up the page.
  if (n * m > 250000) {
    return { a: '<del class="w">' + esc(before) + '</del>',
             b: '<ins class="w">' + esc(after) + '</ins>' };
  }

  const L = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      L[i][j] = A[i] === B[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
    }
  }
  let i = 0, j = 0, a = '', b = '';
  while (i < n && j < m) {
    if (A[i] === B[j]) { a += esc(A[i]); b += esc(B[j]); i++; j++; }
    else if (L[i + 1][j] >= L[i][j + 1]) { a += '<del class="w">' + esc(A[i]) + '</del>'; i++; }
    else { b += '<ins class="w">' + esc(B[j]) + '</ins>'; j++; }
  }
  while (i < n) { a += '<del class="w">' + esc(A[i]) + '</del>'; i++; }
  while (j < m) { b += '<ins class="w">' + esc(B[j]) + '</ins>'; j++; }
  return { a, b };
}

function outcomeHtml(list, side, other) {
  if (!list.length) {
    return '<div class="outcome empty">No primary outcome registered at this version.</div>';
  }
  return list.map((o, k) => {
    const partner = other[k] || { m: '', t: '' };
    const dm = wordDiff(side === 'a' ? o.m : partner.m, side === 'a' ? partner.m : o.m);
    const dt = wordDiff(side === 'a' ? o.t : partner.t, side === 'a' ? partner.t : o.t);
    const measure = side === 'a' ? dm.a : dm.b;
    const tf = side === 'a' ? dt.a : dt.b;
    return '<div class="outcome"><div class="measure">' + measure + '</div>' +
      ((o.t || partner.t) ? '<div class="tf"><b>time frame</b>' + tf + '</div>' : '') +
      '</div>';
  }).join('');
}

function timelineSvg(d) {
  if (!d.pc || !d.change_date) return '';
  const W = 900, left = 100, right = W - 100;
  const retro = d.days_after_pc !== null && d.days_after_pc > 0;
  const mid = retro ? left + (right - left) * 0.42 : right;
  const endX = retro ? right : mid;
  return '<div class="timeline"><svg viewBox="0 0 ' + W + ' 74" role="img" ' +
    'aria-label="Timeline from primary completion to the outcome change">' +
    '<line class="tl-line" x1="' + left + '" y1="34" x2="' + mid + '" y2="34"/>' +
    (retro ? '<line class="tl-gap" x1="' + mid + '" y1="34" x2="' + right + '" y2="34"/>' : '') +
    '<circle class="tl-dot" cx="' + mid + '" cy="34" r="6"/>' +
    '<circle class="tl-dot accent" cx="' + endX + '" cy="34" r="6"/>' +
    '<text class="tl-text strong" x="' + mid + '" y="18" text-anchor="middle">primary completion</text>' +
    '<text class="tl-text" x="' + mid + '" y="54" text-anchor="middle">' + d.pc + '</text>' +
    '<text class="tl-text strong" x="' + endX + '" y="18" text-anchor="middle">outcome changed</text>' +
    '<text class="tl-text" x="' + endX + '" y="54" text-anchor="middle">' + d.change_date + '</text>' +
    (retro ? '<text class="tl-text strong" x="' + ((mid + right) / 2) + '" y="70" text-anchor="middle">' +
      fmt(d.days_after_pc) + ' days after the data was in</text>' : '') +
    '</svg></div>';
}

function renderDiff(d) {
  const defensible = d.label === 'COUNT_CHANGED' || d.label === 'SUBSTANTIVE';
  $('#diff-body').innerHTML =
    '<div class="card">' +
      '<div class="diff-head">' +
        '<span class="nct">' + d.nct + '</span>' +
        '<span class="verdict ' + d.label + '">' + d.label + '</span>' +
        (d.retrospective
          ? '<span class="pill silent">after completion</span>'
          : '<span class="pill">before completion</span>') +
        '<span class="hint">' + esc(d.detail || '') + '</span>' +
        '<a class="src" style="margin-left:auto" href="' + d.source +
          '" target="_blank" rel="noopener">registry history &#8599;</a>' +
      '</div>' +
      timelineSvg(d) +
      '<div class="diff-cols">' +
        '<div class="diff-col"><h4>Before &mdash; version ' + (d.version - 1) + '</h4>' +
          '<div class="when">' + d.before.length + ' primary outcome' +
            (d.before.length === 1 ? '' : 's') + '</div>' +
          outcomeHtml(d.before, 'a', d.after) + '</div>' +
        '<div class="diff-col"><h4>At the change &mdash; version ' + d.version + '</h4>' +
          '<div class="when">' + d.after.length + ' primary outcome' +
            (d.after.length === 1 ? '' : 's') + '</div>' +
          outcomeHtml(d.after, 'b', d.before) + '</div>' +
      '</div>' +
      '<p class="hint" style="margin:18px 0 0">' +
        (defensible
          ? 'This pair is counted in primary figure 1.'
          : 'This pair is <strong>not</strong> counted in primary figure 1 &mdash; ' +
            'the change did not survive adjudication as a substantive one.') +
      '</p>' +
    '</div>';
  $('#diff-status').textContent = d.nct + ' · version ' + (d.version - 1) + ' → ' + d.version;
  document.querySelectorAll('.featured-strip button').forEach(
    (b) => b.classList.toggle('on', b.dataset.nct === d.nct));
}

async function diffBucket(prefix) {
  if (diffs.loaded.has(prefix)) return diffs.loaded.get(prefix);
  const b = await load('diffs/' + prefix + '.json');
  const map = new Map(b.diffs.map((d) => [d.nct, d]));
  diffs.loaded.set(prefix, map);
  return map;
}

async function showDiff(nct) {
  try {
    const m = await diffBucket(nct.slice(3, 6));
    const d = m.get(nct);
    if (!d) {
      $('#diff-status').textContent = nct + ' — not among the adjudicated pairs';
      return;
    }
    renderDiff(d);
  } catch (e) {
    $('#diff-status').textContent = 'could not load ' + nct + ': ' + e.message;
  }
}

async function initDiff() {
  let idx;
  try { idx = await load('diffs/index.json'); } catch (e) { idx = { available: false }; }
  diffs.index = idx;

  if (!idx.available) {
    $('#diff-body').innerHTML = '<div class="notice pending"><h4>Not yet measured</h4>' +
      '<p>The version pairs have not been collected. Blocked on ' +
      (idx.blocked_on || 'M4') + '.</p></div>';
    return;
  }

  const feat = idx.featured || [];
  $('#diff-featured').innerHTML = feat.map((f) =>
    '<button data-nct="' + f.nct + '" title="' + f.label + ', ' +
    fmt(f.days_after_pc) + ' days after completion">' +
    f.nct + ' · +' + fmt(f.days_after_pc) + 'd</button>').join('');

  $('#diff-featured').addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (b) showDiff(b.dataset.nct);
  });
  $('#diff-q').addEventListener('change', (e) => {
    const v = e.target.value.trim().toUpperCase();
    if (/^NCT\d{8}$/.test(v)) showDiff(v);
  });

  if (feat.length) showDiff(feat[0].nct);
}
