export interface User {
  user_id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  last_login_at?: string;
  created_at: string;
}

export interface UserPermissions {
  is_admin: boolean;
  can_manage_users: boolean;
  has_warehouse_access: boolean;
  warehouses: Record<string, any>;
}

export interface AuthenticatedUser extends User {
  permissions: UserPermissions;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user_id: string;
}