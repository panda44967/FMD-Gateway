# Design Decisions

## Confirmed decisions

### 1. Product focus

Build a personal portfolio project, not a copy of Agile and not an enterprise production system.

### 2. Primary value

The system's primary value is improving supplier submission quality before internal review, then producing explainable product/BOM compliance outcomes.

### 3. FMD, not a fixed questionnaire

Do not make suppliers answer a static list of hundreds of substances as the primary workflow. The primary data is structured composition:

`part -> homogeneous material -> CAS/substance -> concentration and mass`

The regulatory lists are maintained by the platform's rule engine and are dynamically matched against disclosed substances. A regulation update can then re-evaluate existing FMDs without asking every supplier to complete a new questionnaire.

### 4. Limited-declaration fallback

Some suppliers cannot provide complete FMD because of supply-chain opacity or CBI. Support an explicitly labelled fallback:

- `Full FMD`: broad composition and mass coverage; supports future re-evaluation.
- `Partial FMD`: known composition with defined gaps.
- `Restricted-substance declaration`: current-list assertion only; cannot support broad future analysis.
- `Evidence only`: document received but insufficient for automated determination.

The fallback exists to manage reality; it must not be silently reported as Full FMD.

### 5. Supplier documents and AI

Supplier files are retained as evidence. The platform may accept their existing FMD/Excel/SDS/test-report files for transition, then use AI/OCR to extract a draft and map fields to the canonical schema. The supplier must attest to the extracted data. AI may flag gaps and contradictions but must not manufacture missing chemistry or make unreviewed legal conclusions.

### 6. Data-gap policy

Unknown, incomplete, or unsupported data produces `Data gap`, not `Compliant`.

### 7. Corporate data boundary

No employer, customer, supplier, product, BOM, or account data may be included. All demo entities, FMDs, evidence documents, and BOM files must be synthetic.

## Open decisions for implementation

- Which synthetic product family to demonstrate: laptop, monitor, charger, cable, or PCB assembly.
- Whether the first demo implements portal entry, CSV upload, or both.
- Exact MVP regulatory rule set and historical versions.
- Authentication approach: no login for a local demo, mock roles, or real demo authentication.
- Deployment choice for a portfolio demonstration.

