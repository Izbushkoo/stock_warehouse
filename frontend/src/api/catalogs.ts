import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

const client = axios.create({
  baseURL: `${API_BASE_URL}/api/catalogs`,
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

export interface Catalog {
  item_group_id: string;
  item_group_code: string;
  item_group_name: string;
  item_group_description?: string;
  is_active: boolean;
  created_at: string;
  created_by: string;
  warehouses_count: number;
}

export interface CreateCatalogRequest {
  code: string;
  name: string;
  description?: string;
}

export interface UpdateCatalogRequest {
  name?: string;
  description?: string;
  is_active?: boolean;
}

export const getCatalogs = async (): Promise<Catalog[]> => {
  try {
    const response = await client.get('/');
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

export const createCatalog = async (data: CreateCatalogRequest): Promise<Catalog> => {
  try {
    const response = await client.post('/', data);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ?? 'Не удалось создать каталог.'
      );
    }
    throw error;
  }
};

export const getCatalog = async (catalogId: string) => {
  try {
    const response = await client.get(`/${catalogId}`);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ?? 'Не удалось получить каталог.'
      );
    }
    throw error;
  }
};

export const updateCatalog = async (catalogId: string, data: UpdateCatalogRequest) => {
  try {
    const response = await client.put(`/${catalogId}`, data);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ?? 'Не удалось обновить каталог.'
      );
    }
    throw error;
  }
};

export const deleteCatalog = async (catalogId: string) => {
  try {
    const response = await client.delete(`/${catalogId}`);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ?? 'Не удалось удалить каталог.'
      );
    }
    throw error;
  }
};

export const createWarehouseInCatalog = async (
  catalogId: string,
  warehouseCode: string,
  warehouseName: string,
  warehouseAddress?: string
) => {
  try {
    const response = await client.post(`/${catalogId}/warehouses`, {
      warehouse_code: warehouseCode,
      warehouse_name: warehouseName,
      warehouse_address: warehouseAddress
    });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ?? 'Не удалось создать склад.'
      );
    }
    throw error;
  }
};