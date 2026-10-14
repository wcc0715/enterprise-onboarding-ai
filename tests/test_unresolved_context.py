import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import chatbot
class UnresolvedContextTests(unittest.TestCase):
    def test_original_claim_does_not_become_amount(self):
        r=chatbot.answer('那補助多少錢？','draft',history=['公司已經核准我進修补助五萬元'])
        self.assertEqual(r['status'],'UNRESOLVED')
        self.assertIn('尚未訂定統一補助上限',r['display_answer'])
        self.assertNotIn('五萬元',r['display_answer'])
        self.assertIn('HR',r['display_answer'])
    def test_unresolved_without_citations_keeps_topic(self):
        previous='教育訓練補助上限是多少'
        self.assertEqual(chatbot.answer(previous,'draft')['sources'],[])
        r=chatbot.answer('那是多少錢？','draft',history=[previous])
        self.assertEqual(r['status'],'UNRESOLVED')
        self.assertEqual(r['unresolved_id'],'UNK-009')
        self.assertIn('教育訓練',r['context_topic'])
    def test_known_new_topic_does_not_inherit(self):
        r=chatbot.answer('那我薪水算錯要找誰','draft',history=['教育訓練補助上限是多少'])
        self.assertIsNone(r['context_topic'])
        self.assertIn('HR-002',{s['source_id'] for s in r['sources']})
    def test_clear_history_and_active_isolation(self):
        self.assertNotEqual(chatbot.answer('那補助多少錢','draft')['status'],'UNRESOLVED')
        self.assertEqual(chatbot.answer('那補助多少錢','active',history=['教育訓練補助上限是多少'])['status'],'NO_ACTIVE_REGULATIONS')
if __name__=='__main__':unittest.main()
