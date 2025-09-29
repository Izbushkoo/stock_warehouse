export type AllegroTokenStatus = 'active' | 'expired' | 'revoked' | 'error' | 'pending';

export interface AllegroToken {
  token_id: string;
  account_name: string;
  marketplace_username?: string;
  client_id: string;
  scopes: string[];
  created_at: string;
  expires_at: string;
  last_sync_at?: string;
  status: AllegroTokenStatus;
  is_default: boolean;
  orders_imported: number;
  last_error?: string | null;
}

export interface AllegroSyncStats {
  total_tokens: number;
  active_tokens: number;
  orders_synced_today: number;
  orders_pending: number;
  last_sync_at?: string;
  backlog_orders: number;
  failed_syncs_today: number;
}

export interface AllegroBuyer {
  name: string;
  email?: string;
  phone?: string;
}

export interface AllegroOrderItem {
  line_item_id: string;
  sku: string;
  name: string;
  quantity: number;
  unit_price: number;
  currency: string;
  vat_rate?: number;
  fulfillment_status?: string;
}

export type AllegroOrderStatus =
  | 'new'
  | 'processing'
  | 'ready_for_shipment'
  | 'shipped'
  | 'cancelled'
  | 'returned';

export interface AllegroOrder {
  order_id: string;
  token_id: string;
  marketplace_order_id: string;
  status: AllegroOrderStatus;
  payment_status: 'paid' | 'pending' | 'refunded' | 'failed';
  fulfillment_status: 'pending' | 'in_progress' | 'fulfilled' | 'cancelled';
  buyer: AllegroBuyer;
  total_amount: number;
  currency: string;
  created_at: string;
  updated_at: string;
  last_synced_at?: string;
  delivery_method?: string;
  shipping_tracking_number?: string;
  items: AllegroOrderItem[];
  tags?: string[];
  notes?: string;
}

export interface AllegroOrderFilters {
  token_id?: string;
  status?: AllegroOrderStatus | 'all';
  payment_status?: AllegroOrder['payment_status'] | 'all';
  fulfillment_status?: AllegroOrder['fulfillment_status'] | 'all';
  created_from?: string;
  created_to?: string;
  search?: string;
  limit?: number;
}

export interface AllegroSyncLog {
  log_id: string;
  token_id?: string;
  token_account_name?: string;
  event_type: 'orders_sync' | 'token_refresh' | 'webhook' | 'maintenance';
  status: 'success' | 'warning' | 'error' | 'info';
  message: string;
  created_at: string;
  duration_ms?: number;
  details?: Record<string, unknown>;
}

export interface AllegroAutomationSettings {
  auto_sync_enabled: boolean;
  sync_interval_minutes: number;
  order_states_to_import: AllegroOrderStatus[];
  notify_on_failures: boolean;
  notify_emails: string[];
}

export interface AllegroHealthStatus {
  overall_status: 'ok' | 'degraded' | 'down';
  services: Array<{
    service: string;
    status: 'ok' | 'degraded' | 'down';
    last_check_at: string;
    message?: string;
  }>;
}

export interface TriggerSyncPayload {
  token_id?: string;
  since?: string;
}

export interface CreateTokenPayload {
  authorization_code: string;
  account_name: string;
  is_default?: boolean;
}

export interface UpdateTokenPayload {
  account_name?: string;
  is_default?: boolean;
}

export interface SyncLogsFilters {
  token_id?: string;
  status?: AllegroSyncLog['status'] | 'all';
  event_type?: AllegroSyncLog['event_type'] | 'all';
  limit?: number;
}
