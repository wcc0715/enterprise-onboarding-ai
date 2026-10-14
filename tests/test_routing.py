import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import chatbot
import routing

class RoutingTests(unittest.TestCase):
    def test_financial_system_failure_is_not_diagnosed(self):
        r=chatbot.answer('我的財務系統打不開，是沒有權限嗎','draft')
        self.assertEqual(r['status'],'DEPARTMENT_GUIDANCE')
        self.assertEqual(r['departments'],['IT'])
        self.assertIn('不能判定您是否缺少權限',r['answer'])
        self.assertIn('向主管提出業務需求',r['answer'])
        self.assertNotIn('財務部門',r['answer'])
    def test_different_system_wording(self):
        for q in ['報帳系統進不去怎麼辦','我無法登入公司的系統','公司的程式開不了']:
            with self.subTest(q=q):
                r=chatbot.answer(q,'draft')
                self.assertEqual(r['status'],'DEPARTMENT_GUIDANCE')
                self.assertIn('IT',r['answer'])
    def test_unknown_details_still_get_initial_department(self):
        r=chatbot.answer('空調的問題應該找誰','draft')
        self.assertEqual(r['status'],'DEPARTMENT_GUIDANCE')
        self.assertIn('行政部門',r['answer'])
    def test_unavailable_sources_prevent_routing(self):
        self.assertIsNone(routing.recommend('財務系統打不開',[],chatbot.ROOT))
        self.assertEqual(chatbot.answer('財務系統打不開','active')['status'],'NO_ACTIVE_REGULATIONS')
    def test_unconfirmed_department_is_not_invented(self):
        r=chatbot.answer('停車位要找誰','draft')
        self.assertEqual(r['status'],'NOT_PROVIDED')
        self.assertEqual(r['sources'],[])

if __name__=='__main__':unittest.main()
