/* External benchmark programs, not an extension of accepted same-harness scores.
   Never infer official participation or copy external leaderboard scores into local lanes. */
(function (root) {
  'use strict';

  const STATUSES = Object.freeze({
    not_verified: 'No verified result',
    adapter_present: 'Integration exists; run unverified',
    external_run: 'Externally executed; not officially published',
    official_published: 'Official result verified'
  });
  const REQUIRED = ['id', 'name', 'category', 'summary', 'coverage', 'next_step',
    'program_url', 'method_url', 'action_url', 'action_label', 'external_method'];
  const safe = value => String(value ?? '').replace(/[&<>"']/g, char =>
    ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[char]));
  function verifiedUrl(value) {
    if (typeof value !== 'string') throw Error('External evaluator URL must be a string');
    const parsed = new URL(value);
    if (parsed.protocol !== 'https:' || !parsed.hostname || parsed.username || parsed.password) {
      throw Error('External evaluator URL must use credential-free HTTPS');
    }
    return parsed.href;
  }
  function validate(doc) {
    if (!doc || doc.schema_version !== 1 || doc.authority_effect !== 'none' ||
        !/^\d{4}-\d{2}-\d{2}$/.test(doc.snapshot_as_of ?? '') ||
        !Array.isArray(doc.programs) || doc.programs.length !== 3) {
      throw Error('Unsupported external evaluation directory format');
    }
    const ids = new Set();
    for (const p of doc.programs) {
      if (!p || typeof p !== 'object' || !/^[a-z][a-z0-9-]{1,31}$/.test(p.id ?? '') ||
          ids.has(p.id) || !Object.hasOwn(STATUSES, p.status)) {
        throw Error('Invalid or duplicate external evaluation program');
      }
      ids.add(p.id);
      for (const field of REQUIRED) {
        if (typeof p[field] !== 'string' || !p[field].trim()) {
          throw Error('External evaluation missing field ' + field);
        }
      }
      for (const field of ['program_url', 'method_url', 'action_url']) verifiedUrl(p[field]);
      if (p.integration_url != null) verifiedUrl(p.integration_url);
      if (p.submission_deadline != null &&
          !/^\d{4}-\d{2}-\d{2}$/.test(p.submission_deadline)) {
        throw Error('Invalid submission deadline');
      }
      if (p.submission_deadline && p.submission_timezone !== 'UTC+08:00') {
        throw Error('Unbound deadline timezone');
      }
      if (p.official_result !== null) {
        const r = p.official_result;
        if (p.status !== 'official_published' || !r || r.reviewed !== true ||
            typeof r.metric !== 'string' || !r.metric.trim() ||
            typeof r.dataset !== 'string' || !r.dataset.trim() ||
            typeof r.evaluator_revision !== 'string' || !r.evaluator_revision.trim() ||
            !/^[0-9a-f]{40}$/.test(r.agent_memory_revision || '') ||
            typeof r.score !== 'number' || !Number.isFinite(r.score) ||
            r.score < 0 || r.score > 100 ||
            !r.evaluation_date || !/^\d{4}-\d{2}-\d{2}$/.test(r.evaluation_date)) {
          throw Error('Official result missing mandatory independently-reviewed provenance');
        }
        verifiedUrl(r.public_result_url);
      } else if (p.status === 'official_published') {
        throw Error('Official status requires source-bound, reviewed evidence');
      }
    }
    if (!['aml', 'amb', 'memoryarena'].every(id => ids.has(id))) {
      throw Error('External program registry is incomplete');
    }
    return doc;
  }
  const link = (href, label) => '<a href="' + safe(verifiedUrl(href)) +
    '" target="_blank" rel="noopener noreferrer">' + safe(label) + ' ↗</a>';
  function render(document, raw) {
    const data = validate(raw);
    const container = document.getElementById('externalProgramGrid');
    const asOf = document.getElementById('externalAsOf');
    if (!container || !asOf) throw Error('External evaluation section is missing');
    container.innerHTML = data.programs.map(p => {
      const result = p.official_result;
      const resultHtml = result
        ? '<p class="ext-result"><strong>Official ' + safe(result.metric) + ':</strong> ' +
          safe(result.score) + ' / 100 · ' + safe(result.dataset) + ' · ' +
          link(result.public_result_url, 'Verified ranking') + '</p>'
        : '<p class="ext-unmeasured">No independently verified official Agent Memory score.</p>';
      const deadline = p.submission_deadline
        ? '<p class="ext-deadline"><strong>Submission deadline:</strong> ' +
          safe(p.submission_deadline) + ' (' + safe(p.submission_timezone) + ')</p>' : '';
      return '<article class="ext-program" aria-labelledby="ext-' + safe(p.id) + '">' +
        '<div class="ext-topline"><span class="ext-category">' + safe(p.category) +
        '</span><span class="ext-state">' + safe(STATUSES[p.status]) + '</span></div>' +
        '<h3 id="ext-' + safe(p.id) + '">' + safe(p.name) + '</h3>' +
        '<p class="ext-coverage">' + safe(p.coverage) + '</p>' +
        '<p class="ext-status"><strong>Our status:</strong> ' + safe(p.summary) + '</p>' +
        resultHtml +
        '<p class="ext-method"><strong>Evaluation method:</strong> ' + safe(p.external_method) + '</p>' +
        '<p class="ext-next"><strong>Next:</strong> ' + safe(p.next_step) + '</p>' +
        deadline +
        '<div class="ext-links">' + link(p.program_url, 'Official site') +
        link(p.method_url, 'Method / source') + link(p.action_url, p.action_label) +
        (p.integration_url ? link(p.integration_url, 'Our provider bridge') : '') +
        '</div></article>';
    }).join('');
    asOf.textContent = 'External directory reviewed ' + data.snapshot_as_of +
      ' · manually maintained, not live third-party scores';
  }
  function load() {
    const target = document.getElementById('externalProgramGrid');
    if (!target) return;
    fetch('./data/external-evaluations.json', {cache:'no-store'})
      .then(response => {
        if (!response.ok) throw Error('External program directory unavailable (' + response.status + ')');
        return response.json();
      })
      .then(data => render(document, data))
      .catch(error => {
        target.textContent = 'External evaluation directory unavailable: ' + error.message;
        const asOf = document.getElementById('externalAsOf');
        if (asOf) asOf.textContent = 'Links are available from the benchmark source repository.';
      });
  }
  root.AgentMemoryExternalEvaluations = {validate, render};
  if (typeof module !== 'undefined' && module.exports) module.exports = {validate, render};
  if (typeof document !== 'undefined') load();
})(typeof window !== 'undefined' ? window : globalThis);
