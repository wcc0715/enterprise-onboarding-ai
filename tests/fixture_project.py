"""未發布情境的隔離測試資料；不依賴真實專案是否已發布。"""
import atexit
import json
from pathlib import Path
import shutil
import tempfile
import chatbot

PROJECT=Path(__file__).resolve().parents[1]
_temporary=tempfile.TemporaryDirectory(prefix="unpublished-fixture-")
atexit.register(_temporary.cleanup)
ROOT=Path(_temporary.name)
for name in ["regulations","metadata","config","knowledge_base"]:
    shutil.copytree(PROJECT/name,ROOT/name)
manifest_path=ROOT/"metadata/regulation_manifest.json"
m=json.loads(manifest_path.read_text())
for r in m["regulations"]:r["active"]=None
manifest_path.write_text(json.dumps(m,ensure_ascii=False,indent=2))

def fixture_answer(*args,**kwargs):
    kwargs.setdefault("root",ROOT)
    return chatbot.answer(*args,**kwargs)
