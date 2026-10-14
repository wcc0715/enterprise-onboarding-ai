import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import chatbot

class FamilyLeaveTests(unittest.TestCase):
    first='我家人突然生病，今天去不了公司，要請假，我要請特休'
    def test_explicit_annual_leave_not_self_sick_leave(self):
        r=chatbot.answer(self.first,'draft')
        self.assertEqual(r['status'],'ANNUAL_LEAVE_URGENT')
        self.assertIn('不是強制期限',r['display_answer'])
        self.assertIn('先通知主管',r['display_answer'])
        self.assertEqual({s['source_id'] for s in r['sources']},{'LEAVE-004','LEAVE-005'})
        self.assertNotIn('診斷證明書',r['display_answer'])
    def test_reason_followup_keeps_specified_annual_leave(self):
        r=chatbot.answer('但是我家人臨時生病啊，沒辦法提前','draft',history=[self.first])
        self.assertEqual(r['status'],'ANNUAL_LEAVE_URGENT')
        self.assertEqual(r['context_topic'],'特休')
        self.assertIn('希望使用特休',r['display_answer'])
        self.assertNotIn('LEAVE-003',{s['source_id'] for s in r['sources']})
    def test_family_without_leave_type_needs_clarification(self):
        r=chatbot.answer('我家人生病可以請病假嗎','draft')
        self.assertEqual(r['status'],'FAMILY_LEAVE_CLARIFY')
        self.assertIn('沒有說明',r['answer'])
    def test_self_sickness_is_still_supported(self):
        r=chatbot.answer('我自己生病，要請病假','draft')
        self.assertIn('LEAVE-003',{s['source_id'] for s in r['sources']})
    def test_new_leave_type_not_overridden(self):
        r=chatbot.answer('但是我改請事假','draft',history=[self.first])
        self.assertIsNone(r['context_topic'])
        self.assertIn('LEAVE-001',{s['source_id'] for s in r['sources']})

if __name__=='__main__':unittest.main()
