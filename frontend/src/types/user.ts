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
  can_manage_warehouses: boolean;
  can_manage_products: boolean;
  can_manage_orders: boolean;
  can_view_reports: boolean;
  has_warehouse_access: boolean;
  warehouses: Record<string, WarehousePermission>;
  total_grants: number;
}

export interface WarehousePermission {
  warehouse_id: string;
  warehouse_name: string;
  item_group_id: string;
  permissions: {
    read: boolean;
    write: boolean;
    admin: boolean;
  };
  source: 'direct_warehouse' | 'inherited_from_item_group' | 'system_admin';
  permission_level?: string;
}

export interface PermissionGrant {
  permission_id: string;
  resource_type: 'item_group' | 'warehouse' | 'system';
  resource_id: string;
  permission_level: 'read' | 'write' | 'admin' | 'owner';
  granted_by: string;
  granted_by_name: string;
  granted_at: string;
  expires_at?: string;
  is_active: boolean;
}

export interface ItemGroupPermission {
  item_group_id: string;
  item_group_name: string;
  permission_level: string;
  granted_at: string;
  expires_at?: string;
}

export interface UserPermissionSummary {
  user_id: string;
  user_email: string;
  user_name: string;
  is_system_admin: boolean;
  item_groups: Record<string, ItemGroupPermission>;
  warehouses: Record<string, WarehousePermission>;
}

export interface UserWithPermissions extends User {
  permissions: UserPermissions;
  permission_grants: PermissionGrant[];
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