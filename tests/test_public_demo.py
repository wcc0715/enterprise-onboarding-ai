"""公開入口邊界；使用測試客戶端，不呼叫真實雲端。"""
import importlib.util
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))

@unittest.skipUnless(importlib.util.find_spec('flask'),'請在 .venv 安裝部署依賴')
class PublicDemoTests(unittest.TestCase):
    def setUp(self):
        import web_service
        self.module=web_service
        self.env=patch.dict('os.environ',{'PUBLIC_URL':'https://example.onrender.com','ENABLE_CLOUD':'false'})
        self.env.start();self.addCleanup(self.env.stop)
        self.client=web_service.app.test_client()
    def get(self,path):return self.client.get(path,base_url='https://example.onrender.com')
    def post(self,**overrides):
        data=dict(question='我家狗生病，我要請假',mode='active',history=[],client_version=self.module.chatbot.RUNNING_VERSION)
        data.update(overrides)
        return self.client.post('/api/chat',json=data,base_url='https://example.onrender.com')
    def test_page_only_shows_active_and_simulation(self):
        text=self.get('/').get_data(as_text=True)
        self.assertNotIn('value="draft"',text)
        self.assertIn('面試展示',text)
        self.assertIn('模擬企業',text)
    def test_active_sources_and_no_cloud_without_opt_in(self):
        with patch('web_service.chatbot.semantic_intent.interpret') as model:
            response=self.post()
        model.assert_not_called()
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.json['is_simulated'])
        self.assertTrue(all('/releases/' in s['source'] for s in response.json['sources']))
    def test_draft_is_rejected(self):self.assertEqual(self.post(mode='draft').status_code,403)
    def test_cross_origin_and_host_rejected(self):
        self.assertEqual(self.client.get('/api/status',base_url='https://evil.example').status_code,403)
        self.assertEqual(self.client.post('/api/chat',json={},headers={'Origin':'https://evil.example'},base_url='https://example.onrender.com').status_code,403)
    def test_health_and_secret_not_in_status(self):
        self.assertEqual(self.get('/healthz').status_code,200)
        with patch.dict('os.environ',{'OLLAMA_API_KEY':'TEST_SECRET_NOT_REAL'}):
            self.assertNotIn('TEST_SECRET_NOT_REAL',self.get('/api/status').get_data(as_text=True))
    def test_limits_and_version(self):
        self.assertEqual(self.post(question='x'*1001).status_code,400)
        self.assertEqual(self.post(client_version='old').json['status'],'CLIENT_UPDATE_REQUIRED')
        self.assertEqual(self.client.post('/api/chat',data='x'*17000,content_type='application/json',base_url='https://example.onrender.com').status_code,413)
    def test_budget_exhausted_uses_rules(self):
        with patch.dict('os.environ',{'ENABLE_CLOUD':'true','OLLAMA_API_KEY':'TEST_SECRET_NOT_REAL','CLOUD_REQUESTS_PER_HOUR':'0'}),patch('web_service.chatbot.semantic_intent.interpret') as model:
            self.assertEqual(self.post().status_code,200)
        model.assert_not_called()

if __name__=='__main__':unittest.main()
