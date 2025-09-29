import {
  createToken,
  deleteToken,
  fetchAutomationSettings,
  fetchHealthStatus,
  fetchOrder,
  fetchOrders,
  fetchSyncLogs,
  fetchSyncStats,
  fetchTokens,
  refreshToken,
  toggleTokenActive,
  triggerManualSync,
  updateAutomationSettings,
  updateToken,
} from '../api/allegro';
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

export class AllegroService {
  static async listTokens(): Promise<AllegroToken[]> {
    return await fetchTokens();
  }

  static async createToken(payload: CreateTokenPayload): Promise<AllegroToken> {
    return await createToken(payload);
  }

  static async updateToken(tokenId: string, payload: UpdateTokenPayload): Promise<AllegroToken> {
    return await updateToken(tokenId, payload);
  }

  static async deleteToken(tokenId: string): Promise<void> {
    await deleteToken(tokenId);
  }

  static async refreshToken(tokenId: string): Promise<AllegroToken> {
    return await refreshToken(tokenId);
  }

  static async toggleTokenActive(tokenId: string, isActive: boolean): Promise<AllegroToken> {
    return await toggleTokenActive(tokenId, isActive);
  }

  static async getSyncStats(): Promise<AllegroSyncStats> {
    return await fetchSyncStats();
  }

  static async triggerManualSync(payload: TriggerSyncPayload = {}): Promise<{ queued: boolean; job_id?: string }> {
    return await triggerManualSync(payload);
  }

  static async listOrders(filters: AllegroOrderFilters = {}): Promise<AllegroOrder[]> {
    return await fetchOrders(filters);
  }

  static async getOrder(orderId: string): Promise<AllegroOrder> {
    return await fetchOrder(orderId);
  }

  static async listSyncLogs(filters: SyncLogsFilters = {}): Promise<AllegroSyncLog[]> {
    return await fetchSyncLogs(filters);
  }

  static async getAutomationSettings(): Promise<AllegroAutomationSettings> {
    return await fetchAutomationSettings();
  }

  static async updateAutomationSettings(payload: AllegroAutomationSettings): Promise<AllegroAutomationSettings> {
    return await updateAutomationSettings(payload);
  }

  static async getHealthStatus(): Promise<AllegroHealthStatus> {
    return await fetchHealthStatus();
  }
}
