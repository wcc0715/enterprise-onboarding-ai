#!/usr/bin/env python3
"""本機條文檢索與摘錄式回答；無語言模型、無網路、無 HRM。"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import regulations as store
import retrieval
import routing
import intent
import presentation
import versions
import query_subjects
import contacts

ROOT = Path(__file__).resolve().parents[1]

def normalize(text):
    return re.sub(r'\s+', '', text.lower())

def load_current(root):
    """驗證整份索引與現行快照，過期、竄改或混版時停止問答。"""
    manifest_path=root/'metadata/regulation_manifest.json'
    manifest_text=manifest_path.read_text(encoding='utf-8')
    manifest=json.loads(manifest_text)
    if not any(r['active'] for r in manifest['regulations']):
        return []
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
    if intent.contact_details_request(question) and not intent.personal_record_request(question) and not intent.restricted_action_request(question):
        return contacts.lookup(question,root,mode)
    personal=intent.personal_record_request(question)
    if personal:
        text='我目前尚未串接 HRM 或員工個人資料，無法查詢或提供'
        text+= '同事或其他員工的薪資、個資等紀錄。' if personal=='others' else '你的實際薪資或其他個人紀錄。'
        if personal=='others' or any(t in normalize(question) for t in ['我是hr','我是主管','我是總經理']):
            text+='即使工作上需要使用這些資料，我目前也無法連接或讀取相關紀錄，或確認你的資料存取授權。'
        text+='如果你需要查詢自己的資料，請登入公司 HRM 查看；薪資問題可以向 HR 薪酬承辦人員確認。'
        return dict(status='PERSONAL_DATA_UNAVAILABLE',answer=text,display_answer=text,sources=[],capability_limit='NO_HRM_OR_PERSONAL_RECORD_ACCESS')
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
    chunks,version_error=versions.restrict(question,chunks)
    if version_error:
        return version_error
    if not chunks:
        return dict(status='NO_ACTIVE_REGULATIONS',answer='目前尚未發布可供查詢的 ACTIVE 規章，無法提供現行制度答案。請假問題可向 HR 確認。',sources=[])
    if '事假' in q and '緊急請假' in q and any(t in q for t in ['建議','該怎麼辦','應該怎麼做']):
        related=[c for c in chunks if c['source_id'] in {'LEAVE-001','LEAVE-002','LEAVE-005'}]
        if {c['source_id'] for c in related}=={'LEAVE-001','LEAVE-002','LEAVE-005'}:
            text='我的建議是：如果現在需要離開或無法到班，先儘速通知主管，說明情況及請假需求。若屬緊急情況，可以先通知，再依實際情況補登 HRM。\n\n你不必先把「事假」和「緊急請假」當成二選一：事假條文也有緊急事故的通知安排；目前資料未說明「緊急請假」是否為獨立假別，也未提供這個情況的假別認定標準。HRM 該選哪個假別，請向 HR 確認，我不能替你認定一定符合資格。'
            sources=[{k:c[k] for k in ['source_id','regulation_id','version','source','effective_date','git_commit']} for c in related]
            text+='\n依據：'+'、'.join(c['source_id']+'｜版本 '+c['version'] for c in related)
            return dict(status='LEAVE_ADVICE',answer=text,display_answer=text,sources=sources,conversation_topic='事假與緊急請假',evidence=[dict(source_id=c['source_id'],version=c['version'],text=c['text'].split('\n',1)[1].strip()) for c in related])
    missing_subject=query_subjects.unsupported_subsidy(question,chunks,root)
    if missing_subject:
        text=f'目前提供的規章沒有「{missing_subject}」制度或上限，我無法確認公司是否提供這項補助，也不能替你猜金額。資料也未指定這項業務的負責單位，需要先確認承辦窗口。'
        return dict(status='SUBJECT_NOT_PROVIDED',answer=text,display_answer=text,sources=[],conversation_topic=missing_subject,missing_subject=missing_subject)
    if intent.equipment_liability(question):
        c=next((c for c in chunks if c['source_id']=='IT-005'),None)
        if c:
            summary,evidence=presentation.render([c],root,question)
            return dict(status='EQUIPMENT_LIABILITY',answer=summary,display_answer=summary,sources=[{k:c[k] for k in ['source_id','regulation_id','version','source','effective_date','git_commit']}],evidence=evidence,conversation_topic='設備損壞責任')
    if intent.data_incident(question):
        c=next((c for c in chunks if c['source_id']=='SEC-006'),None)
        if c:
            body=c['text'].split('\n',1)[1].strip()
            text='請立即通報 IT 或指定資安人員，不要等到明天才說。通報時提供事件時間、收件對象及涉及資料等必要資訊，後續由授權人員評估處理。我目前無法確認事件影響，也沒有規章依據可以替你判定處理期限。'
            # 摘錄現行來源，保留將來修訂時的追溯依據。
            if not all(t in body for t in ['立即通報','事件時間','收件對象','涉及資料']):
                text=body
            text+=f'\n依據：SEC-006｜版本 {c["version"]}'
            return dict(status='DATA_INCIDENT_REPORT',answer=text,display_answer=text,sources=[{k:c[k] for k in ['source_id','regulation_id','version','source','effective_date','git_commit']}],conversation_topic='資料誤寄或外洩',evidence=[dict(source_id=c['source_id'],version=c['version'],text=body)])
    action=intent.restricted_action_request(question)
    if action:
        key='SEC-005' if action=='access_change' else 'IT-006'
        c=next((c for c in chunks if c['source_id']==key),None)
        if c:
            if action=='access_change':
                intro='我可以幫你整理申請方式，但目前沒有連接系統管理功能，無法替你開通或調整權限，也無法確認你的存取授權。請依規章讓主管確認業務需求，再由 IT 評估設定，不是直接開最高權限。'
                body=c['text'].split('\n',1)[1].strip()
                display=intro+'\n\n'+body
            else:
                intro='我可以幫你確認流程，但不能替你認定設備分類或核准攜出。主管同意也不能單獨取代 IT 對敏感設備的認定與評估核准；目前仍需要依設備的實際風險與授權範圍處理。'
                body=c['text'].split('\n',1)[1].strip()
                selected=[line[3:] for line in c['text'].splitlines() if line.startswith(('2. ','3. ','4. ','6. '))]
                display=intro+'\n\n'+'\n'.join(selected) if selected else intro+'\n\n'+body
            citation=f'\n依據：{key}｜版本 {c["version"]}'
            return dict(status='ACTION_UNAVAILABLE',answer=intro+'\n\n'+body+citation,display_answer=display+citation,sources=[{k:c[k] for k in ['source_id','regulation_id','version','source','effective_date','git_commit']}],capability_limit='NO_ADMIN_OR_APPROVAL_ACTIONS',evidence=[dict(source_id=key,version=c['version'],text=body)])
    if '敏感設備' in q and any(t in q for t in ['是什麼','什麼是','哪些','怎麼判斷','算不算','是指','定義','哪種','什麼樣']):
        c=next((c for c in chunks if c['source_id']=='IT-006'),None)
        known_style=store.read(root/'config/answer_style.json')['entries'].get('IT-006')
        item=next((i for i in store.read(root/'metadata/unresolved_items.json')['items'] if i['id']=='UNK-012'),None)
        if c and item and item['status']=='RESOLVED_IN_DRAFT' and mode=='draft':
            definition=[line for line in c['text'].splitlines() if line.startswith(('2. ','3. '))]
            if len(definition)==2:
                text='這份 v1.2 草案已補上定義：\n\n'+'\n'.join(line[3:] for line in definition)+'\n\n所以，不能只因為設備是筆電就認定敏感；還需要 IT 依實際資訊安全風險認定。\n依據：IT-006｜版本 '+c['version']
                return dict(status='DEFINED_TERM_DRAFT',answer=text,display_answer=text,sources=[{k:c[k] for k in ['source_id','regulation_id','version','source','effective_date','git_commit']}],evidence=[dict(source_id=c['source_id'],version=c['version'],text=c['text'].split('\n',1)[1].strip())])
        if c and item and item['status']=='UNRESOLVED' and known_style and store.sha(c['text'])==known_style['clause_sha256']:
            text='你問的是「敏感設備」的意思。這份規章只說敏感設備要另依授權要求管理，沒有提供定義、清單或判斷標準，所以我不能直接判定哪些設備算敏感設備。'
            related=[c]
            equipment=next((c for c in chunks if c['source_id']=='IT-004'),None)
            if equipment:
                text+='\n\n依 IT 負責設備配置評估的職掌，建議先向 IT 確認你要帶的設備是否需要額外授權；這是初步詢問方向，資料沒有指定敏感設備的正式認定單位。'
                related.append(equipment)
            text+='\n依據：'+ '、'.join(c['source_id']+'｜版本 '+c['version'] for c in related)
            return dict(status='UNDEFINED_TERM',answer=text,display_answer=text,sources=[{k:c[k] for k in ['source_id','regulation_id','version','source','effective_date','git_commit']} for c in related],unresolved_id='UNK-012',conversation_topic='敏感設備',evidence=[dict(source_id=c['source_id'],version=c['version'],text=c['text'].split('\n',1)[1].strip()) for c in related])
    if intent.carrying_out(question) and any(t in q for t in ['設備','筆電','電腦','螢幕']):
        c=next((c for c in chunks if c['source_id']=='IT-006'),None)
        if c:
            summary,evidence=presentation.render([c],root,question)
            text='了解，你想確認的是把設備帶出公司。你要帶的是已配發的個人筆電，還是共用／另外申請的設備？也想和你確認，是否已取得攜出授權？\n\n'+summary
            return dict(status='EQUIPMENT_CARRY_CLARIFY',answer=text,display_answer=text,sources=[{k:c[k] for k in ['source_id','regulation_id','version','source','effective_date','git_commit']}],conversation_topic='設備攜出',evidence=evidence)
    selected_leave=intent.specified_leave(question)
    if selected_leave=='特休' and any(t in q for t in ['突然','臨時','今天','來不及','沒辦法提前','無法提前']):
        related=[c for c in chunks if c['source_id'] in {'LEAVE-004','LEAVE-005'}]
        annual=next((c for c in related if c['source_id']=='LEAVE-004'),None)
        emergency=next((c for c in related if c['source_id']=='LEAVE-005'),None)
        if annual and emergency and '建議提前三個工作天通知主管，但非強制期限' in annual['text'] and '先通知主管' in emergency['text']:
            text='了解，你想請的是特休。提前三個工作天只是建議，不是強制期限，不能把它當成今天無法請特休的理由。建議你儘速通知主管，說明今天無法到班、希望使用特休。若屬緊急請假，可以先通知主管，再依實際情況補登 HRM，相關流程仍須符合適用法令。'
            text+='\n\n特休日期原則上由你排定；公司若有急迫經營需求，須依法協商調整，不能直接套用一般事假的主管核准規則。'
            if intent.family_illness(question):
                text+='你提到的是家人生病，我不會直接把員工本人的病假證明要求套用在這次特休。'
            text+='不確定補登方式時，可以向 HR 確認；目前沒有提供統一補登期限。'
            sources=[{k:c[k] for k in ['source_id','regulation_id','version','source','effective_date','git_commit']} for c in related]
            text+='\n依據：'+ '、'.join(c['source_id']+'｜版本 '+c['version'] for c in related)
            return dict(status='ANNUAL_LEAVE_URGENT',answer=text,display_answer=text,sources=sources,conversation_topic='特休',requested_leave='特休',evidence=[dict(source_id=c['source_id'],version=c['version'],text=c['text'].split('\n',1)[1].strip()) for c in related])
    if intent.pet_subject(question) and any(t in q for t in ['請假','事假','特休','病假']):
        related=[c for c in chunks if c['source_id'] in {'LEAVE-002','LEAVE-005'}]
        if {c['source_id'] for c in related}=={'LEAVE-002','LEAVE-005'}:
            text='了解，你是因為狗狗或其他寵物的狀況需要請假。你可以透過 HRM 提出申請；如果情況緊急、來不及先完成申請，可以先通知主管，再依實際情況補登 HRM。相關流程仍須符合適用法令。'
            advice=any(t in q for t in ['建議','該怎麼辦','應該怎麼做'])
            if advice:
                text='我的建議是先處理通知：如果你現在需要照顧寵物、無法到班，先儘速告訴主管你的情況與請假需求。若情況緊急、來不及先完成申請，可以先通知，再依實際情況補登 HRM，相關流程仍須符合適用法令。\n\n至於用哪種假，我目前不能替你決定：資料未提供寵物生病的假別認定標準。請向 HR 確認 HRM 應選的假別，不能直接把寵物生病套用成你本人的病假。'
            elif selected_leave:
                text+='\n\n你提到想請'+selected_leave+'；目前資料未提供寵物生病的假別認定標準，不能把寵物生病當成你本人生病來套用病假規定。適用假別不確定時，請向 HR 確認。'
            else:
                text+='\n\n你想使用事假還是特休？目前資料未提供寵物生病的假別認定標準；不確定該選哪種假，可以向 HR 確認。'
            text+='\n依據：'+'、'.join(c['source_id']+'｜版本 '+c['version'] for c in related)
            return dict(status='PET_LEAVE_ADVICE' if advice else 'PET_LEAVE_CLARIFY',answer=text,display_answer=text,sources=[{k:c[k] for k in ['source_id','regulation_id','version','source','effective_date','git_commit']} for c in related],conversation_topic='請假',evidence=[dict(source_id=c['source_id'],version=c['version'],text=c['text'].split('\n',1)[1].strip()) for c in related])
    if intent.family_illness(question) and selected_leave!='特休':
        related=[c for c in chunks if c['source_id'] in {'LEAVE-002','LEAVE-005'}]
        if {c['source_id'] for c in related}=={'LEAVE-002','LEAVE-005'}:
            advice=any(t in q for t in ['建議','該怎麼辦','應該怎麼做'])
            text=('我的建議是先通知主管，說明你因家人的狀況需要請假。' if advice else '了解，你是因為家人生病需要請假。')
            text+='你可以透過 HRM 提出申請；若情況緊急、來不及先完成申請，可以先通知主管，再依實際情況補登 HRM。相關流程仍須符合適用法令。'
            text+='\n\n目前提供的規章沒有說明照顧家人能否使用病假，我不能直接套用員工本人生病的證明要求；假別不確定時，請向 HR 確認。'
            if not selected_leave and not advice:
                text+='你打算使用特休、事假，還是想確認其他假別？'
            text+='\n依據：'+'、'.join(c['source_id']+'｜版本 '+c['version'] for c in related)
            return dict(status='FAMILY_LEAVE_ADVICE' if advice else 'FAMILY_LEAVE_CLARIFY',answer=text,display_answer=text,sources=[{k:c[k] for k in ['source_id','regulation_id','version','source','effective_date','git_commit']} for c in related],conversation_topic='請假',evidence=[dict(source_id=c['source_id'],version=c['version'],text=c['text'].split('\n',1)[1].strip()) for c in related])
    if any(t in q for t in ['系統','登入','軟體','程式']) and any(t in q for t in ['打不開','登不進','進不去','開不了','無法登入','不能登入','沒有權限']):
        guidance=routing.recommend(question,chunks,root)
        if guidance:
            return guidance
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
    if any(t in q for t in ['請假','假單']) and any(t in q for t in ['臨時有事','臨時急事','突然有事','突然有急事','突發事情']):
        c=next((c for c in chunks if c['source_id']=='LEAVE-005'),None)
        if c:
            intro='我理解您是臨時發生事情，來不及事前完成請假申請，這個理解是否正確？若屬緊急請假，可以先通知主管，再依實際情況補登 HRM。'
            body=c['text'].split('\n',1)[1].strip()
            return dict(status='LEAVE_URGENT_CLARIFY',answer=intro+'\n\n緊急請假條文：\n'+body+'\n目前提供的規章未列出緊急情況認定標準或統一補登期限；若不確定情況或假別，請向 HR 確認。'+f'\n來源：{c["source_id"]}｜版本 {c["version"]}｜{c["source"]}',sources=[{k:c[k] for k in ['source_id','regulation_id','version','source','effective_date','git_commit']}],conversation_topic='請假')
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
            return dict(conversation_topic='請假',status='LEAVE_FOLLOWUP',answer=intro+'\n\n'+'\n\n'.join(sections),sources=sources)
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
            return dict(status='UNRESOLVED',answer=answer,display_answer=answer,sources=[],unresolved_id=item['id'],conversation_topic=item['question'],unresolved_regulation=item['regulation'])
    vague_equipment={'設備','我需要設備','需要設備','我要設備','我想申請設備','我要申請設備','申請設備','我需要工作設備','我想申請工作設備'}
    if query['original'].rstrip('？?！!。') in vague_equipment and any(c['source_id']=='IT-004' for c in chunks):
        text='可以，我幫你確認設備申請流程。你需要哪種設備、準備用來做什麼？會帶出公司使用嗎？先確認這些資訊，才能區分設備配置與攜出授權；目前還不能保證設備一定能提供。'
        status='CLARIFY' if '申請' in query['original'] else 'CLARIFY_INTENT'
        return dict(status=status,answer=text,display_answer=text,sources=[],candidate_topics=['設備申請'],candidate_source_ids=['IT-004'],conversation_topic='設備申請',pending_fields=['equipment_type','purpose','carry_out'])
    if query['original'] in ['請假', '我要請假', '我要申請設備', '申請設備']:
        return dict(status='CLARIFY',answer='我理解您可能想詢問請假申請或設備申請流程，是否正確？請補充假別或設備類型，以便查找對應規章。請假細節可向 HR 確認。',sources=[])
    hits=retrieval.rank(chunks,query,vocabulary)
    if intent.family_illness(question):
        hits=[pair for pair in hits if pair[1]['source_id']!='LEAVE-003']
    if not hits:
        guidance=routing.recommend(question,chunks,root) if any(t in q for t in ['找誰','問誰','誰處理','誰協助','有問題','怎麼辦','無法','不能','打不開','壞','異常']) else None
        if guidance:
            return guidance
        candidates=[c for c in chunks if c['source_id'] in query['candidate_ids']]
        if candidates:
            topics=list(dict.fromkeys(c['text'].splitlines()[0].split(' ',2)[-1] for c in candidates))
            understanding='、'.join(topics)
            if set(query['candidate_ids'])=={'LEAVE-001','LEAVE-004'}:
                question='您想問的是請假時間或流程嗎？預計使用特休、事假，還是其他假別？'
            else:
                question=f'我理解您可能在詢問「{understanding}」，這個理解是否正確？請告訴我具體情境，或說明您想問的其他事項。'
            return dict(status='CLARIFY_INTENT',answer=question+'目前只找到可能相關的主題，資訊不足，尚不能判定適用規定。',sources=[],candidate_topics=topics,candidate_source_ids=[c['source_id'] for c in candidates],retrieval=query)
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
