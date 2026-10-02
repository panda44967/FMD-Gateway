import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fmd_server.settings')
django.setup()

from fmd_core.models import RegulatoryRule, Supplier

def seed():
    print("Seeding initial suppliers and parts catalog...")
    suppliers_parts_data = [
        {
            'code': 'SUP-LUX-001',
            'name': 'Luxshare Precision Ltd.',
            'email': 'compliance@luxshare.com',
            'quality_score': 96.5,
            'parts': [
                ('IPN-CBL-001', '100W USB-C Fast Charging Cable Assembly'),
                ('IPN-CONN-002', 'USB-C 24-Pin Male Plug Sub-Assembly'),
                ('IPN-CONN-006', '3.5mm Gold-Plated Audio Jack'),
                ('IPN-ANT-007', 'Wi-Fi 7 Embedded FPC Antenna'),
            ]
        },
        {
            'code': 'SUP-TI-001',
            'name': 'Texas Instruments Inc.',
            'email': 'env-compliance@ti.com',
            'quality_score': 99.0,
            'parts': [
                ('IPN-IC-555', 'Precision Timer Bipolar IC'),
            ]
        },
        {
            'code': 'SUP-MUR-001',
            'name': 'Murata Manufacturing Co., Ltd.',
            'email': 'chem-compliance@murata.com',
            'quality_score': 98.5,
            'parts': [
                ('IPN-CAP-104', 'MLCC 0402 100nF Ceramic Capacitor'),
            ]
        },
        {
            'code': 'SUP-ADI-001',
            'name': 'Analog Devices Inc.',
            'email': 'green-compliance@analog.com',
            'quality_score': 98.0,
            'parts': [
                ('IPN-PMIC-4618', '26V 15A Step-Down DC/DC uModule Regulator'),
            ]
        },
        {
            'code': 'SUP-TE-001',
            'name': 'TE Connectivity Ltd.',
            'email': 'product-compliance@te.com',
            'quality_score': 97.5,
            'parts': [
                ('IPN-CONN-282', 'Micro-Fit 3.0 Dual-Row Header Connector'),
            ]
        },
        {
            'code': 'SUP-FOX-002',
            'name': 'Foxconn Technology Group',
            'email': 'green.compliance@foxconn.com',
            'quality_score': 94.0,
            'parts': [
                ('IPN-MB-003', 'Mainboard Multilayer High-Speed PCB Assembly'),
                ('IPN-CASE-004', 'CNC Anodized Aluminum Uni-Chassis'),
            ]
        },
        {
            'code': 'SUP-DEL-003',
            'name': 'Delta Electronics',
            'email': 'compliance@deltaww.com',
            'quality_score': 95.5,
            'parts': [
                ('IPN-PSU-005', '65W GaN High-Efficiency Power Module'),
            ]
        }
    ]

    from fmd_core.models import SupplierPart
    for s_item in suppliers_parts_data:
        supp, _ = Supplier.objects.update_or_create(
            supplier_code=s_item['code'],
            defaults={
                'name': s_item['name'],
                'contact_email': s_item['email'],
                'quality_score': s_item['quality_score']
            }
        )
        for pn, desc in s_item['parts']:
            SupplierPart.objects.get_or_create(
                part_number=pn,
                defaults={
                    'supplier': supp,
                    'part_name': desc,
                    'fmd_tier': 'Partial FMD',
                    'overall_status': 'Data gap',
                    'rohs_status': 'Data gap',
                    'reach_status': 'Data gap',
                    'pfas_status': 'Data gap',
                }
            )
            # Ensure part links to the supplier
            SupplierPart.objects.filter(part_number=pn).update(supplier=supp, part_name=desc)

    print("Seeding baseline regulatory rules...")
    rules = [
        # EU RoHS Directive 2011/65/EU Annex II
        {'regulation': 'EU RoHS', 'version': '2026.09', 'substance_name': 'Lead', 'cas': '7439-92-1', 'threshold_pct': 0.1, 'is_svhc': True, 'notes': 'Homogeneous material threshold: 0.1% (1000 ppm)'},
        {'regulation': 'EU RoHS', 'version': '2026.09', 'substance_name': 'Cadmium', 'cas': '7440-43-9', 'threshold_pct': 0.01, 'is_svhc': True, 'notes': 'Homogeneous material threshold: 0.01% (100 ppm)'},
        {'regulation': 'EU RoHS', 'version': '2026.09', 'substance_name': 'Mercury', 'cas': '7439-97-6', 'threshold_pct': 0.1, 'is_svhc': False, 'notes': 'Homogeneous material threshold: 0.1% (1000 ppm)'},
        {'regulation': 'EU RoHS', 'version': '2026.09', 'substance_name': 'Hexavalent Chromium', 'cas': '18540-29-9', 'threshold_pct': 0.1, 'is_svhc': False, 'notes': 'Homogeneous material threshold: 0.1% (1000 ppm)'},
        {'regulation': 'EU RoHS', 'version': '2026.09', 'substance_name': 'DEHP (Phthalate)', 'cas': '117-81-7', 'threshold_pct': 0.1, 'is_svhc': True, 'notes': 'Homogeneous material threshold: 0.1% (1000 ppm)'},
        # REACH SVHC Candidate List
        {'regulation': 'REACH SVHC', 'version': '2026.09', 'substance_name': 'Lead', 'cas': '7439-92-1', 'threshold_pct': 0.1, 'is_svhc': True, 'notes': 'ECHA Candidate List: 0.1% w/w trigger for SCIP notification & Article 33 communication'},
        {'regulation': 'REACH SVHC', 'version': '2026.09', 'substance_name': 'Cadmium', 'cas': '7440-43-9', 'threshold_pct': 0.1, 'is_svhc': True, 'notes': 'ECHA Candidate List: 0.1% w/w notification trigger'},
        {'regulation': 'REACH SVHC', 'version': '2026.09', 'substance_name': 'DEHP', 'cas': '117-81-7', 'threshold_pct': 0.1, 'is_svhc': True, 'notes': 'ECHA Candidate List: 0.1% w/w notification trigger'},
        # PFAS (Universal / Group restrictions)
        {'regulation': 'PFAS', 'version': '2026.09', 'substance_name': 'PFOA (Perfluorooctanoic acid)', 'cas': '335-67-1', 'is_pfas': True, 'notes': 'POPs & REACH Annex XVII restricted fluorinated compound'},
        {'regulation': 'PFAS', 'version': '2026.09', 'substance_name': 'PTFE (Polytetrafluoroethylene)', 'cas': '9002-84-0', 'is_pfas': True, 'notes': 'Fluoropolymer requiring intentional-use inquiry and purity evidence'},
        {'regulation': 'PFAS', 'version': '2026.09', 'substance_name': 'PFOS (Perfluorooctane sulfonic acid)', 'cas': '1763-23-1', 'is_pfas': True, 'notes': 'POPs restricted PFAS'},
        # Taiwan RoHS CNS 15663 / BSMI Section 5
        {'regulation': 'Taiwan RoHS', 'version': 'CNS 15663 Rev 3.0', 'substance_name': 'Lead (Pb)', 'cas': '7439-92-1', 'threshold_pct': 0.1, 'notes': 'Taiwan CNS 15663 Table 1 threshold: 0.1% wt'},
        {'regulation': 'Taiwan RoHS', 'version': 'CNS 15663 Rev 3.0', 'substance_name': 'Cadmium (Cd)', 'cas': '7440-43-9', 'threshold_pct': 0.01, 'notes': 'Taiwan CNS 15663 Table 1 threshold: 0.01% wt'},
        {'regulation': 'Taiwan RoHS', 'version': 'CNS 15663 Rev 3.0', 'substance_name': 'Mercury (Hg)', 'cas': '7439-97-6', 'threshold_pct': 0.1, 'notes': 'Taiwan CNS 15663 Table 1 threshold: 0.1% wt'},
        {'regulation': 'Taiwan RoHS', 'version': 'CNS 15663 Rev 3.0', 'substance_name': 'Hexavalent Chromium (Cr+6)', 'cas': '18540-29-9', 'threshold_pct': 0.1, 'notes': 'Taiwan CNS 15663 Table 1 threshold: 0.1% wt'},
        {'regulation': 'Taiwan RoHS', 'version': 'CNS 15663 Rev 3.0', 'substance_name': 'Polybrominated Biphenyls (PBB)', 'cas': '59536-65-1', 'threshold_pct': 0.1, 'notes': 'Taiwan CNS 15663 Table 1 threshold: 0.1% wt'},
        {'regulation': 'Taiwan RoHS', 'version': 'CNS 15663 Rev 3.0', 'substance_name': 'Polybrominated Diphenyl Ethers (PBDE)', 'cas': '1163-19-5', 'threshold_pct': 0.1, 'notes': 'Taiwan CNS 15663 Table 1 threshold: 0.1% wt'},
    ]

    for r in rules:
        RegulatoryRule.objects.update_or_create(
            regulation=r['regulation'],
            cas=r['cas'],
            defaults=r
        )

    print(f"Successfully seeded {len(rules)} regulatory rules in English.")

if __name__ == '__main__':
    seed()
