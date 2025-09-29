import { formatDistanceToNow } from 'date-fns';
import { ru } from 'date-fns/locale';
import { AllegroSyncLog, AllegroToken, SyncLogsFilters } from '../../types/allegro';
import styles from './SyncLogsPanel.module.css';

interface SyncLogsPanelProps {
  logs: AllegroSyncLog[];
  tokens: AllegroToken[];
  filters: SyncLogsFilters;
  onFiltersChange: (filters: SyncLogsFilters) => void;
}

const statusClass = (status: AllegroSyncLog['status']) => {
  switch (status) {
    case 'success':
      return `${styles.badge} ${styles.success}`;
    case 'warning':
      return `${styles.badge} ${styles.warning}`;
    case 'error':
      return `${styles.badge} ${styles.error}`;
    default:
      return `${styles.badge} ${styles.info}`;
  }
};

const SyncLogsPanel = ({ logs, tokens, filters, onFiltersChange }: SyncLogsPanelProps) => {
  const handleChange = (field: keyof SyncLogsFilters, value: string) => {
    const next = { ...filters };
    if (!value || value === 'all') {
      delete next[field];
    } else {
      next[field] = value as any;
    }
    onFiltersChange(next);
  };

  return (
    <section className={styles.container}>
      <div className={styles.filters}>
        <select
          className={styles.select}
          value={filters.token_id ?? 'all'}
          onChange={(event) => handleChange('token_id', event.target.value)}
        >
          <option value="all">Все токены</option>
          {tokens.map((token) => (
            <option key={token.token_id} value={token.token_id}>
              {token.account_name}
            </option>
          ))}
        </select>

        <select
          className={styles.select}
          value={filters.status ?? 'all'}
          onChange={(event) => handleChange('status', event.target.value)}
        >
          <option value="all">Все статусы</option>
          <option value="success">Успех</option>
          <option value="warning">Предупреждение</option>
          <option value="error">Ошибка</option>
          <option value="info">Инфо</option>
        </select>

        <select
          className={styles.select}
          value={filters.event_type ?? 'all'}
          onChange={(event) => handleChange('event_type', event.target.value)}
        >
          <option value="all">Все события</option>
          <option value="orders_sync">Синхронизация заказов</option>
          <option value="token_refresh">Обновление токена</option>
          <option value="webhook">Webhook</option>
          <option value="maintenance">Сервисные работы</option>
        </select>
      </div>

      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Время</th>
              <th>Токен</th>
              <th>Тип</th>
              <th>Статус</th>
              <th>Сообщение</th>
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 ? (
              <tr>
                <td colSpan={5} className={styles.emptyState}>
                  Записей нет
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.log_id}>
                  <td>{formatDistanceToNow(new Date(log.created_at), { addSuffix: true, locale: ru })}</td>
                  <td>{log.token_account_name ?? '—'}</td>
                  <td>{log.event_type}</td>
                  <td>
                    <span className={statusClass(log.status)}>{log.status}</span>
                  </td>
                  <td>{log.message}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
};

export default SyncLogsPanel;
