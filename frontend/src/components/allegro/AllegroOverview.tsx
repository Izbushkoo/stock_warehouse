import { formatDistanceToNow } from 'date-fns';
import { ru } from 'date-fns/locale';
import {
  AllegroHealthStatus,
  AllegroSyncStats,
  AllegroToken,
  TriggerSyncPayload,
} from '../../types/allegro';
import styles from './AllegroOverview.module.css';

interface AllegroOverviewProps {
  tokens: AllegroToken[];
  stats?: AllegroSyncStats;
  health?: AllegroHealthStatus;
  syncing: boolean;
  onManualSync: (payload?: TriggerSyncPayload) => Promise<void>;
}

const statusClass = (status: 'ok' | 'degraded' | 'down') => {
  switch (status) {
    case 'ok':
      return `${styles.statusBadge} ${styles.statusOk}`;
    case 'degraded':
      return `${styles.statusBadge} ${styles.statusDegraded}`;
    case 'down':
    default:
      return `${styles.statusBadge} ${styles.statusDown}`;
  }
};

const AllegroOverview = ({ tokens, stats, health, syncing, onManualSync }: AllegroOverviewProps) => {
  const activeTokens = tokens.filter((token) => token.status === 'active').length;
  const defaultToken = tokens.find((token) => token.is_default);

  const handleManualSync = async () => {
    await onManualSync();
  };

  return (
    <div className={styles.container}>
      <div className={styles.summaryCards}>
        <div className={styles.card}>
          <span className={styles.cardTitle}>Активные токены</span>
          <span className={styles.cardValue}>{activeTokens}</span>
          <span className={styles.cardSubtitle}>
            {tokens.length > 0
              ? `Всего подключено ${tokens.length} аккаунтов`
              : 'Нет подключенных аккаунтов Allegro'}
          </span>
        </div>

        <div className={styles.card}>
          <span className={styles.cardTitle}>Заказы сегодня</span>
          <span className={styles.cardValue}>{stats?.orders_synced_today ?? 0}</span>
          <span className={styles.cardSubtitle}>
            {stats?.last_sync_at
              ? `Последняя синхронизация ${formatDistanceToNow(new Date(stats.last_sync_at), {
                  addSuffix: true,
                  locale: ru,
                })}`
              : 'Синхронизаций еще не было'}
          </span>
        </div>

        <div className={styles.card}>
          <span className={styles.cardTitle}>Заказы в обработке</span>
          <span className={styles.cardValue}>{stats?.orders_pending ?? 0}</span>
          <span className={styles.cardSubtitle}>Нужно подтвердить или отправить</span>
        </div>

        <div className={styles.card}>
          <span className={styles.cardTitle}>Неудачные синхронизации</span>
          <span className={styles.cardValue}>{stats?.failed_syncs_today ?? 0}</span>
          <span className={styles.cardSubtitle}>Ошибки за последние 24 часа</span>
        </div>
      </div>

      <div className={styles.syncPanel}>
        <div className={styles.syncCard}>
          <div className={styles.syncHeader}>
            <span className={styles.syncTitle}>Ручная синхронизация</span>
            <button
              className={styles.syncButton}
              onClick={handleManualSync}
              disabled={syncing || tokens.length === 0}
            >
              {syncing ? 'Синхронизация…' : 'Запустить' }
            </button>
          </div>
          <p>
            Запускает немедленный импорт заказов из Allegro orders backup для всех активных токенов.
            Используйте при возникновении расхождений или перед закрытием дня.
          </p>
          {defaultToken && (
            <p>
              Токен по умолчанию: <strong>{defaultToken.account_name}</strong>
            </p>
          )}
        </div>

        <div className={`${styles.syncCard}`}>
          <div className={styles.syncHeader}>
            <span className={styles.syncTitle}>Статус систем</span>
          </div>
          <div className={styles.healthList}>
            {(health?.services ?? []).length > 0 ? (
              health?.services?.map((service) => (
                <div key={service.service} className={styles.healthItem}>
                  <div className={styles.healthInfo}>
                    <span className={styles.healthTitle}>{service.service}</span>
                    <span className={styles.healthTimestamp}>
                      Проверено {formatDistanceToNow(new Date(service.last_check_at), {
                        addSuffix: true,
                        locale: ru,
                      })}
                    </span>
                  </div>
                  <span className={statusClass(service.status)}>
                    {service.status === 'ok'
                      ? 'В норме'
                      : service.status === 'degraded'
                        ? 'Замедление'
                        : 'Не работает'}
                  </span>
                </div>
              ))
            ) : (
              <div className={styles.healthItem}>
                <span className={styles.healthTitle}>Нет данных о статусе системы</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AllegroOverview;
