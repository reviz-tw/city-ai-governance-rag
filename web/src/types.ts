export interface Citation {
  citation_id: number;
  title: string;
  link?: string;
  snippet?: string;
  id?: string;
  document_id?: string;
  language?: string;
  version?: string;
  block_ids?: string[];
  chunk_id?: string;
  page_start?: number;
  page_end?: number;
}

export interface ChunkTranslationResult {
  document_id: string;
  version: number;
  source_language: string;
  language: string;
  complete: boolean;
  chunks: Array<{
    chunk_id:string;
    original:string;
    refs:Array<{block_id:string;start:number;end:number;page:number|null}>;
    status:'missing'|'queued'|'running'|'completed'|'failed'|'blocked';
    text:string|null;
    error:string|null;
    attempts:number;
  }>;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations?: Citation[];
  timestamp: string;
  isStreaming?: boolean;
  // Live presentation metadata only; restored conversations display in full.
  detailedStart?: number;
  response_language?: string;
  error?: string;
  errorKey?: import('./lib/panel-copy').PanelKey;
  status?: string;
  stage?: 'searching' | 'generating' | 'expanding';
  sourceCount?: number;
  answer_detail?: 'progressive'|'brief'|'detailed';
  pendingSourceCount?: number;
}
