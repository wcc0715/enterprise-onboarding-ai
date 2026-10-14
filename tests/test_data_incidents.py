import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import chatbot
from fixture_project import fixture_answer

class DataIncidentTests(unittest.TestCase):
    def test_variants_get_immediate_report(self):
        for q in ['我寄錯公司資料，等明天再說好嗎？','客戶文件傳錯人了怎麼辦','我誤傳含個資的附件','公司機密檔案洩漏了']:
            with self.subTest(q=q):
                r=fixture_answer(q,'draft')
                self.assertEqual(r['status'],'DATA_INCIDENT_REPORT')
                self.assertIn('立即通報 IT',r['display_answer'])
                self.assertIn('事件時間、收件對象及涉及資料',r['display_answer'])
                self.assertIn('授權人員',r['display_answer'])
                self.assertEqual(r['sources'][0]['source_id'],'SEC-006')
    def test_non_company_typo_is_not_incident(self):
        self.assertNotEqual(fixture_answer('我寄錯生日祝福了','draft')['status'],'DATA_INCIDENT_REPORT')
    def test_active_does_not_leak_draft(self):
        self.assertEqual(fixture_answer('我寄錯公司資料','active')['status'],'NO_ACTIVE_REGULATIONS')

if __name__=='__main__':unittest.main()
