#!/usr/bin/env python3
"""本機條文檢索與摘錄式回答；無語言模型、無網路、無 HRM。"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import regulations as store
import retrieval

ROOT = Path(__file__).resolve().parents[1]

def normalize(text):
    return re.sub(r'\s+', '', text.lower())

def load_current(root):
    """驗證整份索引與現行快照，過期、竄改或混版時停止問答。"""
    manifest_path=root/'metadata/regulation_manifest.json'
    manifest_text=manifest_path.read_text(encoding='utf-8')
    manifest=json.loads(manifest_text)
    index=store.read(root/'knowledge_base/current.json')
    if index['manifest_sha256']!=store.sha(manifest_text):
        raise ValueError('規章資料已變更，知識庫尚未同步，請管理者執行 sync。')
    expected=[]
    seen=set()
    for r in manifest['regulations']:
        a=r['active']
        if not a:
            continue
        if a['status']!='ACTIVE' or a['effective_date']>datetime.now().astimezone().date().isoformat():
            raise ValueError('現行規章狀態或生效日期不符合要求。')
        path=(root/a['source']).resolve()
        if not path.is_relative_to(root.resolve()) or path.suffix!='.md':
            raise ValueError('來源文件位置不符合要求。')
        text=path.read_text(encoding='utf-8')
        if store.sha(text)!=a['sha256']:
            raise ValueError('正式來源雜湊不符，請管理者檢查。')
        parsed=store.clauses(text)
        if not parsed:
            raise ValueError('正式來源沒有可解析條文。')
        for key,body in parsed.items():
            if key in seen or not key.startswith(r['id']+'-'):
                raise ValueError('來源編號重複或不符合規章。')
            seen.add(key)
            expected.append(dict(source_id=key,regulation_id=r['id'],version=a['version'],source=a['source'],
                                 document_sha256=a['sha256'],chunk_sha256=store.sha(body),
                                 effective_date=a['effective_date'],git_commit=a['git_commit'],text=body))
    if index['chunks']!=expected:
        raise ValueError('索引與現行版本不一致，請管理者重新同步。')
    return index['chunks']

def load_draft(root):
    """僅供管理者明示選擇的草案測試，不寫入正式索引。"""
    manifest=store.read(root/'metadata/regulation_manifest.json')
    chunks=[]
    for r in manifest['regulations']:
        d=r['draft']
        path=(root/d['source']).resolve()
        if d['status']!='DRAFT' or not path.is_relative_to(root.resolve()):
            raise ValueError('草案來源或狀態不符。')
        text=path.read_text(encoding='utf-8')
        if store.sha(text)!=d['sha256']:
            raise ValueError('草案已修改但 metadata 未更新，請先審閱與 revise。')
        for key,body in store.clauses(text).items():
            chunks.append(dict(source_id=key,regulation_id=r['id'],version=d['version'],source=d['source'],
                               effective_date=None,git_commit=None,text=body))
    return chunks

def respond(question, root=ROOT, mode='active'):
    if mode not in {'active','draft'}:
        raise ValueError('不支援的模式。')
    try:
        vocabulary=retrieval.load(root)
        query=retrieval.expand(question,vocabulary)
    except (OSError,ValueError,KeyError,TypeError) as e:
        return dict(status='RETRIEVAL_UNAVAILABLE',answer='檢索詞彙設定無法使用，請管理者檢查；不推測制度答案。',sources=[])
    q=query['expanded']
    if not query['original']:
        return dict(status='CLARIFY',answer='請輸入您想詢問的制度問題。',sources=[])
    if '特休' in q and any(t in q for t in ['我還有', '剩幾', '剩多少', '餘額', '剩餘']):
        return dict(status='HRM_UNAVAILABLE',answer='目前無法直接查詢您的個人特休餘額，請登入公司 HRM 系統查看。',sources=[])
    try:
        chunks=load_current(root) if mode=='active' else load_draft(root)
    except (OSError,ValueError,KeyError,TypeError) as e:
        return dict(status='INDEX_UNAVAILABLE',answer=f'目前無法提供現行規章回答：{e}',sources=[])
    if not chunks:
        return dict(status='NO_ACTIVE_REGULATIONS',answer='目前尚未發布可供查詢的 ACTIVE 規章，無法提供現行制度答案。請假問題可向 HR 確認。',sources=[])
    if 'leave-notice' in query['intent_ids'] and not any(t in q for t in ['事假','特休','病假','緊急請假']):
        related=[c for c in chunks if c['source_id'] in {'LEAVE-001','LEAVE-004'}]
        if related:
            intro='您預計使用特休還是一般事假？出國或旅遊本身無法判定假別，通知與申請要求需依假別區分。若不確定假別，請向 HR 確認。'
            sections=[];sources=[]
            for c in related:
                title='若使用一般事假' if c['source_id']=='LEAVE-001' else '若使用特休'
                body=c['text'].split('\n',1)[1].strip()
                sections.append(title+'：\n'+body+f'\n來源：{c["source_id"]}｜版本 {c["version"]}｜{c["source"]}')
                sources.append({k:c[k] for k in ['source_id','regulation_id','version','source','effective_date','git_commit']})
            return dict(status='LEAVE_TYPE_CLARIFY',answer=intro+'\n\n'+'\n\n'.join(sections),sources=sources,retrieval=query)
    if '緊急請假' not in q and any(t in q for t in ['請假', '假單']) and any(t in q for t in ['忘記', '忘了', '漏申請', '沒申請', '未申請', '來不及']):
        related=[c for c in chunks if c['source_id'] in {'LEAVE-002','LEAVE-005'}]
        if related:
            intro='您是忘記事前申請，還是已請假但尚未登錄 HRM？目前提供的規章未訂定一般漏申請的補辦期限或完整處理方式，請向 HR 確認。不能直接將緊急請假的補登方式套用所有漏申請情況。'
            sections=[]
            sources=[]
            for c in related:
                heading='一般請假流程' if c['source_id']=='LEAVE-002' else '若屬緊急請假，規章另有以下規定'
                body=c['text'].split('\n',1)[1].strip()
                sections.append(heading+'：\n'+body+f'\n來源：{c["source_id"]}｜版本 {c["version"]}｜{c["source"]}')
                sources.append({k:c[k] for k in ['source_id','regulation_id','version','source','effective_date','git_commit']})
            return dict(status='LEAVE_FOLLOWUP',answer=intro+'\n\n'+'\n\n'.join(sections),sources=sources)
    training_terms=['外部課程','外部教育訓練','進修','研習','職能訓練','外部培訓']
    past_terms=['上禮拜','上星期','上週','上個月','已經參加','已參加','參加過','事後','補申請','昨天參加']
    if any(t in q for t in training_terms) and any(t in q for t in past_terms):
        c=next((c for c in chunks if c['source_id']=='TRAIN-003'),None)
        if c:
            body=c['text'].split('\n',1)[1].strip()
            text='目前提供的規章要求事前申請，但未訂定外部課程事後補申請規則，因此無法判定您已參加的課程是否可以補申請或取得補助。您提到公司說可以補助，這不等於本系統已查證核定紀錄；請向主管或 HR 確認是否已有事前申請或核定，以及適用的處理流程。'
            return dict(status='TRAIN_POST_EVENT',answer=text+'\n\n規章依據：\n'+body+f'\n來源：{c["source_id"]}｜版本 {c["version"]}｜{c["source"]}',sources=[{k:c[k] for k in ['source_id','regulation_id','version','source','effective_date','git_commit']}],unresolved_id='UNK-011')
    unknown=store.read(root/'metadata/unresolved_items.json')
    active_ids={c['regulation_id'] for c in chunks}
    for item in unknown['items']:
        groups=vocabulary['unknown_rules'].get(item['id'])
        if item['regulation'] in active_ids and item['status']=='UNRESOLVED' and groups and all(any(t in q for t in g) for g in groups):
            unit=item['consultation_unit']
            suffix=f'請進一步向 {unit} 確認。' if unit else '目前提供的資料也未確認負責單位，請先確認負責單位後詢問。'
            answer=f'目前提供的公司規章尚未訂定「{item["question"]}」。{suffix}'
            if item['id']=='UNK-009':
                answer='目前提供的公司規章尚未訂定統一補助上限。建議向 HR 確認。'
            return dict(status='UNRESOLVED',answer=answer,sources=[],unresolved_id=item['id'])
    if query['original'] in ['請假', '我要請假', '我要申請設備', '申請設備']:
        return dict(status='CLARIFY',answer='請補充假別或設備類型，以便查找對應規章。請假細節可向 HR 確認。',sources=[])
    hits=retrieval.rank(chunks,query,vocabulary)
    if not hits:
        return dict(status='NOT_PROVIDED',answer=f'目前提供的{"現行規章" if mode=="active" else "草案資料"}中，找不到此問題的明確依據。請補充問題細節；若負責單位已確認，請向該單位詢問。',sources=[])
    hits.sort(key=lambda pair:(-pair[0],pair[1]['source_id']))
    selected=[c for _,c in hits[:4]]
    # 整條摘錄保留例外，絕不由關鍵字推定規則或生成新制度。
    sections=[]
    sources=[]
    for c in selected:
        body=c['text'].split('\n',1)[1].strip()
        sections.append(body+f'\n來源：{c["source_id"]}｜版本 {c["version"]}｜{c["source"]}')
        sources.append({k:c[k] for k in ['source_id','regulation_id','version','source','effective_date','git_commit']})
    return dict(retrieval=query,status='EXTRACTED',answer='以下為檢索到的相關規章原文，請確認是否對應您的情境：\n\n'+'\n\n'.join(sections),sources=sources)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('question')
    parser.add_argument('--json',action='store_true')
    args=parser.parse_args()
    result=respond(args.question)
    print(json.dumps(result,ensure_ascii=False,indent=2) if args.json else result['answer'])

if __name__=='__main__':
    main()
