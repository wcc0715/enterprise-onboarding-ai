"""十類案例與索引防護：僅使用臨時測試快照，非正式發布。"""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from argparse import Namespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import assistant
import regulations as store

ROOT=Path(__file__).resolve().parents[1]
class AssistantTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'tests')
        self.root=Path(self.tmp.name).resolve()
        for name in ['regulations','metadata','knowledge_base','config']:
            shutil.copytree(ROOT/name,self.root/name)
        self.original=store.ROOT,store.MANIFEST
        store.ROOT=self.root;store.MANIFEST=self.root/'metadata/regulation_manifest.json'
        manifest=store.read(store.MANIFEST)
        for r in manifest['regulations']:
            draft=r['draft']
            path=f'regulations/releases/{r["id"]}/0.1.0.md'
            dest=self.root/path;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(self.root/draft['source'],dest)
            r['active']=dict(draft,status='ACTIVE',source=path,effective_date='2026-10-14',git_commit='TEST_FIXTURE_ONLY',published_at='TEST_FIXTURE_ONLY')
        store.atomic(store.MANIFEST,manifest)
        store.sync(Namespace())
    def tearDown(self):
        store.ROOT,store.MANIFEST=self.original
        self.tmp.cleanup()
    def ask(self,q):return assistant.respond(q,self.root)
    def test_ten_question_categories(self):
        cases=[
            ('上班時間？','EXTRACTED','八小時'),
            ('可以共用帳密？','EXTRACTED','不得共用'),
            ('我要申請設備','CLARIFY','設備類型'),
            ('緊急請假來不及登記？','EXTRACTED','先通知主管'),
            ('特休一定要提前三天批准？','EXTRACTED','非強制期限'),
            ('教育訓練一年補助多少錢？','UNRESOLVED','尚未訂定統一補助上限'),
            ('病假證明要哪些？','EXTRACTED','特殊情況'),
            ('我還有幾天特休？','HRM_UNAVAILABLE','HRM'),
            ('公司提供停車補助嗎？','CLARIFY_INTENT','資訊不足'),
            ('會議室設備故障與冷氣壞了怎麼處理？','EXTRACTED','行政部門'),
        ]
        for q,status,text in cases:
            with self.subTest(q=q):
                result=self.ask(q)
                self.assertEqual(result['status'],status)
                self.assertIn(text,result['answer'])
        result=self.ask('病假證明要哪些？')
        self.assertTrue(any(s['source_id']=='LEAVE-003' and s['version']=='0.1.0' for s in result['sources']))
        self.assertIn('資訊設備故障通知 IT',self.ask(cases[-1][0])['answer'])
    def test_retired_and_stale_index_excluded(self):
        m=store.read(store.MANIFEST)
        m['regulations'][0]['active']=None
        store.atomic(store.MANIFEST,m)
        self.assertEqual(self.ask('病假')['status'],'INDEX_UNAVAILABLE')
        store.sync(Namespace())
        self.assertEqual(self.ask('病假')['status'],'NOT_PROVIDED')
    def test_draft_only_and_index_tamper(self):
        index=self.root/'knowledge_base/current.json'
        d=store.read(index);d['chunks'][0]['text']='測試竄改'
        store.atomic(index,d)
        self.assertEqual(self.ask('病假')['status'],'INDEX_UNAVAILABLE')
        m=store.read(store.MANIFEST)
        for r in m['regulations']:r['active']=None
        store.atomic(store.MANIFEST,m);store.sync(Namespace())
        self.assertEqual(self.ask('病假')['status'],'NO_ACTIVE_REGULATIONS')
    def test_unknown_unit_not_invented(self):
        result=self.ask('設備損壞責任由誰判定？')
        self.assertEqual(result['status'],'UNRESOLVED')
        self.assertIn('未確認負責單位',result['answer'])
    def test_snapshot_tamper_stops_answer(self):
        (self.root/'regulations/releases/LEAVE/0.1.0.md').write_text('corrupt')
        self.assertEqual(self.ask('病假')['status'],'INDEX_UNAVAILABLE')

if __name__=='__main__':unittest.main()
