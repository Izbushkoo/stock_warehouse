import { useState, useEffect } from 'react';
import styles from './CatalogManagement.module.css';

const CatalogManagement = () => {
  const [catalogs, setCatalogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // TODO: Загрузка каталогов с бекенда
    setLoading(false);
  }, []);

  if (loading) {
    return <div className={styles.loading}>Загрузка...</div>;
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2>Управление каталогами</h2>
        <button className={styles.addButton}>
          Создать каталог
        </button>
      </div>

      <div className={styles.catalogsList}>
        {catalogs.length === 0 ? (
          <p>Каталоги не найдены</p>
        ) : (
          <p>Список каталогов будет здесь</p>
        )}
      </div>
    </div>
  );
};

export default CatalogManagement;