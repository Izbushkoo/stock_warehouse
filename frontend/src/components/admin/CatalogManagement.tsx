import { useState, useEffect } from 'react';
import { getCatalogs, createCatalog, deleteCatalog, Catalog, CreateCatalogRequest } from '../../api/catalogs';
import styles from './CatalogManagement.module.css';

interface CreateCatalogModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: CreateCatalogRequest) => void;
  loading: boolean;
}

const CreateCatalogModal = ({ isOpen, onClose, onSubmit, loading }: CreateCatalogModalProps) => {
  const [formData, setFormData] = useState<CreateCatalogRequest>({
    code: '',
    name: '',
    description: ''
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const handleClose = () => {
    setFormData({ code: '', name: '', description: '' });
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className={styles.modalOverlay}>
      <div className={styles.modal}>
        <div className={styles.modalHeader}>
          <h3>Создать каталог</h3>
          <button onClick={handleClose} className={styles.closeButton}>×</button>
        </div>
        
        <form onSubmit={handleSubmit} className={styles.modalForm}>
          <div className={styles.formGroup}>
            <label htmlFor="code">Код каталога *</label>
            <input
              id="code"
              type="text"
              value={formData.code}
              onChange={(e) => setFormData({ ...formData, code: e.target.value })}
              required
              placeholder="Например: ELECTRONICS"
            />
          </div>
          
          <div className={styles.formGroup}>
            <label htmlFor="name">Название *</label>
            <input
              id="name"
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              placeholder="Например: Электроника"
            />
          </div>
          
          <div className={styles.formGroup}>
            <label htmlFor="description">Описание</label>
            <textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Описание каталога (необязательно)"
              rows={3}
            />
          </div>
          
          <div className={styles.modalActions}>
            <button type="button" onClick={handleClose} className={styles.cancelButton}>
              Отмена
            </button>
            <button type="submit" disabled={loading} className={styles.submitButton}>
              {loading ? 'Создание...' : 'Создать'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const CatalogManagement = () => {
  const [catalogs, setCatalogs] = useState<Catalog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);

  const loadCatalogs = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getCatalogs();
      setCatalogs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки каталогов');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCatalogs();
  }, []);

  const handleCreateCatalog = async (data: CreateCatalogRequest) => {
    try {
      setCreateLoading(true);
      await createCatalog(data);
      setIsCreateModalOpen(false);
      await loadCatalogs(); // Перезагружаем список
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка создания каталога');
    } finally {
      setCreateLoading(false);
    }
  };

  const handleDeleteCatalog = async (catalogId: string, catalogName: string) => {
    if (!confirm(`Вы уверены, что хотите удалить каталог "${catalogName}"?`)) {
      return;
    }

    try {
      await deleteCatalog(catalogId);
      await loadCatalogs(); // Перезагружаем список
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка удаления каталога');
    }
  };

  if (loading) {
    return <div className={styles.loading}>Загрузка каталогов...</div>;
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2>Управление каталогами</h2>
        <button 
          className={styles.addButton}
          onClick={() => setIsCreateModalOpen(true)}
        >
          Создать каталог
        </button>
      </div>

      {error && (
        <div className={styles.error}>
          {error}
          <button onClick={() => setError(null)} className={styles.errorClose}>×</button>
        </div>
      )}

      <div className={styles.catalogsList}>
        {catalogs.length === 0 ? (
          <div className={styles.emptyState}>
            <p>Каталоги не найдены</p>
            <button 
              className={styles.createFirstButton}
              onClick={() => setIsCreateModalOpen(true)}
            >
              Создать первый каталог
            </button>
          </div>
        ) : (
          <div className={styles.catalogsGrid}>
            {catalogs.map((catalog) => (
              <div key={catalog.item_group_id} className={styles.catalogCard}>
                <div className={styles.catalogHeader}>
                  <h3>{catalog.item_group_name}</h3>
                  <span className={`${styles.status} ${catalog.is_active ? styles.active : styles.inactive}`}>
                    {catalog.is_active ? 'Активен' : 'Неактивен'}
                  </span>
                </div>
                
                <div className={styles.catalogInfo}>
                  <p><strong>Код:</strong> {catalog.item_group_code}</p>
                  {catalog.item_group_description && (
                    <p><strong>Описание:</strong> {catalog.item_group_description}</p>
                  )}
                  <p><strong>Складов:</strong> {catalog.warehouses_count}</p>
                  <p><strong>Создан:</strong> {new Date(catalog.created_at).toLocaleDateString('ru-RU')}</p>
                </div>
                
                <div className={styles.catalogActions}>
                  <button className={styles.editButton}>
                    Редактировать
                  </button>
                  <button 
                    className={styles.deleteButton}
                    onClick={() => handleDeleteCatalog(catalog.item_group_id, catalog.item_group_name)}
                  >
                    Удалить
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <CreateCatalogModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleCreateCatalog}
        loading={createLoading}
      />
    </div>
  );
};

export default CatalogManagement;