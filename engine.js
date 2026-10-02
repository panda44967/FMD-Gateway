// ==========================================================================
// FMD Compliance Gateway - Client & API Bridge (English Localization)
// ==========================================================================

const API_BASE = window.location.origin.includes('http')
  ? (window.location.origin + '/api')
  : 'http://127.0.0.1:8008/api';

const rules = {
  "7439-92-1": { n: "Lead", rohs: 0.1, svhc: true },
  "7440-43-9": { n: "Cadmium", rohs: 0.01, svhc: true },
  "117-81-7": { n: "DEHP (Phthalate)", rohs: 0.1, svhc: true },
  "335-67-1": { n: "PFOA", pfas: true },
  "9002-84-0": { n: "PTFE", pfas: true }
};

const sample = `part_number,fmd_tier,material_id,material_name,material_mass_g,cas,concentration_pct,pfas_intentional_use,evidence_status
CBL-USB4-01,Partial FMD,M-01,Cable jacket,8.3,9002-84-0,99.3,Unknown,None
CBL-USB4-01,Partial FMD,M-02,Copper conductor,12.4,7440-50-8,99.9,No,Test report
CBL-USB4-01,Partial FMD,M-03,Solder joint,0.5,7439-92-1,0.35,No,Supplier declaration
CBL-USB4-01,Partial FMD,M-03,Solder joint,0.5,7440-31-5,99.65,No,Supplier declaration`;

const greenSample = `part_number,fmd_tier,material_id,material_name,material_mass_g,cas,concentration_pct,pfas_intentional_use,evidence_status
CBL-USBC-GREEN01,Full FMD,M-01,Outer Jacket (Halogen-free TPE),6.5,308070-21-5,82.5,No,Test report
CBL-USBC-GREEN01,Full FMD,M-01,Outer Jacket (Halogen-free TPE),6.5,9002-88-4,17.2,No,Test report
CBL-USBC-GREEN01,Full FMD,M-02,Core Wire Insulation (Polypropylene),2.8,9003-07-0,99.6,No,Test report
CBL-USBC-GREEN01,Full FMD,M-03,Conductor Wire (Oxygen-free Copper),14.2,7440-50-8,99.99,No,Test report
CBL-USBC-GREEN01,Full FMD,M-04,Connector Housing (Stainless Steel SUS304),1.8,7439-89-6,71.5,No,Test report
CBL-USBC-GREEN01,Full FMD,M-04,Connector Housing (Stainless Steel SUS304),1.8,7440-47-3,18.5,No,Test report
CBL-USBC-GREEN01,Full FMD,M-04,Connector Housing (Stainless Steel SUS304),1.8,7440-02-0,9.8,No,Test report
CBL-USBC-GREEN01,Full FMD,M-05,Lead-free Solder Joint (SAC305),0.35,7440-31-5,96.5,No,Test report
CBL-USBC-GREEN01,Full FMD,M-05,Lead-free Solder Joint (SAC305),0.35,7440-22-4,3.0,No,Test report
CBL-USBC-GREEN01,Full FMD,M-05,Lead-free Solder Joint (SAC305),0.35,7440-50-8,0.5,No,Test report`;

const c = x => ({
  "Approved": "approved",
  "Review": "review",
  "Condition": "condition",
  "Blocked": "blocked",
  "Data gap": "data-gap"
}[x] || "data-gap");

const tag = x => `<span class="status ${c(x)}">${x}</span>`;

function read(t) {
  let [a, ...b] = t.trim().split(/\r?\n/);
  let h = a.split(',');
  return b.map((l, i) => Object.fromEntries(h.map((x, j) => [x, (l.split(',')[j] || '').trim()]))).map((x, i) => ({ ...x, line: i + 2 }));
}

// Fallback offline evaluator
function evaluateClient(rows) {
  let required = ["part_number", "fmd_tier", "material_id", "material_name", "material_mass_g", "cas", "concentration_pct", "pfas_intentional_use", "evidence_status"];
  let missing = required.filter(x => !Object.hasOwn(rows[0] || {}, x));
  if (missing.length) return { error: `Evaluation rejected: Missing required column(s) [${missing.join(', ')}]` };

  let totals = {}, issues = [];
  let out = rows.map(r => {
    let pct = Number(r.concentration_pct);
    let z = rules[r.cas];
    let bad = !/^\d{2,7}-\d{2}-\d$/.test(r.cas) || !Number.isFinite(pct) || !r.evidence_status;
    totals[r.material_id] = (totals[r.material_id] || 0) + (Number.isFinite(pct) ? pct : 0);

    let rohs = 'Approved', reach = 'Approved', pfas = 'Approved', action = 'Passed automated validation';
    if (bad) {
      rohs = reach = pfas = 'Data gap';
      action = 'Provide verified CAS, concentration, and test evidence';
      issues.push([`${r.material_name} — Incomplete chemistry`, `Line ${r.line}: CAS format invalid or missing document`]);
    }
    if (z?.rohs !== undefined && pct > z.rohs) {
      rohs = 'Blocked';
      action = `RoHS ${z.n} ${pct}% exceeds limit of ${z.rohs}%; valid exemption or substitution required`;
      issues.push([`${r.material_name} — RoHS Threshold Exceedance`, `${z.n} ${pct}% · ${r.part_number}`]);
    }
    if (z?.svhc && pct > 0.1) {
      reach = 'Review';
      action = action === 'Passed automated validation' ? 'Verify article boundary; establish SCIP / Art. 33 disclosure task' : action;
      issues.push([`${r.material_name} — REACH SVHC Disclosure Review`, `${z.n} ${pct}% (>0.1% w/w)`]);
    }
    if (z?.pfas || ['unknown', 'yes'].includes((r.pfas_intentional_use || '').toLowerCase())) {
      pfas = 'Data gap';
      action = action === 'Passed automated validation' ? 'Declare specific PFAS intentional use & submit Total Fluorine test report' : action;
      issues.push([`${r.material_name} — PFAS Inquiry & Evidence Gap`, `${r.part_number} · Intentional use: ${r.pfas_intentional_use || 'Unspecified'}`]);
    }
    return { r, z, bad, rohs, reach, pfas, action };
  });

  Object.entries(totals).forEach(([id, v]) => {
    if (v < 98 || v > 102) {
      let x = out.find(x => x.r.material_id === id);
      if (x) {
        x.bad = true;
        x.action = `Mass-balance deficit: Material totals ${v.toFixed(1)}%; must total ~100%`;
        issues.push([`${x.r.material_name} — Mass-Balance Deficit`, `Material ${id} discloses only ${v.toFixed(1)}%`]);
      }
    }
  });

  let tier = rows[0].fmd_tier;
  let blocked = out.some(x => x.rohs === 'Blocked');
  let gap = out.some(x => x.bad || x.pfas === 'Data gap') || tier !== 'Full FMD';
  return {
    part: rows[0].part_number,
    tier,
    out,
    issues,
    overall: blocked ? 'Blocked' : gap ? 'Data gap' : 'Approved',
    materials: new Set(rows.map(x => x.material_id)).size
  };
}

// Render Evaluation Trace
function showAssessment(d) {
  if (d.error) {
    importResult.hidden = false;
    importResult.textContent = d.error;
    return;
  }
  assessment.hidden = false;
  importResult.hidden = false;
  importResult.innerHTML = `<strong>Evaluated Part: ${d.part}</strong> — Declaration Tier: <b>${d.tier}</b> (Cannot be treated as Full FMD). Generated <b>${d.issues.length}</b> actionable supplier tasks.`;
  assessmentTitle.textContent = `${d.part} · ${d.tier}`;
  assessmentStatus.className = `status ${c(d.overall)}`;
  assessmentStatus.textContent = d.overall.toUpperCase();
  assessmentSummary.textContent = d.overall === 'Data gap'
    ? 'Parent-level compliance assertion rejected: Missing sub-tier chemistry or unsupported material declarations identified.'
    : 'Granular compliance trace verified against active jurisdiction thresholds and exemption rules.';

  traceMetrics.innerHTML = `
    <div class="trace-stat-box"><b>${d.materials}</b><span>Homogeneous Materials</span></div>
    <div class="trace-stat-box"><b>${d.out.length}</b><span>Disclosed Substances</span></div>
    <div class="trace-stat-box"><b>${d.issues.length}</b><span>Actionable Tasks</span></div>
    <div class="trace-stat-box"><b>${d.tier}</b><span>Declaration Tier</span></div>
  `;

  assessmentRows.innerHTML = d.out.map(x => `
    <tr>
      <td>
        <strong>${x.r.material_name}</strong><br>
        <small style="color: var(--text-muted);">${x.z?.n || 'Unmatched Substance'} · CAS ${x.r.cas} · ${x.r.concentration_pct}%</small>
        ${x.r.evidence_status ? `<br><span style="display:inline-block; margin-top:3px; background: rgba(56, 189, 248, 0.12); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.25); font-size: 10.5px; padding: 1px 6px; border-radius: 4px;">📑 ${x.r.evidence_status}</span>` : ''}
      </td>
      <td>${tag(x.bad ? 'Data gap' : 'Approved')}</td>
      <td>${tag(x.rohs)}</td>
      <td>${tag(x.reach)}</td>
      <td>${tag(x.pfas)}</td>
      <td class="action-copy">${x.action}</td>
    </tr>
  `).join('');

  assessment.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Format backend response
function formatServerPartData(partData) {
  let allSubs = [];
  let issues = (partData.review_tasks || []).map(t => [t.title, t.remediation_instruction]);

  (partData.materials || []).forEach(m => {
    (m.substances || []).forEach(s => {
      allSubs.push({
        r: {
          material_name: m.name,
          cas: s.cas,
          concentration_pct: s.concentration_pct,
          pfas_intentional_use: s.pfas_intentional_use,
          evidence_status: s.evidence_status,
          exemption: s.exemption || 'None'
        },
        z: { n: s.name || s.cas },
        bad: !m.mass_balance_valid || s.rohs_eval === 'Data gap',
        rohs: s.rohs_eval,
        reach: s.reach_eval,
        pfas: s.pfas_eval,
        action: s.action_required || 'Passed automated validation'
      });
    });
  });

  return {
    part: partData.part_number,
    tier: partData.fmd_tier,
    out: allSubs,
    issues: issues,
    overall: partData.overall_status,
    materials: (partData.materials || []).length
  };
}

// Ingestion via backend API
async function handleCsvUpload(csvText) {
  try {
    let res = await fetch(`${API_BASE}/fmd/upload/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ csv_text: csvText })
    });

    if (res.ok) {
      let data = await res.json();
      let formatted = formatServerPartData(data.part);
      showAssessment(formatted);
      refreshDashboard();
      return;
    }
  } catch (err) {
    console.warn('Backend API unreachable, running client fallback evaluator:', err);
  }

  showAssessment(evaluateClient(read(csvText)));
}

// Dashboard refresh from Django API
async function refreshDashboard() {
  try {
    // 1. Stats
    let sRes = await fetch(`${API_BASE}/overview/stats/`);
    if (sRes.ok) {
      let stats = await sRes.json();
      if (document.getElementById('coverageValue')) document.getElementById('coverageValue').textContent = `${stats.coverage_rate}%`;
      if (document.getElementById('coverageMeter')) document.getElementById('coverageMeter').style.width = `${stats.coverage_rate}%`;
      if (document.getElementById('pendingMetric')) document.getElementById('pendingMetric').textContent = String(stats.pending_tasks).padStart(2, '0');
      if (document.getElementById('approvedMetric')) document.getElementById('approvedMetric').textContent = String(stats.approved_parts).padStart(2, '0');
      if (document.getElementById('gapMetric')) document.getElementById('gapMetric').textContent = String(stats.data_gap_parts).padStart(2, '0');
      if (document.getElementById('issueCount')) document.getElementById('issueCount').textContent = stats.pending_tasks;
    }

    // 2. Review Tasks
    let tRes = await fetch(`${API_BASE}/tasks/`);
    if (tRes.ok) {
      let tasks = await tRes.json();
      let queue = document.getElementById('reviewQueue');
      let tpl = document.getElementById('queueTemplate');
      if (queue && tpl) {
        queue.innerHTML = '';
        tasks.slice(0, 6).forEach(t => {
          let item = tpl.content.cloneNode(true);
          let sevEl = item.querySelector('.severity-pill');
          if (sevEl) {
            sevEl.classList.remove('blocked', 'review', 'data-gap');
            sevEl.classList.add(t.severity);
          }
          item.querySelector('.queue-title').textContent = t.title;
          item.querySelector('.queue-sub').textContent = `${t.part_number} · ${t.remediation_instruction.slice(0, 56)}...`;
          item.querySelector('button').addEventListener('click', () => {
            alert(`[SUPPLIER REMEDIATION TASK]\n\nPart Number: ${t.part_number}\n\nTask: ${t.title}\n\nInstruction:\n${t.remediation_instruction}`);
          });
          queue.appendChild(item);
        });
      }
    }

    // 3. BOM Parts (Atlas USB-C 65W Fast Charger)
    let pRes = await fetch(`${API_BASE}/parts/`);
    if (pRes.ok) {
      let parts = await pRes.json();
      let bomRows = document.getElementById('bomRows');
      if (bomRows && parts.length > 0) {
        // Prioritize BOM catalog parts (IPN-*) for the Atlas 65W Fast Charger
        let bomParts = parts.filter(p => p.part_number.startsWith('IPN-'));
        if (bomParts.length === 0) bomParts = parts;

        // Calculate aggregated Product Eligibility Roll-up
        let productStatusBadge = document.getElementById('productStatus');
        if (productStatusBadge) {
          let hasBlocked = bomParts.some(p => p.overall_status === 'Blocked');
          let hasDataGap = bomParts.some(p => p.overall_status === 'Data gap');
          let hasReview = bomParts.some(p => p.overall_status === 'Review');

          if (hasBlocked) {
            productStatusBadge.className = 'status blocked';
            productStatusBadge.textContent = 'BLOCKED (NON-COMPLIANT)';
          } else if (hasDataGap) {
            productStatusBadge.className = 'status data-gap';
            productStatusBadge.textContent = 'DATA GAP (INCOMPLETE)';
          } else if (hasReview) {
            productStatusBadge.className = 'status review';
            productStatusBadge.textContent = 'REVIEW REQUIRED';
          } else {
            productStatusBadge.className = 'status approved';
            productStatusBadge.textContent = 'MARKET CLEARANCE APPROVED';
          }
        }

        bomRows.innerHTML = bomParts.map(p => `
          <tr>
            <td><strong>${p.part_number}</strong></td>
            <td style="color: #cbd5e1;">${p.part_name || 'Component Sub-Assembly'}</td>
            <td style="font-size: 12px; color: #94a3b8;">${p.supplier_name || 'External Supplier'}</td>
            <td><span class="status condition">${p.fmd_tier}</span></td>
            <td>${tag(p.rohs_status)}</td>
            <td>${tag(p.reach_status)}</td>
            <td>${tag(p.pfas_status)}</td>
            <td>${tag(p.overall_status)}</td>
          </tr>
        `).join('');
      }
    }

    // 4. Supplier Collaboration & Magic Links Hub
    let supRes = await fetch(`${API_BASE}/supplier/context/`);
    if (supRes.ok) {
      let supData = await supRes.json();
      let hubRows = document.getElementById('supplierHubRows');
      let badge = document.getElementById('supplierHubBadge');
      if (supData.available_suppliers && hubRows) {
        if (badge) badge.textContent = `${supData.available_suppliers.length} Connected Suppliers`;
        hubRows.innerHTML = supData.available_suppliers.map(s => {
          let progressPct = s.parts_count > 0 ? Math.round((s.submitted_count / s.parts_count) * 100) : 0;
          let isComplete = s.submitted_count === s.parts_count && s.parts_count > 0;
          let partsBadges = (s.parts || []).map(pn => `<code style="font-size: 11px; padding: 2px 6px; background: rgba(56, 189, 248, 0.1); color: #38bdf8; border-radius: 4px; margin-right: 4px; display: inline-block; margin-bottom: 3px;">${pn}</code>`).join('');
          return `
            <tr>
              <td><strong style="color: #93c5fd; font-family: var(--font-mono);">${s.supplier_code}</strong></td>
              <td>
                <div style="font-weight: 600; color: #f8fafc;">${s.name}</div>
                <div style="font-size: 11px; color: var(--text-muted);">${s.contact_email || 'Verified Supplier Contact'}</div>
              </td>
              <td>${partsBadges || '<span style="color: var(--text-muted);">No parts assigned</span>'}</td>
              <td>
                <span class="status ${isComplete ? 'approved' : (s.submitted_count > 0 ? 'review' : 'condition')}" style="font-size: 11px; padding: 2px 8px;">
                  ${s.submitted_count} / ${s.parts_count} Disclosed (${progressPct}%)
                </span>
              </td>
              <td>
                <a href="/supplier/?vendor=${encodeURIComponent(s.supplier_code)}" target="_blank" class="btn btn-secondary btn-sm" style="font-size: 11.5px; border-color: rgba(56, 189, 248, 0.4); color: #38bdf8; white-space: nowrap;" title="Open isolated single-tenant supplier portal for ${s.name}">
                  🔗 Open Supplier Portal ↗
                </a>
              </td>
            </tr>
          `;
        }).join('');
      }
    }
  } catch (e) {
    console.log('Django server not active, using default static presentation.');
  }
}

// Trigger Dynamic Re-evaluation
async function triggerReevaluate() {
  const btn = document.getElementById('btnReevaluate');
  const statusEl = document.getElementById('reevaluateStatus');
  if (btn) btn.disabled = true;
  if (statusEl) statusEl.textContent = 'Evaluating database against active rules...';

  try {
    let res = await fetch(`${API_BASE}/regulations/reevaluate/`, { method: 'POST' });
    if (res.ok) {
      let d = await res.json();
      let summary = d.summary;
      if (statusEl) {
        statusEl.textContent = `✅ Screening completed: ${summary.total_evaluated} part(s) evaluated, ${summary.impacted_parts_count} impacted.`;
      }
      refreshDashboard();
      return;
    }
  } catch (err) {
    if (statusEl) statusEl.textContent = '⚠️ Start Django backend server (python manage.py runserver)';
  } finally {
    if (btn) btn.disabled = false;
  }
}

// Regulatory Radar & Auto-Sync Functions
async function loadRegulatoryRadar() {
  try {
    let res = await fetch(`${API_BASE}/regulations/status/`);
    if (!res.ok) return;
    let data = await res.json();

    // 1. Last Sync Badge
    const badge = document.getElementById('radarLastSyncBadge');
    if (badge) {
      if (data.last_sync) {
        badge.innerHTML = `🛡️ Feeds Active · Last Swept: ${data.last_sync.timestamp} (${data.total_active_rules} Rules)`;
        badge.className = data.last_sync.parts_impacted > 0 ? 'status condition' : 'status approved';
      } else {
        badge.textContent = `🛡️ Active Rules: ${data.total_active_rules}`;
      }
    }

    // 2. Frameworks Grid
    const regGrid = document.getElementById('regGrid');
    if (regGrid && data.regulations) {
      regGrid.innerHTML = data.regulations.map(r => `
        <div class="reg-card">
          <div style="display: flex; align-items: center; justify-content: space-between;">
            <strong style="color: #38bdf8; font-size: 13.5px;">${r.regulation}</strong>
            <span class="status approved" style="font-size: 11px; padding: 2px 7px;">${r.count} Rules</span>
          </div>
          <div style="font-size: 11px; color: var(--text-muted); font-family: var(--font-mono);">${r.version}</div>
          <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.4; margin-top: 4px;">${r.citation}</div>
        </div>
      `).join('');
    }

    // 3. Audit Logs
    const auditRows = document.getElementById('syncAuditRows');
    const auditCount = document.getElementById('syncAuditCount');
    if (auditRows && data.recent_sync_logs) {
      if (auditCount) auditCount.textContent = `${data.recent_sync_logs.length} logged runs`;
      if (data.recent_sync_logs.length === 0) {
        auditRows.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 16px;">No synchronization runs logged yet.</td></tr>`;
      } else {
        auditRows.innerHTML = data.recent_sync_logs.map(l => `
          <tr>
            <td><code>${l.timestamp}</code></td>
            <td><span style="color: #93c5fd;">${l.triggered_by}</span></td>
            <td>${l.rules_checked}</td>
            <td>${l.rules_updated > 0 ? `<b style="color: #f59e0b;">+${l.rules_updated}</b>` : '0'}</td>
            <td>${l.parts_revaluated}</td>
            <td>${l.parts_impacted > 0 ? `<b style="color: #f87171;">${l.parts_impacted}</b>` : '<span style="color:#34d399;">0</span>'}</td>
            <td><span class="status ${l.parts_impacted > 0 ? 'condition' : 'approved'}">${l.status}</span></td>
          </tr>
        `).join('');
      }
    }
  } catch (err) {
    console.warn('Could not load regulatory radar:', err);
  }
}

async function triggerRegulatorySync(mode = 'check_only') {
  const btnClean = document.getElementById('btnSyncClean');
  const btnEcha = document.getElementById('btnSimulateEcha');
  const btnReset = document.getElementById('btnResetRules');
  const banner = document.getElementById('radarImpactBanner');
  const title = document.getElementById('radarImpactTitle');
  const detail = document.getElementById('radarImpactDetail');

  if (btnClean) btnClean.disabled = true;
  if (btnEcha) btnEcha.disabled = true;
  if (btnReset) btnReset.disabled = true;

  try {
    let res = await fetch(`${API_BASE}/regulations/sync/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: mode, triggered_by: 'Manual (Internal Reviewer Workspace)' })
    });

    if (res.ok) {
      let data = await res.json();
      let evalSummary = data.evaluation;

      // Refresh radar and KPI dashboard
      await loadRegulatoryRadar();
      await refreshDashboard();

      if (banner && title && detail) {
        banner.style.display = 'block';
        if (data.mode === 'simulate_reach_batch_update') {
          title.textContent = `⚠️ Retrospective Impact: ${evalSummary.impacted_parts_count} Part(s) Flagged by ECHA Update!`;
          let impactedList = evalSummary.impacted_parts.map(p => `• <b>${p.part_number}</b> (${p.part_name}): Shifted from <code>${p.old_status}</code> to <code style="color:#f59e0b;">${p.new_status}</code> (New task: ${p.latest_task || 'REACH SVHC exceedance'})`).join('<br>');
          detail.innerHTML = `
            <div><b>New Rule Applied:</b> ${data.notes.join('; ')}</div>
            <div style="margin-top: 6px;"><b>BOM Sweep Impact:</b><br>${impactedList || 'No affected parts found.'}</div>
            <div style="margin-top: 6px; font-size: 11px; color: var(--text-muted);">New ReviewTask tickets have been automatically dispatched to compliance reviewers.</div>
          `;
          banner.style.background = 'rgba(239, 68, 68, 0.12)';
          banner.style.borderColor = 'rgba(239, 68, 68, 0.35)';
          title.style.color = '#f87171';
        } else if (data.mode === 'reset_baseline') {
          title.textContent = `↺ Regulatory Rules Restored to Baseline`;
          detail.innerHTML = `Ruleset reverted to standard baseline. All parts re-evaluated across the repository (${evalSummary.total_evaluated} parts swept).`;
          banner.style.background = 'rgba(16, 185, 129, 0.12)';
          banner.style.borderColor = 'rgba(16, 185, 129, 0.35)';
          title.style.color = '#34d399';
        } else {
          title.textContent = `✅ Scheduled Feed Check Completed (All Up-To-Date)`;
          detail.innerHTML = `Audited active rules against upstream ECHA, BSMI, and IEC 62474 feeds. Zero rule drift detected; all ${evalSummary.total_evaluated} existing database parts verified.`;
          banner.style.background = 'rgba(16, 185, 129, 0.12)';
          banner.style.borderColor = 'rgba(16, 185, 129, 0.35)';
          title.style.color = '#34d399';
        }
      }
    } else {
      alert('Failed to synchronize regulations: ' + res.statusText);
    }
  } catch (err) {
    alert('Synchronization error: ' + err);
  } finally {
    if (btnClean) btnClean.disabled = false;
    if (btnEcha) btnEcha.disabled = false;
    if (btnReset) btnReset.disabled = false;
  }
}

// Event Bindings
const loadSampleEl = document.getElementById('loadSample');
if (loadSampleEl) {
  loadSampleEl.onclick = () => handleCsvUpload(sample);
}
if (document.getElementById('loadGreenSample')) {
  document.getElementById('loadGreenSample').onclick = () => handleCsvUpload(greenSample);
}

const csvUploadEl = document.getElementById('csvUpload');
if (csvUploadEl) {
  csvUploadEl.onchange = e => {
    let f = e.target.files[0];
    if (!f) return;
    
    if (f.name.toLowerCase().endsWith('.xlsx') || f.name.toLowerCase().endsWith('.xls')) {
      let formData = new FormData();
      formData.append('file', f);
      fetch(`${API_BASE}/fmd/upload/`, { method: 'POST', body: formData })
        .then(res => res.json())
        .then(data => {
          if (data.part) {
            showAssessment(formatServerPartData(data.part));
            refreshDashboard();
            loadRegulatoryRadar();
          } else if (data.error) {
            showAssessment({ error: data.error });
          }
        })
        .catch(err => {
          alert('Failed to process Excel file: ' + err);
        });
    } else {
      let r = new FileReader();
      r.onload = () => handleCsvUpload(r.result);
      r.readAsText(f);
    }
  };
}

const dlTplEl = document.getElementById('downloadTemplate');
if (dlTplEl) {
  dlTplEl.onclick = () => {
    let a = document.createElement('a');
    a.href = '/api/fmd/template/download/?part_number=GENERIC-PART';
    a.download = 'FMD_Declaration_Template.xlsx';
    a.click();
  };
}

const resetDemoEl = document.getElementById('resetDemo');
if (resetDemoEl) {
  resetDemoEl.onclick = () => {
    const assessEl = document.getElementById('assessment');
    if (assessEl) assessEl.hidden = true;
    const impRes = document.getElementById('importResult');
    if (impRes) impRes.hidden = true;
    refreshDashboard();
  };
}

// Initial Load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    refreshDashboard();
    loadRegulatoryRadar();
  });
} else {
  refreshDashboard();
  loadRegulatoryRadar();
}
