import re
from .models import SupplierPart, HomogeneousMaterial, SubstanceDeclaration, RegulatoryRule, ReviewTask

CAS_REGEX = re.compile(r'^\d{2,7}-\d{2}-\d$')

def verify_cas_checksum(cas_str: str) -> bool:
    """
    Validates official CAS Registry Number check digit:
    The last digit C must equal (sum(i * d_i)) mod 10 from right to left.
    """
    digits = [int(c) for c in (cas_str or '') if c.isdigit()]
    if len(digits) < 4:
        return False
    check_digit = digits[-1]
    weight_digits = digits[:-1]
    total = sum((i + 1) * d for i, d in enumerate(reversed(weight_digits)))
    return (total % 10) == check_digit

def is_cbi_substance(cas_str, name_str=""):
    """
    Identifies if a declared substance is a confidential / proprietary trade secret.
    """
    c = (cas_str or "").strip().lower()
    n = (name_str or "").strip().lower()
    cbi_keywords = ['cbi', 'proprietary', 'trade secret', 'confidential', 'not to declare', 'misc-system', 'secret']
    return any(k in c for k in cbi_keywords) or any(k in n for k in cbi_keywords)

def evaluate_part(part: SupplierPart, cbi_attested: bool = None):
    """
    Deterministic Compliance Rule Engine with 5%/10% CBI Tolerance:
    1. Evaluates homogeneous material mass balance (% w/w).
    2. Enforces 5%/10% CBI rules:
       - < 5% CBI: Full FMD standard release.
       - 5% - 10% CBI: Conditional release if CBI Non-Hazardous Attestation is executed.
       - > 10% CBI: Data Gap rejection (exceeds allowable tolerance).
    3. Matches active RegulatoryRule records from database for RoHS, REACH SVHC, PFAS.
    4. Generates actionable, structured ReviewTask entries for supplier remediation.
    """
    if cbi_attested is None:
        cbi_attested = getattr(part, 'cbi_attested', False)
    else:
        part.cbi_attested = cbi_attested
    active_rules = RegulatoryRule.objects.filter(is_active=True)
    rules_by_cas = {}
    for r in active_rules:
        rules_by_cas.setdefault(r.cas.strip(), []).append(r)

    # Clear unresolved previous tasks for this part
    part.review_tasks.all().delete()

    any_blocked = False
    any_data_gap = False
    any_review = False

    materials = part.materials.all()

    for mat in materials:
        substances = mat.substances.all()
        
        explicit_pct = sum(s.concentration_pct for s in substances if not is_cbi_substance(s.cas, s.name))
        cbi_pct = sum(s.concentration_pct for s in substances if is_cbi_substance(s.cas, s.name))
        total_pct = explicit_pct + cbi_pct
        mat.total_concentration_pct = round(total_pct, 3)

        # 1. Mass Balance Tolerance Check (98.0% - 102.0% w/w)
        if total_pct < 98.0 or total_pct > 102.0:
            mat.mass_balance_valid = False
            any_data_gap = True
            ReviewTask.objects.create(
                part=part,
                material=mat,
                title=f"{mat.name} — Mass balance deficit ({mat.total_concentration_pct}%)",
                severity='data-gap',
                remediation_instruction=f"Homogeneous material {mat.name} ({mat.material_id}) total disclosed concentration is {mat.total_concentration_pct}%, outside the 98.0%–102.0% mass-balance tolerance. Supplier must declare full formulation."
            )
        else:
            # 2. CBI / Proprietary Chemistry Tolerance Evaluation
            if cbi_pct > 10.0:
                mat.mass_balance_valid = False
                any_data_gap = True
                ReviewTask.objects.create(
                    part=part,
                    material=mat,
                    title=f"{mat.name} — Excessive proprietary/CBI chemistry ({round(cbi_pct, 1)}%)",
                    severity='data-gap',
                    remediation_instruction=f"Proprietary/CBI chemistry in {mat.name} ({round(cbi_pct, 1)}%) exceeds the 10.0% international tolerance limit. Supplier must disclose explicit CAS numbers or provide an accredited SGS/TUV lab test report."
                )
            elif 5.0 <= cbi_pct <= 10.0:
                if cbi_attested:
                    mat.mass_balance_valid = True
                    any_review = True
                    ReviewTask.objects.create(
                        part=part,
                        material=mat,
                        title=f"{mat.name} — Approved under CBI allowance ({round(cbi_pct, 1)}%)",
                        severity='review',
                        remediation_instruction=f"Material contains {round(cbi_pct, 1)}% proprietary chemistry within the 10.0% allowance, certified non-hazardous via supplier CBI attestation. Released under Conditional Approval."
                    )
                else:
                    mat.mass_balance_valid = False
                    any_data_gap = True
                    ReviewTask.objects.create(
                        part=part,
                        material=mat,
                        title=f"{mat.name} — Mandatory CBI attestation required ({round(cbi_pct, 1)}%)",
                        severity='data-gap',
                        remediation_instruction=f"Material contains {round(cbi_pct, 1)}% proprietary chemistry. Supplier must execute the mandatory CBI Non-Hazardous Legal Attestation before this material can be approved."
                    )
            else:
                # cbi_pct < 5.0%: Standard Full FMD pass
                mat.mass_balance_valid = True

        mat.save()

        # Evaluate each substance row
        for sub in substances:
            cas = sub.cas.strip()
            pct = sub.concentration_pct

            # If identified as valid CBI / Proprietary substance
            if is_cbi_substance(cas, sub.name):
                sub.rohs_eval = 'Approved'
                sub.reach_eval = 'Approved'
                sub.pfas_eval = 'Approved'
                sub.action_required = f"Proprietary ingredient ({round(pct, 2)}%) covered by CBI trade secret policy"
                sub.save()
                continue

            rules = rules_by_cas.get(cas, [])
            rohs_res = 'Approved'
            reach_res = 'Approved'
            pfas_res = 'Approved'
            actions = []

            # Syntax & Evidence Validation (Format + Mathematical Checksum)
            has_valid_format = bool(CAS_REGEX.match(cas))
            has_valid_checksum = verify_cas_checksum(cas) if has_valid_format else False
            is_valid_cas = has_valid_format and has_valid_checksum
            has_evidence = sub.evidence_status and sub.evidence_status.lower() != 'none'

            if not is_valid_cas or not has_evidence:
                rohs_res = reach_res = pfas_res = 'Data gap'
                any_data_gap = True
                
                if has_valid_format and not has_valid_checksum:
                    err_msg = f"CAS [{cas}] failed mathematical check digit validation (probable typo in digits)"
                elif not has_valid_format:
                    err_msg = f"CAS [{cas}] format is invalid"
                else:
                    err_msg = f"Missing required evidence document (current: {sub.evidence_status})"
                    
                actions.append(err_msg)
                ReviewTask.objects.create(
                    part=part,
                    material=mat,
                    title=f"{mat.name} — Substance validation error ({cas})",
                    severity='data-gap',
                    remediation_instruction=f"{err_msg}. Provide verified CAS and attach laboratory test report or SDS."
                )

            # Match against active regulatory rules
            for rule in rules:
                # 1. EU RoHS Check with Annex III Exemption Handling
                if rule.regulation == 'EU RoHS' and rule.threshold_pct is not None:
                    if pct > rule.threshold_pct:
                        ex_raw = getattr(sub, 'exemption', 'None') or 'None'
                        ex_clean = ex_raw.strip()
                        ex_key = ex_clean.lower().replace(' ', '').replace('–', '-').replace('—', '-')

                        # Evaluate Standard RoHS Annex III Exemptions
                        if ex_key in ['6(c)', '6c']:
                            # Copper alloy containing up to 4.0% lead by weight
                            if pct <= 4.0:
                                rohs_res = 'Approved'
                                act_msg = f"RoHS compliant under Exemption 6(c) (Lead in copper alloy: {pct}% <= 4.0%)"
                                actions.append(act_msg)
                                any_review = True
                                ReviewTask.objects.create(
                                    part=part,
                                    material=mat,
                                    title=f"{mat.name} — RoHS Exemption 6(c) applied ({pct}% Pb in copper alloy)",
                                    severity='review',
                                    remediation_instruction=f"Exemption 6(c) claimed for Lead ({pct}% <= 4.0% w/w in copper alloy). Verify alloy specification and fulfill SCIP notification obligations."
                                )
                            else:
                                rohs_res = 'Blocked'
                                any_blocked = True
                                act_msg = f"RoHS Lead {pct}% exceeds maximum 4.0% allowable limit under Exemption 6(c)"
                                actions.append(act_msg)
                                ReviewTask.objects.create(
                                    part=part,
                                    material=mat,
                                    title=f"{mat.name} — Exemption 6(c) limit exceeded ({pct}% Pb > 4.0%)",
                                    severity='blocked',
                                    remediation_instruction=f"Concentration {pct}% exceeds the 4.0% maximum allowable lead limit in copper alloys under RoHS Exemption 6(c)."
                                )
                        elif ex_key in ['7(a)', '7a', '7(a)-i', '7(a)-ii', '7(a)-iii', '7(a)-iv']:
                            # High melting temperature solders (>= 85% Lead)
                            if pct >= 85.0:
                                rohs_res = 'Approved'
                                act_msg = f"RoHS compliant under Exemption 7(a) (High-temperature solder: {pct}% Pb >= 85%)"
                                actions.append(act_msg)
                                any_review = True
                                ReviewTask.objects.create(
                                    part=part,
                                    material=mat,
                                    title=f"{mat.name} — RoHS Exemption 7(a) applied ({pct}% Pb in high-melt solder)",
                                    severity='review',
                                    remediation_instruction=f"Exemption 7(a) claimed for high melting temperature solder ({pct}% Pb >= 85%). Verify application is internal die-attach or high-temp interconnection."
                                )
                            else:
                                rohs_res = 'Blocked'
                                any_blocked = True
                                act_msg = f"RoHS Exemption 7(a) requires high-melting solder with >= 85% Lead (current: {pct}%)"
                                actions.append(act_msg)
                                ReviewTask.objects.create(
                                    part=part,
                                    material=mat,
                                    title=f"{mat.name} — Exemption 7(a) formulation invalid ({pct}% Pb < 85%)",
                                    severity='blocked',
                                    remediation_instruction=f"RoHS Exemption 7(a) strictly requires high-temperature solder with >= 85% Lead. Current concentration is {pct}%."
                                )
                        elif ex_key in ['7(c)-i', '7(c)-1', '7(c)i', '7c-1', '7c-i', '7(c)']:
                            # Lead in glass or ceramic matrix (resistors, piezos, diodes)
                            rohs_res = 'Approved'
                            act_msg = f"RoHS compliant under Exemption 7(c)-I (Lead in glass/ceramic matrix: {pct}%)"
                            actions.append(act_msg)
                            any_review = True
                            ReviewTask.objects.create(
                                part=part,
                                material=mat,
                                title=f"{mat.name} — RoHS Exemption 7(c)-I applied ({pct}% Pb in glass/ceramic)",
                                severity='review',
                                remediation_instruction=f"Exemption 7(c)-I claimed for Lead ({pct}%) in glass or ceramic matrix (e.g. chip resistor glaze, piezoelectric). Monitor EU renewal status."
                            )
                        elif ex_key in ['7(c)-ii', '7(c)-2', '7(c)ii', '7c-2', '7c-ii']:
                            # Lead in dielectric ceramic in capacitors (>= 125 V AC / >= 250 V DC)
                            rohs_res = 'Approved'
                            act_msg = f"RoHS compliant under Exemption 7(c)-II (Lead in capacitor dielectric: {pct}%)"
                            actions.append(act_msg)
                            any_review = True
                            ReviewTask.objects.create(
                                part=part,
                                material=mat,
                                title=f"{mat.name} — RoHS Exemption 7(c)-II applied ({pct}% Pb in capacitor dielectric)",
                                severity='review',
                                remediation_instruction=f"Exemption 7(c)-II claimed for Lead in capacitor dielectric ceramic. Ensure rated voltage is >= 125 V AC or >= 250 V DC."
                            )
                        elif ex_key in ['6(a)', '6a', '6(a)-i', '6(a)-ii']:
                            # Lead in steel alloys (up to 0.35%)
                            if pct <= 0.35:
                                rohs_res = 'Approved'
                                act_msg = f"RoHS compliant under Exemption 6(a) (Lead in steel alloy: {pct}% <= 0.35%)"
                                actions.append(act_msg)
                                any_review = True
                                ReviewTask.objects.create(
                                    part=part,
                                    material=mat,
                                    title=f"{mat.name} — RoHS Exemption 6(a) applied ({pct}% Pb in steel)",
                                    severity='review',
                                    remediation_instruction=f"Exemption 6(a) claimed for Lead in steel ({pct}% <= 0.35% w/w). Confirm steel machining alloy grade."
                                )
                            else:
                                rohs_res = 'Blocked'
                                any_blocked = True
                                act_msg = f"RoHS Lead {pct}% exceeds maximum 0.35% allowable limit under Exemption 6(a)"
                                actions.append(act_msg)
                                ReviewTask.objects.create(
                                    part=part,
                                    material=mat,
                                    title=f"{mat.name} — Exemption 6(a) limit exceeded ({pct}% Pb > 0.35%)",
                                    severity='blocked',
                                    remediation_instruction=f"Concentration {pct}% exceeds the 0.35% maximum allowable lead limit in steel under RoHS Exemption 6(a)."
                                )
                        elif ex_key in ['6(b)', '6b', '6(b)-i', '6(b)-ii']:
                            # Lead in aluminium alloys (up to 0.4%)
                            if pct <= 0.4:
                                rohs_res = 'Approved'
                                act_msg = f"RoHS compliant under Exemption 6(b) (Lead in aluminium alloy: {pct}% <= 0.4%)"
                                actions.append(act_msg)
                                any_review = True
                                ReviewTask.objects.create(
                                    part=part,
                                    material=mat,
                                    title=f"{mat.name} — RoHS Exemption 6(b) applied ({pct}% Pb in aluminium)",
                                    severity='review',
                                    remediation_instruction=f"Exemption 6(b) claimed for Lead in aluminium ({pct}% <= 0.4% w/w). Confirm aluminum alloy grade."
                                )
                            else:
                                rohs_res = 'Blocked'
                                any_blocked = True
                                act_msg = f"RoHS Lead {pct}% exceeds maximum 0.4% allowable limit under Exemption 6(b)"
                                actions.append(act_msg)
                                ReviewTask.objects.create(
                                    part=part,
                                    material=mat,
                                    title=f"{mat.name} — Exemption 6(b) limit exceeded ({pct}% Pb > 0.4%)",
                                    severity='blocked',
                                    remediation_instruction=f"Concentration {pct}% exceeds the 0.4% maximum allowable lead limit in aluminium under RoHS Exemption 6(b)."
                                )
                        else:
                            # No exemption or unknown exemption
                            rohs_res = 'Blocked'
                            any_blocked = True
                            act_msg = f"RoHS {rule.substance_name} {pct}% exceeds threshold {rule.threshold_pct}% (Exemption: {ex_clean})"
                            actions.append(act_msg)
                            ReviewTask.objects.create(
                                part=part,
                                material=mat,
                                title=f"{mat.name} — RoHS threshold exceedance ({rule.substance_name})",
                                severity='blocked',
                                remediation_instruction=f"{rule.substance_name} (CAS: {cas}) concentration is {pct}%, exceeding EU RoHS limit of {rule.threshold_pct}%. Provide valid exemption claim (e.g. 6(c), 7(a), 7(c)-I) or substitute material."
                            )

                # 2. REACH SVHC Check
                if rule.is_svhc or rule.regulation == 'REACH SVHC':
                    if pct > 0.1:
                        reach_res = 'Review'
                        any_review = True
                        act_msg = f"REACH SVHC {rule.substance_name} {pct}% (>0.1% w/w)"
                        actions.append(act_msg)
                        ReviewTask.objects.create(
                            part=part,
                            material=mat,
                            title=f"{mat.name} — REACH SVHC communication & SCIP obligation ({rule.substance_name})",
                            severity='review',
                            remediation_instruction=f"Contains ECHA Candidate List substance {rule.substance_name} at {pct}% (>0.1% w/w). Verify article boundary and fulfill SCIP notification and supply chain communication obligations."
                        )

                # 3. PFAS Check
                if rule.is_pfas or rule.regulation == 'PFAS':
                    pfas_res = 'Data gap'
                    any_data_gap = True
                    act_msg = f"PFAS restricted substance {rule.substance_name}"
                    actions.append(act_msg)

            # PFAS Intentional-use check
            intentional = (sub.pfas_intentional_use or '').lower()
            if intentional in ['unknown', 'yes'] or pfas_res == 'Data gap':
                pfas_res = 'Data gap'
                any_data_gap = True
                ReviewTask.objects.create(
                    part=part,
                    material=mat,
                    title=f"{mat.name} — PFAS intentional-use inquiry & evidence gap",
                    severity='data-gap',
                    remediation_instruction=f"Material {mat.name} contains potential per/polyfluoroalkyl substances or intentional-use is '{sub.pfas_intentional_use}'. Supplier must declare specific functional use and submit Total Fluorine or PFAS test report."
                )

            sub.rohs_eval = rohs_res
            sub.reach_eval = reach_res
            sub.pfas_eval = pfas_res
            sub.action_required = "; ".join(actions) if actions else "Passed automated validation"
            sub.save()

    # Part-level compliance aggregation
    part.rohs_status = 'Blocked' if any_blocked else 'Approved'
    part.reach_status = 'Review' if any_review else 'Approved'
    part.pfas_status = 'Data gap' if any_data_gap else 'Approved'

    if any_blocked:
        part.overall_status = 'Blocked'
    elif any_data_gap or part.fmd_tier not in ['Full FMD', 'Partial FMD']:
        part.overall_status = 'Data gap'
    elif any_review:
        part.overall_status = 'Review'
    else:
        part.overall_status = 'Approved'

    part.save()
    return part


def reevaluate_all_parts():
    """
    Dynamic Re-evaluation Core Function:
    Batch re-screens all database parts against the latest active regulatory rules.
    Retains CBI attestation status and detects newly emerging compliance issues.
    """
    parts = SupplierPart.objects.all()
    impacted = []

    for part in parts:
        old_status = part.overall_status
        old_rohs = part.rohs_status
        old_reach = part.reach_status
        old_pfas = part.pfas_status

        evaluate_part(part, cbi_attested=part.cbi_attested)
        part.refresh_from_db()

        status_changed = (old_status != part.overall_status)
        sub_status_changed = (old_rohs != part.rohs_status or old_reach != part.reach_status or old_pfas != part.pfas_status)

        if status_changed or sub_status_changed:
            impacted.append({
                'part_number': part.part_number,
                'part_name': part.part_name,
                'supplier_name': part.supplier.name if part.supplier else 'Unknown',
                'old_status': old_status,
                'new_status': part.overall_status,
                'fmd_tier': part.fmd_tier,
                'tasks_count': part.review_tasks.count(),
                'latest_task': part.review_tasks.last().title if part.review_tasks.exists() else ''
            })

    return {
        'total_evaluated': parts.count(),
        'impacted_parts_count': len(impacted),
        'impacted_parts': impacted,
    }
