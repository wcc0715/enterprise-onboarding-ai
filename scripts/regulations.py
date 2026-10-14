#!/usr/bin/env python3
"""離線規章生命週期工具；只使用 Python 標準函式庫及 Git。"""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from contextlib import contextmanager

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'metadata/regulation_manifest.json'

def git(*args, check=True):
    executable = os.environ.get('ONBOARDING_GIT') or shutil.which('git')
    if not executable:
        raise ValueError('找不到 Git；請設定 ONBOARDING_GIT。')
    return subprocess.run([executable, '-C', str(ROOT), *args], text=True,
                          encoding='utf-8', capture_output=True, check=check)

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.update-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)

def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def source(path):
    resolved = (ROOT / path).resolve()
    if not resolved.is_relative_to(ROOT) or resolved.suffix != '.md':
        raise ValueError('來源必須為專案內可解析 Markdown。')
    return resolved.read_text(encoding='utf-8')

def clauses(text):
    matches = list(re.finditer(r'^## ([A-Z]+-\d{3}) (.+)$', text, re.M))
    return {m[1]: text[m.start():matches[i+1].start() if i+1 < len(matches) else len(text)].strip()
            for i, m in enumerate(matches)}

@contextmanager
def lock():
    path = ROOT / 'metadata/.operation.lock'
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError('已有更新作業執行；中斷後請確認無執行程序再移除鎖定檔。')
    try:
        os.close(fd)
        yield
    finally:
        path.unlink()

def now():
    return datetime.now(timezone.utc).isoformat()

def check(args):
    current = read(MANIFEST)
    baseline = git('show', f'{args.base}:metadata/regulation_manifest.json', check=False)
    old = json.loads(baseline.stdout) if baseline.returncode == 0 else {'regulations': []}
    before = {r['id']: r for r in old['regulations']}
    after = {r['id']: r for r in current['regulations']}
    paths = set(git('ls-tree', '-r', '--name-only', args.base, '--', 'regulations').stdout.splitlines())
    paths |= {str(p.relative_to(ROOT)) for p in (ROOT/'regulations').rglob('*.md')}
    paths = {p for p in paths if p.endswith('.md') and not p.startswith(('regulations/releases/','regulations/revisions/'))}
    rows = []
    for path in sorted(paths):
        previous = git('show', f'{args.base}:{path}', check=False)
        old_text = previous.stdout if previous.returncode == 0 else ''
        exists = (ROOT/path).exists()
        new_text = source(path) if exists else ''
        associated = next((r for r in after.values() if r.get('draft', {}).get('source') == path), None)
        associated_old = next((r for r in before.values() if r.get('draft', {}).get('source') == path), None)
        if old_text == new_text and associated == associated_old:
            continue
        code = (associated or associated_old or {}).get('id', Path(path).stem)
        a, b = clauses(old_text), clauses(new_text)
        changed = [key for key in sorted(a.keys() | b.keys()) if a.get(key) != b.get(key)]
        row = dict(regulation_id=code, name=(associated or associated_old or {}).get('name','未登錄'),
                   old_version=(associated_old or {}).get('draft',{}).get('version'),
                   new_version=(associated or {}).get('draft',{}).get('version'),
                   changed_clauses=changed, before={key:a.get(key) for key in changed},
                   after={key:b.get(key) for key in changed},
                   change_type='ADDED' if previous.returncode else 'DELETED' if not exists else 'MODIFIED',
                   publication_status='DRAFT' if associated else 'UNREGISTERED',
                   affects_existing_knowledge_base=bool((associated or associated_old or {}).get('active')),
                   source=path, content_before=old_text, content_after=new_text,
                   metadata_before=associated_old, metadata_after=associated,
                   hash_matches_metadata=bool(associated and exists and sha(new_text)==associated['draft']['sha256']),
                   diff=''.join(difflib.unified_diff(old_text.splitlines(True),new_text.splitlines(True),fromfile=f'{args.base}/{path}',tofile=path)))
        rows.append(row)
    report = dict(checked_at=now(),base=args.base,changes=rows,
                  note='影響欄表示修訂涉及既有 ACTIVE 規章；草案變更不會自動更新正式知識庫。刪除工作文件不等於廢止。')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if args.output:
        out=(ROOT/args.output).resolve()
        if not out.is_relative_to(ROOT):
            raise ValueError('報告必須位於專案內。')
        atomic(out,report)

def revise(args):
    with lock():
        manifest=read(MANIFEST)
        r=next(r for r in manifest['regulations'] if r['id']==args.id)
        versions=[v['version'] for v in r['history']] + ([r['active']['version']] if r['active'] else [])
        if not re.fullmatch(r'\d+\.\d+\.\d+',args.version) or args.version in versions:
            raise ValueError('需提供未發布過的三段數字版本號。')
        r['draft'].update(version=args.version,status='DRAFT',sha256=sha(source(r['draft']['source'])),
                          updated_date=args.updated_date,summary=args.summary)
        atomic(MANIFEST,manifest)

def publish(args):
    if not args.confirm:
        raise ValueError('發布需要使用者明確確認後提供 --confirm；Git Commit 不等於發布。')
    datetime.strptime(args.effective_date,'%Y-%m-%d')
    with lock():
        manifest=read(MANIFEST)
        r=next(r for r in manifest['regulations'] if r['id']==args.id)
        d=r['draft']
        if d['status']!='DRAFT':
            raise ValueError('只有 DRAFT 可發布。')
        unresolved=[i for i in read(ROOT/'metadata/unresolved_items.json')['items'] if i['regulation']==args.id and i['status']=='UNRESOLVED']
        if any(i['blocks_publication'] is not False for i in unresolved):
            raise ValueError('請由發布者確認該規章所有未知項目是否阻擋發布；true/null 均阻擋。')
        content=source(d['source'])
        if sha(content)!=d['sha256']:
            raise ValueError('草案雜湊不符；先執行 revise 更新 metadata 並審閱。')
        if git('status','--porcelain','--',d['source'],'metadata').stdout:
            raise ValueError('規章及 metadata 必須先 Commit。')
        commit=git('rev-parse','HEAD').stdout.strip()
        if git('show',f'{commit}:{d["source"]}').stdout!=content:
            raise ValueError('來源不符合 Commit。')
        snapshot=ROOT/'regulations/releases'/args.id/f'{d["version"]}.md'
        if snapshot.exists():
            raise ValueError('版本快照已存在，禁止覆蓋。')
        if r['active'] and args.effective_date<=r['active']['effective_date']:
            raise ValueError('新版生效日須晚於現行版；預約發布尚未支援。')
        if args.effective_date>datetime.now().astimezone().date().isoformat():
            raise ValueError('預約生效尚未支援；請到生效日再發布。')
        snapshot.parent.mkdir(parents=True,exist_ok=True)
        snapshot.write_text(content,encoding='utf-8')
        release=dict(d,status='ACTIVE',source=str(snapshot.relative_to(ROOT)),effective_date=args.effective_date,
                     git_commit=commit,published_at=now(),summary=args.summary)
        if r['active']:
            r['history'].append(dict(r['active'],status='RETIRED',retired_at=now()))
        r['active']=release
        atomic(MANIFEST,manifest)
        print('已發布；請 Commit 發布快照與 metadata，再執行 sync。')

def retire(args):
    if not args.confirm:
        raise ValueError('廢止須經使用者確認並提供 --confirm。')
    with lock():
        manifest=read(MANIFEST)
        r=next(r for r in manifest['regulations'] if r['id']==args.id)
        if not r['active']:
            raise ValueError('沒有 ACTIVE 版本。')
        r['history'].append(dict(r['active'],status='RETIRED',retired_at=now(),retirement_summary=args.summary))
        r['active']=None
        atomic(MANIFEST,manifest)
        print('已廢止；請 Commit 後 sync。')

def sync(args):
    with lock():
        log=ROOT/'knowledge_base/update_log.json'
        records=read(log) if log.exists() else []
        try:
            chunks=[]
            manifest=read(MANIFEST)
            for r in manifest['regulations']:
                active=r['active']
                if not active:
                    continue
                if active['status']!='ACTIVE':
                    raise ValueError('現行版本狀態不符。')
                if active['effective_date'] > datetime.now().astimezone().date().isoformat():
                    raise ValueError('尚未生效的規章不得進入索引。')
                content=source(active['source'])
                if sha(content)!=active['sha256']:
                    raise ValueError('發布快照雜湊不符。')
                parsed=clauses(content)
                if not parsed or any(not key.startswith(r['id']+'-') for key in parsed):
                    raise ValueError('缺少條文或來源編號不符合規章。')
                for key,text in parsed.items():
                    chunks.append(dict(source_id=key,regulation_id=r['id'],version=active['version'],
                                       source=active['source'],document_sha256=active['sha256'],
                                       chunk_sha256=sha(text),effective_date=active['effective_date'],
                                       git_commit=active['git_commit'],text=text))
            old=read(ROOT/'knowledge_base/current.json') if (ROOT/'knowledge_base/current.json').exists() else {'chunks':[]}
            a={c['source_id']:c for c in old['chunks']}
            b={c['source_id']:c for c in chunks}
            affected=[k for k in sorted(a.keys()|b.keys()) if a.get(k)!=b.get(k)]
            payload=dict(schema_version=1,built_at=now(),manifest_sha256=sha(MANIFEST.read_text(encoding='utf-8')),chunks=chunks)
            atomic(ROOT/'knowledge_base/current.json',payload)
            records.append(dict(at=now(),result='SUCCESS',chunk_count=len(chunks),affected_source_ids=affected))
        except Exception as e:
            records.append(dict(at=now(),result='FAILED',error=str(e)))
            atomic(log,records)
            raise
        atomic(log,records)
        print(f'同步成功：{len(chunks)} 區塊；受影響 {len(affected)} 區塊。')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    c=sub.add_parser('check'); c.add_argument('--base',default='HEAD'); c.add_argument('--output')
    c=sub.add_parser('revise'); c.add_argument('id'); c.add_argument('--version',required=True); c.add_argument('--updated-date',required=True); c.add_argument('--summary',required=True)
    c=sub.add_parser('publish'); c.add_argument('id'); c.add_argument('--effective-date',required=True); c.add_argument('--summary',required=True); c.add_argument('--confirm',action='store_true')
    c=sub.add_parser('retire'); c.add_argument('id'); c.add_argument('--summary',required=True); c.add_argument('--confirm',action='store_true')
    sub.add_parser('sync')
    args=parser.parse_args()
    try:
        if args.command=='check':
            git('rev-parse','--verify',args.base)
        if args.command=='revise':
            datetime.strptime(args.updated_date,'%Y-%m-%d')
        globals()[args.command](args)
    except (ValueError,KeyError,StopIteration,OSError,subprocess.CalledProcessError) as e:
        parser.exit(1,f'操作失敗：{e}\n')

if __name__=='__main__':
    main()
