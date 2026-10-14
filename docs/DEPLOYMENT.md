# 公開面試展示部署

公開網站不是 GitHub Pages。使用 Flask + Gunicorn 執行既有 Python 問答，Render Free Web Service 提供 HTTPS 網址。

## Render 設定

1. 登入 Render，New → Web Service → Public Git Repository。
2. 儲存庫：https://github.com/wcc0715/enterprise-onboarding-ai 。分支 master，Root Directory 留空。
3. Runtime Python；Build Command：`pip install -r requirements.txt`。
4. Start Command：`gunicorn --chdir scripts web_service:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120 --access-logfile /dev/null`。
5. 選 Free，Health Check Path `/healthz`。也可使用根目錄 render.yaml 的 Blueprint 設定。
6. 預設 ENABLE_CLOUD=false，不需要金鑰就可展示 ACTIVE 規章問答。Render 自動提供 RENDER_EXTERNAL_URL；其他平台必須設定 PUBLIC_URL 為完整 HTTPS 網址。
7. 部署成功後複製 Render 實際分配的網址，放入 README 與履歷；未成功前不得編造展示網址。

若要啟用真實模型：先在 Render 的環境變數設定 `OLLAMA_API_KEY` 秘密值，再設定 `ENABLE_CLOUD=true`、`OLLAMA_MODEL=gemma4:31b`。金鑰不放 GitHub、前端、README 或聊天中。當前金鑰驗證尚未確認成功，預設先提供不依賴模型的展示。

## 展示邊界

- 僅 ACTIVE，不公開草案查詢、發布或管理功能；頁面標示模擬企業。
- 保留來源、版本、生效日與 Git Commit。未知制度不補造，無 HRM 存取。
- 不保存聊天內容；每次最多 1000 字，最多六輪問題，整包限制 16KB。
- 一個 worker、兩個同時問答槽；雲端全站每小時預設最多 30 次問答，每題可能呼叫模型兩次。計數僅在記憶體中，重啟會清空，不能視為帳務硬上限或完整防濫用系統。
- 超過雲端預算改用受控規章回覆；雲端不可用也保留回退。
- 應用不記錄問題或金鑰，主機平台仍可能保存基礎存取資訊。
- Free 服務閒置 15 分鐘會休眠，重新開啟可能需等待。不要承諾企業正式營運的可用性。

參考：[Render Flask 部署](https://render.com/docs/deploy-flask)、[免費方案限制](https://render.com/docs/free)。
