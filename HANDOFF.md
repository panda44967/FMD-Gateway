# FMD Compliance Gateway — Handoff

## Purpose

This is a personal portfolio prototype for a **Full Material Disclosure (FMD) compliance gateway** for electronic-product suppliers. It addresses a practical review bottleneck:

- A top-level supplier may assert `compliant`, while upstream material/substance information is incomplete.
- A reviewer then has to search a large BOM manually for missing declarations, unsupported evidence, concentration gaps, and possible regulatory hits.
- This product must **not** convert incomplete data into compliance. A `Partial FMD`, `Restricted-substance declaration`, or `Evidence only` submission is not a `Full FMD`.

The desired outcome is a clear, actionable queue: *which part/material is problematic, why, what evidence is missing, and what the supplier needs to provide*.

## Safety and scope

- Keep this a portfolio project with **synthetic data only**. Do not add employer, customer, supplier, product, BOM, or credential data.
- Do not present the current regulatory rules as legal advice or a complete production rule set.
- All regulatory lists must eventually be versioned by source, effective date, and jurisdiction.

## Current application

The prototype is static and has no dependency installation or backend requirement. Open `index.html` in a browser.

| File | Role |
|---|---|
| `index.html` | Dashboard, supplier intake, evaluation-trace and BOM UI |
| `styles.css` / `assessment.css` | Visual styling |
| `engine.js` | Browser-side CSV parsing and synthetic MVP evaluator |
| `sample-fmd.csv` | Deliberately incomplete synthetic USB-C cable declaration |
| `README.md` | Short product summary |
| `PROJECT_BRIEF.md` | Canonical product/data-model requirements |
| `DECISIONS.md` | Confirmed design decisions and open choices |

### What works now

Press **"Load Demo Declaration"** or upload a CSV using the required columns:

```csv
part_number,fmd_tier,material_id,material_name,material_mass_g,cas,concentration_pct,pfas_intentional_use,evidence_status
```

The local evaluator:

1. Rejects missing required columns.
2. Checks basic CAS shape, numeric concentration, and evidence presence.
3. Totals disclosed concentrations within each `material_id`; totals outside 98–102% become a material-balance data gap.
4. Matches a **tiny synthetic catalogue** in `engine.js`.
5. Evaluates RoHS sample thresholds at homogeneous-material level.
6. Marks an SVHC hit above 0.1% as `Review`, not automatically as a ban.
7. Treats known/unknown intentional PFAS use as a request for data and evidence.
8. Keeps any non-`Full FMD` tier as `Data gap` at part level.

The sample intentionally creates:

- A PFAS information gap for PTFE / cable jacket.
- A RoHS block for lead at 0.35% in the solder joint.
- An SVHC review task for the same lead row.
- A `Partial FMD` overall result even though some rows have data.

## Important implementation limitation

`engine.js` is demonstration logic, not a legal rule engine. Its `rules` object contains only a few CAS numbers for visualising the workflow. It must not be expanded by casually hard-coding large legal lists in UI code.

The most recent browser UI verification was limited because local `file://` reload navigation was blocked by the browser-control policy. The static page was previously opened successfully. Manually refresh the browser and press the sample-load button after edits.

## Product decisions to preserve

- Canonical data model: `supplier part → homogeneous material → substance/CAS → concentration + mass → evidence → regulatory evaluation`.
- Source PDFs, SDSs and test reports are evidence, not the canonical compliance record.
- AI/OCR may create a draft and flag contradictions. A supplier must attest before extracted data becomes an official declaration.
- Unknown or unsupported data is `Data gap`, never compliant by default.
- Regulation outcomes differ: RoHS is a homogeneous-material restriction; REACH SVHC can cause communication/SCIP obligations; PFAS needs a group/risk/evidence treatment; CRM is supply-risk intelligence.

## Recommended next build sequence

1. **Refactor the evaluator into data files and functions.** Move the sample catalogue from `engine.js` into `data/regulated-substances.demo.json`, with `source`, `listVersion`, `effectiveDate`, CAS, EC, aliases, rule type, threshold and unit.
2. **Add an import-result model.** Show a numbered supplier remediation task for each issue, including a precise request such as: `Cable jacket: declare intentional PFAS use and attach supporting material evidence.`
3. **Model article boundaries.** Add `article_id` / component relationships. REACH SVHC’s 0.1% w/w decision needs the relevant article boundary; it is not interchangeable with a complete product mass.
4. **Add declaration coverage.** Track material mass covered / part mass, disclosed substance mass / material mass, evidence freshness, and declaration tier separately. Do not collapse this into one green status.
5. **Add a synthetic multi-level BOM.** The reviewer queue should aggregate all child parts but retain drill-down paths: product → BOM line → supplier part → material → substance → evidence.
6. **Only then add persistence/API.** Suggested stack from the brief: Next.js + TypeScript frontend, FastAPI evaluator/import API, PostgreSQL, local object-storage interface.

## Regulatory implementation notes

- RoHS rules need scope, material level, limit, unit, effective date, applicable exemption and exemption sunset date.
- REACH Candidate List records need a date/version and must produce the appropriate communication/SCIP workflow rather than a generic non-compliance result.
- PFAS cannot be safely represented only as a fixed CAS list. Preserve `intentional use`, application/material risk and evidence status; support future group/structural matching with human review.

Official sources should be fetched and versioned before implementing real rules. The local reference PDFs/text files are research inputs, not automatically licensed production datasets.

## Open product choices

- Synthetic product family: laptop, monitor, charger, cable, or PCB assembly.
- Intake priority: guided portal entry, CSV upload, or both.
- Authentication for demo: none, mock roles, or real authentication.
- Portfolio deployment approach.

