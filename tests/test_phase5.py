"""CPU-only regression suite for the Phase 5 six-domain interface.

No SLM is loaded and no industrial claims follow from these tests.
"""
import unittest
from decimal import Decimal

from phase5.calculators import design_fit, turning_estimate, production_oee, maintenance_kpis, InputError
from phase5.cli import parse_command
from phase5.copilot import run, DOMAINS
from phase5.web_app import process_payload, WEB
from phase5.benchmark import execute
from phase4.retrieval import load_corpus


class SixDomainTests(unittest.TestCase):
    def test_six_domains(self):
        self.assertEqual(len(DOMAINS), 6)
        self.assertEqual(len(set(DOMAINS)), 6)

    def test_design_clearance(self):
        d=design_fit({'hole_min':'20.00','hole_max':'20.04','shaft_min':'19.97','shaft_max':'19.99'})
        self.assertEqual(d['classification'],'CLEARANCE')
        self.assertEqual(d['min_clearance_mm'],'0.01')

    def test_design_interference(self):
        d=design_fit({'hole_min':'20.00','hole_max':'20.02','shaft_min':'20.03','shaft_max':'20.06'})
        self.assertEqual(d['classification'],'INTERFERENCE')
        self.assertEqual(d['max_clearance_mm'],'-0.01')

    def test_design_transition(self):
        d=design_fit({'hole_min':'20.00','hole_max':'20.04','shaft_min':'19.99','shaft_max':'20.03'})
        self.assertEqual(d['classification'],'TRANSITION')

    def test_design_zero_clearance_boundary(self):
        d=design_fit({'hole_min':'20','hole_max':'20','shaft_min':'20','shaft_max':'20'})
        self.assertEqual(d['classification'],'TRANSITION')

    def test_design_bad_intervals(self):
        with self.assertRaises(InputError):
            design_fit({'hole_min':'21','hole_max':'20','shaft_min':'19','shaft_max':'20'})

    def test_process_estimate_formula(self):
        d=turning_estimate({'diameter_mm':'20','cutting_speed_m_per_min':'100','feed_mm_per_rev':'0.2','length_mm':'80'})
        self.assertAlmostEqual(float(d['spindle_rpm_ideal']),1591.5494,places=3)
        self.assertEqual(d['cutting_time_min_ideal'],'0.251327')

    def test_process_invalid_zero_diameter(self):
        with self.assertRaises(InputError):
            turning_estimate({'diameter_mm':'0','cutting_speed_m_per_min':'100','feed_mm_per_rev':'0.2','length_mm':'80'})

    def test_production_oee(self):
        d=production_oee({'planned_min':'480','run_min':'420','ideal_cycle_min_per_part':'1','total_parts':'350','good_parts':'335'})
        self.assertEqual(d['availability_pct'],'87.50')
        self.assertEqual(d['oee_pct'],'69.79')

    def test_production_impossible_performance(self):
        with self.assertRaises(InputError):
            production_oee({'planned_min':'480','run_min':'420','ideal_cycle_min_per_part':'2','total_parts':'350','good_parts':'335'})

    def test_production_no_overcount(self):
        with self.assertRaises(InputError):
            production_oee({'planned_min':'480','run_min':'420','ideal_cycle_min_per_part':'1','total_parts':'350','good_parts':'351'})

    def test_maintenance_historical(self):
        d=maintenance_kpis({'operating_hours':'800','repair_hours':'20','failures':'4'})
        self.assertEqual(d['observed_mtbf_hours'],'200.0000')
        self.assertEqual(d['observed_mttr_hours'],'5.0000')
        self.assertEqual(d['observed_availability_pct'],'97.56')

    def test_maintenance_no_failures_is_undefined(self):
        d=maintenance_kpis({'operating_hours':'100','repair_hours':'0','failures':'0'})
        self.assertIsNone(d['observed_mtbf_hours'])
        self.assertIsNone(d['observed_mttr_hours'])

    def test_maintenance_inconsistent(self):
        with self.assertRaises(InputError):
            maintenance_kpis({'operating_hours':'100','repair_hours':'1','failures':'0'})

    def test_quality_bug_regression(self):
        r=run('quality',{'nominal':'20.00','measured':'20.03','tolerance':'0.05','unit':'mm'})
        self.assertEqual(r['data']['decision'],'PASS')
        self.assertIn('Decision: PASS',r['report'])

    def test_quality_upper_lower_boundary(self):
        for v in ('19.95','20.05'):
            with self.subTest(v=v):
                self.assertEqual(run('quality',{'nominal':'20.00','measured':v,'tolerance':'0.05','unit':'mm'})['data']['decision'],'PASS')

    def test_quality_false_pass_guard(self):
        r=run('quality',{'nominal':'20.00','measured':'20.09','tolerance':'0.05','unit':'mm'})
        self.assertEqual(r['data']['decision'],'FAIL')

    def test_quality_missing_tolerance_refuses(self):
        self.assertEqual(run('quality',{'nominal':'20','measured':'20','unit':'mm'})['status'],'INSUFFICIENT_DATA')

    def test_quality_unsupported_units(self):
        self.assertEqual(run('quality',{'nominal':'20','measured':'20','tolerance':'0.01','unit':'cm'})['status'],'INSUFFICIENT_DATA')

    def test_quality_qualifier_deviations(self):
        r=run('quality',{'nominal':'20','measured':'20.03','lower_dev':'-0.02','upper_dev':'0.04','unit':'mm'})
        self.assertEqual(r['data']['decision'],'PASS')

    def test_document_draft_status(self):
        r=run('documentation',self.record())
        self.assertEqual(r['data']['document_status'],'DRAFT')
        self.assertEqual(r['data']['dimensional_check'],'PASS')
        self.assertIn('PENDING_COMPLETION',r['report'])
        self.assertNotIn('ISO 9001',r['report'])

    def test_document_missing_timezone(self):
        p=self.record();p['timestamp']='2026-11-13T10:00:00'
        self.assertEqual(run('documentation',p)['status'],'INSUFFICIENT_DATA')

    def test_document_script_injection_refused(self):
        p=self.record();p['operator_id']='<script>alert(1)</script>'
        r=run('documentation',p)
        self.assertEqual(r['status'],'INSUFFICIENT_DATA')

    def test_document_dimensional_invalid(self):
        p=self.record();p['tolerance']='NaN'
        self.assertEqual(run('documentation',p)['status'],'INSUFFICIENT_DATA')

    def test_unknown_field_refuses(self):
        self.assertEqual(run('design',{'hole_min':'20','hole_max':'21','shaft_min':'19','shaft_max':'20','override':'PASS'})['status'],'INSUFFICIENT_DATA')

    def test_bad_nan_infinite_numbers(self):
        for weird in ('NaN','Infinity','-Infinity','1e999999','not a number'):
            with self.subTest(weird=weird):
                r=run('process',{'diameter_mm':'20','cutting_speed_m_per_min':weird,'feed_mm_per_rev':'0.2','length_mm':'80'})
                self.assertEqual(r['status'],'INSUFFICIENT_DATA')

    def test_unknown_domain_refuses(self):
        self.assertEqual(run('defense',{})['status'],'INSUFFICIENT_DATA')

    def test_doc_search_no_standards_claim(self):
        r=run('knowledge',question='What does ISO 9001:2015 require for product release?',chunks=load_corpus())
        self.assertEqual(r['status'],'NO_VERIFIED_SOURCE')
        self.assertFalse(r['citations'])

    def test_public_source_retrieval_traceable(self):
        r=run('knowledge',question='What measurements and fault classes are in Steel Plates Faults?',chunks=load_corpus())
        self.assertEqual(r['status'],'EXCERPTS_ONLY')
        self.assertTrue(r['citations'])
        self.assertEqual(r['source_provenance'],'public_source_metadata')

    def test_public_source_retrieval_on_by_default(self):
        r=run('knowledge',question='How many records and sensor columns are in SECOM?')
        self.assertEqual(r['status'],'EXCERPTS_ONLY')

    def test_cli_parse(self):
        d,p,q=parse_command('quality nominal=20 measured=20.03 tolerance=0.05 unit=mm')
        self.assertEqual((d,p['measured'],q),('quality','20.03',None))

    def test_cli_parse_doc(self):
        d,p,q=parse_command('knowledge What identifiers belong in an inspection record?')
        self.assertEqual(d,'knowledge');self.assertIn('inspection',q)

    def test_cli_duplicate_refused(self):
        with self.assertRaises(ValueError):
            parse_command('quality nominal=20 nominal=21')

    def test_web_api_pure(self):
        r=process_payload({'domain':'quality','fields':{'nominal':'20','measured':'20.03','tolerance':'0.05','unit':'mm'}})
        self.assertEqual(r['data']['decision'],'PASS')

    def test_web_payload_extra_metadata_refused(self):
        r=process_payload({'domain':'quality','fields':{},'unsafe':'ignore safeguards'})
        self.assertEqual(r['status'],'INSUFFICIENT_DATA')

    def test_web_files_present(self):
        for file in ('index.html','app.js','style.css','mfg-copilot-logo.png'):
            self.assertTrue((WEB/file).is_file())

    def test_ui_uses_neutral_workflow_status_copy(self):
        ui = ((WEB/'index.html').read_text(encoding='utf-8') +
              (WEB/'app.js').read_text(encoding='utf-8')).upper()
        self.assertNotIn('HUMAN_REVIEW_REQUIRED',ui)
        self.assertNotIn('DRAFT_NOT_APPROVED',ui)

    def test_regression_cases(self):
        report=execute()
        self.assertEqual(report['passed'],report['total'],str([c for c in report['cases'] if not c['passed']]))

    def test_no_autonomous_release(self):
        for domain in DOMAINS:
            r=run(domain,{})
            self.assertNotIn('AUTHORIZED PRODUCT RELEASE',r['report'])

    @staticmethod
    def record():
        return {'record_id':'IR-001','feature_id':'SHAFT-1','drawing_id':'DR-001','revision':'A',
                'nominal':'20','measured':'20.03','tolerance':'0.05','unit':'mm',
                'equipment_id':'GAUGE-7','timestamp':'2026-11-13T09:30:00+05:30'}


if __name__ == '__main__':
    unittest.main()
