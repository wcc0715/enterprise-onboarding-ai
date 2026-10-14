import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import chatbot

class UndefinedTermsTests(unittest.TestCase):
    def test_sensitive_equipment_definition_is_unprovided(self):
        for q in ['敏感設備是什麼','什麼是敏感設備','哪些設備算敏感設備','筆電算不算敏感設備']:
            with self.subTest(q=q):
                r=chatbot.answer(q,'draft')
                self.assertEqual(r['status'],'DEFINED_TERM_DRAFT')
                self.assertIn('經 IT 依實際資訊安全風險認定',r['display_answer'])
                self.assertIn('IT 部門負責認定',r['display_answer'])
                self.assertNotIn('一定算',r['display_answer'])
                self.assertIn('IT-006',{s['source_id'] for s in r['sources']})
    def test_definition_question_does_not_need_history(self):
        r=chatbot.answer('敏感設備是什麼','draft',history=['我想申請設備','那我要帶出去'])
        self.assertEqual(r['status'],'DEFINED_TERM_DRAFT')
        self.assertIsNone(r['context_topic'])
    def test_no_draft_leaks_into_active_mode(self):
        self.assertEqual(chatbot.answer('敏感設備是什麼','active')['status'],'NO_ACTIVE_REGULATIONS')

if __name__=='__main__':unittest.main()
