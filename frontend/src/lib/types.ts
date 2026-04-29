export type KnowledgeBase = {
  id: number;
  name: string;
  description?: string | null;
  document_count?: number;
  chunk_count?: number;
  index_status?: string;
  created_at?: string | null;
};

export type DocumentRecord = {
  id: string;
  knowledge_base_id: number;
  title: string;
  authors: string[];
  abstract?: string | null;
  source_file?: string | null;
  parse_status: string;
  chunk_count?: number;
  created_at?: string | null;
};

export type LocalMinerURun = {
  command: string[];
  output_dir: string;
  artifacts: string[];
  stdout: string;
  stderr: string;
  duration_seconds: number;
};

export type LocalMinerUIngestResponse = {
  document: DocumentRecord;
  mineru: LocalMinerURun;
};

export type LocalMinerUStatus = {
  available: boolean;
  command: string;
  version?: string | null;
  error?: string | null;
};

export type Chunk = {
  document_id: string;
  chunk_id: string;
  content: string;
  section_path: string;
  page_start?: number | null;
  page_end?: number | null;
  content_type: "text" | "table" | "figure_caption" | "mixed" | string;
  metadata?: Record<string, unknown>;
};

export type EvidenceUnit = {
  id: number;
  knowledge_base_id: number;
  document_id: string;
  chunk_id: string;
  evidence_type: string;
  canonical_section: string;
  claim_text: string;
  normalized_facts?: Record<string, unknown>;
  source_text: string;
  page_start?: number | null;
  page_end?: number | null;
  citation_text: string;
  confidence: number;
  created_at?: string | null;
};

export type Citation = {
  chunk_id: string;
  document_id: string;
  section_path: string;
  page_start?: number | null;
  page_end?: number | null;
  citation_text: string;
  source_text: string;
  score: number;
};

export type RetrievedChunk = {
  chunk_id: string;
  document_id: string;
  content: string;
  source_text?: string;
  score: number;
  section_path?: string;
  page_start?: number | null;
  page_end?: number | null;
  content_type?: string;
  citation_text?: string;
  metadata?: Record<string, unknown>;
};

export type QueryResponse = {
  answer: string;
  citations: Citation[];
  retrieved_chunks: RetrievedChunk[];
  evidence_units?: EvidenceUnit[];
  evidence_sufficiency?: "sufficient" | "partial" | "insufficient" | string;
};

export type Stats = {
  knowledge_bases: number;
  documents: number;
  chunks: number;
  evidence_units?: number;
  vectors_sqlite?: number;
  index_status?: string;
  query_count?: number;
  answer_count?: number;
  recent_documents?: DocumentRecord[];
};

export type PublicConfig = {
  app_name: string;
  env: string;
  api_prefix: string;
  embedding_backend: string;
  embedding_model: string;
  embedding_source?: string;
  jina_api_key_configured?: boolean;
  jina_api_key_masked?: string | null;
  vector_store: string;
  mineru_api_url?: string | null;
  mineru_cli_command?: string;
  mineru_local_output_dir?: string;
  parser_mode: "mock" | "mineru" | string;
  llm_provider: string;
  llm_base_url?: string | null;
  llm_model?: string | null;
  llm_source?: string;
  llm_api_key_configured?: boolean;
  llm_api_key_masked?: string | null;
  llm_configured: boolean;
};

export type EmbeddingSettings = {
  embedding_backend: string;
  embedding_model: string;
  embedding_source: string;
  jina_api_key_configured: boolean;
  jina_api_key_masked?: string | null;
};

export type LLMSettings = {
  llm_provider: string;
  llm_base_url?: string | null;
  llm_model?: string | null;
  llm_source: string;
  llm_api_key_configured: boolean;
  llm_api_key_masked?: string | null;
};
