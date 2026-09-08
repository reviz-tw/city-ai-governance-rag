export interface Crux {
  title: string;
  description: string;
  proPoints: string[];
  conPoints: string[];
}

export type LanguageCode = 'zh' | 'en' | 'ja' | 'fr' | 'es' | 'ru' | 'ar';

export interface Topic {
  id: string;
  category: string;
  title: string;
  description: string;
  tags: string[];
  documentsCount: number;
  sampleQuestions: string[];
  keyCruxes: Crux[];
  icon?: 'phone' | 'shield' | 'users' | 'leaf';
  bg?: string;
  border?: string;
  iconBg?: string;
  iconFg?: string;
}

export interface Citation {
  citation_id: number;
  title: string;
  link?: string;
  snippet?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations?: Citation[];
  timestamp: string;
  isStreaming?: boolean;
}

export interface GovernanceDocument {
  filename: string;
  gcs_uri: string;
  size_bytes: number;
  size_formatted: string;
  updated_at: string;
  content_type: string;
  city: string;
  country: string;
  policy_domain: string;
  document_type: string;
  language: string;
  publication_year: string;
  ai_summary: string;
  status: string;
}

export interface DocumentChunk {
  chunk_index: number;
  content: string;
  token_count: number;
  char_count: number;
  metadata: Record<string, any>;
}

export interface DocumentChunksDetail {
  filename: string;
  gcs_uri: string;
  size_formatted: string;
  metadata: Record<string, any>;
  total_chunks: number;
  total_characters: number;
  chunks: DocumentChunk[];
}
