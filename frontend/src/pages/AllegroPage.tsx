import { useEffect, useMemo, useState } from 'react';
import AllegroOverview from '../components/allegro/AllegroOverview';
import TokenManager from '../components/allegro/TokenManager';
import OrdersPanel from '../components/allegro/OrdersPanel';
import OrderDetailsDrawer from '../components/allegro/OrderDetailsDrawer';
import SyncLogsPanel from '../components/allegro/SyncLogsPanel';
import AutomationSettings from '../components/allegro/AutomationSettings';
import { AllegroService } from '../services/allegro';
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
  UpdateTokenPayload,
} from '../types/allegro';
import styles from './AllegroPage.module.css';


type AllegroTab = 'overview' | 'orders' | 'tokens' | 'logs' | 'automation';

const AllegroPage = () => {
  const [activeTab, setActiveTab] = useState<AllegroTab>('overview');
  const [tokens, setTokens] = useState<AllegroToken[]>([]);
  const [tokensLoading, setTokensLoading] = useState(false);
  const [stats, setStats] = useState<AllegroSyncStats | undefined>(undefined);
  const [health, setHealth] = useState<AllegroHealthStatus | undefined>(undefined);
  const [syncing, setSyncing] = useState(false);
  const [orders, setOrders] = useState<AllegroOrder[]>([]);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [orderFilters, setOrderFilters] = useState<AllegroOrderFilters>({ limit: 50 });
  const [selectedOrder, setSelectedOrder] = useState<AllegroOrder | null>(null);
  const [logs, setLogs] = useState<AllegroSyncLog[]>([]);
  const [logsFilters, setLogsFilters] = useState<SyncLogsFilters>({ limit: 50 });
  const [automationSettings, setAutomationSettings] = useState<AllegroAutomationSettings | undefined>();
  const [automationLoading, setAutomationLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadTokens = async () => {
    setTokensLoading(true);
    try {
      const data = await AllegroService.listTokens();
      setTokens(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить токены Allegro.');
    } finally {
      setTokensLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const data = await AllegroService.getSyncStats();
      setStats(data);
    } catch (err) {
      console.warn('Failed to load Allegro sync stats', err);
    }
  };

  const loadHealth = async () => {
    try {
      const data = await AllegroService.getHealthStatus();
      setHealth(data);
    } catch (err) {
      console.warn('Failed to load Allegro health status', err);
    }
  };

  const loadOrders = async () => {
    setOrdersLoading(true);
    try {
      const data = await AllegroService.listOrders(orderFilters);
      setOrders(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить заказы Allegro.');
    } finally {
      setOrdersLoading(false);
    }
  };

  const loadLogs = async () => {
    try {
      const data = await AllegroService.listSyncLogs(logsFilters);
      setLogs(data);
    } catch (err) {
      console.warn('Failed to load Allegro sync logs', err);
    }
  };

  const loadAutomation = async () => {
    setAutomationLoading(true);
    try {
      const data = await AllegroService.getAutomationSettings();
      setAutomationSettings(data);
    } catch (err) {
      console.warn('Failed to load automation settings', err);
    } finally {
      setAutomationLoading(false);
    }
  };

  useEffect(() => {
    loadTokens();
    loadStats();
    loadHealth();
    loadAutomation();
  }, []);

  useEffect(() => {
    loadOrders();
  }, [orderFilters]);

  useEffect(() => {
    loadLogs();
  }, [logsFilters]);

  const handleManualSync = async () => {
    setSyncing(true);
    setMessage(null);
    try {
      const response = await AllegroService.triggerManualSync();
      setMessage(response.queued ? 'Синхронизация добавлена в очередь.' : 'Синхронизация запущена.');
      await loadStats();
      await loadOrders();
      await loadLogs();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось запустить синхронизацию.');
    } finally {
      setSyncing(false);
    }
  };

  const handleCreateToken = async (payload: CreateTokenPayload) => {
    setTokensLoading(true);
    setError(null);
    setMessage(null);
    try {
      await AllegroService.createToken(payload);
      await loadTokens();
      await loadStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать токен Allegro.');
      throw err;
    } finally {
      setTokensLoading(false);
    }
  };

  const handleUpdateToken = async (tokenId: string, updates: UpdateTokenPayload) => {
    setTokensLoading(true);
    setError(null);
    setMessage(null);
    try {
      await AllegroService.updateToken(tokenId, updates);
      await loadTokens();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось обновить токен Allegro.');
    } finally {
      setTokensLoading(false);
    }
  };

  const handleDeleteToken = async (tokenId: string) => {
    if (!window.confirm('Удалить токен Allegro?')) return;
    setTokensLoading(true);
    setError(null);
    setMessage(null);
    try {
      await AllegroService.deleteToken(tokenId);
      await loadTokens();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось удалить токен Allegro.');
    } finally {
      setTokensLoading(false);
    }
  };

  const handleRefreshToken = async (tokenId: string) => {
    setTokensLoading(true);
    setError(null);
    setMessage(null);
    try {
      await AllegroService.refreshToken(tokenId);
      await loadTokens();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось обновить токен Allegro.');
    } finally {
      setTokensLoading(false);
    }
  };

  const handleToggleToken = async (tokenId: string, isActive: boolean) => {
    setTokensLoading(true);
    setError(null);
    setMessage(null);
    try {
      await AllegroService.toggleTokenActive(tokenId, isActive);
      await loadTokens();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось изменить статус токена Allegro.');
    } finally {
      setTokensLoading(false);
    }
  };

  const handleSaveAutomation = async (settingsToSave: AllegroAutomationSettings) => {
    setMessage(null);
    setError(null);
    try {
      const saved = await AllegroService.updateAutomationSettings(settingsToSave);
      setAutomationSettings(saved);
      setMessage('Настройки автоматизации сохранены.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сохранить настройки автоматизации.');
      throw err;
    }
  };

  const tabs = useMemo(
    () => [
      { id: 'overview' as AllegroTab, label: 'Обзор' },
      { id: 'orders' as AllegroTab, label: 'Заказы' },
      { id: 'tokens' as AllegroTab, label: 'Токены' },
      { id: 'logs' as AllegroTab, label: 'Логи' },
      { id: 'automation' as AllegroTab, label: 'Автоматизация' },
    ],
    [],
  );

  return (
    <div className={styles.container}>
      <div className={styles.pageHeader}>
        <h1 className={styles.title}>Allegro orders backup</h1>
        <p className={styles.subtitle}>
          Консолидированное управление токенами, заказами и синхронизацией Allegro в единой системе склада.
        </p>
      </div>

      <div className={styles.tabs}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`${styles.tabButton} ${activeTab === tab.id ? styles.tabButtonActive : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {message && <div className={styles.alert}>{message}</div>}
      {error && <div className={styles.alert} style={{ background: 'rgba(248, 113, 113, 0.12)', color: '#b91c1c', borderColor: 'rgba(248, 113, 113, 0.35)' }}>{error}</div>}

      {activeTab === 'overview' && (
        <AllegroOverview
          tokens={tokens}
          stats={stats}
          health={health}
          syncing={syncing}
          onManualSync={handleManualSync}
        />
      )}

      {activeTab === 'orders' && (
        <>
          {ordersLoading ? (
            <div className={styles.loading}>Загрузка заказов…</div>
          ) : (
            <OrdersPanel
              orders={orders}
              loading={ordersLoading}
              tokens={tokens}
              filters={orderFilters}
              onFiltersChange={setOrderFilters}
              onRefresh={loadOrders}
              onSelectOrder={setSelectedOrder}
            />
          )}
        </>
      )}

      {activeTab === 'tokens' && (
        <TokenManager
          tokens={tokens}
          loading={tokensLoading}
          onCreate={handleCreateToken}
          onUpdate={handleUpdateToken}
          onDelete={handleDeleteToken}
          onRefresh={handleRefreshToken}
          onToggleActive={handleToggleToken}
        />
      )}

      {activeTab === 'logs' && (
        <SyncLogsPanel logs={logs} tokens={tokens} filters={logsFilters} onFiltersChange={setLogsFilters} />
      )}

      {activeTab === 'automation' && (
        <>
          {automationLoading && !automationSettings ? (
            <div className={styles.loading}>Загрузка настроек…</div>
          ) : (
            <AutomationSettings initialSettings={automationSettings} onSave={handleSaveAutomation} />
          )}
        </>
      )}

      {selectedOrder && (
        <OrderDetailsDrawer order={selectedOrder} onClose={() => setSelectedOrder(null)} />
      )}
    </div>
  );
};

export default AllegroPage;
