"""只從先前問題辨識檢索主題，不把對話當作規章證據。"""
import assistant

def resolve(question,history,root,mode):
    direct=assistant.respond(question,root,mode)
    if direct['status']!='NOT_PROVIDED' or not history:
        return question,None
    q=assistant.normalize(question)
    if not (q.startswith(('但是','那','所以','因為','因爲','就是','其實','這','它','還')) or q in {'可以嗎','可以申請嗎','找誰','多少錢','幾天','要找誰申請','對','是','是的','沒錯','對啊'}):
        return question,None
    for previous in reversed(history[-6:]):
        result=assistant.respond(previous,root,mode)
        ids=[s['source_id'] for s in result['sources']]
        if result['status']=='CLARIFY_INTENT':
            ids=result['candidate_source_ids']
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
