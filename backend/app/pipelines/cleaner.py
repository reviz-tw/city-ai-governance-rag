import json
import logging
import re
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from app.core.config import settings
from app.models.schema import GovernanceMetadata, ChunkPreview, DocumentCleanAndTagResponse

logger = logging.getLogger(__name__)

if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

CLEANER_PROMPT = """你是一位「全球城市 AI 治理研究」的資深顧問與知識工程師。
你的任務是分析使用者提供的政策文件或報告，進行結構化預處理、雜訊清理，並抽取專業的 Metadata 與重點摘要。

文件原始檔名: {filename}
文件內容前 15,000 字元:
---
{content}
---

請輸出繁體中文為主的 JSON 回應（格式必須完全符合以下結構，不要包含 markdown 標籤外的雜訊）：
{{
  "cleaned_text": "經過排版整理與雜訊清理後的主要本文內容",
  "suggested_metadata": {{
    "title": "精確文件標題",
    "city": "城市名稱 (如: 台北, 倫敦, 紐約, 新加坡, 東京, 首爾, 赫爾辛基, 阿姆斯特丹, 巴塞隆納 等)",
    "country": "國家名稱 (如: 台灣, 英國, 美國, 新加坡, 日本, 韓國, 芬蘭, 荷蘭, 西班牙 等)",
    "region": "地區/洲別 (如: 亞太, 歐洲, 北美, 全球)",
    "policy_domain": "政策領域 (選取最符合項目: 演算法透明度與可解釋性, 資料隱私與安全, 公共治理與智慧城市, 交通與移動性, 倫理審查與風險分級, 生成式AI使用規範, 政府採購準則, 數位權利保障)",
    "document_type": "文件類型 (選取最符合項目: 市政府自治法規, 政策白皮書, 框架與技術指引, 顧問評估報告, 標竿案例研究)",
    "language": "原文主要語言代碼 (如: zh-TW, en, ja, ko, es, fr, de)",
    "publication_year": 2025,
    "source_url": "若內文提及網址或機關名稱則填寫",
    "tags": ["關鍵字1", "關鍵字2", "關鍵字3"]
  }},
  "summary": "150字以內之繁體中文核心政策摘要",
  "key_takeaways": [
    "要點1",
    "要點2",
    "要點3"
  ]
}}
"""

def clean_and_annotate_document(raw_text: str, filename: Optional[str] = None) -> DocumentCleanAndTagResponse:
    """使用 Gemini LLM 進行文件預清理與專業治理 Metadata 標註"""
    try:
        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            generation_config={"response_mime_type": "application/json"}
        )
        
        prompt = CLEANER_PROMPT.format(
            filename=filename or "未知檔案",
            content=raw_text[:15000]
        )
        
        response = model.generate_content(prompt)
        data = json.loads(response.text)
        
        meta = data.get("suggested_metadata", {})
        metadata_obj = GovernanceMetadata(
            title=meta.get("title", filename or "未命名治理文件"),
            city=meta.get("city", "全球"),
            country=meta.get("country", "未指定"),
            region=meta.get("region", "全球"),
            policy_domain=meta.get("policy_domain", "公共治理與智慧城市"),
            document_type=meta.get("document_type", "政策白皮書"),
            language=meta.get("language", "zh-TW"),
            publication_year=meta.get("publication_year", 2025),
            source_url=meta.get("source_url"),
            tags=meta.get("tags", [])
        )
        
        return DocumentCleanAndTagResponse(
            cleaned_text=data.get("cleaned_text", raw_text),
            suggested_metadata=metadata_obj,
            summary=data.get("summary", ""),
            key_takeaways=data.get("key_takeaways", [])
        )
    except Exception as e:
        logger.error(f"AI 清理與標註失敗，使用預設規則回退: {e}")
        # Fallback default metadata
        default_meta = GovernanceMetadata(
            title=filename or "匯入之 AI 治理文件",
            city="未知城市",
            country="未知國家",
            region="全球",
            policy_domain="公共治理與智慧城市",
            document_type="政策白皮書",
            language="zh-TW",
            publication_year=2025,
            tags=["AI治理", "城市政策"]
        )
        return DocumentCleanAndTagResponse(
            cleaned_text=raw_text,
            suggested_metadata=default_meta,
            summary="未能自動產出摘要，已載入原始文字。",
            key_takeaways=[]
        )

def preview_chunks(
    text: str, 
    metadata: Dict[str, Any], 
    chunk_size: int = 500, 
    chunk_overlap: int = 80
) -> List[ChunkPreview]:
    """將文字進行切片 (Chunking) 並計算長度供 Admin UI 預覽"""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: List[str] = []
    current_chunk = []
    current_len = 0
    
    for para in paragraphs:
        para_len = len(para)
        if current_len + para_len > chunk_size and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            # 保留部分重疊 (overlap)
            if chunk_overlap > 0 and len(current_chunk) > 1:
                current_chunk = [current_chunk[-1], para]
                current_len = len(current_chunk[0]) + para_len
            else:
                current_chunk = [para]
                current_len = para_len
        else:
            current_chunk.append(para)
            current_len += para_len
            
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
        
    previews = []
    for idx, chunk in enumerate(chunks):
        previews.append(ChunkPreview(
            chunk_index=idx + 1,
            content=chunk,
            token_count=max(1, len(chunk) // 2),  # 估算 token 數 (中英文混合)
            char_count=len(chunk),
            metadata=metadata
        ))
        
    return previews
