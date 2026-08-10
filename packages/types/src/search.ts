/** Mirrors apps/backend's search endpoint
 * (app/presentation/api/v1/schemas.py's SearchRequest/SearchResponse/SearchResultResponse). */
export type RetrievalMethod = "metadata" | "semantic" | "both";

export interface SearchRequest {
  query: string;
}

export interface SearchResult {
  file_id: string;
  name: string;
  path: string;
  mime_type: string | null;
  score: number;
  retrieval_method: RetrievalMethod;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
}
