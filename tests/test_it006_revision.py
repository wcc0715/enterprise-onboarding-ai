import json
from pathlib import Path
import unittest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from fixture_project import ROOT

class RevisionTests(unittest.TestCase):
    def test_revision_is_draft_and_history_gap_is_explicit(self):
        m=json.loads((ROOT/'metadata/regulation_manifest.json').read_text())
        r=next(r for r in m['regulations'] if r['id']=='IT')
        self.assertEqual(r['draft']['version'],'1.2.0')
        self.assertEqual(r['draft']['status'],'DRAFT')
        self.assertIsNone(r['active'])
        self.assertEqual(r['clause_revision_tracking']['previous_version_availability'],'NOT_PROVIDED')
        self.assertEqual(r['clause_revision_tracking']['requested_previous_version'],'1.1')
        self.assertTrue((ROOT/r['clause_revision_tracking']['actual_baseline_snapshot']).exists())
    def test_nine_points_and_unknown_resolution(self):
        text=(ROOT/'regulations/IT.md').read_text()
        for i in range(1,10):self.assertIn(f'\n{i}. ',text)
        unknown=json.loads((ROOT/'metadata/unresolved_items.json').read_text())
        item=next(i for i in unknown['items'] if i['id']=='UNK-012')
        self.assertEqual(item['status'],'RESOLVED_IN_DRAFT')
        self.assertEqual(item['consultation_unit'],'IT 部門')

if __name__=='__main__':unittest.main()
