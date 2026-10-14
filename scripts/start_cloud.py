#!/usr/bin/env python3
"""使用者於本機終端機輸入金鑰，輸入不回顯、不写檔案。"""
import argparse
import getpass
import os
from http.server import ThreadingHTTPServer
import chatbot
import cloud_generation

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',default='gemma4:31b')
    p.add_argument('--port',type=int,default=8767)
    a=p.parse_args()
    if not os.environ.get('OLLAMA_API_KEY'):
        key=getpass.getpass('請在本機輸入 Ollama API Key（不顯示、不保存）：').strip()
        if not key:p.exit(1,'未輸入金鑰，未啟動雲端服務。\n')
        os.environ['OLLAMA_API_KEY']=key
        del key
    chatbot.Handler.model=a.model;chatbot.Handler.provider='cloud'
    server=ThreadingHTTPServer(('127.0.0.1',a.port),chatbot.Handler)
    print('正在確認 Ollama Cloud 連線（不顯示金鑰）…',flush=True)
    try:
        probe=cloud_generation.request_json('僅回 JSON：{"ok":true}',{'message':'連線測試，不涉及員工或規章資料'},a.model,max_tokens=200)
        if probe!={'ok':True}:raise ValueError('連線測試格式不符')
        print('雲端模型已成功回應；實際回答品質仍需測試。',flush=True)
    except Exception as error:
        print('雲端檢查未通過：'+cloud_generation.error_code(error)+'；服務仍可使用規章回覆。',flush=True)
    print(f'Ollama Cloud 模式：http://127.0.0.1:{a.port}；模型 {a.model}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close();os.environ.pop('OLLAMA_API_KEY',None)
