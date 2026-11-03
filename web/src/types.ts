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
