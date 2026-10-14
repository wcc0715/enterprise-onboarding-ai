import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import chatbot
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
                r=chatbot.answer(q,'draft')
                self.assertEqual(r['status'],'EXTRACTED')
                self.assertIn(expected,{s['source_id'] for s in r['sources']})
    def test_unknown_alias_and_personal_balance(self):
        self.assertEqual(chatbot.answer('薪轉戶的截止日是幾號','draft')['status'],'UNRESOLVED')
        self.assertEqual(chatbot.answer('研習補助額度是多少','draft')['status'],'UNRESOLVED')
        self.assertEqual(chatbot.answer('我還有幾天年假','draft')['status'],'HRM_UNAVAILABLE')
    def test_unknown_topic_and_vague_question(self):
        self.assertEqual(chatbot.answer('餐費補助多少','draft')['status'],'NOT_PROVIDED')
        self.assertEqual(chatbot.answer('我要申請設備','draft')['status'],'CLARIFY')
        self.assertEqual(chatbot.answer('','draft')['status'],'CLARIFY')
    def test_case_width_normalization(self):
        self.assertIn('SEC-003',{s['source_id'] for s in chatbot.answer('私人ＵＳＢ可以使用嗎','draft')['sources']})
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

if __name__=='__main__':unittest.main()
