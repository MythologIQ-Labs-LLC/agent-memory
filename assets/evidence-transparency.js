/* Agent Memory read-only competitive coverage projection.
   No accepted score, comparator eligibility or memory authority is created here. */
(function (root) {
  'use strict';

  const normalize = x => String(x ?? '').trim().toLowerCase().replaceAll('_', '-');
  const isScore = x => typeof x === 'number' && Number.isFinite(x);
  const safe = x => String(x ?? '').replace(/[&<>"']/g, c => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
  })[c]);
  const goodUrl = x => {
    try { const u = new URL(String(x)); return u.protocol === 'https:' ? u.href : '#'; }
    catch { return '#'; }
  };
  function audit(data) {
    if (data?.schema_version !== 1 || data?.source?.authority_effect !== 'none' ||
        !/^[a-f0-9]{40}$/.test(data?.source?.head || '') ||
        !Array.isArray(data?.profiles) || !Array.isArray(data?.competitors)) {
      throw new Error('Untrusted competitive evidence projection');
    }
    const registry = data.competitors.map(x => ({
      id:x.id, name:x.name, state:x.state, url:x.url,
      aliases:new Set([x.id, ...(x.observed_ids || [])].map(normalize))
    }));
    const controls = new Set();
    const counted = new Set();
    const evidence = new Map();
    const metricRows = [];
    const profiles = [];
    for (const p of data.profiles) {
      if (!Array.isArray(p.metrics)) throw new Error('Profile without metrics');
      const peerIds = new Set(), metrics = [];
      const family = String(p.lane_id || '').startsWith('longmemeval') ? 'LongMemEval'
        : String(p.lane_id || '').startsWith('amb-') ? 'AMB PrecisionMemBench' : 'Other';
      for (const m of p.metrics) {
        if (!Array.isArray(m.rows)) throw new Error('Metric without rows');
        const control = m.rows.find(x => x.role === 'control' && isScore(x.score));
        if (!control) throw new Error('Accepted metric lacks scored control: ' + m.metric);
        if (!['higher', 'lower'].includes(m.direction)) throw new Error('Metric direction not specified');
        const peers = m.rows.filter(x => x.role === 'comparator' && isScore(x.score));
        metrics.push({id:m.metric,peerCount:new Set(peers.map(x=>normalize(x.system))).size});
        for (const r of m.rows) {
          if (!isScore(r.score)) continue;
          if (r.role === 'control') controls.add(normalize(r.system));
          if (!['control','baseline','comparator'].includes(r.role)) throw new Error('Unknown metric role');
          if (!r.run_url || !r.run_url.includes('/blob/' + data.source.head + '/')) {
            throw new Error('Evidence link not pinned to exact source snapshot');
          }
          const key = r.run_url;
          const existing = evidence.get(key) || { system:r.system,role:r.role,known:false,missing:false };
          if (Number.isInteger(r.sample_count) && r.sample_count >= 0) existing.known = true;
          else existing.missing = true;
          evidence.set(key, existing);
          metricRows.push({
            profile:p.profile_id, family, plane:p.plane, metric:m.metric, direction:m.direction,
            system:r.system,role:r.role,score:r.score,
            sample_count:Number.isInteger(r.sample_count)?r.sample_count:null,
            evidence:r.run_url,source_head:data.source.head,
            snapshot_as_of:data.source.dashboard_as_of
          });
        }
        for (const r of peers) {
          const id = normalize(r.system);
          peerIds.add(id);
          counted.add(id);
        }
      }
      const columns = registry.filter(x => x.id !== 'agent-memory').map(x => ({
        id:x.id,name:x.name,state:x.state,
        accepted: [...peerIds].some(pId => x.aliases.has(pId))
      }));
      profiles.push({
        id:p.profile_id,family,plane:p.plane,
        metrics,peerCount:peerIds.size,peers:[...peerIds].sort(),columns,
        source:p.benchmark_file,input_sha256:p.input_sha256
      });
    }
    const aligned = registry.filter(x=>x.id!=='agent-memory' && x.state==='measured'
      && ![...counted].some(id=>x.aliases.has(id))).map(x=>x.id);
    if (aligned.length) throw new Error('Measured registry systems lack accepted score rows: '+aligned.join(', '));
    const countedMissing = [...counted].filter(id=>!registry.some(x=>x.state==='measured' && x.aliases.has(id)));
    if (countedMissing.length) throw new Error('Accepted peer not registered as measured: '+countedMissing.join(', '));

    const familyGroups=[...new Set(profiles.map(x=>x.family))];
    const uniqueEvidence=[...evidence.values()];
    const observed = uniqueEvidence.filter(x=>x.role==='comparator');
    return {
      source:data.source,
      summary:{
        measuredExternalProducts:counted.size,
        targetExternalProducts:6,
        targetRemaining:Math.max(0,6-counted.size),
        acceptedPlanes:profiles.length,
        metricContexts:profiles.reduce((n,p)=>n+p.metrics.length,0),
        benchmarkFamilies:familyGroups.length,
        registeredUnmeasured:registry.filter(x=>x.state==='not_run').length,
        distinctEvidenceLinks:evidence.size,
        linksMissingSampleCounts:uniqueEvidence.filter(x=>!x.known).length,
        observedComparatorLinks:observed.length
      },
      profiles,metricRows,registry,measuredIds:[...counted].sort(),controls:[...controls].sort()
    };
  }
  function csv(auditResult) {
    const keys=['profile','family','plane','metric','direction','system','role','score',
      'sample_count','evidence','source_head','snapshot_as_of'];
    const cell=v => {
      let x = v==null ? '' : String(v);
      if (/^[\s]*[=+@-]/.test(x)) x = "'" + x;
      return '"' + x.replaceAll('"','""') + '"';
    };
    return [keys.join(','), ...auditResult.metricRows.map(row=>keys.map(k=>cell(row[k])).join(','))].join('\r\n') + '\r\n';
  }
  function render(doc, data) {
    const a = audit(data);
    const sum=doc.getElementById('coverageSummary');
    const table=doc.getElementById('coverageMatrix');
    const gaps=doc.getElementById('provenanceGaps');
    if (!sum || !table || !gaps) return a;
    const stat=(number,label)=>'<div class="coverage-stat"><strong>'+safe(number)+'</strong><span>'+safe(label)+'</span></div>';
    sum.innerHTML=[
      stat(a.summary.measuredExternalProducts + ' / ' + a.summary.targetExternalProducts,'External memory products with accepted comparable results'),
      stat(a.summary.benchmarkFamilies,'Distinct benchmark families covered by accepted peer results'),
      stat(a.summary.targetRemaining,'Additional products needed for minimum cohort')
    ].join('');
    const systems=a.registry.filter(x=>x.id!=='agent-memory');
    table.innerHTML='<thead><tr><th scope="col">Evaluation profile</th><th scope="col">Native metrics</th>'+
      systems.map(x=>'<th scope="col" title="'+safe(x.name)+'">'+safe(x.name)+'</th>').join('')+
      '</tr></thead><tbody>'+
      a.profiles.map(p=>'<tr><th scope="row"><span class="profile-name">'+safe(p.id)+'</span><small>'+safe(p.family)+'</small></th>'+
        '<td class="num">'+p.metrics.length+'</td>'+
        p.columns.map(c=>c.accepted?'<td><span class="coverage-tag measured">Measured</span></td>':
          '<td><span class="coverage-tag unmeasured" title="No accepted same-harness result in this profile">No result</span></td>').join('')+
        '</tr>').join('')+'</tbody>';
    const noDenom=a.summary.linksMissingSampleCounts;
    gaps.innerHTML='<p><strong>'+safe(a.summary.distinctEvidenceLinks)+'</strong> unique source-evidence links surfaced. '+
      '<strong>'+safe(noDenom)+'</strong> links have no sample count in this published projection. '+
      (noDenom?'Check the linked underlying evidence for actual denominators; absence here does not mean the original run omitted them. ':'')+
      'Full inference, host and cost identity is not carried in this compact website snapshot; do not treat a website score as a complete execution manifest.</p>'+
      '<p>As of <strong>'+safe(data.source.dashboard_as_of)+'</strong>. Exact dashboard revision <code>'+safe(data.source.head.slice(0,12))+
      '</code>; source object <code>'+safe(data.source.dashboard_blob.slice(0,12))+
      '</code>. Rows from outside these frozen accepted profiles, published vendor claims, baselines and systems not run are excluded from measured competitor counts.</p>';
    const exportBtn=doc.getElementById('exportEvidenceCsv');
    if (exportBtn) {
      exportBtn.addEventListener('click',()=>{
        const blob=new Blob([csv(a)],{type:'text/csv;charset=utf-8'});
        const link=doc.createElement('a');
        const objectURL=URL.createObjectURL(blob);
        link.href=objectURL;link.download='agent-memory-accepted-comparisons-'+
          String(data.source.dashboard_as_of||'snapshot')+'.csv';
        doc.body.append(link);link.click();link.remove();
        URL.revokeObjectURL(objectURL);
      });
    }
    return a;
  }
  root.AgentMemoryPeerEvidence=Object.freeze({audit,csv,render});
})(globalThis);
