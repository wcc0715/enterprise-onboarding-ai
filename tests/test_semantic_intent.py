import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import chatbot
import semantic_intent

class SemanticTests(unittest.TestCase):
    def interpretation(self,subject='family'):
        return dict(source_ids=['LEAVE-002','LEAVE-005'],subject=subject,task='leave',urgent=True,advice=False)
    def test_unlisted_relative_routes_leave_not_self_illness(self):
        with patch('semantic_intent.interpret',return_value=self.interpretation()):
            r=chatbot.answer('我表弟突然不舒服，今天要請假','draft',model='mock',provider='cloud')
        self.assertEqual(r['status'],'FAMILY_LEAVE_CLARIFY')
        self.assertEqual(r['interpretation_status'],'模型意圖解析成功')
        self.assertNotIn('LEAVE-003',{s['source_id'] for s in r['sources']})
    def test_semantic_advice_keeps_pet_context(self):
        meaning=self.interpretation('pet');meaning['advice']=True
        with patch('semantic_intent.interpret',return_value=meaning):
            r=chatbot.answer('你覺得我現在該做什麼','draft',history=['我家狗吐了，我要請假'],model='mock',provider='cloud')
        self.assertEqual(r['status'],'PET_LEAVE_ADVICE')
    def test_guards_skip_model(self):
        with patch('semantic_intent.interpret') as parse:
            for q in ['請查我的薪水金額','IT-006 v1.1 可以帶出去嗎','教育訓練補助上限多少']:
                chatbot.answer(q,'draft',model='mock',provider='cloud')
            chatbot.answer('我弟弟生病要請假','active',model='mock',provider='cloud')
            chatbot.answer('你的建議呢','draft',history=['IT-006 v1.1 可以帶出去嗎'],model='mock',provider='cloud')
        parse.assert_not_called()
    def test_invalid_source_and_subject_rejected(self):
        chunks=[dict(source_id='LEAVE-003',text='病假')]
        for meaning in [dict(source_ids=['FAKE'],subject='self',task='leave',urgent=False,advice=False),dict(source_ids=['LEAVE-003'],subject='pet',task='leave',urgent=False,advice=False)]:
            with patch('cloud_generation.request_json',return_value=meaning):
                with self.assertRaises(ValueError):semantic_intent.interpret('問題',[],chunks,'mock')
    def test_error_classification_does_not_expose_body(self):
        from urllib.error import HTTPError
        import cloud_generation
        error=HTTPError('https://ollama.com',401,'secret',{},None)
        self.assertEqual(cloud_generation.error_code(error),'AUTH_FAILED')

if __name__=='__main__':unittest.main()
