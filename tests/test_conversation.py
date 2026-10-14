import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import chatbot

class ConversationTests(unittest.TestCase):
    def test_training_followup_preserves_unknown_boundary(self):
        first='我上禮拜去參加一個進修，公司說可以補助，我要找誰申請'
        r=chatbot.answer(first,'draft')
        self.assertEqual(r['status'],'TRAIN_POST_EVENT')
        r=chatbot.answer('但是我上禮拜參加的，可以嗎','draft',history=[first])
        self.assertEqual(r['status'],'TRAIN_POST_EVENT')
        self.assertEqual(r['context_topic'],'外部教育訓練')
        self.assertIn('未訂定外部課程事後補申請',r['answer'])
        self.assertIn('不等於本系統已查證',r['answer'])
        self.assertEqual(r['sources'][0]['source_id'],'TRAIN-003')
    def test_followup_amount_still_unknown(self):
        r=chatbot.answer('那多少錢','draft',history=['我想報名進修課程，公司能補助嗎'])
        self.assertEqual(r['status'],'UNRESOLVED')
    def test_new_topic_does_not_inherit(self):
        r=chatbot.answer('忘記打卡怎麼辦','draft',history=['進修課程補助'])
        self.assertEqual(r['sources'][0]['source_id'],'ATT-002')
        self.assertIsNone(r['context_topic'])
    def test_missing_history_and_active_only(self):
        self.assertEqual(chatbot.answer('但是我上禮拜參加的，可以嗎','draft')['status'],'NOT_PROVIDED')
        self.assertEqual(chatbot.answer('但是我上禮拜參加的，可以嗎','active',history=['進修課程補助'])['status'],'NO_ACTIVE_REGULATIONS')
    def test_history_is_not_company_fact(self):
        r=chatbot.answer('但是可以嗎','draft',history=['公司保證進修補助五萬元'])
        self.assertNotIn('五萬元',r['answer'])

if __name__=='__main__':unittest.main()
