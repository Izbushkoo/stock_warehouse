import axios from 'axios';
import type { User, AuthenticatedUser, LoginRequest, TokenResponse, UserPermissions } from '../types/user';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

const client = axios.create({
  baseURL: `${API_BASE_URL}/auth`,
  withCredentials: true
});

const userManagementClient = axios.create({
  baseURL: `${API_BASE_URL}/api/users`,
  withCredentials: true
});

// Добавляем токен к каждому запросу
const addAuthToken = (config: any) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
};

client.interceptors.request.use(addAuthToken);
userManagementClient.interceptors.request.use(addAuthToken);

export interface RegisterPayload {
  email: string;
  password: string;
  display_name: string;
}

export const login = async (payload: LoginRequest): Promise<TokenResponse> => {
  try {
    const response = await client.post('/login', payload);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ?? 'Неверный email или пароль.'
      );
    }
    throw error;
  }
};

export const getCurrentUser = async (): Promise<AuthenticatedUser> => {
  try {
    const response = await client.get('/me/permissions');
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ?? 'Не удалось получить данные пользователя.'
      );
    }
    throw error;
  }
};

export const logout = async (): Promise<void> => {
  try {
    await client.post('/logout');
  } catch (error) {
    // Игнорируем ошибки при выходе
    console.warn('Logout error:', error);
  }
};

export const register = async (payload: RegisterPayload): Promise<User> => {
  try {
    const response = await client.post('/register', payload);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ?? 'Не удалось создать пользователя.'
      );
    }
    throw error;
  }
};

export const getUsers = async (): Promise<User[]> => {
  try {
    const response = await client.get('/users');
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ?? 'Не удалось получить список пользователей.'
      );
    }
    throw error;
  }
};

export const updateUserStatus = async (userId: string, isActive: boolean): Promise<User> => {
  try {
    const response = await userManagementClient.patch(`/${userId}/status`, { is_active: isActive });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ?? 'Не удалось обновить статус пользователя.'
      );
    }
    throw error;
  }
};

export const updateUserPermissions = async (userId: string, permissions: Partial<UserPermissions>): Promise<User> => {
  try {
    const response = await userManagementClient.patch(`/${userId}/permissions`, { permissions });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ?? 'Не удалось обновить разрешения пользователя.'
      );
    }
    throw error;
  }
};

export const deleteUser = async (userId: string): Promise<void> => {
  try {
    await userManagementClient.delete(`/${userId}`);
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ?? 'Не удалось удалить пользователя.'
      );
    }
    throw error;
  }
};

export const updateUser = async (userId: string, userData: Partial<User>): Promise<User> => {
  try {
    const response = await userManagementClient.patch(`/${userId}`, userData);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ?? 'Не удалось обновить данные пользователя.'
      );
    }
    throw error;
  }
};
