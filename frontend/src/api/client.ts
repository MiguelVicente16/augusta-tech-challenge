import type { Incentive, Company, Match, ChatMessage } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  // Incentives
  async getIncentives(params?: {
    skip?: number;
    limit?: number;
    search?: string;
  }): Promise<Incentive[]> {
    const queryParams = new URLSearchParams();
    if (params?.skip) queryParams.append("skip", params.skip.toString());
    if (params?.limit) queryParams.append("limit", params.limit.toString());
    if (params?.search) queryParams.append("search", params.search);

    return this.request<Incentive[]>(`/api/v1/incentives?${queryParams}`);
  }

  async getIncentive(id: number): Promise<Incentive> {
    return this.request<Incentive>(`/api/v1/incentives/${id}`);
  }

  async countIncentives(): Promise<{ count: number }> {
    return this.request<{ count: number }>(`/api/v1/incentives/count`);
  }

  // Companies
  async getCompanies(params?: {
    skip?: number;
    limit?: number;
    search?: string;
  }): Promise<Company[]> {
    const queryParams = new URLSearchParams();
    if (params?.skip) queryParams.append("skip", params.skip.toString());
    if (params?.limit) queryParams.append("limit", params.limit.toString());
    if (params?.search) queryParams.append("search", params.search);

    return this.request<Company[]>(`/api/v1/companies?${queryParams}`);
  }

  async getCompany(id: number): Promise<Company> {
    return this.request<Company>(`/api/v1/companies/${id}`);
  }

  // Matches
  async getMatches(params?: {
    incentive_id?: number;
    company_id?: number;
    skip?: number;
    limit?: number;
  }): Promise<Match[]> {
    const queryParams = new URLSearchParams();
    if (params?.incentive_id) queryParams.append("incentive_id", params.incentive_id.toString());
    if (params?.company_id) queryParams.append("company_id", params.company_id.toString());
    if (params?.skip) queryParams.append("skip", params.skip.toString());
    if (params?.limit) queryParams.append("limit", params.limit.toString());

    return this.request<Match[]>(`/api/v1/matches?${queryParams}`);
  }

  async getTopMatchesForIncentive(incentiveId: number): Promise<Match[]> {
    return this.request<Match[]>(`/api/v1/matches/incentive/${incentiveId}/top`);
  }

  // Matching
  async runBatchMatching(params?: {
    force_refresh?: boolean;
    max_total_cost?: number;
  }): Promise<{
    total_incentives: number;
    successful_matches: number;
    failed_matches: number;
    total_cost: number;
    matches_per_incentive: Record<string, number>;
  }> {
    return this.request(`/api/v1/matching/batch`, {
      method: "POST",
      body: JSON.stringify({
        force_refresh: params?.force_refresh || false,
        max_total_cost: params?.max_total_cost || null,
      }),
    });
  }

  async runBatchMatchingStream(
    params: {
      force_refresh?: boolean;
      max_total_cost?: number;
    },
    onProgress: (data: any) => void
  ): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/v1/matching/batch-stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        force_refresh: params?.force_refresh || false,
        max_total_cost: params?.max_total_cost || null,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error("Response body is null");
    }

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split("\n").filter((line) => line.trim());

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const jsonData = line.slice(6);
          try {
            const data = JSON.parse(jsonData);
            onProgress(data);
          } catch (e) {
            console.error("Failed to parse SSE data:", e);
          }
        } else if (line.trim()) {
          // Handle non-SSE formatted JSON
          try {
            const data = JSON.parse(line);
            onProgress(data);
          } catch (e) {
            console.error("Failed to parse progress data:", e);
          }
        }
      }
    }
  }

  async runMatchingForIncentive(params: {
    incentive_id: number;
    max_cost?: number;
  }): Promise<{
    incentive_id: number;
    matches: Array<{
      company_id: number;
      company_name: string;
      score: number;
      rank: number;
      reasoning: Record<string, any>;
    }>;
    total_cost: number;
    processing_time: number;
  }> {
    return this.request(`/api/v1/matching/run`, {
      method: "POST",
      body: JSON.stringify({
        incentive_id: params.incentive_id,
        max_cost: params.max_cost || 0.30,
      }),
    });
  }

  async exportMatchesToCSV(): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/api/v1/matching/export`, {
      method: "GET",
      headers: {
        "Accept": "text/csv",
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }

    return response.blob();
  }

  // Chatbot
  async sendMessage(message: string, history: ChatMessage[]): Promise<ReadableStream<Uint8Array>> {
    const response = await fetch(`${this.baseUrl}/api/v1/chatbot/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        conversation_history: history,
        stream: true
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }

    if (!response.body) {
      throw new Error("Response body is null");
    }

    return response.body;
  }
}

export const apiClient = new ApiClient();
