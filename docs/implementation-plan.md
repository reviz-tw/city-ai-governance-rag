# TODO 實作計畫與進度

2026-09-17，Demo 已結束，原 TODO 全部納入。以下以實作、測試、雲端可用性三層判定，不以刪除清單代替驗收。

| 工作 | 實作 | 驗證與剩餘條件 |
|---|---|---|
| Google Gen AI SDK／模型 | 已完成統一 SDK、ADC、global、設定與鎖版，移除 legacy fallback | 兩個模型已在 tdf-ocf 實際生成；dev 候選 FE 串流及 MCP 非串流均通過 |
| 語言／context | 已完成共同 schema、偵測、有限歷史、摘要、獨立來源篩選與 SSE | 本機自動化與真實多語生成通過；標準 Chunk Documents 的 zh-TW→en／ja 與 en→zh-TW Search 已通過 |
| Google 登入／權限 | 已完成 GIS、cookie、名單、文件 ACL、角色、個人短期 MCP 憑證 | OAuth 用戶端與兩個測試帳號已建立，本機 Gmail 真實登入通過；dev 候選 Gmail 與 hcchien@reviz.tw 管理員登入均已通過 |
| FE 去專題化 | 已完成移除專題側欄、預設台北、固定文件數 | 保留六種介面語言與九種內容語言代碼；新增面板說明以繁中為主 |
| 圖表／PDF／PPTX | 已完成共用任務、證據重讀、草稿確認、渲染、預覽下載與隔離 | 真實模型生成、dev Cloud Tasks／檔案下載、到期清理與多語排版檢視已通過 |
| 原文／翻譯 | 已完成抽取、定位、版本、分段、術語、完整／部分狀態與並排閱讀 | 結構、數字與完整性自動化通過；複雜 PDF 保留擷取限制，完整譯本待人工抽驗 |
| 切片修改／發布 | 已完成 baseline、草稿 diff、審閱 hash、版本衝突、背景匯入、檢索驗證與回復 | 標準 Chunk-as-Document 已通過雲端發布、合併／拆分、回復、原文 hash 與 FE／MCP 跨語驗收；CHUNK_INDEX_ENABLED=true |
| 持久化 dev | 使用者已核准台灣 PostgreSQL、私有 GCS、Cloud Tasks、Secret Manager | 建立與候選部署完成；切片新版 00047-pol 已占 100% 流量，背景任務沿用 candidate worker 標籤，後續部署需核對版本 |

已確認決策：Google／Gmail 登入；Gemini global 可處理研究文件；外部測試模式與網站名單限定 hcchien@gmail.com、hcchien@reviz.tw；管理員僅 hcchien@reviz.tw。Google 基本身分登入適用測試名單例外，實際登入限制由網站名單執行。

已完成候選版建立、真實 Gmail 登入、持久化任務、Cloud Tasks、PDF／PPTX／圖表／翻譯下載及 MCP 共用契約。剩餘驗收：完整政策譯本人工抽驗；固定研究題組的模型品質／成本比較已記錄於 model-benchmark.md。依使用者授權，已在候選切片流程驗收後切換流量；未通過的項目維持未完成。
