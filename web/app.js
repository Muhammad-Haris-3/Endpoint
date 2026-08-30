/* Endpoint — the web tier.
 *
 * Reads the static JSON that scripts/materialise.py writes. No queries, no
 * framework, no external requests.
 *
 * THE RULE THIS FILE EXISTS TO ENFORCE: every section of the data carries an
 * `available` flag, and a section that is not available renders as "not yet
 * measured" — never as zero, never as an empty chart that reads like a finding.
 * A frontend that renders a missing file as 0% would publish a false result
 * produced by an absent file, which is worse than publishing nothing.
 */
'use strict';

const DATA = '../data/serve';
const $ = (s) => document.querySelector(s);

const fmt = (n) => (n === null || n === undefined) ? '—' : n.toLocaleString('en-US');
const pctOf = (x, d) => (x === null || x === undefined) ? '—' : (100 * x / d).toFixed(1) + '%';
const pct = (r, dp) => (r === null || r === undefined) ? '—' : (100 * r).toFixed(dp === undefined ? 1 : dp) + '%';

async function load(name) {
  const res = await fetch(`${DATA}/${name}`);
  if (!res.ok) throw new Error(`${name}: HTTP ${res.status}`);
  return res.json();
}

/* ---------- small SVG helpers (no chart library) ---------- */

const NS = 'http://www.w3.org/2000/svg';
function el(tag, attrs, text) {
  const n = document.createElementNS(NS, tag);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  if (text !== undefined) n.textContent = text;
  return n;
}

/* ---------- hero + reporting ---------- */

function renderHero(s) {
  const f2 = s.figure_2_non_reporting;
  $('#hero-num').textContent = pct(f2.rate);
  $('#hero-denom').textContent =
    `${fmt(f2.silent)} of ${fmt(f2.frame)} trials · interventional · primary completion 2015–2022 · census, not a sample`;
}

function renderReportingTiles(s) {
  const f2 = s.figure_2_non_reporting, L = s.lateness;
  const tiles = [
    { v: pct(f2.rate), k: 'posted no results at all', n: `${fmt(f2.silent)} of ${fmt(f2.frame)}`, accent: true },
    { v: pct(L.over_deadline_rate), k: `of those that did post were later than ${L.deadline_days} days`, n: `${fmt(L.over_deadline)} of ${fmt(L.datable)}` },
    { v: fmt(L.median_days), k: 'median days, completion → posting', n: 'the deadline is 365' },
    { v: fmt(f2.posted), k: 'trials posted results', n: pct(1 - f2.rate) + ' of the frame' },
  ];
  $('#reporting-tiles').innerHTML = tiles.map((t) => `
    <div class="tile${t.accent ? ' accent' : ''}">
      <div class="v">${t.v}</div><div class="k">${t.k}</div><div class="n">${t.n}</div>
    </div>`).join('');
}

function rateTable(target, obj, labelHead, opts) {
  const rows = Object.entries(obj)
    .filter(([, d]) => d.trials >= (opts && opts.min ? opts.min : 1))
    .sort((a, b) => b[1].trials - a[1].trials);
  const max = Math.max(...rows.map(([, d]) => d.silent_rate));
  const t = $(target);
  t.innerHTML = `<thead><tr>
      <th>${labelHead}</th><th class="num">Trials</th><th class="num">Silent</th><th>Rate</th>
    </tr></thead><tbody>${rows.map(([k, d]) => `
      <tr>
        <td class="mono">${k}</td>
        <td class="num">${fmt(d.trials)}</td>
        <td class="num">${fmt(d.silent)}</td>
        <td class="bar-cell">
          <span class="bar${d.silent_rate < 0.4 ? ' good' : ''}" style="width:${(d.silent_rate / max * 92).toFixed(1)}px"></span>
          <span style="position:relative;left:100px" class="mono">${pct(d.silent_rate)}</span>
        </td>
      </tr>`).join('')}</tbody>`;
}

function renderLateness(d) {
  const svg = $('#lateness-chart');
  const L = d.lateness_days;
  if (!L.available) return;
  const W = svg.clientWidth || 640, H = 220, pad = { l: 8, r: 8, t: 14, b: 34 };
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  const counts = L.counts, edges = L.edges;
  const max = Math.max(...counts);
  const bw = (W - pad.l - pad.r) / counts.length;
  const labels = edges.map((e, i) => i === 0 ? '≤0' : `${edges[i - 1]}–${e}`).concat([`>${edges[edges.length - 1]}`]);

  counts.forEach((c, i) => {
    const h = max ? (H - pad.t - pad.b) * (c / max) : 0;
    const x = pad.l + i * bw;
    // The deadline sits at 365, which is edges[3]; anything past it is over.
    const over = i > 3;
    svg.appendChild(el('rect', {
      x: x + 2, y: H - pad.b - h, width: Math.max(bw - 4, 1), height: h,
      class: over ? 'bar' : 'bar dim', rx: 2,
    }));
    if (c > 0 && bw > 34) {
      svg.appendChild(el('text', { x: x + bw / 2, y: H - pad.b - h - 5, class: 'val', 'text-anchor': 'middle' },
        c > 999 ? (c / 1000).toFixed(0) + 'k' : String(c)));
    }
    if (bw > 30) {
      svg.appendChild(el('text', { x: x + bw / 2, y: H - pad.b + 14, class: 'lbl', 'text-anchor': 'middle' }, labels[i]));
    }
  });
  // deadline marker between bucket 3 and 4
  const dx = pad.l + 4 * bw;
  svg.appendChild(el('line', { x1: dx, y1: pad.t - 6, x2: dx, y2: H - pad.b, stroke: 'currentColor', 'stroke-dasharray': '4 3', 'stroke-width': 1.5, opacity: .55 }));
  svg.appendChild(el('text', { x: dx + 6, y: pad.t + 4, class: 'lbl' }, '365-day deadline'));
  svg.appendChild(el('text', { x: pad.l, y: H - 6, class: 'lbl' }, 'days from primary completion to results posted'));
}

/* ---------- funnel ---------- */

function renderFunnel(f) {
  const svg = $('#funnel-chart');
  const W = svg.clientWidth || 800, rowH = 46, pad = { l: 4, r: 4, t: 10 };
  const H = pad.t + f.stages.length * rowH + 20;
  svg.setAttribute('height', H);
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  const base = f.stages[0].count;
  const barMax = W - 260;

  f.stages.forEach((s, i) => {
    const y = pad.t + i * rowH;
    const w = s.available && s.count !== null ? Math.max(barMax * (s.count / base), 2) : barMax * 0.999;
    svg.appendChild(el('rect', {
      x: 0, y: y + 6, width: w, height: 24, rx: 4,
      class: s.available ? 'funnel-bar' : 'funnel-bar pending',
      opacity: s.available ? (1 - i * 0.14) : 1,
    }));
    svg.appendChild(el('text', { x: 8, y: y + 22, class: 'funnel-label', fill: s.available ? '#fff' : 'currentColor' },
      s.label.length > 52 ? s.label.slice(0, 51) + '…' : s.label));
    const right = el('text', { x: W - 4, y: y + 22, class: 'funnel-count', 'text-anchor': 'end' },
      s.available && s.count !== null
        ? `${fmt(s.count)}   ${pctOf(s.count, base)}`
        : `not yet measured — blocked on ${s.blocked_on}`);
    svg.appendChild(right);
  });
}

/* ---------- outcome switching ---------- */

function renderSwitching(s) {
  const f1 = s.figure_1_outcome_switching;
  const host = $('#switching-body');
  if (f1.available) {
    host.innerHTML = `
      <div class="tiles">
        <div class="tile accent"><div class="v">${pct(f1.rate)}</div>
          <div class="k">of trials substantively changed their primary outcome after primary completion</div>
          <div class="n">${fmt(f1.defensible_retrospective)} of ${fmt(s.figure_2_non_reporting.frame)}</div></div>
        <div class="tile"><div class="v">${fmt(f1.adjudicated)}</div>
          <div class="k">flagged pairs adjudicated against the outcome text</div>
          <div class="n">two archived versions fetched and diffed per trial</div></div>
      </div>`;
    return;
  }
  const fo = f1.flagged_only || {};
  host.innerHTML = `
    <div class="notice pending">
      <h4>Not yet measured</h4>
      <p>
        ${f1.note ? f1.note.replace(/"/g, '&quot;') : ''}
      </p>
      <p style="margin-top:12px"><strong>Blocked on:</strong> ${f1.blocked_on || 'the version crawl'}.</p>
    </div>
    <div class="tiles" style="margin-top:8px">
      <div class="tile"><div class="v">${pct(fo.rate)}</div>
        <div class="k">registry <em>flag</em> rate — trials the registry marks as having changed their primary outcome after completion</div>
        <div class="n">${fmt(fo.retrospective_flagged)} of ${fmt(fo.flagged)} flagged · <strong>this is not the finding</strong></div></div>
      <div class="tile"><div class="v">37.7%</div>
        <div class="k">of that flag did not survive reading the text, on a 400-trial pilot</div>
        <div class="n">which is why the number above is not reported as the answer</div></div>
    </div>`;
}

/* ---------- participants ---------- */

function renderParticipants(s, d) {
  const f3 = s.figure_3_participants;
  $('#enrol-sum').textContent = fmt(f3.preregistered_sum);
  $('#enrol-median').textContent = fmt(f3.median_trial);
  $('#enrol-note').textContent =
    `pre-registered figure · ${fmt(f3.trials_with_enrolment)} trials · ${fmt(f3.enrolment_absent)} without an enrolment field`;

  const svg = $('#concentration-chart');
  const C = d.enrolment_concentration;
  const W = svg.clientWidth || 640, H = 150, pad = { l: 96, r: 60, t: 10, b: 24 };
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  const entries = Object.entries(C.top_n_shares).sort((a, b) => Number(a[0]) - Number(b[0]));
  const barMax = W - pad.l - pad.r;
  const rowH = (H - pad.t - pad.b) / entries.length;
  entries.forEach(([k, share], i) => {
    const y = pad.t + i * rowH;
    svg.appendChild(el('text', { x: pad.l - 10, y: y + rowH / 2 + 4, class: 'lbl', 'text-anchor': 'end' },
      `top ${fmt(Number(k))}`));
    svg.appendChild(el('rect', { x: pad.l, y: y + 3, width: barMax, height: rowH - 10, rx: 3, fill: 'var(--grid)' }));
    svg.appendChild(el('rect', { x: pad.l, y: y + 3, width: Math.max(barMax * share, 2), height: rowH - 10, rx: 3, class: 'bar' }));
    svg.appendChild(el('text', { x: pad.l + barMax + 8, y: y + rowH / 2 + 4, class: 'val' }, pct(share)));
  });
  svg.appendChild(el('text', { x: pad.l, y: H - 6, class: 'lbl' },
    `of ${fmt(C.total)} total enrolment · median trial ${fmt(C.median)}`));
}

/* ---------- explorer ---------- */

const explorer = { index: null, loaded: new Map(), rows: [] };

async function bucketFor(prefix) {
  if (explorer.loaded.has(prefix)) return explorer.loaded.get(prefix);
  const b = await load(`trials/${prefix}.json`);
  explorer.loaded.set(prefix, b.trials);
  return b.trials;
}

function renderTrials(rows, note) {
  const t = $('#trials-table');
  const shown = rows.slice(0, 200);
  t.innerHTML = `<thead><tr>
      <th>NCT</th><th>Sponsor</th><th>Phase</th><th class="num">Completed</th>
      <th class="num">Enrolled</th><th class="num">Versions</th><th>Results</th><th>Source</th>
    </tr></thead><tbody>${shown.map((r) => `
      <tr>
        <td class="mono">${r.nct}</td>
        <td>${r.sponsor_class || '—'}</td>
        <td class="mono">${r.phase || '—'}</td>
        <td class="num mono">${r.pc || '—'}</td>
        <td class="num">${fmt(r.enrol)}</td>
        <td class="num">${fmt(r.versions)}</td>
        <td>${r.results
          ? `<span class="pill posted">posted ${r.results}</span>`
          : '<span class="pill silent">none</span>'}</td>
        <td><a class="src" href="${r.source}" target="_blank" rel="noopener">open ↗</a></td>
      </tr>`).join('')}</tbody>`;
  $('#explorer-status').textContent =
    `${fmt(rows.length)} rows${rows.length > 200 ? ' — showing first 200' : ''}${note ? ' · ' + note : ''}`;
}

function applyFilters() {
  const sp = $('#f-sponsor').value, rs = $('#f-results').value;
  let rows = explorer.rows;
  if (sp) rows = rows.filter((r) => r.sponsor_class === sp);
  if (rs === '0') rows = rows.filter((r) => !r.results);
  if (rs === '1') rows = rows.filter((r) => !!r.results);
  renderTrials(rows, `shard ${explorer.currentPrefix}`);
}

async function initExplorer(breakdowns) {
  explorer.index = await load('trials/index.json');
  const sel = $('#f-sponsor');
  Object.keys(breakdowns.by_sponsor_class).sort().forEach((k) => {
    if (k === '(none)') return;
    const o = document.createElement('option'); o.value = k; o.textContent = k; sel.appendChild(o);
  });

  const first = Object.keys(explorer.index.buckets).sort()[0];
  explorer.currentPrefix = first;
  explorer.rows = await bucketFor(first);
  applyFilters();

  $('#q').addEventListener('input', async (e) => {
    const v = e.target.value.trim().toUpperCase();
    if (/^NCT\d{8}$/.test(v)) {
      const prefix = v.slice(3, 6);
      if (!explorer.index.buckets[prefix]) { renderTrials([], 'no shard holds that ID'); return; }
      explorer.currentPrefix = prefix;
      explorer.rows = await bucketFor(prefix);
      const hit = explorer.rows.filter((r) => r.nct === v);
      renderTrials(hit.length ? hit : [], hit.length ? 'exact match' : 'not in the frame');
    } else if (v === '') {
      applyFilters();
    } else {
      renderTrials(explorer.rows.filter((r) => r.nct.includes(v)), `shard ${explorer.currentPrefix}`);
    }
  });
  $('#f-sponsor').addEventListener('change', applyFilters);
  $('#f-results').addEventListener('change', applyFilters);
}

/* ---------- methods ---------- */

function renderProvenance(m) {
  const p = m.provenance;
  const rows = [
    ['built', p.built_utc],
    ['frame size', fmt(p.frame_size)],
    ['frame sha256', p.frame_sha256],
    ['pre-registration sha256', p.prereg_sha256],
    ['history batch', p.history_batch],
    ['versions batch', p.versions_batch || 'pending'],
    ['pipeline commit', p.pipeline_commit],
  ];
  $('#provenance').innerHTML = rows.map(([k, v]) => `<dt>${k}</dt><dd>${v || '—'}</dd>`).join('');
  $('#footer-prov').textContent =
    `frame ${p.frame_sha256 ? p.frame_sha256.slice(0, 12) : '—'} · built ${p.built_utc}`;

  const h = m.pipeline_health;
  const hc = h.history_crawl || {}, vc = h.version_crawl || {};
  const st = hc.stats || {};
  $('#health').innerHTML = [
    ['history crawl', hc.complete === true ? 'complete' : (hc.available === false ? 'absent' : 'incomplete')],
    ['records collected', fmt(hc.records)],
    ['missing from frame', fmt(hc.missing)],
    ['fetch failures', fmt(hc.failures)],
    ['HTTP 403 / 429', `${fmt(st.http_403)} / ${fmt(st.http_429)}`],
    ['version crawl', vc.available ? `adjudicated ${fmt(vc.adjudicated)}` : 'pending'],
  ].map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('');
}

/* ---------- boot ---------- */

(async function main() {
  try {
    const [summary, breakdowns, distributions, funnel, manifest] = await Promise.all([
      load('summary.json'), load('breakdowns.json'), load('distributions.json'),
      load('funnel.json'), load('manifest.json'),
    ]);

    renderHero(summary);
    renderReportingTiles(summary);
    rateTable('#sponsor-table', breakdowns.by_sponsor_class, 'Sponsor class', { min: 50 });
    rateTable('#phase-table', breakdowns.by_phase, 'Phase', { min: 500 });
    renderLateness(distributions);
    renderFunnel(funnel);
    renderSwitching(summary);
    renderParticipants(summary, distributions);
    renderProvenance(manifest);
    await initExplorer(breakdowns);
    await initDiff();
  } catch (err) {
    document.querySelector('main').insertAdjacentHTML('afterbegin',
      `<div class="wrap"><div class="notice" style="margin-top:24px">
         <h4>Data not loaded</h4>
         <p>${String(err.message || err)}</p>
         <p>Run <span class="mono">python scripts/materialise.py</span> to generate
            <span class="mono">data/serve/</span>, then serve the repository root.</p>
       </div></div>`);
  }
})();
