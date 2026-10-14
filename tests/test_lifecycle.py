"""隔離工作目錄驗證生命週期；不變更正式規章。"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
import io

PROJECT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('regulations',PROJECT/'scripts/regulations.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=(Path(self.tmp.name)/'fixture').resolve()
        shutil.copytree(PROJECT,self.root,ignore=shutil.ignore_patterns('.git','__pycache__'))
        self.original=m.ROOT,m.MANIFEST
        m.ROOT=self.root; m.MANIFEST=self.root/'metadata/regulation_manifest.json'
        m.git('init')
        m.git('config','user.name','Test Fixture')
        m.git('config','user.email','fixture@example.invalid')
        m.git('add','.'); m.git('commit','-m','fixture')
    def tearDown(self):
        m.ROOT,m.MANIFEST=self.original
        self.tmp.cleanup()
    def test_draft_excluded_and_failure_preserves_index(self):
        m.sync(Namespace())
        self.assertEqual(m.read(self.root/'knowledge_base/current.json')['chunks'],[])
        m.publish(Namespace(id='LEAVE',confirm=True,effective_date='2026-10-14',summary='fixture only'))
        m.sync(Namespace())
        index=(self.root/'knowledge_base/current.json').read_bytes()
        self.assertEqual(len(m.read(self.root/'knowledge_base/current.json')['chunks']),5)
        r=m.read(m.MANIFEST)['regulations'][0]
        (self.root/r['active']['source']).write_text('corrupt',encoding='utf-8')
        with self.assertRaises(ValueError):m.sync(Namespace())
        self.assertEqual((self.root/'knowledge_base/current.json').read_bytes(),index)
        self.assertEqual(m.read(self.root/'knowledge_base/update_log.json')[-1]['result'],'FAILED')
    def test_confirmation_and_unknown_block(self):
        with self.assertRaises(ValueError):m.publish(Namespace(id='LEAVE',confirm=False,effective_date='2026-10-14',summary='test'))
        unresolved=m.read(self.root/'metadata/unresolved_items.json')
        unresolved['items'][0]['blocks_publication']=None
        m.atomic(self.root/'metadata/unresolved_items.json',unresolved)
        m.git('add','.');m.git('commit','-m','fixture unknown block')
        with self.assertRaises(ValueError):m.publish(Namespace(id='IT',confirm=True,effective_date='2026-10-14',summary='test'))
    def test_add_modify_delete_report(self):
        (self.root/'regulations/LEAVE.md').unlink()
        with (self.root/'regulations/ATT.md').open('a',encoding='utf-8') as f:f.write('\n測試修改\n')
        (self.root/'regulations/NEW.md').write_text('# fixture',encoding='utf-8')
        out=io.StringIO()
        with redirect_stdout(out):m.check(Namespace(base='HEAD',output=None))
        rows=json.loads(out.getvalue())['changes']
        types={r['regulation_id']:r['change_type'] for r in rows}
        self.assertEqual(types['LEAVE'],'DELETED')
        self.assertEqual(types['ATT'],'MODIFIED')
        self.assertEqual(types['NEW'],'ADDED')
    def test_draft_preserves_active_and_retirement(self):
        m.publish(Namespace(id='LEAVE',confirm=True,effective_date='2026-10-13',summary='fixture'))
        active=m.read(m.MANIFEST)['regulations'][0]['active']
        with (self.root/'regulations/LEAVE.md').open('a',encoding='utf-8') as f:f.write('\n測試修訂\n')
        m.revise(Namespace(id='LEAVE',version='0.2.0',updated_date='2026-10-14',summary='fixture'))
        self.assertEqual(m.read(m.MANIFEST)['regulations'][0]['active'],active)
        m.git('add','.');m.git('commit','-m','fixture revision')
        m.publish(Namespace(id='LEAVE',confirm=True,effective_date='2026-10-14',summary='fixture revision'))
        manifest=m.read(m.MANIFEST)['regulations'][0]
        self.assertEqual(manifest['history'][0]['status'],'RETIRED')
        m.sync(Namespace())
        self.assertEqual({c['version'] for c in m.read(self.root/'knowledge_base/current.json')['chunks']},{'0.2.0'})
        m.retire(Namespace(id='LEAVE',confirm=True,summary='fixture'))
        m.sync(Namespace())
        self.assertEqual(m.read(self.root/'knowledge_base/current.json')['chunks'],[])

if __name__=='__main__':unittest.main()
