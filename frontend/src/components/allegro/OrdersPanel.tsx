import { useMemo } from 'react';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';
import { AllegroOrder, AllegroOrderFilters, AllegroToken } from '../../types/allegro';
import styles from './OrdersPanel.module.css';

interface OrdersPanelProps {
  orders: AllegroOrder[];
  loading: boolean;
  tokens: AllegroToken[];
  filters: AllegroOrderFilters;
  onFiltersChange: (filters: AllegroOrderFilters) => void;
  onRefresh: () => void;
  onSelectOrder: (order: AllegroOrder) => void;
}

const formatMoney = (amount: number, currency: string) =>
  new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  }).format(amount);

const statusBadgeClass = (status: AllegroOrder['status']) => {
  switch (status) {
    case 'new':
      return `${styles.statusBadge} ${styles.statusNew}`;
    case 'processing':
      return `${styles.statusBadge} ${styles.statusProcessing}`;
    case 'ready_for_shipment':
      return `${styles.statusBadge} ${styles.statusReady_for_shipment}`;
    case 'shipped':
      return `${styles.statusBadge} ${styles.statusShipped}`;
    case 'cancelled':
      return `${styles.statusBadge} ${styles.statusCancelled}`;
    case 'returned':
      return `${styles.statusBadge} ${styles.statusReturned}`;
    default:
      return styles.statusBadge;
  }
};

const OrdersPanel = ({ orders, loading, tokens, filters, onFiltersChange, onRefresh, onSelectOrder }: OrdersPanelProps) => {
  const tokenOptions = useMemo(() => [{ token_id: 'all', account_name: 'Все аккаунты' }, ...tokens], [tokens]);

  const handleChange = (field: keyof AllegroOrderFilters, value: string) => {
    const nextFilters: AllegroOrderFilters = { ...filters };
    if (!value || value === 'all') {
      delete nextFilters[field];
    } else {
      nextFilters[field] = value as any;
    }
    onFiltersChange(nextFilters);
  };

  const handleDateChange = (field: keyof AllegroOrderFilters, value: string) => {
    const nextFilters: AllegroOrderFilters = { ...filters, [field]: value || undefined };
    if (!value) {
      delete nextFilters[field];
    }
    onFiltersChange(nextFilters);
  };

  const clearFilters = () => {
    onFiltersChange({});
  };

  return (
    <section className={styles.container}>
      <div className={styles.filters}>
        <div className={styles.filterField}>
          <label className={styles.label} htmlFor="token-select">Аккаунт</label>
          <select
            id="token-select"
            className={styles.select}
            value={filters.token_id ?? 'all'}
            onChange={(event) => handleChange('token_id', event.target.value)}
          >
            {tokenOptions.map((token) => (
              <option key={token.token_id} value={token.token_id === 'all' ? 'all' : token.token_id}>
                {token.account_name}
              </option>
            ))}
          </select>
        </div>

        <div className={styles.filterField}>
          <label className={styles.label} htmlFor="status-select">Статус заказа</label>
          <select
            id="status-select"
            className={styles.select}
            value={filters.status ?? 'all'}
            onChange={(event) => handleChange('status', event.target.value)}
          >
            <option value="all">Все</option>
            <option value="new">Новые</option>
            <option value="processing">В обработке</option>
            <option value="ready_for_shipment">Готовы к отгрузке</option>
            <option value="shipped">Отгружены</option>
            <option value="cancelled">Отменены</option>
            <option value="returned">Возвраты</option>
          </select>
        </div>

        <div className={styles.filterField}>
          <label className={styles.label} htmlFor="payment-select">Оплата</label>
          <select
            id="payment-select"
            className={styles.select}
            value={filters.payment_status ?? 'all'}
            onChange={(event) => handleChange('payment_status', event.target.value)}
          >
            <option value="all">Все</option>
            <option value="paid">Оплачено</option>
            <option value="pending">Ожидает</option>
            <option value="refunded">Возврат</option>
            <option value="failed">Ошибка</option>
          </select>
        </div>

        <div className={styles.filterField}>
          <label className={styles.label} htmlFor="fulfillment-select">Фулфилмент</label>
          <select
            id="fulfillment-select"
            className={styles.select}
            value={filters.fulfillment_status ?? 'all'}
            onChange={(event) => handleChange('fulfillment_status', event.target.value)}
          >
            <option value="all">Все</option>
            <option value="pending">Не начат</option>
            <option value="in_progress">В процессе</option>
            <option value="fulfilled">Отгружен</option>
            <option value="cancelled">Отменен</option>
          </select>
        </div>

        <div className={styles.filterField}>
          <label className={styles.label} htmlFor="date-from">Дата с</label>
          <input
            id="date-from"
            type="date"
            className={styles.dateInput}
            value={filters.created_from ?? ''}
            onChange={(event) => handleDateChange('created_from', event.target.value)}
          />
        </div>

        <div className={styles.filterField}>
          <label className={styles.label} htmlFor="date-to">Дата по</label>
          <input
            id="date-to"
            type="date"
            className={styles.dateInput}
            value={filters.created_to ?? ''}
            onChange={(event) => handleDateChange('created_to', event.target.value)}
          />
        </div>

        <div className={styles.filterField}>
          <label className={styles.label} htmlFor="search">Поиск</label>
          <input
            id="search"
            className={styles.input}
            placeholder="Заказ, email, телефон"
            value={filters.search ?? ''}
            onChange={(event) => handleChange('search', event.target.value)}
          />
        </div>
      </div>

      <div className={styles.refreshRow}>
        <button className={styles.clearButton} onClick={clearFilters}>Сбросить фильтры</button>
        <button className={styles.refreshButton} onClick={onRefresh} disabled={loading}>
          {loading ? 'Обновляем…' : 'Обновить список'}
        </button>
      </div>

      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Дата</th>
              <th>Allegro ID</th>
              <th>Клиент</th>
              <th>Статус</th>
              <th>Сумма</th>
              <th>Оплата</th>
              <th>Фулфилмент</th>
              <th>Токен</th>
            </tr>
          </thead>
          <tbody>
            {orders.length === 0 && !loading ? (
              <tr>
                <td colSpan={8} className={styles.emptyState}>Заказы не найдены</td>
              </tr>
            ) : (
              orders.map((order) => (
                <tr key={order.order_id} className={styles.row} onClick={() => onSelectOrder(order)}>
                  <td>{format(new Date(order.created_at), 'd MMM yyyy HH:mm', { locale: ru })}</td>
                  <td>{order.marketplace_order_id}</td>
                  <td>
                    <div>{order.buyer.name}</div>
                    <div>{order.buyer.email}</div>
                  </td>
                  <td>
                    <span className={statusBadgeClass(order.status)}>
                      {order.status === 'new'
                        ? 'Новый'
                        : order.status === 'processing'
                          ? 'В обработке'
                          : order.status === 'ready_for_shipment'
                            ? 'Готов к отгрузке'
                            : order.status === 'shipped'
                              ? 'Отгружен'
                              : order.status === 'cancelled'
                                ? 'Отменен'
                                : 'Возврат'}
                    </span>
                  </td>
                  <td>{formatMoney(order.total_amount, order.currency)}</td>
                  <td>{order.payment_status === 'paid' ? 'Оплачено' : order.payment_status === 'pending' ? 'Ожидает' : order.payment_status === 'refunded' ? 'Возврат' : 'Ошибка'}</td>
                  <td>{order.fulfillment_status === 'pending' ? 'Не начат' : order.fulfillment_status === 'in_progress' ? 'В процессе' : order.fulfillment_status === 'fulfilled' ? 'Отгружен' : 'Отменен'}</td>
                  <td>{tokens.find((token) => token.token_id === order.token_id)?.account_name ?? '—'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
};

export default OrdersPanel;
