# 需求與資料架構

目標使用者為新進員工；支援 HR、IT、行政與訓練常見制度查詢。管理者負責草案、人工審閱、發布及廢止。驗收：七類資料完整、來源可追溯、未知項目清楚、無未確認制度進入正式索引。

manifest 每類規章包含 id/name/draft/active/history；版本記錄保存 version/status/source/updated_date/effective_date/summary/sha256/git_commit/published_at。null 表示未提供。updated_date 為人工指定資料更新日，不等同生效日。

規章工作文件 → DRAFT metadata → 人工確認 → 不變發布快照 → ACTIVE 指標 → 整體索引 current.json。舊版保存於 history，status 為 RETIRED。Git 保存全歷史；內容以 UTF-8 字串 SHA-256 驗證。

正式索引是一個 JSON 快照，不是向量資料庫。每條規章標題為切分邊界，避免例外脫離主條文。未來 embedding、向量索引与檢索器可放入 knowledge_base 新子目錄；向量庫需以完整 generation 切換，禁止就地混寫。檢索入口須驗證 manifest hash 與索引一致，不一致停止問答或明確呈現先前知識庫時間，不能宣稱最新。發布後尚未 sync 時存在舊索引；本機問答入口 scripts/assistant.py 已實作一致性驗證，不一致時停止回答。

工具以專案內排他鎖避免同時修改 manifest/索引；索引以同目錄暫存檔與 os.replace 替換。失敗記錄在 update_log。鎖因意外中止殘留時，先確認無程序執行再移除。發布快照與 manifest 並非跨檔案交易；若發布中斷留下未登錄快照，人工檢查後恢復，不可直接覆寫。

尚未提供權限驗證、發布人身分、電子簽核、不可竄改稽核、預約生效、HRM、PDF/DOCX 解析、向量/生成模型及聊天 UI。--confirm 是操作者確認旗標，不具授權驗證能力。發布、廢止與同步是分開操作；發布後必須同步並驗證成功。

AI 必須直接回答並引用 source_id/version/source。無現行證據就說資料未提供；不得將模擬規章中「依法」延伸成自行推論的法規內容。特休餘額須引導 HRM，補助上限不得生成金額。跨規章查詢保留各版本來源與例外。

目前新增關鍵字檢索與條文摘錄 CLI。驗證 manifest 雜湊、ACTIVE 狀態、生效日、來源文件雜湊、完整區塊與版本對應；未知事項僅對現行規章套用。個人特休餘額為能力限制回覆，不依草案產生制度答案。檢索排序不代表答案正確率；複雜語意與未收錄用語仍可能漏查。
