"""可維護的詞彙正規化與意圖檢索，不產生規章內容。"""
import json
import re
import unicodedata

def normalize(text):
    return re.sub(r'\s+','',unicodedata.normalize('NFKC',text).lower())

def load(root):
    data=json.loads((root/'config/retrieval_vocabulary.json').read_text(encoding='utf-8'))
    if data['schema_version']!=1:
        raise ValueError('不支援詞彙設定版本')
    def terms(values):
        if not isinstance(values,list) or not values or any(not isinstance(t,str) or not t.strip() for t in values):
            raise ValueError('詞彙須為非空字串清單')
    for key,values in data['topics'].items():
        if not re.fullmatch(r'(LEAVE|ATT|IT|SEC|HR|ADMIN|TRAIN)-\d{3}',key):
            raise ValueError('來源編號不符合格式')
        terms(values)
    for c in data['concepts']:
        terms([c['canonical']]);terms(c['aliases'])
    for groups in data['unknown_rules'].values():
        if not groups:raise ValueError('未知意圖缺少群組')
        for group in groups:terms(group)
    for rule in data['context_rules']:
        if not rule['all_groups']:raise ValueError('意圖必須有匹配条件')
        for group in rule['all_groups']:terms(group)
        terms(rule['expand'])
        if any(s not in data['topics'] for s in rule['source_ids']):
            raise ValueError('意圖來源未登錄')
    return data

def expand(question,data):
    original=normalize(question)
    additions=[];matched=[];targets=[]
    # 單次展開，避免同義詞遞迴引入不相關意圖。
    for c in data['concepts']:
        if any(normalize(a) in original for a in c['aliases']):
            additions.append(normalize(c['canonical']))
    expanded=original+' '+ ' '.join(dict.fromkeys(additions))
    for rule in data['context_rules']:
        if all(any(normalize(t) in expanded for t in group) for group in rule['all_groups']):
            matched.append(rule['id']);targets.extend(rule['source_ids']);additions.extend(rule['expand'])
    return dict(original=original,expanded=original+' '+' '.join(dict.fromkeys(normalize(a) for a in additions)),
                expanded_terms=list(dict.fromkeys(additions)),intent_ids=matched,target_ids=list(dict.fromkeys(targets)))

def rank(chunks,query,data):
    hits=[];q=query['expanded']
    for c in chunks:
        code=c['source_id']
        title=normalize(c['text'].splitlines()[0].split(' ',2)[-1])
        matched={normalize(t) for t in data['topics'].get(code,[]) if normalize(t) in q}
        score=sum(len(t) for t in matched)+(10 if code in query['target_ids'] else 0)
        if code.lower() in q:score+=30
        if title and title in q:score+=len(title)
        if score:hits.append((score,c))
    return hits
