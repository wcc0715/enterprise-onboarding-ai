import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import chatbot
import query_subjects
class QuerySubjectTests(unittest.TestCase):
    def test_missing_specific_subject_not_training(self):
        for q in ['公司停車費補助上限多少？','停車有津貼嗎','午餐能不能給補助？','租屋補助多少錢']:
            with self.subTest(q=q):
                r=chatbot.answer(q,'draft')
                self.assertEqual(r['status'],'SUBJECT_NOT_PROVIDED')
                self.assertIn('無法確認公司是否提供',r['display_answer'])
                self.assertIn('未指定',r['display_answer'])
                self.assertEqual(r['sources'],[])
                self.assertNotIn('向行政',r['display_answer'])
    def test_known_training_and_vague_subsidy_unchanged(self):
        self.assertEqual(chatbot.answer('教育訓練補助上限多少','draft')['status'],'UNRESOLVED')
        self.assertEqual(chatbot.answer('我要補助','draft')['status'],'CLARIFY_INTENT')
    def test_future_source_not_marked_missing(self):
        chunks=[dict(text='## TEST 停車\n停車補助依規定管理')]
        self.assertIsNone(query_subjects.unsupported_subsidy('停車費補助多少',chunks,chatbot.ROOT))
    def test_draft_does_not_leak(self):
        self.assertEqual(chatbot.answer('停車補助多少','active')['status'],'NO_ACTIVE_REGULATIONS')
if __name__=='__main__':unittest.main()
