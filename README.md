# 企業新進人員 AI 知識助理

Enterprise Onboarding AI Knowledge Assistant

本機 PoC：需求分析、規章管理、版本差異、發布與 RAG 索引同步。制度依使用者提供內容建立，為模擬企業內部制度，尚未全部完成法律審查，不能宣稱法規合規。提供本機命令列檢索與條文摘錄；提供本機聊天網頁，尚無實際語言模型或 HRM 連線，不使用付費 API。

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

初始七類皆為 **0.1.0 / DRAFT**，ACTIVE 為 null；生效日與發布時間未提供。草案內容來自已確認討論，但討論確認不等同正式發布。36 條條文具有穩定來源編號。11 項未知事項列於 metadata。使用者已確認這些事項不阻擋發布，員工應向負責單位確認；請假向 HR。尚未提供的其他諮詢單位保留 null，不自行指定。

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

3. 人工審閱內容、例外與未知事項。目前使用者已將 11 項未知事項確認為 blocks_publication=false，改由員工向負責單位確認；仍不得填補未知內容。未來新增項目的 true/null 仍阻擋發布。諮詢單位 null 不可自行填寫。
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

## 本機問答原型

```sh
python3 scripts/assistant.py '上班時間？'
python3 scripts/assistant.py '我還有幾天特休？'
python3 scripts/assistant.py '教育訓練一年補助多少錢？' --json
```

這是關鍵字檢索與原文摘錄式問答，不是完整的向量 RAG 或生成式 AI。條文整段顯示以保留例外，附上來源編號、版本與文件；未知事項依清單引導負責單位，未提供的單位不自行指定。問題語意對照僅屬檢索設定，並非新增制度。複雜或不同措辭的問題可能查不到，需要補充問題或人工查閱。

正式入口只讀 ACTIVE；本專案目前全為 DRAFT，因此一般制度問題會回覆尚無已發布規章。個人特休餘額問題會直接說明未串接 HRM。索引與 manifest/發布快照不一致時停止回答，避免用舊規章答覆；管理者應先排除問題並執行 sync。

目前九項自動測試通過，涵蓋條文引用、未知與錯誤前提、模糊問題、跨規章、廢止排除、版本更新、索引與來源竄改及失敗保留。皆為隔離 fixture；未執行模型、向量檢索或真實員工驗收。

## 本機聊天機器人

```sh
python3 scripts/chatbot.py --port 8766
```

瀏覽器開啟 http://127.0.0.1:8766 。預設為正式模式；目前尚無 ACTIVE 資料。要測試現有七份制度，手動選擇「草案測試 · 未發布」；回答會清楚標示草案，不改變發布狀態或正式索引。

問題 → 能力與未知事項檢查 → 檢索條文 → 受控回答組合 → 來源引用。追問可用本次對話的最近六題辨識主題，仍重新檢索，不以先前聊天或使用者指令改寫規章。聊天不寫入檔案或瀏覽器持久儲存。只綁定 127.0.0.1，不對外部署；不具正式員工身分驗證，草案模式僅供本機開發測試。

若已有本機 Ollama 與已下載模型，可使用：

```sh
python3 scripts/chatbot.py --port 8766 --model <本機模型名稱>
```

僅連接固定的 127.0.0.1:11434，不自動安裝或下載模型、不呼叫雲端 API。模型只選擇／排序已檢索來源 ID，程式檢查來源後，以完整條文生成結構化回答，避免自由生成制度與遺漏例外。模型無效或不可用時回退到條文組合。這不是自由改寫式生成模型，也不是向量 RAG；目前真實模型尚未連線驗證，模型測試使用 mock。

服務停止：執行服務的終端機按 Ctrl+C。問題最多 1000 字；查詢模式與回答方式會顯示於訊息下方。HTTP 拒絕非同源請求，不提供任意檔案讀取接口。

## 詞彙與意圖維護

檢索設定在 config/retrieval_vocabulary.json，邏輯在 scripts/retrieval.py。支援 Unicode 全半形與英文大小寫正規化、同義詞單次展開、條文詞彙、需同時匹配多組詞彙的意圖規則，以及未知事項意圖。設定每次提問重新讀取，新增詞彙不需修改規章、不需提高規章版本或發布；應審閱設定並保存 Git。

例如 concepts 中 canonical=特休、aliases=[年假, 特別休假]；context_rules 各組採 OR 召回候選，命中任一詞就可進入理解確認；多組同時命中只用於提高明確度，並非找到候選的必要條件。可將進修／研習搭配報名／補助導向 TRAIN-003，避免只因「補助」就任意回覆訓練制度。topics 對應穩定條文編號，來源候選仍限當次允許的 ACTIVE 或草案測試區塊。

先執行 `python3 -m unittest discover -s tests -v` 檢查同義詞與未知拒答。這些詞彙只供檢索，不代表「年假」或活動已獲認定符合公司補助資格；回答仍須以條文及人工核定為依據。未收錄的措辭、錯別字與複雜語意仍可能漏查，下一階段可加入本機 embedding 語意檢索，經獨立品質驗證後再啟用。

詞彙已覆蓋七類全部 36 條文，每條文有兩個改寫測試問題，共 72 題，存於 tests/vocabulary_cases.json；逐條對照見 docs/VOCABULARY_COVERAGE.md。出國／旅遊搭配提前多久的問題，若未提供假別，先釐清特休或事假，再列出各自條文，不直接認定旅遊一定使用特休。已通過 25 項 unittest，含 72 題子案例；尚不能保證所有未見問法都能理解。

## 對話上下文

聊天頁只在記憶體保留最近六題，不寫入檔案或 localStorage。只有目前問題未找到來源且符合追問語氣時，才重新檢索上一題，取已驗證的单一條文主題補充問題；先前回答、使用者宣稱公司核准或金額都不作為企業制度依據。明確新主題照新問題檢索；多主題或無可驗證來源時不推定。模式切換、清除對話或重新載入頁面會重置。

例如先問進修補助，再問「但是我上禮拜參加的，可以嗎」，會接續外部教育訓練，說明規章要求事前申請、事後補申請規則未訂定，無法判定是否可補申請或取得補助。這是規則式主題延續，不具完整語言模型對話理解。30 項自動測試通過。

## OR 候選與理解確認

檢索先以 OR 找可能相關主題。context_rules 任一群組命中即召回候選；完整群組命中可提高直接回答的明確度，但不阻擋部分命中問題進入釐清。broad_hints 支援七類概略詞彙。只有部分或廣泛命中時，回覆「我理解您可能在詢問……，是否正確？」並要求具體情境；候選主題不是已認定適用條文，sources 維持空清單。候選仍只來自當次允許的 ACTIVE 或明示草案測試資料。

單一主題確認可接續對話，多主題只說「對」仍需選擇或補充，不直接猜測。未知補助不得因「補助」命中訓練類而認定成立。現有詞彙涵蓋表與 72 題作為回歸基準，不能宣稱已列舉所有員工可能說法。35 項測試通過。

補充原因的「因為／所以／其實」可延續最近的已驗證主題。上一題同時引用同一類規章時保留共同主題，不任意挑一條；明確跨類別問題仍須釐清。臨時有事而來不及請假時，以理解確認與條件式緊急請假說明回覆，不自行判定事件一定符合緊急請假，不編造補登期限。38 項測試通過。

## 負責單位引導

config/department_routes.json 保存已提供規章支持的職掌與初步詢問方向，scripts/routing.py 在問題原因無法判定時給出有來源的引導。例如財務系統打不開不代表已確認缺少權限；先依帳號／權限職掌建議向 IT 求助，如需新增權限，再由主管確認業務需求。系統名稱含「財務」不直接導向財務部門。薪資、辦公環境與訓練等問題依對應已提供職掌建議詢問單位。

部門引導明確標示為初步判斷，不推定故障原因、資格、個人權限、費用或期限；只在當次允許的規章來源存在時使用。多單位同分時釐清問題性質。沒有職掌依據時仍說明未提供並詢問細節，不自行填入未知事项的 consultation_unit。43 項自動測試通過。

## 小助理回答風格

聊天畫面先呈現易讀重點與必要例外，用自然稱呼協助員工理解。36 條摘要存於 config/answer_style.json，每筆綁定條文 SHA-256；條文變更後未審閱新版摘要時回退到最新原文，不沿用舊摘要。display_answer 為聊天顯示內容，answer 保留原始完整回答；evidence 保存完整條文，畫面可在「查看完整條文與來源」展開。規章仍是唯一制度依據，摘要不能新增企業制度。46 項測試通過。

明確假別與描述對象優先於詞彙命中：家人生病不直接當作員工本人生病；已指定特休的請假原因／提前通知追問，延續特休而不是轉成病假。未指定假別時先釐清，不新增家庭照顧類制度。51 項測試通過。
