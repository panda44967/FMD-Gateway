# FMD Gateway & Supply Chain Environmental Compliance System
## Complete System Architecture, Business Logic & Project Handover Memory

> **Notice for Future AI Assistants**:
> This document is the **single source of truth** for this project. Read this file completely when starting a new session on any computer to restore 100% memory of the architecture, design decisions, business rules, models, API endpoints, and user requirements.

---

## 1. Project Background & System Objectives

The **FMD Gateway** (Full Material Declaration Compliance Platform) is an enterprise-grade environmental compliance system built for electronics and hardware OEMs. It automates chemical compliance verification across global supply chains according to:
1. **EU RoHS Directive 2011/65/EU & (EU) 2015/863 (RoHS 3)**: Restricts 10 hazardous substances (Lead, Cadmium, Mercury, Cr(VI), PBB, PBDE, DEHP, BBP, DBP, DIBP). Supports official **Annex III & IV Exemptions** (e.g. 6(c), 7(a), 7(c)-I).
2. **EU REACH Regulation (EC) 1907/2006 (SVHC Candidate List)**: Article 33/59 declarations for Substances of Very High Concern (> 0.1% w/w).
3. **PFAS Global Restrictions**: OECD definition & US EPA TSCA Section 8(a)(7) reporting, screening for per- and polyfluoroalkyl substances.
4. **Taiwan RoHS CNS 15663 (BSMI)**: Section 5 Marking of Presence of Restricted Substances.
5. **Product Bill of Materials (BOM) Roll-up**: Aggregates child component compliance up to the parent product (Demo device: *Atlas USB-C 65W Fast Charger*).

---

## 2. Architecture & Tech Stack

### Core Technology
- **Backend**: Python 3.12, Django 5.1, Django REST Framework (DRF), SQLite (`db.sqlite3`).
- **Frontend**: Vanilla JavaScript (ES6+), Semantic HTML5, Custom CSS (`styles.css`) with CSS variables and modern dark theme. Zero heavy frontend frameworks (React/Vue) — intentionally built with native web standards for maximum portability, zero build step, and instant deployment.
- **Document & Spreadsheet Engines**:
  - `openpyxl`: Excel (.xlsx) parsing, styling, formula validation, locked template generation.
  - `pypdf` & `reportlab`: PDF inspection and parsing for third-party lab reports (SGS, TÜV Rheinland) and material safety data sheets (MSDS/SDS).
  - Flexible column normalizer & AI Document Intelligence: Extracts formulations from non-standard spreadsheets or test reports.

### Local Server Setup
- Default port: `http://127.0.0.1:8008/`
- Startup command: `python manage.py runserver 127.0.0.1:8008`

---

## 3. Key Pages & Two-Sided User Roles

The system is split into two distinct operational views:

### Role A: OEM Compliance Reviewer Workspace (`index.html`)
- **URL**: `http://127.0.0.1:8008/`
- **Purpose**: Internal dashboard for OEM compliance officers, quality engineers, and supply chain managers.
- **Key Features**:
  1. **Compliance Summary KPI Cards**: Disclosure Coverage (%), Pending Reviews, EU Market Eligible count, Identified Data Gaps.
  2. **Compliance Review Queue**: Actionable remediation tasks with severity pills (`blocked`, `review`, `condition`, `data-gap`).
  3. **Evaluation Trace Panel**: Dynamic drill-down table showing all homogeneous materials, CAS numbers, concentrations, and evaluations.
  4. **Supplier Collaboration & Magic Links Hub (`#supplierHub`)**:
     - Lists all 7 connected enterprise suppliers (`SUP-LUX-001`, `SUP-TI-001`, `SUP-MUR-001`, `SUP-ADI-001`, `SUP-TE-001`, `SUP-FOX-002`, `SUP-DEL-003`).
     - Shows assigned part numbers, contacts, and real-time intake campaign progress (e.g. `1 / 4 Disclosed`).
     - Includes `[🔗 Open Supplier Portal ↗]` buttons to simulate each vendor in a new tab.
  5. **Header Quick Launcher**: Top navigation dropdown (`🌐 Launch Supplier Portal: [Select Vendor...]`) for one-click access to any supplier portal.
  6. **Product BOM Roll-up**: Multi-tier Bill of Materials for *Atlas USB-C 65W Fast Charger*.
  7. **Global Chemical Regulations Radar (`#rules`)**:
     - Live rule count tracker per framework (RoHS, REACH, PFAS, BSMI).
     - **Zero-Burden Retrospective Engine**: When regulations update, background sweep audits all existing parts without requiring suppliers to resubmit documentation.
     - **Sandbox Simulator**: Button to simulate ECHA adding Nickel (CAS 7440-02-0) as REACH SVHC and observe BOM impact in real-time.

### Role B: External Supplier Material Declaration Portal (`supplier.html`)
- **URL**: `http://127.0.0.1:8008/supplier/?vendor=SUP-TI-001` (Accepts `?vendor=<SUPPLIER_CODE>`)
- **Purpose**: External single-tenant portal where suppliers view assigned compliance requests and submit formulations.
- **Key Features**:
  1. **Single-Tenant Isolation**: Header confirms `🏢 Authorized Supplier: <Name> (Code: <Code>) | 🔒 Single-Tenant Verified`. External suppliers can ONLY see parts assigned to their own company.
  2. **Reviewer Simulation Mode**: Embedded inside the top blue isolation banner for internal OEM reviewers to switch between all 7 vendors on the fly during testing/demos.
  3. **Assigned Compliance Requests Queue**:
     - Shows part numbers, MPNs, descriptions, due dates, statuses.
     - Status displays revision badges (e.g., `Submitted ✓ [Rev 2]` or `Action Required`).
     - Action buttons: `📥 Download Template`, `⬆️ Smart Upload`, `👁️ View Formulation`, and `🔄 Submit Revision`.
  4. **Pre-Submission Quality Gate (`#qualityGateSection`)**:
     - Instant automated screening upon file drop or upload.
     - **Multi-Revision History Selector**: Dropdown to toggle between `Rev 2 (Active)` and `Rev 1 (Historical Snapshot)`.
     - **Historical Audit Banner**: When viewing superseded revisions, displays an amber banner and disables the signature block (read-only audit mode).
  5. **CBI Foolproof Lock (`#cbiLockBanner`)**:
     - Automatically locks submission if proprietary trade secret chemistry (5%-10%) is detected.
     - Unlocks only after supplier executes the **CBI Non-Hazardous Legal Attestation**.
  6. **Legal Attestation & Sign-off**: Authorized corporate signature with cryptographic submission reference ID generation.

---

## 4. Critical Business Logic & Algorithms

### 1. 100% English Front-End Rule (Strict Constraint)
- **All user-facing UI text, buttons, alerts, and tooltips in `index.html`, `supplier.html`, and `engine.js` must remain 100% pure English with 0 Chinese characters.**
- Explanations in chat with the user may be in Traditional Chinese if requested by the user, but code and UI files must remain 100% English.

### 2. Multi-Revision Lifecycle (`PartRevision`)
- Submissions are **non-destructive**. When a supplier uploads a corrected or updated formulation, the existing formulation is NOT wiped out.
- The previous submission is archived as `PartRevision` (Rev 1), and the new upload becomes Rev 2.
- Full composition snapshot (`snapshot_data`) preserves homogeneous materials, substances, CAS, concentrations, and evaluations.

### 3. Mass-Balance Screening
- In electronics FMD, homogeneous materials must total approximately 100% w/w.
- **Tolerance Window**: 98.0% to 102.0%.
- If total < 98% or > 102%, the material is flagged with `Mass-balance deficit` and overall verdict becomes `Data gap`.

### 4. Confidential Business Information (CBI) Protection
- Major chemical suppliers (e.g., resins, adhesives) protect proprietary formulas.
- **Threshold**: Proprietary substances (CAS `CBI-SYSTEM` or keywords like `proprietary`, `trade secret`, `cbi`) are accepted up to **10.0% w/w** per material.
- **Foolproof Lock Mechanism**: If CBI is detected between 5.0% and 10.0%, submission is strictly `LOCKED (CBI GAP)`. The supplier MUST complete a signed non-hazardous declaration confirming no RoHS/REACH SVHC substances are hidden under the CBI trade secret.

### 5. RoHS Annex III/IV Exemptions
- Exemption codes (e.g. `6(c)` for copper alloys with up to 4% lead; `7(a)` for high-temp solders up to 85% lead; `7(c)-I` for lead in dielectric ceramics).
- When a substance (e.g. Lead CAS 7439-92-1) exceeds 0.1% (1000 ppm) but has a valid exemption selected, the evaluation becomes `Approved` with a badge (`⚖️ Exemption: 6(c)`) instead of `Blocked`.

### 6. Zero-Burden Retrospective BOM Sweeping
- When regulations update (e.g., ECHA publishes a new SVHC batch), the compliance engine sweeps all parts in the database in the background.
- Eliminates the need to send mass re-survey emails to suppliers when existing FMD data already contains the disclosed chemistry.

### 7. Smart AI Document & Format Routing
- Supports standard Excel (`.xlsx`, `.csv`), non-standard spreadsheets (unstructured layouts auto-mapped by AI), and PDF laboratory test reports (SGS/TÜV) or raw MSDS files.
- Extracted data is presented in an interactive modal for human verification before committing to the database.

---

## 5. Database Schema & Data Models (`fmd_core/models.py`)

1. **`Supplier`**:
   - `supplier_code` (e.g., `SUP-TI-001`, `SUP-LUX-001`)
   - `name`, `contact_email`, `quality_score`, `is_active`
2. **`SupplierPart`**:
   - `supplier` (FK to `Supplier`)
   - `part_number` (Internal Part Number, e.g. `IPN-IC-555`, `IPN-CBL-001`)
   - `part_name`, `fmd_tier` (`Full FMD`, `Partial FMD`, `RoHS Only`)
   - `rohs_status`, `reach_status`, `pfas_status`, `overall_status`
   - `raw_csv`, `cbi_attested`, `updated_at`
3. **`PartRevision`**:
   - `part` (FK to `SupplierPart`, `related_name='revisions'`)
   - `revision_number` (1, 2, 3...)
   - `file_name`, `fmd_tier`, `overall_status`, `rohs_status`, `reach_status`, `pfas_status`
   - `cbi_detected`, `cbi_attested`
   - `snapshot_data` (JSON tree of complete composition and evaluations)
   - `raw_csv`, `change_summary`, `created_at`
4. **`HomogeneousMaterial`**:
   - `part` (FK to `SupplierPart`, `related_name='materials'`)
   - `material_id` (e.g. `M-01`), `name`, `mass_g`, `total_concentration_pct`, `mass_balance_valid`
5. **`SubstanceDeclaration`**:
   - `material` (FK to `HomogeneousMaterial`, `related_name='substances'`)
   - `cas` (CAS Registry Number), `name`
   - `concentration_pct`, `concentration_ppm`
   - `pfas_intentional_use`, `evidence_status`, `exemption`
   - `rohs_eval`, `reach_eval`, `pfas_eval`, `action_required`
6. **`RegulatoryRule`**:
   - `regulation` (`EU RoHS`, `REACH SVHC`, `PFAS`, `Taiwan RoHS`)
   - `cas`, `substance_name`, `threshold_pct`, `threshold_ppm`, `is_active`
7. **`ReviewTask`**:
   - `part` (FK to `SupplierPart`), `material`, `title`, `severity`, `remediation_instruction`, `is_resolved`
8. **`RegulatorySyncLog`**:
   - `timestamp`, `triggered_by`, `rules_checked`, `rules_updated`, `parts_revaluated`, `parts_impacted`, `status`, `details`

---

## 6. Real-World Benchmark Test Samples (`test_samples/`)

The system includes 4 authentic manufacturer test files:
1. `TI_NE555DR_Material_Declaration.xlsx` (Part `IPN-IC-555`, Supplier `SUP-TI-001`)
2. `Murata_GRM155R71C104KA88D_Chemical_Data.xlsx` (Part `IPN-CAP-104`, Supplier `SUP-MUR-001`)
3. `ADI_LTM4618_Material_Declaration.pdf` (Part `IPN-PMIC-4618`, Supplier `SUP-ADI-001`)
4. `TE_Connectivity_MicroFit_RoHS_Report.pdf` (Part `IPN-CONN-282`, Supplier `SUP-TE-001`)

---

## 7. Migration Guide to a New Computer

When transferring this project to a new computer:

### Step 1: Copy Project Folder
Copy the entire `FMD` directory (including `db.sqlite3` and `test_samples/`) to the new PC. You can exclude the `.venv` folder to save size.

### Step 2: Set Up Python Virtual Environment
On the new machine:
```bash
# Navigate to project directory
cd FMD

# Create virtual environment
python -m venv .venv

# Activate environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Install all required packages
pip install -r requirements.txt
```

### Step 3: Run Database Migrations (if needed)
```bash
python manage.py migrate
```

### Step 4: Start Django Server
```bash
python manage.py runserver 127.0.0.1:8008
```

### Step 5: Test Execution
Verify that everything is operational by running:
```bash
python -c "import urllib.request; print('Server HTTP:', urllib.request.urlopen('http://127.0.0.1:8008/').status)"
```
