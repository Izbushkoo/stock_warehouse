import { format } from 'date-fns';
import { ru } from 'date-fns/locale';
import { AllegroOrder } from '../../types/allegro';
import styles from './OrderDetailsDrawer.module.css';

interface OrderDetailsDrawerProps {
  order: AllegroOrder;
  onClose: () => void;
}

const OrderDetailsDrawer = ({ order, onClose }: OrderDetailsDrawerProps) => {
  const statusLabel = () => {
    switch (order.status) {
      case 'new':
        return 'Новый';
      case 'processing':
        return 'В обработке';
      case 'ready_for_shipment':
        return 'Готов к отгрузке';
      case 'shipped':
        return 'Отгружен';
      case 'cancelled':
        return 'Отменен';
      case 'returned':
        return 'Возврат';
      default:
        return order.status;
    }
  };

  const paymentLabel = () => {
    switch (order.payment_status) {
      case 'paid':
        return 'Оплачено';
      case 'pending':
        return 'Ожидает оплаты';
      case 'refunded':
        return 'Возврат';
      case 'failed':
        return 'Ошибка оплаты';
      default:
        return order.payment_status;
    }
  };

  const fulfillmentLabel = () => {
    switch (order.fulfillment_status) {
      case 'pending':
        return 'Не начат';
      case 'in_progress':
        return 'В процессе';
      case 'fulfilled':
        return 'Отгружен';
      case 'cancelled':
        return 'Отменен';
      default:
        return order.fulfillment_status;
    }
  };

  return (
    <div className={styles.overlay}>
      <div className={styles.drawer}>
        <div className={styles.header}>
          <h3 className={styles.title}>Заказ {order.marketplace_order_id}</h3>
          <button className={styles.closeButton} onClick={onClose} aria-label="Закрыть">
            ×
          </button>
        </div>

        <div className={styles.section}>
          <span className={styles.sectionTitle}>Информация о заказе</span>
          <div className={styles.keyValue}>
            <span>Создан</span>
            <span>{format(new Date(order.created_at), 'd MMMM yyyy HH:mm', { locale: ru })}</span>
          </div>
          <div className={styles.keyValue}>
            <span>Статус</span>
            <span className={styles.badge}>{statusLabel()}</span>
          </div>
          <div className={styles.keyValue}>
            <span>Оплата</span>
            <span>{paymentLabel()}</span>
          </div>
          <div className={styles.keyValue}>
            <span>Фулфилмент</span>
            <span>{fulfillmentLabel()}</span>
          </div>
          {order.last_synced_at && (
            <div className={styles.keyValue}>
              <span>Последняя синхронизация</span>
              <span>{format(new Date(order.last_synced_at), 'd MMM yyyy HH:mm', { locale: ru })}</span>
            </div>
          )}
        </div>

        <div className={styles.section}>
          <span className={styles.sectionTitle}>Покупатель</span>
          <div className={styles.keyValue}>
            <span>Имя</span>
            <span>{order.buyer.name}</span>
          </div>
          {order.buyer.email && (
            <div className={styles.keyValue}>
              <span>Email</span>
              <span>{order.buyer.email}</span>
            </div>
          )}
          {order.buyer.phone && (
            <div className={styles.keyValue}>
              <span>Телефон</span>
              <span>{order.buyer.phone}</span>
            </div>
          )}
        </div>

        <div className={styles.section}>
          <span className={styles.sectionTitle}>Товары</span>
          <div className={styles.itemsList}>
            {order.items.map((item) => (
              <div key={item.line_item_id} className={styles.itemRow}>
                <div>
                  <strong>{item.name}</strong>
                  <span> • SKU: {item.sku}</span>
                </div>
                <div>
                  Количество: {item.quantity} × {item.unit_price} {item.currency}
                </div>
                {item.fulfillment_status && <div>Фулфилмент: {item.fulfillment_status}</div>}
              </div>
            ))}
          </div>
        </div>

        <div className={styles.section}>
          <span className={styles.sectionTitle}>Отгрузка</span>
          <div className={styles.keyValue}>
            <span>Метод доставки</span>
            <span>{order.delivery_method ?? '—'}</span>
          </div>
          <div className={styles.keyValue}>
            <span>Трек-номер</span>
            <span>{order.shipping_tracking_number ?? '—'}</span>
          </div>
        </div>

        {order.notes && (
          <div className={styles.section}>
            <span className={styles.sectionTitle}>Заметки</span>
            <div>{order.notes}</div>
          </div>
        )}

        <div className={styles.footer}>
          <button className={styles.secondaryButton} onClick={onClose}>
            Закрыть
          </button>
          <button className={styles.button} onClick={onClose}>
            Перейти к заказу в Allegro
          </button>
        </div>
      </div>
    </div>
  );
};

export default OrderDetailsDrawer;
