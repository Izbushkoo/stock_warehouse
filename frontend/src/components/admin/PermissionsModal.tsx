import { useState, useEffect, useCallback } from 'react';
import { User, UserPermissionSummary } from '../../types/user';
import { updateUserPermissions } from '../../api/auth';
import { getUserPermissions, grantPermission, revokePermission } from '../../api/permissions';
import { getCatalogs, Catalog } from '../../api/catalogs';
import Modal from '../ui/Modal';
import Button from '../ui/Button';
import styles from './PermissionsModal.module.css';

interface PermissionsModalProps {
  isOpen: boolean;
  onClose: () => void;
  user: User;
  onUserUpdated: (updatedUser: User) => void;
}

const PermissionsModal: React.FC<PermissionsModalProps> = ({
  isOpen,
  onClose,
  user,
  onUserUpdated
}) => {
  const [permissions, setPermissions] = useState({
    is_admin: false
  });
  const [userPermissions, setUserPermissions] = useState<UserPermissionSummary | null>(null);
  const [allCatalogs, setAllCatalogs] = useState<Catalog[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setError(null);
      console.log('Loading permissions for user:', user.user_id);

      // Загружаем разрешения пользователя
      const userPermsData = await getUserPermissions(user.user_id);
      console.log('Loaded permissions:', userPermsData);
      setUserPermissions(userPermsData);
      setPermissions({
        is_admin: userPermsData.is_system_admin
      });

      // Загружаем все каталоги
      const catalogsData = await getCatalogs();
      console.log('Loaded catalogs:', catalogsData);
      setAllCatalogs(catalogsData);
    } catch (err) {
      console.error('Failed to load data:', err);
      setError(err instanceof Error ? err.message : 'Не удалось загрузить данные');
    }
  }, [user.user_id]);

  useEffect(() => {
    if (isOpen && user) {
      loadData();
    }
  }, [isOpen, user, loadData]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const updatedUser = await updateUserPermissions(user.user_id, permissions);
      onUserUpdated(updatedUser);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка');
    } finally {
      setLoading(false);
    }
  };

  const handlePermissionChange = (permission: string) => {
    setPermissions(prev => ({
      ...prev,
      [permission]: !prev[permission as keyof typeof prev]
    }));
  };

  const handleGrantCatalogPermission = async (catalogId: string, permissionLevel: string) => {
    const actionKey = `grant-${catalogId}-${permissionLevel}`;
    setActionLoading(actionKey);

    try {
      await grantPermission(
        user.user_id,
        'item_group',
        catalogId,
        permissionLevel
      );

      // Перезагружаем данные
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка выдачи разрешения');
    } finally {
      setActionLoading(null);
    }
  };

  const handleRevokeCatalogPermission = async (catalogId: string) => {
    const actionKey = `revoke-${catalogId}`;
    setActionLoading(actionKey);

    try {
      await revokePermission(
        user.user_id,
        'item_group',
        catalogId
      );

      // Перезагружаем данные
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка отзыва разрешения');
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Разрешения: ${user.display_name}`} size="large">
      <form onSubmit={handleSubmit} className={styles.form}>
        {error && (
          <div className={styles.error}>
            {error}
          </div>
        )}

        <div className={styles.permissionsList}>
          {/* Системные разрешения */}
          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>Системные разрешения</h3>

            <div className={styles.permissionItem}>
              <div className={styles.permissionHeader}>
                <label className={styles.checkboxLabel}>
                  <input
                    type="checkbox"
                    checked={permissions.is_admin}
                    onChange={() => handlePermissionChange('is_admin')}
                    className={styles.checkbox}
                  />
                  <span className={styles.permissionTitle}>Системный администратор</span>
                </label>
              </div>
              <p className={styles.permissionDescription}>
                Полный доступ ко всем функциям системы, всем каталогам и складам
              </p>
            </div>
          </div>

          {/* Управление разрешениями на каталоги */}
          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>Разрешения на каталоги</h3>
            {allCatalogs.length === 0 ? (
              <p>Каталоги не найдены</p>
            ) : (
              allCatalogs.map((catalog) => {
                const hasPermission = userPermissions?.item_groups[catalog.item_group_id];
                return (
                  <div key={catalog.item_group_id} className={styles.catalogPermissionItem}>
                    <div className={styles.catalogHeader}>
                      <div className={styles.catalogInfo}>
                        <h4 className={styles.catalogName}>{catalog.item_group_name}</h4>
                        <p className={styles.catalogCode}>Код: {catalog.item_group_code}</p>
                        {catalog.item_group_description && (
                          <p className={styles.catalogDescription}>{catalog.item_group_description}</p>
                        )}
                      </div>
                      <div className={styles.catalogActions}>
                        {hasPermission ? (
                          <div className={styles.currentPermission}>
                            <span className={styles.permissionBadge}>
                              {hasPermission.permission_level.toUpperCase()}
                            </span>
                            <Button
                              variant="danger"
                              size="small"
                              loading={actionLoading === `revoke-${catalog.item_group_id}`}
                              onClick={() => handleRevokeCatalogPermission(catalog.item_group_id)}
                            >
                              Отозвать
                            </Button>
                          </div>
                        ) : (
                          <div className={styles.grantPermissions}>
                            <Button
                              variant="success"
                              size="small"
                              loading={actionLoading === `grant-${catalog.item_group_id}-read`}
                              onClick={() => handleGrantCatalogPermission(catalog.item_group_id, 'read')}
                            >
                              READ
                            </Button>
                            <Button
                              variant="warning"
                              size="small"
                              loading={actionLoading === `grant-${catalog.item_group_id}-write`}
                              onClick={() => handleGrantCatalogPermission(catalog.item_group_id, 'write')}
                            >
                              WRITE
                            </Button>
                            <Button
                              variant="info"
                              size="small"
                              loading={actionLoading === `grant-${catalog.item_group_id}-admin`}
                              onClick={() => handleGrantCatalogPermission(catalog.item_group_id, 'admin')}
                            >
                              ADMIN
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Разрешения на склады */}
          {userPermissions && Object.keys(userPermissions.warehouses).length > 0 && (
            <div className={styles.section}>
              <h3 className={styles.sectionTitle}>Доступ к складам</h3>
              {Object.entries(userPermissions.warehouses).map(([id, warehouse]) => (
                <div key={id} className={styles.permissionItem}>
                  <div className={styles.permissionHeader}>
                    <span className={styles.permissionTitle}>{warehouse.warehouse_name}</span>
                    <div className={styles.permissionBadges}>
                      {warehouse.permissions.read && <span className={styles.badge}>Чтение</span>}
                      {warehouse.permissions.write && <span className={styles.badge}>Запись</span>}
                      {warehouse.permissions.admin && <span className={styles.badge}>Админ</span>}
                    </div>
                  </div>
                  <p className={styles.permissionDescription}>
                    Источник: {warehouse.source === 'direct_warehouse' ? 'Прямое разрешение на склад' :
                      warehouse.source === 'inherited_from_item_group' ? 'Унаследовано от каталога' :
                        'Системный администратор'}
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* Информация о логике разрешений */}
          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>Как работают разрешения</h3>
            <div className={styles.infoBox}>
              <p><strong>Каталог (ItemGroup):</strong></p>
              <ul>
                <li><strong>READ</strong> - видеть остатки по всем складам в каталоге</li>
                <li><strong>WRITE</strong> - управлять остатками на всех складах в каталоге</li>
                <li><strong>ADMIN</strong> - управлять каталогом и выдавать разрешения</li>
              </ul>

              <p><strong>Склад (Warehouse):</strong></p>
              <ul>
                <li><strong>READ</strong> - видеть остатки только на этом складе</li>
                <li><strong>WRITE</strong> - управлять остатками только на этом складе</li>
                <li><strong>ADMIN</strong> - управлять складом и выдавать разрешения</li>
              </ul>

              <p><strong>Наследование:</strong> Разрешения на каталог автоматически распространяются на все склады в нем.</p>
            </div>
          </div>
        </div>

        <div className={styles.actions}>
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            disabled={loading}
          >
            Отмена
          </Button>
          <Button
            type="submit"
            variant="primary"
            loading={loading}
          >
            Сохранить разрешения
          </Button>
        </div>
      </form>
    </Modal>
  );
};

export default PermissionsModal;