# TODO

最後更新：2026-09-16

狀態：[實作計畫](docs/implementation-plan.md)與[驗證紀錄](docs/verification.md)。下列「現況／Demo」描述保留為改動前基準；勾選表示已有實作與對應驗證，未勾選表示仍有雲端或人工驗收缺口，不能以刪除取代完成。

## P0：多語系與 MCP 語言契約

### 1. MCP 缺少可靠的回答語言判定

#### 現況與問題

- 前端會把使用者選擇的介面語言明確傳給後端。
- MCP 的 `ask_city_ai_governance_rag` 只有 optional `language` 參數；是否傳入目前取決於呼叫 MCP 的 LLM 如何產生 tool arguments，沒有保證。
- 後端沒有偵測問題語言。MCP 未傳 `language` 時，回答語言會直接預設為繁體中文。

#### Demo 階段暫定決策

- UI 語言與 AI 回答語言分開處理：
  - `interface_language` 只控制按鈕、選單與提示文字。
  - `response_language` 控制 AI 最終回答語言，預設值為 `auto`。
  - `source_languages` 獨立控制來源文件語言，不能由 UI 語言或回答語言隱含決定。
- `response_language=auto` 時，依下列優先順序解析：
  1. 使用者在問題中明確指定的回答語言，例如「請用英文回答」。
  2. 使用者另外設定的固定回答語言；demo 階段若尚未提供此設定則略過。
  3. 偵測本次提問所使用的語言；例如英文介面輸入完整中文問題，預設以中文回答。
  4. 問題太短、以數字／專有名詞為主或偵測信心不足時，才使用 `interface_language` 作為 fallback。
  5. 多輪對話參考近期主要語言，避免因單一外語術語而頻繁切換回答語言。
- Demo 完成後重新檢視此策略及使用者測試結果，再決定是否在 FE 增加獨立的「回答語言」選項。

#### 待辦

- [x] 將問答工具的參數改名為語意明確的 `response_language`，不要再用含義模糊的 `language`。
- [x] FE 繼續明確傳入 `response_language`。
- [x] FE 傳入獨立的 `interface_language`；demo 階段預設傳入 `response_language="auto"`。
- [x] MCP client 可依對話語言提供 `response_language`，但後端不能把這視為唯一保障。
- [x] 當 `response_language` 未提供時，由後端根據 `question` 做語言偵測；優先採可測試、低成本的語言辨識器，而不是再呼叫一次生成式 LLM。
- [x] 對短句、數字、專有名詞或多語混合問題設定明確 fallback，例如 MCP host locale 或 `zh-TW`。
- [x] 實作語言解析優先序：明確指令 > 固定回答語言 > 提問語言偵測 > UI 語言 fallback。
- [x] 為多輪對話定義語言穩定規則，避免回答語言在相鄰訊息間不必要地跳動。
- [x] 統一並驗證語言代碼，採 BCP 47／既定 mapping，例如 `zh-TW`、`en`、`ja`、`fr`、`es`、`ru`。
- [x] 在不記錄完整問題內容的前提下，記錄最終回答語言及來源：`explicit`、`detected` 或 `fallback`。

#### 驗收條件

- [x] FE 與 MCP 對 `response_language` 的行為一致。
- [x] 英文介面輸入完整中文問題時，`response_language=auto` 會以中文回答。
- [x] 無法可靠判斷問題語言時，才退回 `interface_language`。
- [x] 明確傳入的 `response_language` 優先於自動偵測結果。
- [x] 為英文、日文、繁體中文及多語混合問題建立自動化測試。

### 2. 回答語言與來源文件語言混用

#### 現況與問題

- `language_filter` 同時控制「回答使用的語言」及「來源文件語言篩選」。
- 中文回答目前會把檢索限制在中文文件；其他回答語言則搜尋完整語料，再由 Gemini 使用指定語言回答。
- 這會造成中文使用者可能找不到英文、日文或其他國家的原文研究，與「多語原生、跨語檢索」的產品敘事不一致。
- MCP 的 `search_city_ai_governance_knowledge.language` 又是純粹的來源文件篩選，與問答工具中同名參數的語意不同。

#### 待辦

- [x] 將參數拆成：
  - `response_language`：最終回答語言。
  - `source_languages`：選用的來源文件語言，可為多值。
- [x] `source_languages` 預設不限制，讓所有語言文件都能參與跨語檢索。
- [x] 只有使用者或研究流程明確要求時，才套用來源語言 filter。
- [x] 文件 metadata 持續保留原始語言，並在引用資訊中顯示來源語言。
- [ ] 重新檢查 Vertex AI Search 的資料結構、語意檢索設定及多語 embedding 是否真的支援預期語種；不要只用生成階段的翻譯能力代替跨語檢索驗證。
- [x] 更新 FE API、MCP tool schema、後端 schema、prompt 與文件，避免同名欄位具有不同含義。

#### 驗收條件

- [ ] 中文提問能檢索到英文／日文等原文，並以中文回答及引用原文來源。
- [ ] 明確指定 `source_languages=["en"]` 時，只回傳英文來源。
- [x] 在上述條件完成前，不把「多語原生」解釋成已驗證的完整跨語檢索能力。

## P1：FE 簡化與共用產出工具（Demo 後實作）

### 已選定方向與範圍

- FE 移除「焦點專題」與「核心剖析」入口及相關 drawer，改為一般城市 AI 治理諮詢介面。
- 新增「製作圖表」、「製作報告 PDF」、「產出投影片」三個工具入口；功能完成前不放置看似可用、實際無法產出的按鈕。
- 架構採 FE API／MCP → 共用產出服務 → 背景任務、預覽與下載，不讓 FE 依賴使用者桌面上的 Claude／Codex session。
- Skills 是 AI 執行流程的指南、範本與選用腳本；MCP 是工具呼叫介面。兩者不能取代實際的資料驗證、繪圖與文件渲染服務。
- 目前 MCP 只有搜尋、問答、文件整理與切片預覽，沒有圖表／PDF／投影片產出。桌面 Claude 示範的檔案產出不代表本專案已提供此能力。

### Implementation plan

- [x] FE 移除兩個側欄入口、TopicDrawer，以及聊天區的目前專題／切換專題控制；將開場文字、範例問題及對話 state 改為不依賴預設專題的設計。
- [x] 解除 `/api/chat/stream` 固定傳入 `city: '台北'` 的限制；研究城市由使用者明確指定或 context 解析，不把 UI 移除等同於取消所有使用者自訂研究範圍。
- [x] 檢查 topic API、型別與多語字串的使用者，只移除不再使用的 FE 相依，不連帶刪除 Admin 或其他仍需要的功能。
- [x] 與 context management 共用輸入契約：明確選擇「這則回答」或「這段對話」，提供 message／source IDs、有限研究 context、目標語言及版型；不隱含取得全部歷史。
- [x] 生成前重新取得使用者有權存取的原始證據；AI 回答僅作為待整理草稿，不作為新的事實來源。保留引用、資料時間、限制及不確定性。
- [x] 建立共用 artifact schema，區分內容規劃、驗證與渲染：包含輸出類型、語言、資料／引用、版型版本、來源版本與生成狀態。
- [x] 製作圖表：AI 產生受限且可驗證的圖表規格與資料，由程式渲染為 SVG／PNG；第一版支援少量統計圖、比較表、流程圖及架構圖，不執行模型任意生成的程式碼。
- [x] 統計圖必須有可追溯的數字、單位、比較期間及來源；只有質性訪談／研究文字時，提供流程圖或質性比較表，不能杜撰數據或把推論冒充統計。
- [x] 製作報告 PDF：先生成可預覽、可修正的報告草稿，再以固定版型產出，包含摘要、分析、建議、限制與參考來源。
- [x] 產出投影片：先提供大綱／頁數／受眾與語言確認，再套版輸出可編輯 PPTX；Google Slides 原生輸出留作後續整合，另行處理 OAuth、檔案目的地與分享權限。
- [x] 選擇可部署的繪圖、PDF 與 PPTX 渲染工具並驗證授權／相依；可參考現有 skills 的流程及範本，但不能假設開發端 skills 已存在於產品執行環境。
- [x] 加入多語字型、換行、中英日混合語言排版驗證；不只測試模型是否能產生外語文字。
- [x] 定義 FE API 的建立任務、查詢狀態、取消／重試、預覽與下載；PDF／投影片等耗時工作採背景任務，顯示 queued／running／completed／failed。
- [x] MCP 以相同服務提供圖表／報告／投影片工具及任務查詢，回傳 artifact ID、狀態與受控下載資訊；不複製另一套生成 pipeline。
- [x] 沿用並檢查實際身份／文件授權；為產出與下載加入使用者隔離、速率／成本限制、保存期限、刪除及受控連結，不能以知道 artifact ID 作為存取權限。
- [x] 文件、對話及模型輸出視為不可信資料；限制渲染器的檔案／網路存取，不因內容指令開啟額外工具權限或讀取其他使用者資料。

### 建議實作順序與驗收

- [x] 先完成 FE 去專題化與 context／來源契約，再建立 artifact 任務基礎；依序完成圖表、PDF、PPTX，最後增加 MCP wrapper。
- [x] FE 沒有殘留兩個舊入口、專題切換或預設台北篩選；仍能正常提問、串流回答、清除對話及切換語言。
- [x] 三個工具都能以選定回答／對話產出可預覽及下載的實際檔案；PDF 可正常閱讀、PPTX 可編輯、圖表數據與來源一致。
- [x] FE 與 MCP 對同一份輸入使用相同內容與渲染規則；未提供的 host 對話不被假定存在。
- [x] 測試多語排版、來源缺失、長內容、失敗／取消／重試、跨使用者存取及連結到期；只有檔案渲染完成才標示產出成功。

## P1：來源文件翻譯（多語閱讀與引用，Demo 後實作）

### 需求與設計方向

- 多語回答不代表使用者能閱讀原始參考文件；FE 應讓使用者從引用來源開啟文件，選擇語言並取得譯本。
- 「跨語檢索」與「文件翻譯」分開：原文仍是檢索與引用的權威來源，翻譯是閱讀輔助，不把所有文件預先翻譯成所有語言作為跨語檢索的必要條件。
- 保留原始文件，不以譯文覆寫原文或研究者修正後的已發布內容；引用需能回到原始文件、頁碼／段落與版本。
- MVP 提供原文／譯文並排閱讀及完整文件文字譯本；可先翻譯引用段落供快速理解，但必須明確區分「段落翻譯」與「全文翻譯」。
- 第一版以保留標題、段落、表格關係與來源頁碼為目標；不承諾任意掃描 PDF、複雜版面或圖片中的文字能完整還原。

### Implementation plan

- [x] 建立獨立 `target_language` 參數並驗證語言代碼；翻譯目標可預設為已解析的回答語言，讓使用者另行切換，不改變 `source_languages` 檢索範圍。
- [x] 引用卡顯示原始語言，提供「查看原文／翻譯段落／翻譯全文」；開始全文翻譯前顯示文件、目標語言、工作範圍及預期等待提示。
- [x] 建立以授權文件 ID／版本與原始段落定位為輸入的翻譯 API；不能讓任意 URL 或外部文字隱含取得受限制文件。
- [x] 翻譯前驗證文本擷取品質，處理標題、表格、註腳及頁碼對應；掃描／圖片文件先標示需要 OCR，擷取不足時警告或拒絕全文翻譯，不宣稱已完整翻譯。
- [x] 長文件依語意段落分批翻譯，維持章節順序、專有名詞／機構／政策術語的一致性；段落保留原文 ID／頁碼，不直接沿用檢索 chunks 的 overlap 造成重複譯文。
- [x] 翻譯規則要求保留數字、日期、單位、否定語意、條件、引用與連結，不自行摘要、補充建議或改寫成研究結論；有歧義或無法翻譯的內容需標示。
- [x] 在閱讀介面標示「AI 輔助翻譯，非官方譯本」，提供原文／譯文並排、原始來源連結及翻譯版本；政策／法律關鍵判斷提醒回查原文。
- [x] 全文翻譯採背景任務，使用共用 artifact 任務狀態、取消／重試、預覽與下載機制；部分成功不得標示全文完成。
- [x] 快取鍵包含文件 ID、原文版本／雜湊、目標語言、翻譯模型／設定與術語表版本；原文／人工修正版本更新時，舊譯本標示過期並重新生成。
- [x] 保存原始文件版本與實際翻譯輸入版本的對應；若使用清理後文字／人工修正內容作為輸入，需揭露並保留其與原文的差異，不假定兩者相同。
- [x] 譯本預設不另外加入搜尋索引，避免同一份研究重複命中或譯文被當成獨立證據；日後如需索引，另行設計原文關聯、去重與版本策略。
- [x] 提供全文譯本下載；文字閱讀版優先，翻譯 PDF 可復用報告渲染服務，另行驗證表格、字型與換行，不宣稱保留原 PDF 完全相同的版面。
- [x] 將同一翻譯服務封裝為 MCP 工具，明確區分引用段落與全文模式、目標語言及任務狀態，供進階使用者使用。
- [x] 沿用原文的存取／下載權限，譯本不能比原文更公開；確認上傳文件的翻譯／再散布權利、模型處理與資料落地要求，設定成本上限、保存期限與刪除規則。
- [x] 文件內容只作為翻譯資料，不執行其中的指令；一般 log 不保存完整原文或譯文。

### 驗收條件

- [x] 使用者能以英文／日文回答的引用卡開啟中文來源，取得指定語言的段落與全文譯本，並隨時回看原文。
- [ ] 譯文的標題、段落、表格、數字、日期、否定及條件語意通過抽樣／關鍵段落人工驗證；全文模式不漏段、不重複、不以摘要代替翻譯。
- [x] 每個譯文段落可追溯原文定位及版本；來源更新時不把舊譯本顯示為最新版本。
- [x] 多語回答仍引用原始文件；譯本不導致重複檢索或產生新的無來源事實。
- [x] 權限隔離、部分失敗、取消／重試、掃描文件警告、過期快取及多語閱讀／下載排版通過測試。

## P1：Context management（Demo 後統一設計與實作）

### 現況與問題

- FE 的 `messagesByTopic` 保留畫面上的對話紀錄，但每次 API request 只傳本次問題，沒有傳入歷史訊息。
- `/chat/stream` 雖然收到 `topic_id`，目前沒有把它用於檢索或生成；模型只取得本次問題與本次檢索片段。
- 因此，「那新北市呢？」、「把剛才的建議整理成報告」等追問，可能缺少必要上下文。
- MCP host 通常自行管理對話，但目前問答工具只接收 `question`、`city`、`language`；後端不能假設已取得 Claude 等 host 的完整歷史。
- 目前沒有明確的歷史摘要、檢索內容去重、token 預算或 context 淘汰策略。

### 待辦

- [x] Demo 後決定 context ownership：FE 傳入有限歷史，或由後端以 session 管理；MCP 則由 host 明確提供必要上下文，不隱含讀取 host 對話。
- [x] 定義共同 context schema，區分本次問題、近期對話、歷史摘要、研究範圍（城市／專題）、回答語言偏好與檢索證據。
- [x] 配合 FE 去專題化移除對預設 `topic_id` 的依賴；研究範圍改由明確的城市／議題 context 表達，定義重新開始及使用者改變範圍時，哪些 context 保留或清除。
- [x] 支援追問解析：根據有限歷史將「那新北市呢？」改寫成可獨立檢索的完整問題，但保留原始問題及使用者意圖。
- [x] 依實際模型限制設定 token 預算，分配給系統指令、歷史、摘要、檢索片段與預留回答空間；不要無限附加全部歷史或文件。
- [x] 保留近期訊息，較舊內容以滾動摘要壓縮；摘要需保留已確認需求、語言偏好、重要限制、未解問題與來源 ID，不能自行新增事實。
- [x] 對檢索片段做相關性排序、去重與長度控制；每次追問重新取得需要的證據，不把前次 AI 回答當成已驗證來源。
- [x] 定義 MCP 的最小 context 輸入，例如 `research_context` 或有限 `history`；避免把整段桌面對話不必要地送往後端。
- [x] 將文件及對話內容視為不可信資料，不能藉由 context 覆蓋系統指令或取得額外權限。
- [x] 若採後端 session，加入使用者／session／專題隔離、有效期限、刪除與重設機制；預設不永久保存完整對話，並清楚揭露傳輸及保存範圍。
- [x] 記錄 context token 用量、摘要／截斷事件與延遲，不在一般 log 中記錄完整對話或敏感文件內容。

### 驗收條件

- [x] FE 能正確處理「那新北市呢？」及「整理剛才的建議」等多輪追問。
- [x] 長對話不超過設定的 token 預算，且摘要後仍保留研究需求與回答語言偏好。
- [x] 改變研究範圍、重新開始及 session 到期時，context 行為符合明確規則。
- [x] 不同使用者／session 的 context 不會混用；MCP 未提供的 host 歷史不會被假定存在。
- [x] 摘要與追問回答不新增無來源事實，引用能對應本次實際取得的原始文件。

## P1：自動切片＋人工修正（Demo 後實作）

### 已選定方向與範圍

- 以自動切片為主，研究者只修正需要處理的例外，不要求逐段人工建立知識庫。
- MVP 流程：保留原始文件 → 自動切片 → 人工修正草稿 → 明確發布 → 重新索引 → 驗證實際檢索結果。
- 人工修正涵蓋文字編輯、合併與拆分段落；不直接覆寫原始研究報告，也不把「儲存草稿」等同於「已進入 AI 知識庫」。
- 優先沿用現有搜尋服務，先驗證 Bring your own chunks 匯入路徑；不在 MVP 自建 embedding／vector database，也不一次打造完整的多人知識庫 CMS。

### 現況與問題

- Admin「切片檢視」目前只是從 GCS 原始文件以固定 `500` 字元、`80` overlap 產生的臨時預覽，並非實際搜尋索引中的 chunks。
- 沒有 chunk 編輯、版本保存或發布 API；上傳流程也未採用使用者修改後的「清理後文字」欄位。
- 現有檢索程式讀取 document snippets，需配合新匯入格式取得真正的 chunk 結果及來源資訊。

### 待辦

- [x] 先做技術驗證：在 dev／測試 data store 匯入自訂 chunks，確認目標服務、SDK 與 data store 設定相容；確認功能發布階段及限制，不先假設現有索引可直接沿用。
- [ ] 驗證同一文件的 chunks 更新、合併／拆分及重新匯入行為，確保舊片段不殘留或與新版重複；通過後才開發完整編輯流程。
- [x] 保存原始文件及可追溯的切片資料：文件 ID、chunk ID、順序、原始頁碼／文字範圍、原始語言、內容、版本與草稿／已發布狀態。
- [x] 建立自動切片 baseline，保留段落與標題脈絡；切片參數與演算法版本須可追溯。
- [x] Admin 並排顯示原始文件與 chunk 草稿，提供文字編輯、合併、拆分及還原自動切片版本。
- [x] 修正「清理後文字」及「切片邊界預覽」操作，讓預覽與保存採用同一份實際內容，而非只改變畫面。
- [x] 將儲存草稿與發布分開；發布前檢查空片段、重複 ID、順序、來源範圍及文字長度，並顯示修改差異。
- [x] 加入 Admin 身分驗證與編輯／發布授權，不能在現有匿名文件管理 API 上直接增加可寫入 chunk 的功能。
- [x] 保存發布版本、操作者與修改紀錄；MVP 先提供單人操作及版本衝突檢查，多人協作／審核流程留待後續。
- [x] 匯出符合搜尋服務要求的 chunk payload，保留原始文件連結與頁碼；重新索引採背景任務並顯示 pending／成功／失敗、重試及錯誤原因。
- [x] 保留前一個可用發布版本，設計重新匯入／回復流程；索引更新尚未確認成功時，不宣告新版已可供 AI 使用。
- [x] 將檢索與引用改成實際 chunk 結果，回傳來源文件、chunk ID、頁碼與可追溯版本，讓 FE／MCP 共用同一份已發布知識。
- [x] 建立回歸測試，涵蓋多語文件、合併／拆分、索引更新失敗、重試、回復與引用正確性。

### 驗收條件

- [ ] 草稿修改不影響 FE／MCP 的正式回答；發布並確認索引完成後，兩個入口都能檢索修正後內容。
- [ ] Admin 顯示的已發布 chunks 與實際搜尋結果一致，不再以本地臨時預覽冒充索引狀態。
- [ ] 合併／拆分後不出現舊片段重複命中，引用仍能對應原始文件與來源範圍。
- [x] 原始文件保持不變，人工修正有版本與修改紀錄，且可回復前一個可用版本。
- [x] 未授權使用者不能編輯或發布；索引失敗可追蹤、重試，且不被顯示為成功。

## P0：Gemini 與 Vertex AI 版本更新

### 現況

- `backend/requirements.txt` 使用寬鬆下限：
  - `google-cloud-discoveryengine>=0.11.0`
  - `google-cloud-aiplatform>=1.71.0`
  - `google-generativeai>=0.8.3`
- 程式同時使用：
  - `vertexai.generative_models.GenerativeModel`
  - `google.generativeai.GenerativeModel`
- 預設模型為 `gemini-2.5-flash`，fallback 仍包含 `gemini-1.5-flash` 與 `gemini-1.5-pro`。

### 風險

- Vertex AI SDK 的 generative AI module 已在 2026-06-24 移除，需遷移至 Google Gen AI SDK。
- `google-generativeai` 已不再積極維護，官方建議改用 `google-genai`。
- 1.5 fallback 已退役；2.5 的官方退役日為 2026-10-20（原敘述過早）。移除舊 SDK 與未驗證 fallback，不能用多個模型名稱保證可用性。
- `google-cloud-discoveryengine>=0.11.0` 允許安裝跨度很大的版本，缺乏可重現的部署基線。

### 待辦

- [x] 將生成模型呼叫統一遷移至 `google-genai`，支援 Vertex AI ADC；若仍保留 Gemini Developer API fallback，也應共用同一套 SDK 與清楚的認證策略。
- [x] 移除 `vertexai.generative_models` 與 `google.generativeai` 的 legacy 呼叫。
- [x] 確認專案是否還需要 `google-cloud-aiplatform`；若僅為舊 generative module 而存在，遷移後移除。
- [x] 移除 `gemini-1.5-flash`、`gemini-1.5-pro` 及已退役模型 fallback。
- [x] 評估將主要模型升級至目前可用的 GA Gemini 模型；候選為 `gemini-3.7-flash`，已完成[固定證據基準](docs/model-benchmark.md)，但合併前必須驗證：
  - 專案已啟用所需 API，且目前帳號／專案具有存取權。
  - `global` 或所選 multi-region 符合資料落地與治理需求。
  - RAG 回答品質、引用遵循、繁中與多語表現、延遲及成本均通過基準測試。
- [x] 將模型 ID 與必要的 generation／thinking 設定集中管理，不在 pipeline 內硬編碼多組 fallback 名稱。
- [x] 評估 `google-cloud-discoveryengine` 升級至 `0.20.2` 或當時最新相容版本，驗證 `SearchRequest`、snippet／summary 設定及 `ImportDocumentsRequest`。
- [x] 建立 lock file 或 constraints，避免只使用 `>=` 造成 Cloud Build 不可重現。
- [x] 建立升級前後 regression suite，至少涵蓋：一般問答、SSE 串流、MCP 問答、引用編號、文件匯入、跨語檢索及錯誤 fallback。
- [ ] 在 staging／dev Cloud Run 完成 smoke test 後才更新 production；記錄實際模型 ID、SDK 版本及 rollback 方法。

### 驗收條件

- [x] 程式碼不再 import `vertexai.generative_models` 或 `google.generativeai`。
- [x] 部署依賴可重現，CI 能從乾淨環境完成安裝、啟動與測試。
- [x] FE 與 MCP 均能以新版 SDK／模型完成串流及非串流回答。
- [x] 所有 configured model IDs 均為當下仍受官方支援且已在目標專案驗證可用的版本。
- [ ] Vertex AI Search 的搜尋與文件匯入流程通過整合測試。

## 官方參考資料

- 搜尋服務切片與 Bring your own chunks：<https://cloud.google.com/generative-ai-app-builder/docs/parse-chunk-documents>
- Vertex AI generative AI module deprecation：<https://cloud.google.com/vertex-ai/generative-ai/docs/deprecations>
- Google Gen AI SDK／Vertex AI quickstart：<https://cloud.google.com/vertex-ai/generative-ai/docs/start/quickstart>
- Gemini API libraries 與 legacy SDK 狀態：<https://ai.google.dev/gemini-api/docs/libraries>
- Vertex AI Gemini 模型版本與生命週期：<https://cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions>
- Gemini 3.7 Flash：<https://cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-7-flash>
- Discovery Engine Python client changelog：<https://cloud.google.com/python/docs/reference/discoveryengine/latest/changelog>
