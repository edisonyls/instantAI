const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

// Knowledge Base APIs
export interface KnowledgeBase {
  id: string;
  name: string;
  description?: string;
  total_documents: number;
  total_chunks: number;
  created_at: string;
  updated_at: string;
}

export interface APIKey {
  key: string;
  knowledge_base_id: string;
  name: string;
  created_at: string;
  last_used?: string;
  usage_count: number;
  is_active: boolean;
}

export interface DocumentInfo {
  id: string;
  filename: string;
  text_length: number;
  chunk_count: number;
  upload_timestamp: string;
  processing_status?: string;
}

export interface CreateKnowledgeBaseRequest {
  name: string;
  description?: string;
}

export interface CreateKnowledgeBaseResponse {
  knowledge_base: KnowledgeBase;
  api_key: APIKey;
  message: string;
}

export interface PublicChatRequest {
  api_key: string;
  message: string;
  session_id?: string;
}

export interface PublicChatResponse {
  response: string;
  session_id: string;
  usage: {
    tokens_used: number;
    context_chunks: number;
    processing_time_ms: number;
  };
  timestamp: string;
}

export interface HealthStatus {
  status: string;
  services: {
    rag: any;
    ollama: any;
  };
  timestamp: string;
}

export interface SystemInfo {
  ai_configuration: {
    ollama_model: string;
    ollama_host: string;
    max_context_length: number;
    similarity_threshold: number;
    max_retrieved_chunks: number;
    embedding_model: string;
  };
  document_processing: {
    chunk_size: number;
    chunk_overlap: number;
    max_file_size_mb: number;
    max_file_size_bytes: number;
  };
  storage: {
    upload_directory: string;
    temp_directory: string;
    chroma_db_path: string;
    vector_db_collection: string;
  };
  security: {
    access_token_expire_minutes: number;
    cors_origins: string[];
  };
  logging: {
    log_level: string;
    log_file: string;
  };
}

// Knowledge Base Management
export async function createKnowledgeBase(
  request: CreateKnowledgeBaseRequest
): Promise<CreateKnowledgeBaseResponse> {
  const response = await fetch(`${API_BASE_URL}/api/knowledge-bases`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Failed to create knowledge base: ${response.statusText}`);
  }

  return response.json();
}

export async function getKnowledgeBases(): Promise<{
  knowledge_bases: KnowledgeBase[];
}> {
  const response = await fetch(`${API_BASE_URL}/api/knowledge-bases`);

  if (!response.ok) {
    throw new Error(`Failed to fetch knowledge bases: ${response.statusText}`);
  }

  return response.json();
}

export async function getKnowledgeBase(id: string): Promise<{
  knowledge_base: KnowledgeBase;
  documents: DocumentInfo[];
  stats: any;
  api_key: APIKey;
}> {
  const response = await fetch(`${API_BASE_URL}/api/knowledge-bases/${id}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch knowledge base: ${response.statusText}`);
  }

  return response.json();
}

// Document Management
export async function uploadDocuments(
  knowledgeBaseId: string,
  files: File[]
): Promise<any> {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append("files", file);
  });

  const response = await fetch(
    `${API_BASE_URL}/api/knowledge-bases/${knowledgeBaseId}/documents`,
    {
      method: "POST",
      body: formData,
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to upload documents: ${response.statusText}`);
  }

  return response.json();
}

export async function deleteDocument(
  knowledgeBaseId: string,
  documentId: string
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/knowledge-bases/${knowledgeBaseId}/documents/${documentId}`,
    {
      method: "DELETE",
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to delete document: ${response.statusText}`);
  }
}

// Public Chat API
export async function publicChat(
  request: PublicChatRequest
): Promise<PublicChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/public/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("Invalid API key");
    } else if (response.status === 429) {
      throw new Error("Rate limit exceeded");
    }
    throw new Error(`Chat request failed: ${response.statusText}`);
  }

  return response.json();
}

// Health Check
export async function getHealthStatus(): Promise<HealthStatus> {
  const response = await fetch(`${API_BASE_URL}/health`);

  if (!response.ok) {
    throw new Error(`Failed to fetch health status: ${response.statusText}`);
  }

  return response.json();
}

// System Info
export async function getSystemInfo(): Promise<SystemInfo> {
  const response = await fetch(`${API_BASE_URL}/api/system-info`);

  if (!response.ok) {
    throw new Error(`Failed to fetch system info: ${response.statusText}`);
  }

  return response.json();
}
