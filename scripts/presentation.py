"""有條文雜湊保護的易讀回答，完整原文另保留於證據欄。"""
import json
import regulations

def render(chunks,root,question):
    data=json.loads((root/'config/answer_style.json').read_text(encoding='utf-8'))
    if data['schema_version']!=1:raise ValueError('不支援回答樣式版本')
    parts=[];evidence=[]
    for c in chunks:
        entry=data['entries'].get(c['source_id'])
        body=c['text'].split('\n',1)[1].strip()
        # 來源修訂後不使用舊改寫，回退到當前原文。
        text=entry['summary'] if entry and entry['clause_sha256']==regulations.sha(c['text']) else body
        if c['source_id']=='LEAVE-004' and '出國' in question:
            text=text.replace('如果你想申請特休，','如果你打算用特休出國，',1)
        parts.append(text+f'\n依據：{c["source_id"]}｜版本 {c["version"]}')
        evidence.append({'source_id':c['source_id'],'version':c['version'],'text':body})
    return '\n\n'.join(parts),evidence
