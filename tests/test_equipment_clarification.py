import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import chatbot
class EquipmentClarificationTests(unittest.TestCase):
    def test_vague_needs_ask_specific_fields(self):
        for q in ['我需要設備','設備','我想申請工作設備','我要申請設備？']:
            with self.subTest(q=q):
                r=chatbot.answer(q,'draft')
                self.assertIn(r['status'],['CLARIFY','CLARIFY_INTENT'])
                self.assertIn('哪種設備',r['display_answer'])
                self.assertIn('做什麼',r['display_answer'])
                self.assertIn('帶出公司',r['display_answer'])
                self.assertNotIn('設備異常、維修',r['display_answer'])
                self.assertEqual(r['sources'],[])
    def test_specific_requests_and_failures_are_not_vague(self):
        for q in ['我想申請第二個螢幕','電腦壞了怎麼辦']:
            self.assertNotIn('pending_fields',chatbot.answer(q,'draft'))
    def test_formal_mode_does_not_use_draft(self):
        self.assertEqual(chatbot.answer('我需要設備','active')['status'],'NO_ACTIVE_REGULATIONS')
if __name__=='__main__':unittest.main()
