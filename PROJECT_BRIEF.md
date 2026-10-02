# Project Brief - FMD Compliance Gateway

## Problem

Electronic-product environmental compliance is moving from restricted-substance declarations to FMD. Suppliers provide data with different templates and levels of detail; some may provide a complete formulation while others provide only a declaration, SDS, or test report. This leaves internal reviewers unable to reliably decide whether a part may be used in a product for a given market.

The project is not intended to replace an enterprise PLM such as Agile. It is a focused system that improves supplier data quality and creates explainable compliance decisions. A BOM export is represented by a synthetic CSV import.

## Users

1. Supplier user: creates or uploads a declaration and resolves actionable data errors.
2. Compliance reviewer: reviews exceptions and evidence rather than manually comparing every source document.
3. Engineering/procurement user: checks product/BOM eligibility by target market.
4. Regulation administrator: versions substances, rules, exemptions, and effective dates.

## Compliance scope for MVP

### Priority 1

- EU RoHS: restricted substances, thresholds, homogeneous-material evaluation, exemptions, expiry dates.
- EU REACH SVHC: Candidate List reporting and 0.1% w/w trigger.
- PFAS: known restricted substances/groups, intentional-use declaration, high-risk material/use questions, and future-risk tracking.

### Priority 2

- China RoHS and EFUP data/marking.
- California Proposition 65.
- US TSCA rules.
- EU Critical Raw Materials (CRM) exposure dashboard.

Different regulations must not be reduced to one universal `pass/fail` formula. For example, RoHS is generally a homogeneous-material threshold evaluation; REACH may trigger communication requirements; Prop 65 needs exposure/warning assessment; CRM is supply-risk intelligence rather than a substance ban.

## Proposed submission model

Use a hybrid intake model:

1. **Guided portal entry** for new or high-risk declarations.
2. **Standard CSV/XLSX template** for suppliers able to prepare structured data offline.
3. **Existing-document import** for transition: supplier FMD, spreadsheet, SDS, and test report are uploaded as evidence. AI/OCR may extract a draft, but a supplier must confirm/correct the structured fields before it becomes an official declaration.

Do not accept a generic PDF as sufficient structured data. AI may normalize names, suggest CAS matches, find missing fields, and flag contradictions, but it must not invent concentration, material boundaries, exemptions, or a final compliance outcome.

## Canonical data model

### Supplier and part

- `supplier`: supplier ID, display name, manufacturing site, contact, data-quality score.
- `supplier_part`: supplier part number, internal part number, part name, category, revision, supplier, lifecycle state.
- `bom_line`: parent product, child part, quantity, revision, target-market context.

### FMD composition

- `homogeneous_material`: material ID, name, category, location in part, mass in grams.
- `substance_declaration`: CAS/EC identifier, normalized substance name, declared concentration, intentional-use status, CBI status, source confidence.
- `material_substance`: relationship between a homogeneous material and a substance.

The system calculates ppm from concentration (`percentage x 10,000`) rather than relying on supplier-entered ppm. It validates the composition mass balance and keeps both declared and calculated values when needed for audit.

### Evidence and traceability

- `evidence_document`: FMD, SDS, test report, certificate, or other document; issue date, validity date, test method, lab accreditation, original file reference.
- `declaration_version`: uploader, upload date, submit date, supplier attestation, status.
- `audit_event`: event type, actor, timestamp, before/after values, reviewer note.

### Regulatory rules

- `regulatory_list_version`: jurisdiction, regulation/list name, publication/effective date, version.
- `regulated_substance`: CAS/EC, aliases, group membership, regulatory identity.
- `rule`: scope, material/product level, threshold, unit, restriction/reporting type, effective date.
- `exemption`: regulation, exemption number, applicability, sunset date, approval state.
- `evaluation_result`: rule evaluated, object evaluated, outcome, reason, evidence used, confidence.

## Required supplier fields

The portal must request the following at the appropriate level:

- Internal part number, supplier part number, supplier, manufacturer site, and revision.
- Homogeneous-material name/category, location, and mass.
- CAS number, substance name, concentration, unit, and intentional-use status.
- RoHS status and applicable exemption where required.
- REACH SVHC information.
- China RoHS / EFUP fields where applicable.
- PFAS intentional-use, use/function, and evidence for high-risk materials.
- Critical raw material content and optional origin/recycled-content information.
- Evidence files, upload date, and uploader identity.

## Automated data-quality gate

Before submission, automatically check:

- Missing or malformed CAS identifiers.
- Vague substance text without a valid identity.
- Missing homogeneous-material boundaries or mass.
- Material composition not summing to an acceptable tolerance around 100%.
- Invalid unit conversion or impossible concentrations.
- Missing evidence for high-risk material/substance combinations.
- Expired or unmatched test evidence.
- RoHS exceedance without a valid exemption.
- High-risk PFAS material with unknown intentional use or no supporting data.

Each failure must result in a specific remediation task, for example: `Cable jacket: provide intentional-use PFAS declaration and supporting material evidence`, rather than a generic `please resubmit` request.

## Compliance outcomes

- `Approved`: complete, current, and compliant for the selected market/product/date.
- `Approved with condition`: compliant only with a valid exemption or documented limitation.
- `Blocked`: confirmed restriction failure or unacceptable evidence.
- `Data gap`: insufficient data; never treat as compliant by default.
- `Future risk`: currently allowed but exposed to a future restriction, list revision, or exemption expiry.

Keep `supplier assertion` separate from `data coverage and evidence quality`. A large EMS/ODM may assert compliance for a supplied assembly but may depend on declarations from upstream suppliers; the platform must show coverage and evidence rather than assuming all sub-tier composition is known.

## Suggested portfolio technology

- Frontend: Next.js + TypeScript.
- API/rules/import: FastAPI + Python.
- Database: PostgreSQL.
- File metadata: object storage interface or local development storage.
- Rules: versioned database records or versioned JSON with effective dates; no hard-coded regulatory values in UI code.
- Demo data: synthetic CSV/JSON only.

## Reference observations

The Dell and Apple documents in this folder informed the project direction: both require FMD/data disclosure and supporting evidence; both emphasize homogeneous-material-level compliance; their supplier requirements include verification/audit concepts. These references are for analysis only and must be reviewed for licensing/confidentiality before inclusion in a public portfolio repository.

