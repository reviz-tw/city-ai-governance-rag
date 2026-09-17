# 渲染相依與授權

部署所需相依均在 Dockerfile／requirements.txt 中，不依赖開發機的 skills 或私有桌面程式。

| 元件 | 使用方式 | 已安裝套件 metadata 的授權 |
|---|---|---|
| ReportLab 4.5.1 | PDF 排版、字型嵌入 | BSD |
| python-pptx 1.0.2 | 可編輯 PPTX 文字與形狀 | MIT |
| Pillow | PNG 繪圖、字型量測 | MIT-CMU |
| google-genai 1.75.0 | Vertex 模型請求 | Apache-2.0 |

SVG 由程式依受限規格產生，文字經 XML escaping；不執行模型程式碼、HTML 或腳本。PDF 以 escaped 文字與固定 ReportLab 元件渲染。PPTX 不含巨集／任意模型形狀代碼，LibreOffice 在獨立暫存 profile 轉出預覽 PDF，設定執行 timeout。

容器安裝 Debian 的 `fonts-dejavu-core`、`fonts-wqy-zenhei`、`libreoffice-impress`，保留各套件在 `/usr/share/doc/*/copyright` 的授權文件。LibreOffice 本體依 MPL-2.0／LGPL 系列條款，字型依各字型套件的再散布／嵌入條款；不把開發機的 Arial／Arial Unicode 字型複製到映像。自訂 FONT_DIR 的字型必須由部署者確認可嵌入與再散布。

容器沒有讓模型提交 shell、Python、外部 URL 抓取或任意檔案讀取介面。LibreOffice 處理的是伺服器自行建立的 PPTX，不直接轉換任意使用者 Office 檔。上述措施不是 OS 級別斷網沙箱；worker 仍需要連接 Google API。

## 投影片製作 skill

`app/skills/research-slides/SKILL.md` 與 `references/examples.md` 隨 Docker 映像部署。`slide_authoring.py` 明確讀取兩者，將內容雜湊寫入任務與快取鍵；不是依靠模型自行發現 skill，也不依赖開發機的全域 skill。

新 PPTX 任務先規劃故事大綱，再產生受限的逐頁 JSON，最後逐頁核對主張、講者備註、原文條件與語氣。正常三次模型請求，若失敗只修正一次，最多五次；仍不通過則顯示任務失敗，不將未通過內容送交匯出。模型審查降低錯誤機會，不能保證每個語意主張正確，使用者仍可在確認前審閱原文與草稿。舊任務沿用既有渲染路徑。

五種版型是重點說明、比較表、流程、引文分析與數據圖。文字、表格、流程和圖表皆為原生 PPTX 物件，圖表包含可編輯資料工作簿。每頁保留來源標示、講者備註與完整文件／段落／版本資訊。請求頁數是整份簡報上限；不固定增加封面、摘要或參考資料頁。證據不足時產生較短簡報並說明缺口。

來源 ID、逐字引文與數值使用確定性檢查；引文僅忽略 PDF 抽字造成的空白及中文字間換行，保留標點與拉丁文字邊界。版面依安裝字型量測換行，使用可讀字級；內容過長時要求改寫或移入備註，不默默截斷。產生草稿、預覽與確認匯出皆執行版面檢查。CJK 使用 regular 字重，避免缺少粗體字型時 LibreOffice 合成粗體造成重疊。
