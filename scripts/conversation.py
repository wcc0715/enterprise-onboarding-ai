"""只從先前問題辨識檢索主題，不把對話當作規章證據。"""
import assistant
import intent
import versions

def resolve(question,history,root,mode):
    direct=assistant.respond(question,root,mode)
    explicit_version=versions.constraints(question)
    if explicit_version['requested'] or explicit_version['excluded']:
        return question,None
    if direct['status'] in {'PERSONAL_DATA_UNAVAILABLE','ACTION_UNAVAILABLE','CONTACT_NOT_PROVIDED','SIMULATED_CONTACTS','CONTACT_CLARIFY'}:
        return question,None
    q=assistant.normalize(question)
    if history and '不是我' in q and intent.family_illness(question+'生病'):
        previous=history[-1]
        if any(t in assistant.normalize(previous) for t in ['請假','事假','特休','病假']):
            leave=intent.specified_leave(previous)
            return '我要請'+(leave or '假')+'；家人生病；'+question,'請假'
    if history and intent.pet_subject(question) and any(t in q for t in ['不是我','狗狗啦','貓咪啦','是寵物']):
        previous=history[-1]
        if any(t in assistant.normalize(previous) for t in ['請假','事假','特休','病假']):
            # 更正對象優先於舊的疾病匹配，仍保留請假任務與明確假別。
            leave=intent.specified_leave(previous)
            return '我要請'+(leave or '假')+'；'+question,'請假'
    advice_followup=q.rstrip('？?。！!') in {'那你的建議呢','你的建議呢','那你建議呢','你建議呢','你的建議是','那你的建議是','你有什麼建議','有什麼建議','那我該怎麼辦','那我應該怎麼做'}
    if history and advice_followup:
        previous=history[-1]
        prior=assistant.respond(previous,root,mode)
        # 保留上一題的具體選項，不縮成「請假管理」等廣泛類別。
        if prior.get('sources'):
            return previous+'；'+question,prior.get('conversation_topic') or '上一題'
    is_followup=q.startswith(('但是','但','那','所以','因為','因爲','就是','其實','這','它','還'))
    if history and is_followup:
        previous_version=versions.constraints(history[-1])
        if len(previous_version['ids'])==1 and len(previous_version['requested'])==1 and direct['status'] in {'NOT_PROVIDED','CLARIFY_INTENT'}:
            label=previous_version['ids'][0]+' v'+previous_version['requested'][0]
            return label+'：'+question,label
    if history and intent.carrying_out(question):
        previous=assistant.respond(history[-1],root,mode)
        previous_equipment=any(s['regulation_id']=='IT' for s in previous['sources'])
        current_categories={s['regulation_id'] for s in direct['sources']}
        if previous_equipment and (not current_categories or current_categories=={'IT'}):
            return '設備攜出：'+question,'設備攜出'
    if history and is_followup and not intent.specified_leave(question):
        previous=history[-1]
        leave=intent.specified_leave(previous)
        # 顯式指定特休且本輪仍補充請假理由／通知時間時，優先保留假別。
        if leave=='特休' and (intent.family_illness(question) or any(t in q for t in ['提前','來不及','通知','請假'])):
            prior=assistant.respond(previous,root,mode)
            if any(s['source_id']=='LEAVE-004' for s in prior['sources']):
                return '特休：'+question,'特休'
    if direct['status'] not in {'NOT_PROVIDED','CLARIFY_INTENT'} or not history:
        return question,None
    q=assistant.normalize(question)
    if not (q.startswith(('但是','但','那','所以','因為','因爲','就是','其實','這','它','還')) or q in {'可以嗎','可以申請嗎','找誰','多少錢','幾天','要找誰申請','對','是','是的','沒錯','對啊'}):
        return question,None
    for previous in reversed(history[-6:]):
        result=assistant.respond(previous,root,mode)
        if result['status']=='UNRESOLVED' and result.get('conversation_topic'):
            return result['conversation_topic']+'：'+question,result['conversation_topic']
        ids=[s['source_id'] for s in result['sources']]
        if result['status']=='CLARIFY_INTENT':
            ids=result['candidate_source_ids']
        if direct['status']=='CLARIFY_INTENT' and not set(direct.get('candidate_source_ids',[])).intersection(ids):
            return question,None
        if result.get('conversation_topic') and result['sources']:
            topic=result['conversation_topic']
            return topic+'：'+question,topic
        if len(ids)>1 and result['status']!='CLARIFY_INTENT':
            categories={s['regulation_id'] for s in result['sources']}
            if len(categories)==1:
                manifest=assistant.store.read(root/'metadata/regulation_manifest.json')
                category=next(iter(categories))
                topic=next(r['name'] for r in manifest['regulations'] if r['id']==category)
                return topic+'：'+question,topic
        if len(ids)==1:
            chunks=assistant.load_current(root) if mode=='active' else assistant.load_draft(root)
            chunk=next((c for c in chunks if c['source_id']==ids[0]),None)
            if chunk:
                title=chunk['text'].splitlines()[0].split(' ',2)[-1]
                return title+'：'+question,title
        if result['status']=='CLARIFY_INTENT' and len(ids)>1 and q in {'對','是','是的','沒錯','對啊'}:
            return previous+'：'+question,None
        # 最近一次無證據或多主題問題不越過它追溯舊主題。
        break
    return question,None
