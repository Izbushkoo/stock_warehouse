import styles from './Footer.module.css';

const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className={styles.footer}>
      <div className={styles.container}>
        <div className={styles.content}>
          <div className={styles.section}>
            <h3 className={styles.title}>Stock Warehouse</h3>
            <p className={styles.description}>
              Система управления товарами и заказами
            </p>
          </div>
          
          <div className={styles.section}>
            <h4 className={styles.sectionTitle}>Функции</h4>
            <ul className={styles.linkList}>
              <li><a href="/catalog" className={styles.link}>Каталог товаров</a></li>
              <li><a href="/warehouses" className={styles.link}>Управление складами</a></li>
              <li><a href="/orders" className={styles.link}>Заказы</a></li>
            </ul>
          </div>
          
          <div className={styles.section}>
            <h4 className={styles.sectionTitle}>Поддержка</h4>
            <ul className={styles.linkList}>
              <li><a href="/help" className={styles.link}>Справка</a></li>
              <li><a href="/contact" className={styles.link}>Контакты</a></li>
            </ul>
          </div>
        </div>
        
        <div className={styles.bottom}>
          <p className={styles.copyright}>
            © {currentYear} Stock Warehouse. Все права защищены.
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;