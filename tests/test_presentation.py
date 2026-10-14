import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import chatbot
from fixture_project import fixture_answer
import presentation

class PresentationTests(unittest.TestCase):
    def test_leave_answer_leads_with_practical_point(self):
        r=fixture_answer('我要請特休出國','draft')
        self.assertIn('如果你打算用特休出國，建議提前三個工作天通知主管',r['display_answer'])
        self.assertIn('不是強制期限',r['display_answer'])
        self.assertIn('須依法和你協商',r['display_answer'])
        self.assertIn('LEAVE-004',r['display_answer'])
        self.assertEqual(r['evidence'][0]['source_id'],'LEAVE-004')
    def test_every_clause_has_current_guarded_summary(self):
        chunks=chatbot.assistant.load_draft(chatbot.ROOT)
        for c in chunks:
            with self.subTest(source=c['source_id']):
                text,evidence=presentation.render([c],chatbot.ROOT,'')
                self.assertTrue(text)
                self.assertIn(c['source_id'],text)
                self.assertIn(c['text'].split('\n',1)[1].strip(),evidence[0]['text'])
    def test_changed_clause_does_not_use_old_summary(self):
        c=dict(chatbot.assistant.load_draft(chatbot.ROOT)[3])
        c['text']='## LEAVE-004 特休\n\n測試修訂內容，尚無新版摘要。'
        text,evidence=presentation.render([c],chatbot.ROOT,'特休出國')
        self.assertIn('測試修訂內容',text)
        self.assertNotIn('三個工作天',text)

if __name__=='__main__':unittest.main()
