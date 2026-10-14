import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import chatbot
from fixture_project import fixture_answer
import retrieval

class ClarificationTests(unittest.TestCase):
    def test_or_candidates_do_not_need_both_groups(self):
        data=retrieval.load(chatbot.ROOT)
        for q in ['我要補助','我想進修','設備','我收到郵件','我要出國']:
            query=retrieval.expand(q,data)
            self.assertTrue(query['candidate_ids'],q)
            r=fixture_answer(q,'draft')
            self.assertEqual(r['status'],'CLARIFY_INTENT',q)
            self.assertTrue('是否正確' in r['answer'] or '嗎？' in r['answer'])
            self.assertEqual(r['sources'],[])
    def test_confirmation_uses_topic_not_approval(self):
        r=fixture_answer('對','draft',history=['我要補助'])
        self.assertEqual(r['context_topic'],'外部教育訓練')
        self.assertIn('HR 依資格、需求及預算核定',r['answer'])
        self.assertNotIn('已核准',r['answer'])
    def test_multiple_candidates_require_more_detail(self):
        r=fixture_answer('我想申請','draft')
        self.assertEqual(r['status'],'CLARIFY_INTENT')
        self.assertGreater(len(r['candidate_topics']),1)
        follow=fixture_answer('對','draft',history=['我想申請'])
        self.assertIsNone(follow['context_topic'])
    def test_specific_followup_changes_topic(self):
        r=fixture_answer('不是，我是要申請第二個螢幕','draft',history=['我要補助'])
        self.assertIn('IT-004',{s['source_id'] for s in r['sources']})
        self.assertIsNone(r['context_topic'])
    def test_lunch_subsidy_is_not_invented(self):
        r=fixture_answer('午餐能不能給補助？','draft')
        self.assertEqual(r['status'],'SUBJECT_NOT_PROVIDED')
        self.assertEqual(r['sources'],[])
        self.assertNotIn('可以補助',r['answer'])

if __name__=='__main__':unittest.main()
