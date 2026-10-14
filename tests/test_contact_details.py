import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import chatbot

class ContactDetailsTests(unittest.TestCase):
    def test_unknown_contacts_are_explicit(self):
        for q in ['請給我 IT 王先生的手機和 HR 電話','IT 的電話幾號？HR 薪酬承辦人員叫什麼名字？','行政分機是多少','人資信箱是什麼','HR 承辦人姓名？']:
            with self.subTest(q=q):
                r=chatbot.answer(q,'draft')
                self.assertEqual(r['status'],'SIMULATED_CONTACTS')
                self.assertIn('全部為虛構',r['display_answer'])
                self.assertIn('@example.invalid',r['display_answer'])
                self.assertEqual(r['sources'],[])
    def test_department_process_not_blocked(self):
        self.assertNotEqual(chatbot.answer('薪資少發應聯絡誰','draft')['status'],'CONTACT_NOT_PROVIDED')
    def test_active_returns_capability_without_draft(self):
        r=chatbot.answer('IT 的電話幾號','active')
        self.assertEqual(r['status'],'CONTACT_NOT_PROVIDED')
        self.assertEqual(r['sources'],[])

if __name__=='__main__':unittest.main()
