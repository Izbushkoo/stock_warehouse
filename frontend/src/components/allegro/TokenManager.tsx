import { useMemo, useState, type FormEvent } from 'react';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';
import {
  AllegroToken,
  CreateTokenPayload,
  UpdateTokenPayload,
} from '../../types/allegro';
import styles from './TokenManager.module.css';

interface TokenManagerProps {
  tokens: AllegroToken[];
  loading: boolean;
  onCreate: (payload: CreateTokenPayload) => Promise<void>;
  onUpdate: (tokenId: string, payload: UpdateTokenPayload) => Promise<void>;
  onDelete: (tokenId: string) => Promise<void>;
  onRefresh: (tokenId: string) => Promise<void>;
  onToggleActive: (tokenId: string, isActive: boolean) => Promise<void>;
}

interface TokenFormState {
  account_name: string;
  authorization_code: string;
  is_default: boolean;
}

const initialFormState: TokenFormState = {
  account_name: '',
  authorization_code: '',
  is_default: false,
};

const statusBadgeClass = (status: AllegroToken['status']) => {
  switch (status) {
    case 'active':
      return `${styles.badge} ${styles.statusActive}`;
    case 'pending':
      return `${styles.badge} ${styles.statusPending}`;
    case 'error':
      return `${styles.badge} ${styles.statusError}`;
    case 'expired':
    case 'revoked':
    default:
      return `${styles.badge} ${styles.statusExpired}`;
  }
};

const TokenManager = ({
  tokens,
  loading,
  onCreate,
  onUpdate,
  onDelete,
  onRefresh,
  onToggleActive,
}: TokenManagerProps) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formState, setFormState] = useState<TokenFormState>(initialFormState);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sortedTokens = useMemo(
    () =>
      [...tokens].sort((a, b) => {
        if (a.is_default) return -1;
        if (b.is_default) return 1;
        return a.account_name.localeCompare(b.account_name, 'ru');
      }),
    [tokens],
  );

  const openModal = () => {
    setFormState(initialFormState);
    setError(null);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
  };

  const handleChange = (field: keyof TokenFormState, value: string | boolean) => {
    setFormState((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      await onCreate({
        account_name: formState.account_name,
        authorization_code: formState.authorization_code,
        is_default: formState.is_default,
      });
      setIsModalOpen(false);
      setFormState(initialFormState);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать токен.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className={styles.container}>
      <div className={styles.header}>
        <div>
          <h2 className={styles.title}>Подключенные аккаунты Allegro</h2>
          <p className={styles.helperText}>
            Управляйте OAuth-токенами, которые используются для синхронизации заказов через Allegro orders backup.
          </p>
        </div>
        <div className={styles.actions}>
          <button className={styles.primaryButton} onClick={openModal} disabled={loading}>
            Подключить новый аккаунт
          </button>
        </div>
      </div>

      {tokens.length === 0 && !loading ? (
        <div className={styles.emptyState}>
          <h3>Нет подключенных токенов</h3>
          <p>Добавьте токен Allegro, чтобы начать резервное копирование и импорт заказов в систему.</p>
        </div>
      ) : (
        <div className={styles.tokensGrid}>
          {sortedTokens.map((token) => (
            <article key={token.token_id} className={styles.tokenCard}>
              <div className={styles.tokenHeader}>
                <div>
                  <div className={styles.tokenName}>{token.account_name}</div>
                  {token.is_default && <span className={styles.defaultBadge}>По умолчанию</span>}
                </div>
                <span className={statusBadgeClass(token.status)}>
                  {token.status === 'active'
                    ? 'Активен'
                    : token.status === 'pending'
                      ? 'Обновляется'
                      : token.status === 'error'
                        ? 'Ошибка'
                        : 'Неактивен'}
                </span>
              </div>

              <div className={styles.metaRow}>
                <span>Создан: {format(new Date(token.created_at), 'd MMMM yyyy', { locale: ru })}</span>
                <span>Экспортировано заказов: {token.orders_imported}</span>
              </div>

              <div className={styles.metaRow}>
                <span>Истекает: {format(new Date(token.expires_at), 'd MMMM yyyy HH:mm', { locale: ru })}</span>
                <span>Клиент: {token.client_id}</span>
              </div>

              {token.last_sync_at && (
                <div className={styles.metaRow}>
                  <span>Последняя синхронизация:</span>
                  <span>{format(new Date(token.last_sync_at), 'd MMMM yyyy HH:mm', { locale: ru })}</span>
                </div>
              )}

              {token.last_error && (
                <div className={styles.errorBox}>Последняя ошибка: {token.last_error}</div>
              )}

              <div className={styles.tokenActions}>
                <button
                  className={styles.secondaryButton}
                  onClick={() => onRefresh(token.token_id)}
                  disabled={loading}
                >
                  Обновить токен
                </button>
                <button
                  className={styles.secondaryButton}
                  onClick={() =>
                    onToggleActive(token.token_id, !(token.status === 'active' || token.status === 'pending'))
                  }
                  disabled={loading}
                >
                  {token.status === 'active' || token.status === 'pending' ? 'Деактивировать' : 'Активировать'}
                </button>
                <button
                  className={styles.secondaryButton}
                  onClick={() => onUpdate(token.token_id, { is_default: !token.is_default })}
                  disabled={loading || token.status !== 'active'}
                >
                  {token.is_default ? 'Сделать вторичным' : 'Сделать основным'}
                </button>
                <button className={styles.dangerButton} onClick={() => onDelete(token.token_id)} disabled={loading}>
                  Удалить
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      {isModalOpen && (
        <div className={styles.modalOverlay}>
          <div className={styles.modal}>
            <h3 className={styles.modalTitle}>Добавить токен Allegro</h3>
            <form className={styles.form} onSubmit={handleSubmit}>
              <label className={styles.label}>
                Название аккаунта
                <input
                  className={styles.input}
                  value={formState.account_name}
                  onChange={(event) => handleChange('account_name', event.target.value)}
                  required
                />
              </label>

              <label className={styles.label}>
                Авторизационный код Allegro
                <textarea
                  className={styles.input}
                  value={formState.authorization_code}
                  onChange={(event) => handleChange('authorization_code', event.target.value)}
                  required
                  rows={4}
                />
                <span className={styles.helperText}>
                  Получите код в приложении Allegro и вставьте его сюда для обмена на токен доступа.
                </span>
              </label>

              <label className={styles.checkboxRow}>
                <input
                  type="checkbox"
                  checked={formState.is_default}
                  onChange={(event) => handleChange('is_default', event.target.checked)}
                />
                Сделать токен основным для всех новых заказов
              </label>

              {error && <div className={styles.errorBox}>{error}</div>}

              <div className={styles.modalActions}>
                <button type="button" className={styles.cancelButton} onClick={closeModal} disabled={isSubmitting}>
                  Отменить
                </button>
                <button type="submit" className={styles.saveButton} disabled={isSubmitting}>
                  {isSubmitting ? 'Сохраняем…' : 'Сохранить токен'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
};

export default TokenManager;
