import { useState, useEffect } from 'react';
import styles from './PermissionsManagement.module.css';

const PermissionsManagement = () => {
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // TODO: Загрузка разрешений с бекенда
    setLoading(false);
  }, []);

  if (loading) {
    return <div className={styles.loading}>Загрузка...</div>;
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2>Управление разрешениями</h2>
        <button className={styles.addButton}>
          Выдать разрешение
        </button>
      </div>

      <div className={styles.permissionsList}>
        {permissions.length === 0 ? (
          <p>Разрешения не найдены</p>
        ) : (
          <p>Список разрешений будет здесь</p>
        )}
      </div>
    </div>
  );
};

export default PermissionsManagement;