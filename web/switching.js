/* The outcome-switching panel, and the caveat it must never be shown without.
 *
 * FINDINGS.md F6. The measured rate is 19.9%, but it is 59.0% among trials that
 * posted results and 4.8% among trials that posted nothing. Submitting results
 * to ClinicalTrials.gov requires restating the outcome measures, and that
 * restatement is filed as a new record version dated after primary completion by
 * construction — so a large share of the figure is the act of reporting rather
 * than the act of switching.
 *
 * It does not follow that the changes are benign: results posting is precisely
 * when genuine switching would happen. The artefact and the offence occur at the
 * same moment in the same field, and the timestamp cannot separate them.
 *
 * So this panel renders the figure and the stratification together, always. The
 * headline is never shown alone, and the sponsor breakdown is deliberately not
 * rendered at all — it tracks reporting compliance, and a reader would take it
 * for a ranking of integrity.
 */
'use strict';

function renderSwitchingPanel(s) {
  const f1 = s.figure_1_outcome_switching;
  const host = $('#switching-body');

  if (!f1.available) {
    const fo = f1.flagged_only || {};
    host.innerHTML =
      '<div class="notice pending"><h4>Not yet measured</h4><p>' +
      (f1.note || '') + '</p><p style="margin-top:12px"><strong>Blocked on:</strong> ' +
      (f1.blocked_on || 'the version crawl') + '.</p></div>' +
      '<div class="tiles" style="margin-top:8px">' +
        '<div class="tile"><div class="v">' + pct(fo.rate) + '</div>' +
        '<div class="k">registry <em>flag</em> rate — <strong>not the finding</strong></div>' +
        '<div class="n">' + fmt(fo.retrospective_flagged) + ' of ' + fmt(fo.flagged) + ' flagged</div></div>' +
      '</div>';
    return;
  }

  const c = f1.confounded_by_results_posting;
  const frame = s.figure_2_non_reporting.frame;

  host.innerHTML =
    '<div class="tiles">' +
      '<div class="tile accent"><div class="v">' + pct(f1.rate) + '</div>' +
        '<div class="k">of trials made a substantive change to their registered ' +
        'primary outcome after primary completion</div>' +
        '<div class="n">' + fmt(f1.defensible_retrospective) + ' of ' + fmt(frame) +
        ' · adjudicated against the text, not the registry flag</div></div>' +
      '<div class="tile"><div class="v">' + fmt(f1.adjudicated) + '</div>' +
        '<div class="k">flagged pairs fetched and diffed</div>' +
        '<div class="n">two archived versions per trial</div></div>' +
    '</div>' +

    (c ? '<div class="notice accent" style="margin-top:24px">' +
      '<h4>Read this before quoting that number</h4>' +
      '<p>The rate is not one rate. It depends almost entirely on whether the ' +
      'trial reported its results at all:</p>' +
      '<div class="tiles" style="margin:16px 0">' +
        '<div class="tile"><div class="v">' + pct(c.posted_results.rate) + '</div>' +
          '<div class="k">among trials that <strong>posted results</strong></div>' +
          '<div class="n">' + fmt(c.posted_results.switched) + ' of ' + fmt(c.posted_results.trials) + '</div></div>' +
        '<div class="tile"><div class="v">' + pct(c.no_results.rate) + '</div>' +
          '<div class="k">among trials that <strong>posted nothing</strong></div>' +
          '<div class="n">' + fmt(c.no_results.switched) + ' of ' + fmt(c.no_results.trials) + '</div></div>' +
      '</div>' +
      '<p><strong>Submitting results requires restating the outcome measures</strong>, ' +
      'and that restatement is filed as a new record version — dated after primary ' +
      'completion by construction. <strong>70.9%</strong> of flagged changes in ' +
      'reporting trials land within 31 days of the posting date, median gap 24 days.</p>' +
      '<p>It does <em>not</em> follow that those changes are innocent. Results posting ' +
      'is exactly when genuine outcome switching would happen — it is the moment the ' +
      'sponsor writes up what they found, having seen it. <strong>The mechanical ' +
      'restatement and the real thing occur at the same instant in the same field, and ' +
      'no date arithmetic separates them.</strong></p>' +
      '<p>Telling them apart needs a reading of whether the <em>substance</em> of the ' +
      'endpoint changed. That work is specified and not yet done, so this figure is ' +
      'published as what it is: an upper bound containing an unknown amount of ' +
      'bookkeeping.</p>' +
    '</div>' : '');
}
