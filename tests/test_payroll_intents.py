import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import chatbot
from fixture_project import fixture_answer

class PayrollIntentTests(unittest.TestCase):
    def test_non_banking_day_variants(self):
        for q in ['五號是非銀行營業日，薪水會往後延嗎？','發薪日銀行休息，薪資哪天發？','5號剛好週末，我的薪水會延後嗎？']:
            with self.subTest(q=q):
                r=fixture_answer(q,'draft')
                self.assertEqual(r['status'],'EXTRACTED')
                self.assertIn('提前到前一個銀行營業日',r['display_answer'])
                self.assertIn('前一個月份',r['display_answer'])
                self.assertIn('HR-001',{s['source_id'] for s in r['sources']})
    def test_shortage_and_repair_variants(self):
        for q in ['我的薪資少發了，只能等下個月補嗎？','薪水少給了要找誰補發？','工資算錯，差額什麼時候處理？']:
            with self.subTest(q=q):
                r=fixture_answer(q,'draft')
                self.assertEqual(r['status'],'EXTRACTED')
                self.assertIn('HR 薪酬承辦人員',r['display_answer'])
                self.assertIn('不能直接認定只能等下個月補發',r['display_answer'])
                self.assertIn('沒有固定補發期限',r['display_answer'])
                self.assertIn('HR-002',{s['source_id'] for s in r['sources']})
    def test_general_salary_queries_still_cannot_read_records(self):
        self.assertEqual(fixture_answer('請查我的這個月薪水金額','draft')['status'],'PERSONAL_DATA_UNAVAILABLE')
    def test_non_payroll_bank_question_not_answered_as_payroll(self):
        r=fixture_answer('銀行週末有開嗎','draft')
        self.assertNotIn('HR-001',{s['source_id'] for s in r['sources']})
    def test_active_only_boundary(self):
        self.assertEqual(fixture_answer('我的薪資少發了，只能等下個月補嗎','active')['status'],'NO_ACTIVE_REGULATIONS')

if __name__=='__main__':unittest.main()
