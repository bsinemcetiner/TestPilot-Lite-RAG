const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

export type DocumentRecord = {
  id: number;
  name: string;
  format: string;
  source_type?: string;
  created_at: string;
  chunk_count?: number;
};

export type DocumentUploadPayload = {
  name: string;
  content: string;
  format: string;
  source_type?: string;
};

export async function getHealth() {
  const response = await fetch(`${API_BASE}/health`);
  return response.json();
}

export async function getDocuments(): Promise<DocumentRecord[]> {
  const response = await fetch(`${API_BASE}/documents`);
  if (!response.ok) {
    throw new Error("Failed to load documents");
  }
  return response.json();
}

export async function getChunkCount(docId: number): Promise<number> {
  const response = await fetch(`${API_BASE}/documents/${docId}/chunks-count`);
  if (!response.ok) {
    throw new Error("Failed to get chunk count");
  }
  const data = await response.json();
  return data.chunk_count;
}

export async function uploadDocumentText(
  payload: DocumentUploadPayload,
): Promise<DocumentRecord> {
  const response = await fetch(`${API_BASE}/documents/upload-text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to upload document");
  }

  return response.json();
}

export async function uploadDocumentFile(
  name: string,
  format: string,
  source_type: string,
  file: File,
): Promise<DocumentRecord> {
  const formData = new FormData();
  formData.append("name", name);
  formData.append("format", format);
  if (source_type) {
    formData.append("source_type", source_type);
  }
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/documents/upload-file`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to upload file");
  }

  return response.json();
}

export type SourceReference = {
  document_name: string;
  chunk_id: string;
  quote?: string;
};

export type TestCase = {
  id: number;
  title: string;
  type: string;
  priority: string;
  preconditions: string[];
  steps: string[];
  expected_result: string;
  source_references: SourceReference[];
};

export type GenerationResponse = {
  test_cases: TestCase[];
  count: number;
  feature: string;
  retrieved_chunks: number;
  provider: string;
  formatted: string;
  id?: string;
  evaluation?: {
    total_cases: number;
    coverage_score: number;
    completeness_score: number;
    groundedness_score: number;
    type_distribution: Record<string, number>;
    issues_found: number;
    issues: string[];
    recommendation: string;
    requirement_coverage_details?: {
      requirement: string;
      covered: boolean;
      match_score: number;
      matched_test_case: string | null;
    }[];
  };
};

export type BackendHistoryItem = {
  id: string;
  feature: string;
  query: string;
  provider: string;
  output_format: string;
  requested_count: number;
  retrieved_chunks_count: number;
  is_pinned: boolean;
  evaluation_metrics: any;
  formatted_output: string;
  created_at: string;
};

export async function getHistory(): Promise<BackendHistoryItem[]> {
  const response = await fetch(`${API_BASE}/history`);
  if (!response.ok) throw new Error("Failed to load history");
  return response.json();
}

export async function getHistoryDetail(id: string): Promise<any> {
  const response = await fetch(`${API_BASE}/history/${id}`);
  if (!response.ok) throw new Error("Failed to load history detail");
  return response.json();
}

export async function deleteHistory(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/history/${id}`, { method: "DELETE" });
  if (!response.ok) throw new Error("Failed to delete history");
}

export async function togglePinHistory(id: string): Promise<{ is_pinned: boolean }> {
  const response = await fetch(`${API_BASE}/history/${id}/pin`, { method: "PATCH" });
  if (!response.ok) throw new Error("Failed to toggle pin");
  return response.json();
}

export async function getProviders(): Promise<string[]> {
  const response = await fetch(`${API_BASE}/providers`);
  if (!response.ok) {
    throw new Error("Failed to load provider list");
  }

  const data = await response.json();
  return data.available_providers ?? ["mock"];
}

export async function generateTestCases(
  featureName: string,
  query: string,
  testTypes: string[],
  numCases: number,
  outputFormat: string = "json",
  provider: string = "mock",
): Promise<GenerationResponse> {
  const response = await fetch(`${API_BASE}/generate-tests`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      feature_name: featureName,
      query,
      test_types: testTypes,
      num_cases: numCases,
      output_format: outputFormat,
      provider,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to generate test cases");
  }

  return response.json();
}
