import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fmd_server.settings')
django.setup()

from rest_framework.test import APIRequestFactory
from fmd_core.views import FmdCsvUploadView, RegulatoryStatusView, RegulatorySyncView
from fmd_core.models import SupplierPart, RegulatoryRule, RegulatorySyncLog, ReviewTask

factory = APIRequestFactory()

def run_tests():
    print("=== 1. Ingesting 100% Compliant Sample (CBL-USBC-GREEN01) ===")
    with open('full-fmd-sample.csv', 'r', encoding='utf-8') as f:
        csv_text = f.read()

    req = factory.post('/api/fmd/upload/', {'csv_text': csv_text}, format='json')
    res = FmdCsvUploadView.as_view()(req)
    assert res.status_code == 201, f"Ingestion failed: {res.data}"
    
    part = SupplierPart.objects.get(part_number='CBL-USBC-GREEN01')
    print(f"Part ingested: {part.part_number}, Overall Status: {part.overall_status}")
    assert part.overall_status == 'Approved', f"Expected Approved, got {part.overall_status}"

    print("\n=== 2. Testing Regulatory Status Endpoint ===")
    status_req = factory.get('/api/regulations/status/')
    status_res = RegulatoryStatusView.as_view()(status_req)
    assert status_res.status_code == 200
    print(f"Active Rules: {status_res.data['total_active_rules']}")
    print(f"Frameworks tracked: {[r['regulation'] for r in status_res.data['regulations']]}")

    print("\n=== 3. Simulating ECHA Update (Adding Nickel to REACH SVHC) ===")
    sync_req = factory.post('/api/regulations/sync/', {'mode': 'simulate_reach_batch_update'}, format='json')
    sync_res = RegulatorySyncView.as_view()(sync_req)
    assert sync_res.status_code == 200, f"Sync failed: {sync_res.data}"
    print(f"Sync message: {sync_res.data['message']}")
    print(f"Impacted parts count: {sync_res.data['evaluation']['impacted_parts_count']}")

    part.refresh_from_db()
    print(f"Part {part.part_number} status after ECHA update: {part.overall_status} (REACH: {part.reach_status})")
    assert part.reach_status == 'Review', f"Expected REACH Review, got {part.reach_status}"
    
    tasks = part.review_tasks.filter(title__contains="REACH SVHC")
    assert tasks.exists(), "Expected new REACH SVHC ReviewTask"
    print(f"Generated task: {tasks.first().title}")

    log = RegulatorySyncLog.objects.first()
    print(f"Sync audit log: {log.status} (Rules checked: {log.rules_checked}, Parts swept: {log.parts_revaluated}, Impacted: {log.parts_impacted})")
    assert log.parts_impacted >= 1, "Log should record impacted parts"

    print("\n=== 4. Resetting to Baseline Ruleset ===")
    reset_req = factory.post('/api/regulations/sync/', {'mode': 'reset_baseline'}, format='json')
    reset_res = RegulatorySyncView.as_view()(reset_req)
    assert reset_res.status_code == 200
    
    part.refresh_from_db()
    print(f"Part status after reset: {part.overall_status}")
    assert part.overall_status == 'Approved', f"Expected Approved after reset, got {part.overall_status}"

    print("\n=== 5. Testing check_only mode ===")
    check_req = factory.post('/api/regulations/sync/', {'mode': 'check_only'}, format='json')
    check_res = RegulatorySyncView.as_view()(check_req)
    assert check_res.status_code == 200
    print(f"Check-only log status: {check_res.data['log']['status']}")

    print("\n>>> ALL REGULATORY SYNC & RETROSPECTIVE RE-EVALUATION TESTS PASSED! <<<")

if __name__ == '__main__':
    run_tests()
