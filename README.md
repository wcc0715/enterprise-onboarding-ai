# 企業新進人員 AI 知識助理

Enterprise Onboarding AI Knowledge Assistant

本機 PoC：需求分析、規章管理、版本差異、發布與 RAG 索引同步。制度依使用者提供內容建立，為模擬企業內部制度，尚未全部完成法律審查，不能宣稱法規合規。沒有聊天介面、模型或 HRM 連線；不使用付費 API。

## 目錄

```text
enterprise-onboarding-ai/
├── README.md / AGENTS.md / .gitignore
├── regulations/                 七份 Markdown 草案
│   └── releases/                發布時才建立，保存不可覆寫快照
├── metadata/
│   ├── regulation_manifest.json
│   └── unresolved_items.json
├── changelog/CHANGELOG.md
├── knowledge_base/              current.json 與 update_log.json
├── scripts/regulations.py
├── tests/                       測試規格與生命週期測試
└── docs/                        需求、架構、更新報告格式
```

初始七類皆為 **0.1.0 / DRAFT**，ACTIVE 為 null；生效日與發布時間未提供。草案內容來自已確認討論，但討論確認不等同正式發布。36 條條文具有穩定來源編號。11 項未知事項列於 metadata，null 代表尚未確認。

## 執行環境

Python 3.11+ 與 Git，無需安裝 Python 套件。請在本專案根目錄執行。

本機系統 Git 缺少 Xcode 開發工具，可使用 Codex 附帶的 Git：

```sh
export ONBOARDING_GIT=/Users/wcc/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/fallback/git
"$ONBOARDING_GIT" status
python3 scripts/regulations.py --help
```

此路徑是本機環境設定，其他電腦可使用自己的 Git，無需讀取任何專案外資料。

## 檢查更新與前後差異

```sh
python3 scripts/regulations.py check --base HEAD --output changelog/latest_report.json
"$ONBOARDING_GIT" diff -- regulations metadata
"$ONBOARDING_GIT" log --oneline --all
"$ONBOARDING_GIT" diff <舊Commit> <新Commit> -- regulations metadata
python3 scripts/regulations.py check --base <舊Commit>
```

check 比較指定 Commit 與目前工作區，包含未追蹤的 Markdown、修改與刪除，以及 metadata 差異。沒有變更時 changes 為空。報告包含條文前後內容、全文差異、舊新版本、發布狀態及既有知識庫影響。版本號不會因編輯文字或檔名自動提高。刪除草案不代表廢止 ACTIVE。

## 修訂與正式發布

1. 編輯 regulations 中對應草案；既有發布快照不得修改。
2. 執行 revise，提供人工決定的版本、更新日期與摘要：

```sh
python3 scripts/regulations.py revise LEAVE --version 0.2.0 --updated-date 2026-10-14 --summary '填入實際修訂摘要'
python3 scripts/regulations.py check --base HEAD
```

3. 人工審閱內容、例外與未知事項。對該規章每個 UNRESOLVED 項目人工確認 blocks_publication：false 可發布但仍不得填補未知內容；true/null 阻擋。人工單位 null 不可自行填寫。
4. 使用 Git 保存已審閱草案與 metadata：`git add regulations metadata`、`git commit -m '審閱規章草案'`（可用 "$ONBOARDING_GIT" 代替 git）。
5. **取得使用者明確發布確認及明確生效日後**，才執行以下範本；不可直接照範例推定日期：

```sh
python3 scripts/regulations.py publish LEAVE --effective-date YYYY-MM-DD --summary '填入正式發布摘要' --confirm
```

publish 驗證來源 Commit 與 SHA-256，保存快照，舊 ACTIVE 轉 RETIRED，新版轉 ACTIVE。發布資料的 git_commit 指向已提交且內容一致的來源草案 Commit。草案編輯區仍為 DRAFT；下次修訂應使用未發布版本號。未提供正式授權時不得執行 --confirm。尚不支援預約生效，未來日期會拒絕。

6. Commit 發布快照與 metadata，執行 `python3 scripts/regulations.py sync`，再 Commit 索引與更新紀錄。Git 歷史、metadata history 與 update_log 共同保存追蹤資料。手動刪檔不能取代廢止流程。
7. 廢止須取得明確確認後：`python3 scripts/regulations.py retire LEAVE --summary '廢止原因' --confirm`，再 Commit 及 sync。

## 知識庫與驗證

`sync` 僅解析 ACTIVE 快照的條文，保留來源 ID、版本、文件、Commit、文件與區塊雜湊。一次產生完整 current.json，避免逐區塊新舊版本混用；失败保留原索引並記錄錯誤。初始 ACTIVE 為零，索引為空，不能用草案回答現行規章問題。

```sh
python3 scripts/regulations.py sync
python3 -m unittest discover -s tests -v
```

測試使用臨時隔離專案，不發布本專案規章。完整 RAG 品質測試尚未執行，規格見 tests/TEST_SPEC.md。

下一步：人工確認發布条件及未知項目、完成必要法律審查與發布，之後選擇本機 embedding/檢索模型並實作帶來源的問答與十類品質驗證。
