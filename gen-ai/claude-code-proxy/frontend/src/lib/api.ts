const API_URL = import.meta.env.VITE_BACKEND_API_URL || 'http://localhost:8000';

class ApiClient {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('token', token);
    }
  }

  getToken(): string | null {
    if (!this.token && typeof window !== 'undefined') {
      this.token = localStorage.getItem('token');
    }
    return this.token;
  }

  clearToken() {
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token');
    }
  }

  private async fetch<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(`${API_URL}${path}`, { ...options, headers });

    if (res.status === 401) {
      // Force re-auth when the token is invalid or expired.
      this.clearToken();
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
      throw new Error('Unauthorized');
    }

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw { status: res.status, detail: body.detail };
    }

    if (res.status === 204) return {} as T;
    return res.json();
  }

  async login(username: string, password: string): Promise<{ access_token: string }> {
    const credentials = btoa(`${username}:${password}`);
    const res = await fetch(`${API_URL}/admin/auth/login`, {
      method: 'POST',
      headers: { Authorization: `Basic ${credentials}` },
    });
    if (!res.ok) throw new Error('Login failed');
    const data = await res.json();
    this.setToken(data.access_token);
    return data;
  }

  // Users
  getUsers = () => this.fetch<User[]>('/admin/users');
  getUser = (id: string) => this.fetch<User>(`/admin/users/${id}`);
  createUser = (data: { name: string; description?: string; monthly_budget_usd?: string | number | null }) =>
    this.fetch<User>('/admin/users', { method: 'POST', body: JSON.stringify(data) });
  deactivateUser = (id: string) =>
    this.fetch<User>(`/admin/users/${id}/deactivate`, { method: 'POST' });
  deleteUser = (id: string) =>
    this.fetch<void>(`/admin/users/${id}`, { method: 'DELETE' });
  getUserBudget = (id: string) =>
    this.fetch<UserBudgetStatus>(`/admin/users/${id}/budget`);
  updateUserBudget = (id: string, monthly_budget_usd: string | number | null) =>
    this.fetch<UserBudgetStatus>(`/admin/users/${id}/budget`, {
      method: 'PUT',
      body: JSON.stringify({ monthly_budget_usd }),
    });
  updateUserRoutingStrategy = (id: string, routing_strategy: 'plan_first' | 'bedrock_only') =>
    this.fetch<User>(`/admin/users/${id}/routing-strategy`, {
      method: 'PUT',
      body: JSON.stringify({ routing_strategy }),
    });

  // Access Keys
  getAccessKeys = (userId: string) =>
    this.fetch<AccessKey[]>(`/admin/users/${userId}/access-keys`);
  createAccessKey = (
    userId: string,
    data: { bedrock_region?: string; bedrock_model?: string } = {}
  ) =>
    this.fetch<AccessKey>(`/admin/users/${userId}/access-keys`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  revokeAccessKey = (keyId: string) =>
    this.fetch<void>(`/admin/access-keys/${keyId}`, { method: 'DELETE' });
  rotateAccessKey = (keyId: string) =>
    this.fetch<AccessKey>(`/admin/access-keys/${keyId}/rotate`, { method: 'POST' });
  registerBedrockKey = (keyId: string, bedrockApiKey: string) =>
    this.fetch<{ status: string }>(`/admin/access-keys/${keyId}/bedrock-key`, {
      method: 'POST',
      body: JSON.stringify({ bedrock_api_key: bedrockApiKey }),
    });

  // Usage
  getUsage = (params: UsageParams) => {
    const query = new URLSearchParams();
    if (params.user_id) query.set('user_id', params.user_id);
    if (params.team_id) query.set('team_id', params.team_id);
    if (params.access_key_id) query.set('access_key_id', params.access_key_id);
    if (params.bucket_type) query.set('bucket_type', params.bucket_type);
    if (params.provider) query.set('provider', params.provider);
    if (params.period) query.set('period', params.period);
    if (params.start_date) query.set('start_date', params.start_date);
    if (params.end_date) query.set('end_date', params.end_date);
    return this.fetch<UsageResponse>(`/admin/usage?${query}`);
  };

  getTopUsers = (params: TopUsersParams) => {
    const query = new URLSearchParams();
    if (params.bucket_type) query.set('bucket_type', params.bucket_type);
    if (params.provider) query.set('provider', params.provider);
    if (params.start_time) query.set('start_time', params.start_time);
    if (params.end_time) query.set('end_time', params.end_time);
    if (params.limit) query.set('limit', String(params.limit));
    return this.fetch<UsageTopUser[]>(`/admin/usage/top-users?${query}`);
  };

  getTopUserSeries = (params: TopUsersParams) => {
    const query = new URLSearchParams();
    if (params.bucket_type) query.set('bucket_type', params.bucket_type);
    if (params.provider) query.set('provider', params.provider);
    if (params.start_time) query.set('start_time', params.start_time);
    if (params.end_time) query.set('end_time', params.end_time);
    if (params.limit) query.set('limit', String(params.limit));
    return this.fetch<UsageTopUserSeries[]>(`/admin/usage/top-users/series?${query}`);
  };

  // Pricing
  getModelPricing = (region: string = 'ap-northeast-2') => {
    const query = new URLSearchParams();
    query.set('region', region);
    return this.fetch<PricingListResponse>(`/api/pricing/models?${query}`);
  };

  reloadPricing = () =>
    this.fetch<void>('/api/pricing/reload', { method: 'POST' });
}

export const api = new ApiClient();

export interface User {
  id: string;
  name: string;
  description: string | null;
  status: string;
  routing_strategy: 'plan_first' | 'bedrock_only';
  monthly_budget_usd?: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserBudgetStatus {
  user_id: string;
  monthly_budget_usd: string | null;
  current_usage_usd: string;
  remaining_usd: string | null;
  usage_percentage: number | null;
  period_start: string;
  period_end: string;
}

export interface AccessKey {
  id: string;
  key_prefix: string;
  status: string;
  bedrock_region: string;
  bedrock_model: string;
  created_at: string;
  raw_key?: string;
  has_bedrock_key?: boolean;
}

export interface UsageParams {
  user_id?: string;
  team_id?: string;
  access_key_id?: string;
  bucket_type?: string;
  provider?: 'plan' | 'bedrock';
  period?: 'day' | 'week' | 'month';
  start_date?: string;
  end_date?: string;
}

export interface TopUsersParams {
  bucket_type?: string;
  provider?: 'plan' | 'bedrock';
  start_time?: string;
  end_time?: string;
  limit?: number;
}

export interface UsageBucket {
  bucket_start: string;
  requests: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cache_write_tokens: number;
  cache_read_tokens: number;
  input_cost_usd: string;
  output_cost_usd: string;
  cache_write_cost_usd: string;
  cache_read_cost_usd: string;
  estimated_cost_usd: string;
}

export interface UsageResponse {
  buckets: UsageBucket[];
  total_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_cache_write_tokens: number;
  total_cache_read_tokens: number;
  total_input_cost_usd: string;
  total_output_cost_usd: string;
  total_cache_write_cost_usd: string;
  total_cache_read_cost_usd: string;
  estimated_cost_usd: string;
  cost_breakdown: CostBreakdownByModel[];
}

export interface UsageTopUser {
  user_id: string;
  name: string;
  total_tokens: number;
  total_requests: number;
}

export interface UsageTopUserSeriesBucket {
  bucket_start: string;
  total_tokens: number;
}

export interface UsageTopUserSeries {
  user_id: string;
  name: string;
  buckets: UsageTopUserSeriesBucket[];
}

// Pricing types
export interface ModelPricing {
  model_id: string;
  region: string;
  input_price: string;
  output_price: string;
  cache_write_price: string;
  cache_read_price: string;
  effective_date: string;
}

export interface PricingListResponse {
  models: ModelPricing[];
  region: string;
}

export interface CostBreakdownByModel {
  model_id: string;
  total_cost_usd: string;
  input_cost_usd: string;
  output_cost_usd: string;
  cache_write_cost_usd: string;
  cache_read_cost_usd: string;
}
