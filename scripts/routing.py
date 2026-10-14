"""依已提供職掌引導詢問單位，僅引用當次允許的條文。"""
import json
import retrieval

def recommend(question,chunks,root):
    data=json.loads((root/'config/department_routes.json').read_text(encoding='utf-8'))
    if data['schema_version']!=1:raise ValueError('不支援部門引導設定')
    q=retrieval.normalize(question)
    available={c['source_id']:c for c in chunks}
    found=[]
    for route in data['routes']:
        matched=[t for t in route['terms'] if retrieval.normalize(t) in q]
        # 所有依據必須存在於本次允許的來源，不能偷讀草案或廢止版。
        if matched and all(s in available for s in route['source_ids']):
            found.append((sum(len(t) for t in matched),route))
    if not found:return None
    found.sort(key=lambda pair:-pair[0])
    winners=[r for score,r in found if score==found[0][0]]
    if len(winners)>1:
        return dict(status='DEPARTMENT_CLARIFY',answer='依提供的職掌，問題可能涉及'+ '、'.join(r['unit'] for r in winners)+'。我理解這可能跨不同單位，請補充是系統操作、資料內容或其他問題，才能給出較合適的詢問方向。',sources=[],departments=[r['unit'] for r in winners])
    route=winners[0]
    sources=[{k:available[s][k] for k in ['source_id','regulation_id','version','source','effective_date','git_commit']} for s in route['source_ids']]
    citations='\n'.join(f'來源：{s["source_id"]}｜版本 {s["version"]}｜{s["source"]}' for s in sources)
    return dict(status='DEPARTMENT_GUIDANCE',answer=route['guidance']+'\n這是依已提供職掌的初步詢問方向，不代表已確認原因或核准資格。\n'+citations,sources=sources,departments=[route['unit']])
