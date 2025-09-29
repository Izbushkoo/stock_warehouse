import axios from 'axios';
import type { UserPermissionSummary } from '../types/user';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

const client = axios.create({
  baseURL: `${API_BASE_URL}/api/permissions`,
  withCredentials: true
});

// Добавляем токен к каждому запросу
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const getUserPermissions = async (userId: string): Promise<UserPermissionSummary> => {
  try {
    const response = await client.get(`/user/${userId}`);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ?? 'Не удалось получить разрешения пользователя.'
      );
    }
    throw error;
  }
};

export const grantPermission = async (
  userId: string,
  resourceType: string,
  resourceId: string,
  permissionLevel: string,
  expiresAt?: string
) => {
  try {
    const response = await client.post('/grant', {
      user_id: userId,
      resource_type: resourceType,
      resource_id: resourceId,
      permission_level: permissionLevel,
      expires_at: expiresAt
    });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ?? 'Не удалось выдать разрешение.'
      );
    }
    throw error;
  }
};

export const revokePermission = async (
  userId: string,
  resourceType: string,
  resourceId: string
) => {
  try {
    const response = await client.post('/revoke', {
      user_id: userId,
      resource_type: resourceType,
      resource_id: resourceId
    });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ?? 'Не удалось отозвать разрешение.'
      );
    }
    throw error;
  }
};

export const getAccessibleItemGroups = async () => {
  try {
    const response = await client.get('/item-groups');
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ?? 'Не удалось получить список каталогов.'
      );
    }
    throw error;
  }
};

export const getAccessibleWarehouses = async (itemGroupId?: string) => {
  try {
    const params = itemGroupId ? { item_group_id: itemGroupId } : {};
    const response = await client.get('/warehouses', { params });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ?? 'Не удалось получить список складов.'
      );
    }
    throw error;
  }
};

export const getWritableWarehouses = async (itemGroupId?: string) => {
  try {
    const params = itemGroupId ? { item_group_id: itemGroupId } : {};
    const response = await client.get('/warehouses/writable', { params });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ?? 'Не удалось получить список складов для записи.'
      );
    }
    throw error;
  }
};