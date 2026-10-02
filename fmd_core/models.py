from django.db import models

class Supplier(models.Model):
    supplier_code = models.CharField('Supplier Code', max_length=64, unique=True)
    name = models.CharField('Supplier Name', max_length=255)
    contact_email = models.EmailField('Contact Email', blank=True, null=True)
    quality_score = models.FloatField('Data Quality Score', default=100.0)
    created_at = models.DateTimeField('Created At', auto_now_add=True)

    class Meta:
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'

    def __str__(self):
        return f"{self.name} ({self.supplier_code})"


class SupplierPart(models.Model):
    TIER_CHOICES = [
        ('Full FMD', 'Full FMD'),
        ('Partial FMD', 'Partial FMD'),
        ('Restricted-substance declaration', 'Restricted-substance declaration'),
        ('Evidence only', 'Evidence only'),
    ]

    STATUS_CHOICES = [
        ('Approved', 'Approved (Compliant)'),
        ('Blocked', 'Blocked (Non-compliant)'),
        ('Data gap', 'Data gap (Incomplete chemistry)'),
        ('Review', 'Review (SCIP / Human verification)'),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='parts', verbose_name='Supplier')
    part_number = models.CharField('Part Number', max_length=128, unique=True, db_index=True)
    part_name = models.CharField('Part Description', max_length=255, blank=True)
    fmd_tier = models.CharField('Declaration Tier', max_length=64, choices=TIER_CHOICES, default='Partial FMD')

    rohs_status = models.CharField('EU RoHS Status', max_length=32, choices=STATUS_CHOICES, default='Data gap')
    reach_status = models.CharField('REACH SVHC Status', max_length=32, choices=STATUS_CHOICES, default='Data gap')
    pfas_status = models.CharField('PFAS Status', max_length=32, choices=STATUS_CHOICES, default='Data gap')
    overall_status = models.CharField('Overall Verdict', max_length=32, choices=STATUS_CHOICES, default='Data gap')

    raw_csv = models.TextField('Original CSV Content', blank=True)
    cbi_attested = models.BooleanField('CBI Non-Hazardous Attested', default=False)
    updated_at = models.DateTimeField('Last Updated', auto_now=True)

    class Meta:
        verbose_name = 'Supplier Part'
        verbose_name_plural = 'Supplier Parts'

    def __str__(self):
        return f"{self.part_number} [{self.overall_status}]"


class PartRevision(models.Model):
    part = models.ForeignKey(SupplierPart, on_delete=models.CASCADE, related_name='revisions', verbose_name='Parent Part')
    revision_number = models.PositiveIntegerField('Revision Number', default=1)
    file_name = models.CharField('Uploaded File Name', max_length=255, blank=True)
    fmd_tier = models.CharField('Declaration Tier', max_length=64, default='Full FMD')
    overall_status = models.CharField('Overall Verdict', max_length=32, default='Data gap')
    rohs_status = models.CharField('RoHS Status', max_length=32, default='Data gap')
    reach_status = models.CharField('REACH Status', max_length=32, default='Data gap')
    pfas_status = models.CharField('PFAS Status', max_length=32, default='Data gap')
    cbi_detected = models.BooleanField('CBI Detected', default=False)
    cbi_attested = models.BooleanField('CBI Attested', default=False)
    snapshot_data = models.JSONField('Composition Snapshot JSON', default=dict)
    raw_csv = models.TextField('Raw File Content', blank=True)
    change_summary = models.TextField('Revision Notes / Reason', blank=True)
    created_at = models.DateTimeField('Submitted At', auto_now_add=True)

    class Meta:
        verbose_name = 'Part Revision'
        verbose_name_plural = 'Part Revisions'
        ordering = ['-revision_number']

    def __str__(self):
        return f"{self.part.part_number} - Rev {self.revision_number} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class HomogeneousMaterial(models.Model):
    part = models.ForeignKey(SupplierPart, on_delete=models.CASCADE, related_name='materials', verbose_name='Parent Part')
    material_id = models.CharField('Material ID', max_length=64)
    name = models.CharField('Material Name', max_length=255)
    mass_g = models.FloatField('Material Mass (g)', default=0.0)
    total_concentration_pct = models.FloatField('Total Disclosed Conc. (%)', default=0.0)
    mass_balance_valid = models.BooleanField('Mass Balance Valid (98%-102%)', default=False)

    class Meta:
        verbose_name = 'Homogeneous Material'
        verbose_name_plural = 'Homogeneous Materials'
        unique_together = ('part', 'material_id')

    def __str__(self):
        return f"{self.part.part_number} - {self.name} ({self.material_id})"


class SubstanceDeclaration(models.Model):
    material = models.ForeignKey(HomogeneousMaterial, on_delete=models.CASCADE, related_name='substances', verbose_name='Parent Material')
    cas = models.CharField('CAS Number', max_length=32, db_index=True)
    name = models.CharField('Substance Name', max_length=255, blank=True)
    concentration_pct = models.FloatField('Disclosed Conc. (%)')
    concentration_ppm = models.FloatField('Calculated Conc. (ppm)', default=0.0)
    pfas_intentional_use = models.CharField('PFAS Intentional Use', max_length=32, default='Unknown')
    evidence_status = models.CharField('Evidence Document Status', max_length=64, default='None')
    exemption = models.CharField('RoHS Exemption', max_length=32, default='None', blank=True)

    rohs_eval = models.CharField('EU RoHS Verdict', max_length=32, default='Approved')
    reach_eval = models.CharField('REACH SVHC Verdict', max_length=32, default='Approved')
    pfas_eval = models.CharField('PFAS Verdict', max_length=32, default='Approved')
    action_required = models.TextField('Actionable Instruction', blank=True)

    class Meta:
        verbose_name = 'Substance Declaration'
        verbose_name_plural = 'Substance Declarations'

    def save(self, *args, **kwargs):
        if self.concentration_pct is not None:
            self.concentration_ppm = self.concentration_pct * 10000.0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cas} ({self.name}) - {self.concentration_pct}%"


class RegulatoryRule(models.Model):
    REGULATION_CHOICES = [
        ('EU RoHS', 'EU RoHS Directive 2011/65/EU'),
        ('REACH SVHC', 'EU REACH Candidate List (SVHC)'),
        ('PFAS', 'PFAS Universal / Group Restrictions'),
        ('Taiwan RoHS', 'Taiwan RoHS (CNS 15663 / BSMI)'),
        ('TSCA', 'US EPA TSCA (Section 6/8)'),
        ('China RoHS', 'China RoHS (SJ/T 11364)'),
        ('Prop 65', 'California Proposition 65'),
    ]

    regulation = models.CharField('Regulation', max_length=64, choices=REGULATION_CHOICES)
    version = models.CharField('Rule Version', max_length=64, default='2026.09')
    substance_name = models.CharField('Substance Name', max_length=255)
    cas = models.CharField('CAS Number', max_length=32, db_index=True)
    threshold_pct = models.FloatField('Threshold Limit (%)', null=True, blank=True)
    is_svhc = models.BooleanField('Is REACH SVHC', default=False)
    is_pfas = models.BooleanField('Is PFAS', default=False)
    exemption_code = models.CharField('Applicable Exemption Code', max_length=64, blank=True)
    effective_date = models.DateField('Effective Date', null=True, blank=True)
    source_url = models.CharField('Official Source URL', max_length=512, blank=True)
    notes = models.TextField('Legal Citations / Regulatory Notes', blank=True)
    is_active = models.BooleanField('Is Active', default=True)

    class Meta:
        verbose_name = 'Regulatory Rule'
        verbose_name_plural = 'Regulatory Rules'

    def __str__(self):
        return f"[{self.regulation} {self.version}] {self.substance_name} ({self.cas})"


class ReviewTask(models.Model):
    SEVERITY_CHOICES = [
        ('blocked', 'Blocked (Critical Exceedance)'),
        ('data-gap', 'Data Gap (Missing Chemistry / Evidence)'),
        ('review', 'Review (SCIP / Article Threshold)'),
    ]

    part = models.ForeignKey(SupplierPart, on_delete=models.CASCADE, related_name='review_tasks', verbose_name='Associated Part')
    material = models.ForeignKey(HomogeneousMaterial, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Associated Material')
    title = models.CharField('Task Title', max_length=255)
    severity = models.CharField('Severity', max_length=32, choices=SEVERITY_CHOICES, default='data-gap')
    remediation_instruction = models.TextField('Actionable Remediation Instruction')
    is_resolved = models.BooleanField('Is Resolved', default=False)
    created_at = models.DateTimeField('Created At', auto_now_add=True)

    class Meta:
        verbose_name = 'Review Task'
        verbose_name_plural = 'Review Tasks'

    def __str__(self):
        return f"[{self.severity}] {self.title} ({self.part.part_number})"


class RegulatorySyncLog(models.Model):
    timestamp = models.DateTimeField('Execution Timestamp', auto_now_add=True)
    triggered_by = models.CharField('Triggered By', max_length=64, default='Scheduler') # 'Scheduler', 'Manual (Admin)', 'API'
    source_name = models.CharField('Authority / Feed Source', max_length=128, default='ECHA / IEC 62474 / Global Feeds')
    rules_checked = models.IntegerField('Rules Checked', default=0)
    rules_updated = models.IntegerField('Rules Updated / Added', default=0)
    parts_revaluated = models.IntegerField('Parts Re-evaluated', default=0)
    parts_impacted = models.IntegerField('Parts Impacted', default=0)
    details = models.JSONField('Structured Audit Details', default=dict, blank=True)
    status = models.CharField('Sync Status', max_length=32, default='Success')

    class Meta:
        verbose_name = 'Regulatory Sync Log'
        verbose_name_plural = 'Regulatory Sync Logs'
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.source_name} - {self.status} ({self.parts_impacted} impacted)"
