"""公開面試展示入口：ACTIVE-only，沿用本機問答，無管理或發布 API。"""
import os
import time
from threading import Lock,BoundedSemaphore
from urllib.parse import urlsplit
from flask import Flask,request,jsonify,Response,send_from_directory
import assistant
import chatbot

app=Flask(__name__,static_folder=None)
app.config['MAX_CONTENT_LENGTH']=16384
_lock=Lock()
_slots=BoundedSemaphore(2)
_cloud_times=[]

def cloud_budget():
    """單 worker 展示版的全站預算，重啟會重置；不是帳務硬上限。"""
    now=time.monotonic()
    with _lock:
        _cloud_times[:]=[t for t in _cloud_times if now-t<3600]
        limit=max(0,min(int(os.environ.get('CLOUD_REQUESTS_PER_HOUR','30')),100))
        if len(_cloud_times)>=limit:return False
        _cloud_times.append(now)
        return True

@app.before_request
def same_origin():
    configured=os.environ.get('PUBLIC_URL') or os.environ.get('RENDER_EXTERNAL_URL')
    if configured:
        parsed=urlsplit(configured)
        if parsed.scheme!='https' or not parsed.netloc or request.host!=parsed.netloc:
            return jsonify(error='展示網址設定不符合要求'),403
        expected=parsed.scheme+'://'+parsed.netloc
    else:
        # 只容許本機測試；公開運行必須設定正式網址。
        if request.host.split(':')[0] not in {'127.0.0.1','localhost'}:
            return jsonify(error='尚未設定公開展示網址'),403
        expected=request.host_url.rstrip('/')
    if request.headers.get('Origin') not in {None,expected}:
        return jsonify(error='僅接受展示頁同源請求'),403

@app.after_request
def headers(response):
    response.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'"})
    return response

@app.get('/')
def index():
    html=(chatbot.ROOT/'web/index.html').read_text(encoding='utf-8')
    html=html.replace('<option value="draft">草案測試 · 未發布</option>','')
    html=html.replace('● 僅限本機','● 面試展示')
    html=html.replace('模擬正式版','面試展示版')
    html=html.replace('沒有串接 HRM，不提供個人餘額或薪資資料。','沒有串接 HRM，不提供個人餘額或薪資資料。請勿輸入真實個資、密碼或公司機密。')
    if os.environ.get('ENABLE_CLOUD')=='true':
        html=html.replace('模擬企業制度，尚未全部法律審查。','模擬企業制度，尚未全部法律審查。問題、必要對話與模擬規章可能傳送至 Ollama Cloud；送出即表示你了解此展示方式。')
    return Response(html,content_type='text/html; charset=utf-8')

@app.get('/app.js')
@app.get('/style.css')
def asset():
    return send_from_directory(chatbot.ROOT/'web',request.path[1:])

@app.get('/healthz')
def health():
    try:
        if not assistant.load_current(chatbot.ROOT):raise ValueError('沒有 ACTIVE')
        return jsonify(status='ok')
    except (OSError,ValueError,KeyError,TypeError):
        return jsonify(status='unavailable'),503

@app.get('/api/status')
def status():
    manifest=assistant.store.read(chatbot.ROOT/'metadata/regulation_manifest.json')
    cloud=os.environ.get('ENABLE_CLOUD')=='true' and bool(os.environ.get('OLLAMA_API_KEY'))
    return jsonify(active_count=sum(bool(r['active']) for r in manifest['regulations']),draft_count=0,app_version=chatbot.RUNNING_VERSION,public_demo=True,provider='cloud' if cloud else 'local',model=os.environ.get('OLLAMA_MODEL','gemma4:31b') if cloud else None)

@app.post('/api/chat')
def chat():
    if not request.is_json:return jsonify(error='需使用 JSON'),400
    data=request.get_json(silent=True)
    if not isinstance(data,dict):return jsonify(error='請求格式不正確'),400
    if data.get('mode','active')!='active':return jsonify(error='公開展示僅查詢已發布的模擬 ACTIVE 規章'),403
    q=data.get('question');history=data.get('history')
    if not isinstance(q,str) or not 0<len(q.strip())<=1000 or not isinstance(history,list) or len(history)>6 or any(not isinstance(x,str) or len(x)>1000 for x in history):
        return jsonify(error='問題或對話格式不正確'),400
    if data.get('client_version')!=chatbot.RUNNING_VERSION:
        return jsonify(status='CLIENT_UPDATE_REQUIRED',answer='展示頁已更新，請重新整理後再提問。',sources=[],mode='active')
    if not _slots.acquire(blocking=False):return jsonify(error='小助理目前忙碌，請稍後再試。'),429
    try:
        cloud=os.environ.get('ENABLE_CLOUD')=='true' and bool(os.environ.get('OLLAMA_API_KEY')) and cloud_budget()
        result=chatbot.answer(q,'active',model=os.environ.get('OLLAMA_MODEL','gemma4:31b') if cloud else None,history=history,provider='cloud' if cloud else 'local')
        result['is_simulated']=True
        return jsonify(result)
    except (OSError,ValueError,KeyError,TypeError):
        return jsonify(error='規章資料暫時無法使用，請稍後重試。'),503
    finally:_slots.release()

@app.errorhandler(413)
def oversized(error):return jsonify(error='問題長度超過展示限制'),413

@app.errorhandler(404)
def missing(error):return jsonify(error='找不到展示功能'),404
