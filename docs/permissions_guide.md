# Руководство по системе разрешений

## Обзор системы

Новая система разрешений построена на гибкой архитектуре, которая поддерживает различные типы ресурсов и уровни доступа.

## Иерархия разрешений

### 1. Типы ресурсов (ResourceType)

- **SYSTEM** - системные разрешения (полный контроль)
- **ITEM_GROUP** - разрешения на инвентарь
- **WAREHOUSE** - разрешения на склад
- **AUDIT** - разрешения на аудит (готово к расширению)
- **MARKETPLACE_ACCOUNTS** - разрешения на маркетплейсы (готово к расширению)

### 2. Уровни разрешений (PermissionLevel)

- **READ** - только просмотр
- **WRITE** - просмотр + изменение
- **ADMIN** - все выше + управление разрешениями
- **OWNER** - полный контроль + передача владения

## Логика работы

### Системный администратор (SYSTEM)
- Создается через скрипт `scripts/create_system_admin.py`
- Имеет доступ ко всем функциям системы
- Может создавать инвентари (ItemGroup)
- Может назначать других системных администраторов

### Администратор инвентаря (ITEM_GROUP)
- Получает разрешение от системного администратора
- Может создавать товары в своем инвентаре
- Может создавать склады для своего инвентаря
- Может назначать разрешения на склады другим пользователям

### Пользователь склада (WAREHOUSE)
- Получает разрешение от администратора инвентаря
- Может работать с конкретным складом согласно уровню доступа
- Администратор склада может назначать разрешения другим пользователям

## API Endpoints

### Создание ресурсов

```bash
# Создать инвентарь (только system admin)
POST /api/permissions/item-groups?item_group_code=INV001&item_group_name=Основной инвентарь

# Создать склад в инвентаре
POST /api/permissions/item-groups/{item_group_id}/warehouses
{
  "warehouse_code": "WH001",
  "warehouse_name": "Основной склад",
  "warehouse_address": "ул. Складская, 1"
}
```

### Управление разрешениями

```bash
# Выдать разрешение на инвентарь
POST /api/permissions/item-groups/{item_group_id}/grant
{
  "user_email": "user@example.com",
  "permission_level": "write"
}

# Выдать разрешение на склад
POST /api/permissions/warehouses/{warehouse_id}/grant
{
  "user_email": "user@example.com",
  "permission_level": "read"
}

# Отозвать разрешение на склад
DELETE /api/permissions/warehouses/{warehouse_id}/permissions/{user_id}
```

### Просмотр разрешений

```bash
# Мои разрешения
GET /api/permissions/my-permissions

# Мои инвентари
GET /api/permissions/item-groups

# Склады в инвентаре
GET /api/permissions/item-groups/{item_group_id}/warehouses

# Пользователи склада
GET /api/permissions/warehouses/{warehouse_id}/permissions
```

## Веб-интерфейс

### Дашборд разрешений
- URL: `/admin/permissions/`
- Показывает все доступные инвентари и склады
- Кнопки для создания и управления

### Управление инвентарем
- URL: `/admin/permissions/item-groups/{id}/manage`
- Добавление пользователей по email
- Создание складов
- Управление разрешениями

### Управление складом
- URL: `/admin/permissions/warehouses/{id}/manage`
- Добавление пользователей по email
- Управление разрешениями склада

## Установка и настройка

### 1. Применить миграции

```bash
# Если есть проблемы с multiple heads
alembic heads  # посмотреть текущие heads
alembic merge head1 head2 -m "merge_migrations"  # объединить
alembic upgrade head  # применить
```

### 2. Создать системного администратора

```bash
python scripts/create_system_admin.py
```

### 3. Проверить работу

```bash
# Запустить приложение
uvicorn src.warehouse_service.app:create_app --factory --reload

# Открыть в браузере
http://localhost:8000/admin/permissions/
```

## Расширение системы

### Добавление нового типа ресурса

1. Добавить в `ResourceType` enum:
```python
class ResourceType(str, Enum):
    # ... существующие
    NEW_MODULE = "new_module"
```

2. Обновить constraint в миграции:
```sql
ALTER TABLE permission DROP CONSTRAINT ck_resource_type;
ALTER TABLE permission ADD CONSTRAINT ck_resource_type 
CHECK (resource_type IN ('item_group', 'warehouse', 'audit', 'marketplace_accounts', 'system', 'new_module'));
```

3. Добавить методы в `PermissionManager`:
```python
def can_access_new_module(self, user_id: UUID, resource_id: UUID) -> bool:
    return self.has_permission(user_id, ResourceType.NEW_MODULE, resource_id, PermissionLevel.READ)
```

4. Создать API endpoints для нового модуля

## Безопасность

- Все разрешения проверяются на уровне API
- Системные администраторы имеют доступ ко всему
- Разрешения могут иметь срок действия (`expires_at`)
- Разрешения можно деактивировать (`is_active`)
- Ведется аудит кто и когда выдал разрешение (`granted_by`, `granted_at`)

## Примеры использования

### Сценарий 1: Новая компания
1. Системный админ создает инвентарь "Основной"
2. Назначает менеджера с правами `admin` на инвентарь
3. Менеджер создает склады и назначает операторов

### Сценарий 2: Мультитенантность
1. Каждый клиент получает свой инвентарь
2. Клиент управляет своими складами и пользователями
3. Системный админ видит все, но не вмешивается

### Сценарий 3: Временный доступ
1. Выдать разрешение с `expires_at`
2. Система автоматически игнорирует просроченные разрешения
3. Можно продлить или отозвать досрочно