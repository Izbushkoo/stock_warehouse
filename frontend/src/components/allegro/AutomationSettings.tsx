import { useEffect, useState } from 'react';
import {
  AllegroAutomationSettings,
  AllegroOrderStatus,
} from '../../types/allegro';
import styles from './AutomationSettings.module.css';

interface AutomationSettingsProps {
  initialSettings?: AllegroAutomationSettings;
  onSave: (settings: AllegroAutomationSettings) => Promise<void>;
}

const ALL_STATUSES: AllegroOrderStatus[] = ['new', 'processing', 'ready_for_shipment', 'shipped', 'cancelled', 'returned'];

const statusLabel = (status: AllegroOrderStatus) => {
  switch (status) {
    case 'new':
      return 'Новые';
    case 'processing':
      return 'В обработке';
    case 'ready_for_shipment':
      return 'Готовы к отгрузке';
    case 'shipped':
      return 'Отгружены';
    case 'cancelled':
      return 'Отмененные';
    case 'returned':
      return 'Возвраты';
    default:
      return status;
  }
};

const AutomationSettings = ({ initialSettings, onSave }: AutomationSettingsProps) => {
  const [settings, setSettings] = useState<AllegroAutomationSettings>(
    initialSettings ?? {
      auto_sync_enabled: true,
      sync_interval_minutes: 30,
      order_states_to_import: ['new', 'processing', 'ready_for_shipment'],
      notify_on_failures: true,
      notify_emails: [],
    },
  );
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialSettings) {
      setSettings(initialSettings);
    }
  }, [initialSettings]);

  const handleStatusToggle = (status: AllegroOrderStatus) => {
    setSettings((prev) => {
      const exists = prev.order_states_to_import.includes(status);
      return {
        ...prev,
        order_states_to_import: exists
          ? prev.order_states_to_import.filter((s) => s !== status)
          : [...prev.order_states_to_import, status],
      };
    });
  };

  const handleEmailsChange = (value: string) => {
    const emails = value
      .split(',')
      .map((email) => email.trim())
      .filter((email) => email.length > 0);
    setSettings((prev) => ({ ...prev, notify_emails: emails }));
  };

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    try {
      await onSave(settings);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сохранить настройки.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <section className={styles.container}>
      <div>
        <h3 className={styles.title}>Автоматизация синхронизации</h3>
        <p className={styles.description}>
          Настройте расписание и уведомления для фоновой синхронизации Allegro orders backup.
        </p>
      </div>

      <label className={styles.checkboxRow}>
        <input
          type="checkbox"
          checked={settings.auto_sync_enabled}
          onChange={(event) => setSettings((prev) => ({ ...prev, auto_sync_enabled: event.target.checked }))}
        />
        Автоматически запускать синхронизацию каждые {settings.sync_interval_minutes} минут
      </label>

      <div className={styles.field}>
        <span className={styles.label}>Интервал синхронизации (минуты)</span>
        <input
          type="number"
          min={5}
          step={5}
          className={styles.input}
          value={settings.sync_interval_minutes}
          onChange={(event) => setSettings((prev) => ({ ...prev, sync_interval_minutes: Number(event.target.value) }))}
        />
        <span className={styles.helper}>Рекомендуемый интервал — 15–30 минут.</span>
      </div>

      <div className={styles.field}>
        <span className={styles.label}>Состояния заказов для импорта</span>
        <div className={styles.badgeGroup}>
          {ALL_STATUSES.map((status) => (
            <button
              key={status}
              type="button"
              className={styles.badge}
              style={{
                opacity: settings.order_states_to_import.includes(status) ? 1 : 0.4,
              }}
              onClick={() => handleStatusToggle(status)}
            >
              {statusLabel(status)}
            </button>
          ))}
        </div>
      </div>

      <label className={styles.checkboxRow}>
        <input
          type="checkbox"
          checked={settings.notify_on_failures}
          onChange={(event) => setSettings((prev) => ({ ...prev, notify_on_failures: event.target.checked }))}
        />
        Отправлять уведомления при ошибках синхронизации
      </label>

      <div className={styles.field}>
        <span className={styles.label}>Email для уведомлений</span>
        <textarea
          className={styles.textarea}
          placeholder="admin@example.com, support@example.com"
          value={settings.notify_emails.join(', ')}
          onChange={(event) => handleEmailsChange(event.target.value)}
        />
        <span className={styles.helper}>Укажите через запятую несколько адресов.</span>
      </div>

      {error && <div className={styles.helper} style={{ color: '#b91c1c' }}>{error}</div>}

      <div className={styles.actions}>
        <button className={styles.secondaryButton} type="button" onClick={() => initialSettings && setSettings(initialSettings)}>
          Сбросить
        </button>
        <button className={styles.button} type="button" onClick={handleSave} disabled={isSaving}>
          {isSaving ? 'Сохраняем…' : 'Сохранить настройки'}
        </button>
      </div>
    </section>
  );
};

export default AutomationSettings;
