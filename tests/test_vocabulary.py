import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import chatbot
from fixture_project import fixture_answer
import retrieval

class VocabularyTests(unittest.TestCase):
    def test_colloquial_variants_find_expected_source(self):
        cases=[('年假怎麼申請','LEAVE-004'),('身體不適怎麼辦','LEAVE-003'),
               ('忘了刷卡要怎麼辦','ATT-002'),('薪水算錯了','HR-002'),
               ('想更換薪轉銀行','HR-003'),('識別證不見了','ADMIN-001'),
               ('會議空間怎麼預約','ADMIN-005'),('可疑信件要怎麼處理','SEC-002'),
               ('電腦開不了','IT-001'),('我想申請多一個螢幕','IT-004'),
               ('筆電帶回家可以嗎','IT-006'),('進修課程可以補助嗎','TRAIN-003')]
        for q,expected in cases:
            with self.subTest(q=q):
                r=fixture_answer(q,'draft')
                self.assertEqual(r['status'],'EQUIPMENT_CARRY_CLARIFY' if expected=='IT-006' else 'EXTRACTED')
                self.assertIn(expected,{s['source_id'] for s in r['sources']})
    def test_unknown_alias_and_personal_balance(self):
        self.assertEqual(fixture_answer('薪轉戶的截止日是幾號','draft')['status'],'UNRESOLVED')
        self.assertEqual(fixture_answer('研習補助額度是多少','draft')['status'],'UNRESOLVED')
        self.assertEqual(fixture_answer('我還有幾天年假','draft')['status'],'HRM_UNAVAILABLE')
    def test_unknown_topic_and_vague_question(self):
        self.assertEqual(fixture_answer('餐費補助多少','draft')['status'],'SUBJECT_NOT_PROVIDED')
        self.assertEqual(fixture_answer('我要申請設備','draft')['status'],'CLARIFY')
        self.assertEqual(fixture_answer('','draft')['status'],'CLARIFY')
    def test_case_width_normalization(self):
        self.assertIn('SEC-003',{s['source_id'] for s in fixture_answer('私人ＵＳＢ可以使用嗎','draft')['sources']})
    def test_configurable_alias_without_code_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'config').mkdir()
            data=retrieval.load(chatbot.ROOT)
            data['concepts'].append({'canonical':'病假','aliases':['測試身體詞彙']})
            (root/'config/retrieval_vocabulary.json').write_text(json.dumps(data),encoding='utf-8')
            query=retrieval.expand('測試身體詞彙',retrieval.load(root))
            self.assertIn('病假',query['expanded_terms'])
    def test_context_requires_both_groups(self):
        data=retrieval.load(chatbot.ROOT)
        self.assertNotIn('TRAIN-003',retrieval.expand('我要補助',data)['target_ids'])
        self.assertIn('TRAIN-003',retrieval.expand('我要報名研習',data)['target_ids'])


class FullCoverageTests(unittest.TestCase):
    def test_all_clauses_have_two_phrase_cases(self):
        cases=json.loads((chatbot.ROOT/'tests/vocabulary_cases.json').read_text())['cases']
        chunks=chatbot.assistant.load_draft(chatbot.ROOT)
        self.assertEqual({c['source_id'] for c in chunks},{c['source_id'] for c in cases})
        for item in cases:
            with self.subTest(question=item['question']):
                r=fixture_answer(item['question'],'draft')
                self.assertIn(item['source_id'],{s['source_id'] for s in r['sources']})
    def test_travel_does_not_assume_leave_type(self):
        for q in ['我要出國，幾天前要請假','下個月去旅遊，休假需要提前多久說？']:
            r=fixture_answer(q,'draft')
            self.assertEqual(r['status'],'LEAVE_TYPE_CLARIFY')
            self.assertIn('特休還是一般事假',r['answer'])
            self.assertIn('非強制期限',r['answer'])
            self.assertIn('一個工作天',r['answer'])

if __name__=='__main__':unittest.main()
