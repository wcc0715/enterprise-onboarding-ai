"""解析明示規章版本並限制候選，不從檔名推定發布或生效。"""
import re
import retrieval

def canonical(version):
    numbers=[int(n) for n in version.split('.')]
    return tuple(numbers+[0]*(3-len(numbers)))

def constraints(question):
    q=retrieval.normalize(question)
    ids=list(dict.fromkeys(m.upper() for m in re.findall(r'(?:leave|att|it|sec|hr|admin|train)-\d{3}',q)))
    requested=[];excluded=[]
    for m in re.finditer(r'(?:v|版本)(\d+\.\d+(?:\.\d+)?)',q):
        prefix=q[max(0,m.start()-8):m.start()]
        target=excluded if any(prefix.endswith(t) for t in ['不要用','不用','不使用','不要使用','排除']) else requested
        target.append(m[1])
    return dict(ids=ids,requested=list(dict.fromkeys(requested)),excluded=list(dict.fromkeys(excluded)))

def restrict(question,chunks):
    c=constraints(question)
    if not c['requested'] and not c['excluded']:return chunks,None
    if len(c['requested'])>1 or len(c['ids'])!=1:
        return [],dict(status='VERSION_CLARIFY',answer='你想查哪一份規章、哪一個版本？請提供規章編號與版本，例如 IT-006 v1.2。我會依你指定的版本查找，不自行換用其他版本。',sources=[])
    code=c['ids'][0]
    candidates=[x for x in chunks if x['source_id']==code]
    if c['requested']:
        wanted=c['requested'][0]
        candidates=[x for x in candidates if canonical(x['version'])==canonical(wanted)]
    candidates=[x for x in candidates if all(canonical(x['version'])!=canonical(v) for v in c['excluded'])]
    if not candidates:
        label='v'+c['requested'][0] if c['requested'] else '符合排除條件的版本'
        return [],dict(status='VERSION_UNAVAILABLE',answer=f'目前提供的資料在這個查詢模式下，沒有可用的 {code} {label}。我不會改用其他版本代答。若是未提供的歷史版本，請補充原文；若是尚未發布的草案，只能在草案測試模式查看。',sources=[],requested_version=c['requested'],excluded_versions=c['excluded'])
    return candidates,None
