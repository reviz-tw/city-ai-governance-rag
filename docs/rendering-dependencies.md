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
