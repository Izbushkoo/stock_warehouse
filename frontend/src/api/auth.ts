import axios from 'axios';
import type { User, AuthenticatedUser, LoginRequest, TokenResponse, UserPermissions } from '../types/user';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

const client = axios.create({
  baseURL: `${API_BASE_URL}/auth`,
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
