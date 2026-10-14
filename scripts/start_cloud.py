#!/usr/bin/env python3
"""使用者於本機終端機輸入金鑰，輸入不回顯、不写檔案。"""
import argparse
import getpass
import os
from http.server import ThreadingHTTPServer
import chatbot

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
    print(f'Ollama Cloud 模式：http://127.0.0.1:{a.port}；模型 {a.model}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close();os.environ.pop('OLLAMA_API_KEY',None)
