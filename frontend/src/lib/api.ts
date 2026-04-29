import type {
  Chunk,
  DocumentRecord,
  EmbeddingSettings,
  EvidenceUnit,
  KnowledgeBase,
  LLMSettings,
  LocalMinerUIngestResponse,
  LocalMinerUStatus,
  PublicConfig,
  QueryResponse,
  Stats
} from "./types";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    ...init
  });
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const data = await response.json();
      message = data.detail ?? message;
    } catch {
      // Keep the status message.
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export const api = {
  listKnowledgeBases: () => request<KnowledgeBase[]>("/knowledge-bases"),
  getKnowledgeBase: (id: number) => request<KnowledgeBase>(`/knowledge-bases/${id}`),
  createKnowledgeBase: (payload: { name: string; description?: string }) =>
    request<KnowledgeBase>("/knowledge-bases", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  deleteKnowledgeBase: (id: number) =>
    request<{ deleted: boolean }>(`/knowledge-bases/${id}`, { method: "DELETE" }),
  listDocuments: (kbId: number) => request<DocumentRecord[]>(`/knowledge-bases/${kbId}/documents`),
  getDocument: (documentId: string) => request<DocumentRecord>(`/documents/${documentId}`),
  deleteDocument: (documentId: string) =>
    request<{ deleted: boolean }>(`/documents/${documentId}`, { method: "DELETE" }),
  listChunks: (documentId: string) => request<Chunk[]>(`/documents/${documentId}/chunks`),
  listEvidenceUnits: (documentId: string) =>
    request<EvidenceUnit[]>(`/documents/${documentId}/evidence-units`),
  listKbEvidenceUnits: (knowledgeBaseId: number) =>
    request<EvidenceUnit[]>(`/knowledge-bases/${knowledgeBaseId}/evidence-units`),
  rebuildEvidence: (knowledgeBaseId: number) =>
    request<{ evidence_units: number }>(`/knowledge-bases/${knowledgeBaseId}/evidence/rebuild`, {
      method: "POST"
    }),
  ingestMock: (knowledgeBaseId: number) =>
    request<{ document_id: string; ingested: boolean }>("/parse/mock", {
      method: "POST",
      body: JSON.stringify({ knowledge_base_id: knowledgeBaseId })
    }),
  uploadDocument: async (knowledgeBaseId: number, file?: File) => {
    const formData = new FormData();
    if (file) formData.append("file", file);
    const response = await fetch(`${API_BASE_URL}/knowledge-bases/${knowledgeBaseId}/documents`, {
      method: "POST",
      body: formData
    });
    if (!response.ok) throw new Error(`Upload failed: HTTP ${response.status}`);
    return response.json() as Promise<DocumentRecord>;
  },
  ingestWithLocalMinerU: async (
    knowledgeBaseId: number,
    payload: {
      file: File;
      method: string;
      lang: string;
      formula: boolean;
      table: boolean;
    }
  ) => {
    const formData = new FormData();
    formData.append("file", payload.file);
    formData.append("method", payload.method);
    formData.append("lang", payload.lang);
    formData.append("formula", String(payload.formula));
    formData.append("table", String(payload.table));
    const response = await fetch(`${API_BASE_URL}/knowledge-bases/${knowledgeBaseId}/documents/mineru-local`, {
      method: "POST",
      body: formData
    });
    if (!response.ok) {
      let message = `MinerU ingest failed: HTTP ${response.status}`;
      try {
        const data = await response.json();
        message = data.detail ?? message;
      } catch {
        // Keep status message.
      }
      throw new Error(message);
    }
    return response.json() as Promise<LocalMinerUIngestResponse>;
  },
  localMinerUStatus: () => request<LocalMinerUStatus>("/mineru/local/status"),
  rebuildIndex: (knowledgeBaseId: number) =>
    request<{ indexed_chunks: number }>(`/knowledge-bases/${knowledgeBaseId}/index/rebuild`, {
      method: "POST"
    }),
  query: (payload: {
    knowledge_base_id: number;
    query: string;
    top_k: number;
    filters?: Record<string, unknown>;
  }) =>
    request<QueryResponse>("/query", {
      method: "POST",
      body: JSON.stringify({ ...payload, filters: payload.filters ?? {} })
    }),
  stats: () => request<Stats>("/stats"),
  config: () => request<PublicConfig>("/config"),
  embeddingSettings: () => request<EmbeddingSettings>("/settings/embedding"),
  updateEmbeddingSettings: (payload: {
    embedding_backend?: string;
    embedding_model?: string;
    jina_api_key?: string;
  }) =>
    request<EmbeddingSettings>("/settings/embedding", {
      method: "PUT",
      body: JSON.stringify(payload)
    }),
  llmSettings: () => request<LLMSettings>("/settings/llm"),
  updateLLMSettings: (payload: {
    llm_provider?: string;
    llm_base_url?: string;
    llm_model?: string;
    llm_api_key?: string;
  }) =>
    request<LLMSettings>("/settings/llm", {
      method: "PUT",
      body: JSON.stringify(payload)
    })
};
