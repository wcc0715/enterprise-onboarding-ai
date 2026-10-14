import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import chatbot
from fixture_project import fixture_answer

class ConversationTests(unittest.TestCase):
    def test_pet_advice_followup_answers_next_step(self):
        r=fixture_answer('你的建議是？','draft',history=['我家狗生病，我要請假'])
        self.assertEqual(r['status'],'PET_LEAVE_ADVICE')
        self.assertEqual(r['context_topic'],'請假')
        self.assertIn('我的建議是先處理通知',r['display_answer'])
        self.assertNotIn('你想使用事假還是特休',r['display_answer'])
        self.assertIn('請向 HR 確認',r['display_answer'])
    def test_pet_illness_focuses_on_leave_not_employee_illness(self):
        for question in ['我家狗狗突然生病了，我想請假','我的貓咪不舒服，我想請假']:
            r=fixture_answer(question,'draft')
            self.assertEqual(r['status'],'PET_LEAVE_CLARIFY')
            self.assertIn('先通知主管',r['display_answer'])
            self.assertNotIn('LEAVE-003',{s['source_id'] for s in r['sources']})
            self.assertNotIn('診斷',r['display_answer'])
    def test_pet_subject_correction_preserves_leave_task(self):
        r=fixture_answer('我家狗狗啦，不是我','draft',history=['我家狗狗突然生病了，我想請假'])
        self.assertEqual(r['status'],'PET_LEAVE_CLARIFY')
        self.assertIn('HRM',r['display_answer'])
        self.assertNotIn('LEAVE-003',{s['source_id'] for s in r['sources']})
    def test_pet_does_not_create_leave_without_context(self):
        r=fixture_answer('我家狗狗啦，不是我','draft')
        self.assertNotEqual(r['status'],'PET_LEAVE_CLARIFY')
        r=fixture_answer('我家狗狗突然生病了，我想請假','active')
        self.assertEqual(r['status'],'NO_ACTIVE_REGULATIONS')
    def test_leave_choice_advice_keeps_specific_question(self):
        r=fixture_answer('那你的建議呢','draft',history=['我家狗狗突然吐了，我要請假','是，我應該請事假還是緊急請假'])
        self.assertEqual(r['status'],'LEAVE_ADVICE')
        self.assertIn('先儘速通知主管',r['display_answer'])
        self.assertIn('請向 HR 確認',r['display_answer'])
        self.assertEqual({s['source_id'] for s in r['sources']},{'LEAVE-001','LEAVE-002','LEAVE-005'})
        self.assertNotIn('LEAVE-003',{s['source_id'] for s in r['sources']})
    def test_advice_does_not_bypass_version_or_active_boundary(self):
        r=fixture_answer('那你的建議呢','draft',history=['IT-006 v1.1 可以帶出去嗎'])
        self.assertEqual(r['sources'],[])
        r=fixture_answer('那你的建議呢','active',history=['事假還是緊急請假'])
        self.assertEqual(r['status'],'NO_ACTIVE_REGULATIONS')
    def test_training_followup_preserves_unknown_boundary(self):
        first='我上禮拜去參加一個進修，公司說可以補助，我要找誰申請'
        r=fixture_answer(first,'draft')
        self.assertEqual(r['status'],'TRAIN_POST_EVENT')
        r=fixture_answer('但是我上禮拜參加的，可以嗎','draft',history=[first])
        self.assertEqual(r['status'],'TRAIN_POST_EVENT')
        self.assertEqual(r['context_topic'],'外部教育訓練')
        self.assertIn('未訂定外部課程事後補申請',r['answer'])
        self.assertIn('不等於本系統已查證',r['answer'])
        self.assertEqual(r['sources'][0]['source_id'],'TRAIN-003')
    def test_temporary_urgent_reason_followup(self):
        first='我臨時有事，但來不及請假'
        r=fixture_answer(first,'draft')
        self.assertEqual(r['status'],'LEAVE_URGENT_CLARIFY')
        self.assertIn('這個理解是否正確',r['answer'])
        r=fixture_answer('因為臨時有事，所以來不及','draft',history=[first])
        self.assertEqual(r['status'],'LEAVE_URGENT_CLARIFY')
        self.assertEqual(r['context_topic'],'請假')
        self.assertIn('先通知主管',r['answer'])
        self.assertIn('若屬緊急請假',r['answer'])
        self.assertNotIn('三個工作天',r['answer'])
    def test_multiple_leave_sources_keep_common_context(self):
        first='我忘記請假了怎麼辦'
        self.assertGreater(len(fixture_answer(first,'draft')['sources']),1)
        r=fixture_answer('因為突然有事，才來不及','draft',history=[first])
        self.assertEqual(r['status'],'LEAVE_URGENT_CLARIFY')
        self.assertEqual(r['context_topic'],'請假')
    def test_reason_without_context_is_not_assumed_leave(self):
        r=fixture_answer('因為臨時有事，所以來不及','draft')
        self.assertEqual(r['status'],'NOT_PROVIDED')
        self.assertEqual(r['sources'],[])

    def test_followup_amount_still_unknown(self):
        r=fixture_answer('那多少錢','draft',history=['我想報名進修課程，公司能補助嗎'])
        self.assertEqual(r['status'],'UNRESOLVED')
    def test_new_topic_does_not_inherit(self):
        r=fixture_answer('忘記打卡怎麼辦','draft',history=['進修課程補助'])
        self.assertEqual(r['sources'][0]['source_id'],'ATT-002')
        self.assertIsNone(r['context_topic'])
    def test_missing_history_and_active_only(self):
        self.assertEqual(fixture_answer('但是我上禮拜參加的，可以嗎','draft')['status'],'NOT_PROVIDED')
        self.assertEqual(fixture_answer('但是我上禮拜參加的，可以嗎','active',history=['進修課程補助'])['status'],'NO_ACTIVE_REGULATIONS')
    def test_history_is_not_company_fact(self):
        r=fixture_answer('但是可以嗎','draft',history=['公司保證進修補助五萬元'])
        self.assertNotIn('五萬元',r['answer'])

if __name__=='__main__':unittest.main()
