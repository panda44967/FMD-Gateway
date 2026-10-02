import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fmd_server.settings')
django.setup()

from rest_framework.test import APIRequestFactory
from fmd_core.views import AiDocumentExtractView, AiDocumentCommitView
from fmd_core.models import SupplierPart, HomogeneousMaterial, SubstanceDeclaration
from fmd_core.ai_parser import extract_metadata_and_type, get_demo_extraction

factory = APIRequestFactory()

def run_tests():
    print("=== 1. Testing AI Parsing: SGS RoHS Test Report ===")
    extract_req = factory.post('/api/fmd/ai-extract/', {'demo_type': 'sgs_rohs', 'part_number': 'IPN-CONN-002'}, format='json')
    extract_res = AiDocumentExtractView.as_view()(extract_req)
    assert extract_res.status_code == 200, f"Extraction failed: {extract_res.data}"
    
    data = extract_res.data
    meta = data['metadata']
    print(f"Document Type: {data['document_type']}")
    print(f"Lab Name: {meta['lab_name']}, Report No: {meta['report_number']}")
    print(f"Freshness: {meta['freshness_badge']}, Age: {meta['age_days']} days (Is Fresh: {meta['is_fresh']})")
    assert meta['is_fresh'] == True, "SGS report should be verified fresh (< 365 days)"
    assert len(data['materials']) == 2, f"Expected 2 materials, got {len(data['materials'])}"

    print("\n=== 2. Testing AI Parsing: Polymer MSDS GHS Section 3 ===")
    msds_req = factory.post('/api/fmd/ai-extract/', {'demo_type': 'resin_msds', 'part_number': 'IPN-CONN-002'}, format='json')
    msds_res = AiDocumentExtractView.as_view()(msds_req)
    assert msds_res.status_code == 200
    msds_data = msds_res.data
    print(f"Document Type: {msds_data['document_type']}")
    print(f"Issuer: {msds_data['metadata']['lab_name']}")
    substances = msds_data['materials'][0]['substances']
    print(f"Extracted Substances: {[s['name'] + ' (' + s['cas'] + '): ' + str(s['concentration_pct']) + '%' for s in substances]}")
    assert any('CBI' in s['cas'] for s in substances), "MSDS should detect 3% CBI additive"

    print("\n=== 3. Testing Freshness Expiration Logic ===")
    # Test date older than 365 days
    old_raw = "SGS Report No: CANEC2300000001 Date: 2024-01-15 Test Report for Electronic Components"
    old_meta = extract_metadata_and_type(old_raw)
    print(f"Old report issue date: {old_meta['issue_date']}, Age: {old_meta['age_days']} days, Is Fresh: {old_meta['is_fresh']}")
    assert old_meta['is_fresh'] == False, "2024 report must be flagged as Expired (> 365 days)"

    print("\n=== 4. Testing Commit of Verified AI Extraction to SupplierPart ===")
    commit_req = factory.post('/api/fmd/ai-commit/', {'part_number': 'IPN-CONN-002', 'extraction_data': data}, format='json')
    commit_res = AiDocumentCommitView.as_view()(commit_req)
    assert commit_res.status_code == 200, f"Commit failed: {commit_res.data}"

    part = SupplierPart.objects.get(part_number='IPN-CONN-002')
    print(f"Part updated: {part.part_number}, Overall Status: {part.overall_status}, RoHS: {part.rohs_status}")
    print(f"Materials saved: {part.materials.count()}, Total substances: {SubstanceDeclaration.objects.filter(material__part=part).count()}")
    assert part.materials.count() == 2
    assert part.overall_status == 'Approved'

    print("\n>>> ALL AI DOCUMENT EXTRACTION & VERIFICATION TESTS PASSED! <<<")

if __name__ == '__main__':
    run_tests()
