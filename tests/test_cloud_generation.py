import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import chatbot
class CloudGenerationTests(unittest.TestCase):
    def test_missing_key_falls_back_without_exposing_secrets(self):
        with patch.dict('os.environ',{},clear=True):
            r=chatbot.answer('特休怎麼申請','draft',model='gemma4:31b',provider='cloud')
        self.assertTrue(r['generation_fallback'])
        self.assertIn('不是強制期限',r['display_answer'])
    def test_capability_limits_do_not_call_cloud(self):
        with patch('cloud_generation.generate') as generation:
            r=chatbot.answer('請查我的薪水金額','draft',model='gemma4:31b',provider='cloud')
        generation.assert_not_called()
        self.assertEqual(r['status'],'PERSONAL_DATA_UNAVAILABLE')
    def test_success_still_marks_draft_and_review(self):
        with patch('semantic_intent.interpret',return_value=dict(source_ids=['LEAVE-004'],subject='unknown',task='leave',urgent=False,advice=False)),patch('cloud_generation.generate',return_value='建議提前三個工作天通知，不是強制。'):
            r=chatbot.answer('特休怎麼申請','draft',model='gemma4:31b',provider='cloud')
        self.assertIn('尚未發布或生效',r['display_answer'])
        self.assertTrue(r['generation_review_required'])
        self.assertEqual(r['sources'][0]['source_id'],'LEAVE-004')
if __name__=='__main__':unittest.main()
