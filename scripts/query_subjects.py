"""具體名詞优先於通用補助詞；資料缺口不等於公司沒有制度。"""
import json
import retrieval

def unsupported_subsidy(question,chunks,root):
    q=retrieval.normalize(question)
    if not any(t in q for t in ['補助','津貼','補貼']):return None
    data=json.loads((root/'config/query_subjects.json').read_text(encoding='utf-8'))
    if data['schema_version']!=1:raise ValueError('不支援主題設定')
    for subject in data['subsidy_subjects']:
        terms=[retrieval.normalize(t) for t in subject['terms']]
        if any(t in q for t in terms):
            # 未來新增可用規章提及此主題時，不能沿用「未提供」的舊判斷。
            if any(any(t in retrieval.normalize(c['text']) for t in terms) for c in chunks):
                continue
            return subject['name']
    return None
