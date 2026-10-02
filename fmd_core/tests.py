from django.test import TestCase
from rest_framework.test import APIClient
from .models import SupplierPart, HomogeneousMaterial, SubstanceDeclaration, RegulatoryRule, ReviewTask, PartRevision

SAMPLE_CSV = """part_number,fmd_tier,material_id,material_name,material_mass_g,cas,concentration_pct,pfas_intentional_use,evidence_status
CBL-USB4-01,Partial FMD,M-01,Cable jacket,8.3,9002-84-0,99.3,Unknown,None
CBL-USB4-01,Partial FMD,M-02,Copper conductor,12.4,7440-50-8,99.9,No,Test report
CBL-USB4-01,Partial FMD,M-03,Solder joint,0.5,7439-92-1,0.35,No,Supplier declaration
CBL-USB4-01,Partial FMD,M-03,Solder joint,0.5,7440-31-5,99.65,No,Supplier declaration
"""

CBI_SAMPLE_CSV = """part_number,fmd_tier,material_id,material_name,material_mass_g,cas,concentration_pct,pfas_intentional_use,evidence_status
CBL-CBI-TEST,Full FMD,M-01,Proprietary Resin,5.0,9002-88-4,92.5,No,Test report
CBL-CBI-TEST,Full FMD,M-01,Proprietary Resin,5.0,CBI-SYSTEM,7.5,No,Supplier declaration
"""

EXEMPTION_SAMPLE_CSV = """part_number,fmd_tier,material_id,material_name,material_mass_g,cas,concentration_pct,pfas_intentional_use,evidence_status,exemption
CONN-BRASS-01,Full FMD,M-01,Machined Brass Contact,1.2,7440-50-8,96.5,No,Test report,None
CONN-BRASS-01,Full FMD,M-01,Machined Brass Contact,1.2,7439-92-1,3.5,No,Supplier declaration,6(c)
"""

class FmdComplianceTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Initialize default regulatory baseline rules
        RegulatoryRule.objects.create(
            regulation='EU RoHS', version='2026.09', substance_name='Lead',
            cas='7439-92-1', threshold_pct=0.1, is_svhc=True
        )
        RegulatoryRule.objects.create(
            regulation='REACH SVHC', version='2026.09', substance_name='Lead',
            cas='7439-92-1', threshold_pct=0.1, is_svhc=True
        )
        RegulatoryRule.objects.create(
            regulation='PFAS', version='2026.09', substance_name='PTFE',
            cas='9002-84-0', is_pfas=True
        )

    def test_fmd_upload_and_evaluation(self):
        """Test standard FMD CSV parsing, mass-balance validation, and regulatory verdict determination."""
        response = self.client.post('/api/fmd/upload/', {'csv_text': SAMPLE_CSV}, format='json')
        self.assertEqual(response.status_code, 201)
        
        part = SupplierPart.objects.get(part_number='CBL-USB4-01')
        self.assertEqual(part.fmd_tier, 'Partial FMD')
        self.assertEqual(part.rohs_status, 'Blocked')      # Lead 0.35% > 0.1% without exemption
        self.assertEqual(part.reach_status, 'Review')      # Lead 0.35% > 0.1% SVHC trigger
        self.assertEqual(part.pfas_status, 'Data gap')     # PTFE unknown use & no evidence
        self.assertEqual(part.overall_status, 'Blocked')   # Worst-case verdict rule

        # Verify review remediation tasks generation
        tasks = ReviewTask.objects.filter(part=part)
        self.assertTrue(tasks.filter(severity='blocked').exists())
        self.assertTrue(tasks.filter(severity='review').exists())
        self.assertTrue(tasks.filter(severity='data-gap').exists())

    def test_dynamic_reevaluation_when_rule_changes(self):
        """Test zero-burden retrospective BOM re-screening upon regulatory updates."""
        self.client.post('/api/fmd/upload/', {'csv_text': SAMPLE_CSV}, format='json')
        part = SupplierPart.objects.get(part_number='CBL-USB4-01')

        # Simulate regulatory update: Add Copper (7440-50-8) as restricted substance
        RegulatoryRule.objects.create(
            regulation='EU RoHS', version='2026.10-DRAFT', substance_name='Copper',
            cas='7440-50-8', threshold_pct=50.0
        )

        res = self.client.post('/api/regulations/reevaluate/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('summary', res.data)
        self.assertEqual(res.data['summary']['total_evaluated'], 1)

        # Confirm retrospective creation of Copper exceedance task
        new_tasks = ReviewTask.objects.filter(part=part, title__contains='Copper')
        self.assertTrue(new_tasks.exists())

    def test_cbi_foolproof_locking_and_attestation(self):
        """Test CBI 7.5% detection, submission locking, and legal attestation resolution."""
        # 1. Upload without attestation -> overall_status is Data gap due to missing mandatory legal sign-off
        res1 = self.client.post('/api/fmd/upload/', {'csv_text': CBI_SAMPLE_CSV, 'cbi_attested': 'false'}, format='json')
        self.assertEqual(res1.status_code, 201)
        part = SupplierPart.objects.get(part_number='CBL-CBI-TEST')
        self.assertEqual(part.overall_status, 'Data gap')

        # 2. Upload with verified corporate attestation -> Conditional release under review
        res2 = self.client.post('/api/fmd/upload/', {'csv_text': CBI_SAMPLE_CSV, 'cbi_attested': 'true'}, format='json')
        self.assertEqual(res2.status_code, 201)
        part.refresh_from_db()
        self.assertEqual(part.overall_status, 'Review')
        self.assertTrue(part.cbi_attested)

    def test_multi_revision_lifecycle_preservation(self):
        """Test non-destructive revision lineage where previous submissions are preserved in PartRevision."""
        # Submit Rev 1
        res1 = self.client.post('/api/fmd/upload/', {'csv_text': SAMPLE_CSV}, format='json')
        self.assertEqual(res1.status_code, 201)
        part = SupplierPart.objects.get(part_number='CBL-USB4-01')
        self.assertEqual(part.revisions.count(), 1)
        rev1 = part.revisions.first()
        self.assertEqual(rev1.revision_number, 1)

        # Submit Rev 2 (Revised formulation)
        res2 = self.client.post('/api/fmd/upload/', {'csv_text': SAMPLE_CSV}, format='json')
        self.assertEqual(res2.status_code, 201)
        part.refresh_from_db()
        self.assertEqual(part.revisions.count(), 2)
        all_rev_numbers = list(part.revisions.values_list('revision_number', flat=True))
        self.assertIn(1, all_rev_numbers)
        self.assertIn(2, all_rev_numbers)

    def test_rohs_annex_iii_exemptions(self):
        """Test RoHS Annex III Exemption 6(c) allowing Lead up to 4% in copper alloys without Blocking."""
        res = self.client.post('/api/fmd/upload/', {'csv_text': EXEMPTION_SAMPLE_CSV}, format='json')
        self.assertEqual(res.status_code, 201)
        part = SupplierPart.objects.get(part_number='CONN-BRASS-01')
        # Exemption 6(c) claimed for 3.5% Lead -> RoHS status is Approved instead of Blocked
        self.assertEqual(part.rohs_status, 'Approved')
