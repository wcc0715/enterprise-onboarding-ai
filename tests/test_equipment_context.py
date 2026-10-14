import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import chatbot

class EquipmentContextTests(unittest.TestCase):
    first='我下禮拜要去出差，需要申請設備'
    def test_carry_followup_switches_to_authorization_topic(self):
        for q in ['但我是要帶出去誒','但我要拿出去','我是要帶回家的']:
            with self.subTest(q=q):
                r=chatbot.answer(q,'draft',history=[self.first])
                self.assertEqual(r['status'],'EQUIPMENT_CARRY_CLARIFY')
                self.assertEqual(r['context_topic'],'設備攜出')
                self.assertIn('是否已取得攜出授權',r['display_answer'])
                self.assertEqual(r['sources'][0]['source_id'],'IT-006')
                self.assertIn('不必每次重申請',r['display_answer'])
                self.assertIn('共用設備須借用登記',r['display_answer'])
    def test_no_context_does_not_assume_equipment(self):
        self.assertEqual(chatbot.answer('但我是要帶出去誒','draft')['status'],'NOT_PROVIDED')
    def test_different_object_not_forced_into_equipment(self):
        r=chatbot.answer('但椅子壞了怎麼辦','draft',history=[self.first])
        self.assertIsNone(r['context_topic'])
        self.assertIn('ADMIN-003',{s['source_id'] for s in r['sources']})
    def test_active_mode_still_excludes_draft(self):
        r=chatbot.answer('但我是要帶出去誒','active',history=[self.first])
        self.assertEqual(r['status'],'NO_ACTIVE_REGULATIONS')

if __name__=='__main__':unittest.main()
