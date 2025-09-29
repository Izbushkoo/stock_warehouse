import styles from './Logo.module.css';

const Logo = () => (
  <div className={styles.logoWrapper}>
    <div className={styles.icon}>📦</div>
    <div>
      <div className={styles.title}>Stock Warehouse</div>
      <div className={styles.subtitle}>управление товарами и заказами</div>
    </div>
  </div>
);

export default Logo;
