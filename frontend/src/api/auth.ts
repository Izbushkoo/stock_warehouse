import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

const client = axios.create({
  baseURL: `${API_BASE_URL}/auth`,
  withCredentials: true
});

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
}

export const login = async (payload: LoginPayload) => {
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

export const register = async (payload: RegisterPayload) => {
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
