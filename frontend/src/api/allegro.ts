import axios from 'axios';
import {
  AllegroAutomationSettings,
  AllegroHealthStatus,
  AllegroOrder,
  AllegroOrderFilters,
  AllegroSyncLog,
  AllegroSyncStats,
  AllegroToken,
  CreateTokenPayload,
  SyncLogsFilters,
  TriggerSyncPayload,
  UpdateTokenPayload,
} from '../types/allegro';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

const allegroClient = axios.create({
  baseURL: `${API_BASE_URL}/api/allegro`,
  withCredentials: true,
});

allegroClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const fetchTokens = async (): Promise<AllegroToken[]> => {
  const response = await allegroClient.get<AllegroToken[]>('/tokens');
  return response.data;
};

export const createToken = async (payload: CreateTokenPayload): Promise<AllegroToken> => {
  const response = await allegroClient.post<AllegroToken>('/tokens', payload);
  return response.data;
};

export const updateToken = async (
  tokenId: string,
  payload: UpdateTokenPayload,
): Promise<AllegroToken> => {
  const response = await allegroClient.patch<AllegroToken>(`/tokens/${tokenId}`, payload);
  return response.data;
};

export const deleteToken = async (tokenId: string): Promise<void> => {
  await allegroClient.delete(`/tokens/${tokenId}`);
};

export const refreshToken = async (tokenId: string): Promise<AllegroToken> => {
  const response = await allegroClient.post<AllegroToken>(`/tokens/${tokenId}/refresh`);
  return response.data;
};

export const toggleTokenActive = async (
  tokenId: string,
  isActive: boolean,
): Promise<AllegroToken> => {
  const response = await allegroClient.post<AllegroToken>(`/tokens/${tokenId}/${isActive ? 'activate' : 'deactivate'}`);
  return response.data;
};

export const fetchSyncStats = async (): Promise<AllegroSyncStats> => {
  const response = await allegroClient.get<AllegroSyncStats>('/stats');
  return response.data;
};

export const triggerManualSync = async (payload: TriggerSyncPayload = {}): Promise<{ queued: boolean; job_id?: string }> => {
  const response = await allegroClient.post<{ queued: boolean; job_id?: string }>('/sync', payload);
  return response.data;
};

export const fetchOrders = async (filters: AllegroOrderFilters = {}): Promise<AllegroOrder[]> => {
  const response = await allegroClient.get<AllegroOrder[]>('/orders', { params: filters });
  return response.data;
};

export const fetchOrder = async (orderId: string): Promise<AllegroOrder> => {
  const response = await allegroClient.get<AllegroOrder>(`/orders/${orderId}`);
  return response.data;
};

export const fetchSyncLogs = async (filters: SyncLogsFilters = {}): Promise<AllegroSyncLog[]> => {
  const params = { ...filters };
  if (params.status === 'all') {
    delete params.status;
  }
  if (params.event_type === 'all') {
    delete params.event_type;
  }
  const response = await allegroClient.get<AllegroSyncLog[]>('/logs', { params });
  return response.data;
};

export const fetchAutomationSettings = async (): Promise<AllegroAutomationSettings> => {
  const response = await allegroClient.get<AllegroAutomationSettings>('/automation-settings');
  return response.data;
};

export const updateAutomationSettings = async (
  payload: AllegroAutomationSettings,
): Promise<AllegroAutomationSettings> => {
  const response = await allegroClient.put<AllegroAutomationSettings>('/automation-settings', payload);
  return response.data;
};

export const fetchHealthStatus = async (): Promise<AllegroHealthStatus> => {
  const response = await allegroClient.get<AllegroHealthStatus>('/health');
  return response.data;
};
