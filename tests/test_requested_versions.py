import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import chatbot
from fixture_project import fixture_answer

class RequestedVersionTests(unittest.TestCase):
    def test_missing_history_not_replaced_by_new_draft(self):
        q='請只使用 IT-006 v1.1，告訴我敏感設備的定義，不要用 v1.2'
        r=fixture_answer(q,'draft')
        self.assertEqual(r['status'],'VERSION_UNAVAILABLE')
        self.assertIn('IT-006 v1.1',r['answer'])
        self.assertIn('不會改用其他版本',r['answer'])
        self.assertEqual(r['sources'],[])
        self.assertNotIn('高權限',r['answer'])
    def test_known_draft_and_semver_alias(self):
        for v in ['v1.2','v1.2.0','版本1.2']:
            r=fixture_answer('IT-006 '+v+' 敏感設備是什麼','draft')
            self.assertEqual(r['sources'][0]['version'],'1.2.0')
            self.assertEqual(len(r['sources']),1)
    def test_active_mode_does_not_read_draft(self):
        r=fixture_answer('請用 IT-006 v1.2 說明敏感設備','active')
        self.assertEqual(r['status'],'VERSION_UNAVAILABLE')
        self.assertEqual(r['sources'],[])
    def test_conflict_and_missing_identifier_clarify(self):
        for q in ['請用 v1.2 告訴我設備規範','比較 IT-006 v1.1 和 v1.2']:
            self.assertEqual(fixture_answer(q,'draft')['status'],'VERSION_CLARIFY')
        self.assertEqual(fixture_answer('IT-006 不用v1.2，說明設備','draft')['status'],'VERSION_UNAVAILABLE')
    def test_followup_keeps_missing_version(self):
        r=fixture_answer('那可以嗎','draft',history=['請用 IT-006 v1.1 解釋攜出'])
        self.assertEqual(r['status'],'VERSION_UNAVAILABLE')
        self.assertEqual(r['sources'],[])

if __name__=='__main__':unittest.main()
