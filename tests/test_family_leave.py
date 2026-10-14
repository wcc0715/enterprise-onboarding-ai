import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import chatbot
from fixture_project import fixture_answer

class FamilyLeaveTests(unittest.TestCase):
    def test_relative_names_do_not_become_employee_sickness(self):
        for relative in ['弟弟','妹妹','哥哥','姊姊','女兒','外婆']:
            r=fixture_answer('我'+relative+'突然生病，我想請假','draft')
            self.assertEqual(r['status'],'FAMILY_LEAVE_CLARIFY')
            self.assertIn('先通知主管',r['display_answer'])
            self.assertNotIn('LEAVE-003',{s['source_id'] for s in r['sources']})
    def test_relative_correction_and_advice(self):
        r=fixture_answer('是我弟弟，不是我','draft',history=['我弟弟突然生病，我想請假'])
        self.assertEqual(r['status'],'FAMILY_LEAVE_CLARIFY')
        r=fixture_answer('你的建議呢','draft',history=['我弟弟突然生病，我想請假'])
        self.assertEqual(r['status'],'FAMILY_LEAVE_ADVICE')
        self.assertIn('我的建議是先通知主管',r['display_answer'])
    first='我家人突然生病，今天去不了公司，要請假，我要請特休'
    def test_explicit_annual_leave_not_self_sick_leave(self):
        r=fixture_answer(self.first,'draft')
        self.assertEqual(r['status'],'ANNUAL_LEAVE_URGENT')
        self.assertIn('不是強制期限',r['display_answer'])
        self.assertIn('先通知主管',r['display_answer'])
        self.assertEqual({s['source_id'] for s in r['sources']},{'LEAVE-004','LEAVE-005'})
        self.assertNotIn('診斷證明書',r['display_answer'])
    def test_reason_followup_keeps_specified_annual_leave(self):
        r=fixture_answer('但是我家人臨時生病啊，沒辦法提前','draft',history=[self.first])
        self.assertEqual(r['status'],'ANNUAL_LEAVE_URGENT')
        self.assertEqual(r['context_topic'],'特休')
        self.assertIn('希望使用特休',r['display_answer'])
        self.assertNotIn('LEAVE-003',{s['source_id'] for s in r['sources']})
    def test_family_without_leave_type_needs_clarification(self):
        r=fixture_answer('我家人生病可以請病假嗎','draft')
        self.assertEqual(r['status'],'FAMILY_LEAVE_CLARIFY')
        self.assertIn('沒有說明',r['answer'])
    def test_self_sickness_is_still_supported(self):
        r=fixture_answer('我自己生病，要請病假','draft')
        self.assertIn('LEAVE-003',{s['source_id'] for s in r['sources']})
    def test_new_leave_type_not_overridden(self):
        r=fixture_answer('但是我改請事假','draft',history=[self.first])
        self.assertIsNone(r['context_topic'])
        self.assertIn('LEAVE-001',{s['source_id'] for s in r['sources']})

if __name__=='__main__':unittest.main()
