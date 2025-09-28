# Unified Warehouse Management System

Комплексная система управления складом, объединяющая функциональность baselinker_to_wix и allegro_orders_backup в единую платформу с полным аудитом, ролевой системой доступа и аналитикой.

## 🏗️ Архитектура

Система построена на принципах:
- **Event Sourcing** - все изменения остатков записываются в `stock_movement` как источник истины
- **CQRS** - разделение команд (движения) и запросов (балансы)
- **Неизменяемость** - записи движений никогда не изменяются
- **Полный аудит** - каждая операция записывается с контекстом
- **RBAC** - гранулярный контроль доступа по складам и группам товаров

## 📊 Основные компоненты

### 1. Складская топология
- **Warehouse** - склады с временными зонами
- **Zone** - зоны склада (приемка, хранение, комплектация, отгрузка, возвраты, брак)
- **BinLocation** - конкретные ячейки хранения с ограничениями вместимости

### 2. Товары и группы
- **ItemGroup** - группы товаров с политиками обработки
- **Item** - товары с SKU и характеристиками
- **Lot** - партии для отслеживания сроков годности
- **SerialNumber** - серийные номера для индивидуального учета

### 3. Система движений (ядро)
- **StockMovement** - журнал всех движений (источник истины)
- **StockBalance** - текущие остатки (материализованное представление)
- **InventoryReservation** - резервы под заказы

### 4. Заказы и продажи
- **SalesOrder** - заказы с маркетплейсов
- **SalesOrderLine** - позиции заказов
- **ReturnOrder** - возвраты с инспекцией

### 5. Медиа и документы
- **MediaAsset** - неизменяемые файлы с SHA-256
- **ItemImage** - изображения товаров
- **DocumentFile** - документы операций
- **MovementAttachment** - файлы к движениям

### 6. Аналитика
- **SalesAnalytics** - детальная аналитика продаж
- **PurchaseRecommendation** - рекомендации по закупкам

### 7. Аудит и безопасность
- **AppUser** - пользователи системы
- **WarehouseAccessGrant** - права доступа
- **AuditLog** - полный аудит изменений
- **DomainEvent** - бизнес-события

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -e .
```

### 2. Настройка базы данных

Создайте файл `.env`:

```env
DATABASE_URL=postgresql://user:password@localhost/warehouse_db
REDIS_URL=redis://localhost:6379
CELERY_BROKER_URL=redis://localhost:6379
CELERY_RESULT_BACKEND=redis://localhost:6379
CELERY_DB_SCHEDULER_URL=postgresql://user:password@localhost/warehouse_db

TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CRITICAL_CHAT_ID=123456789
TELEGRAM_HEALTH_CHAT_ID=123456789

SUPERADMIN_EMAIL=admin@warehouse.local
SUPERADMIN_PASSWORD=admin123
```

### 3. Выполнение миграций

```bash
alembic upgrade head
```

Это создаст:
- Полную схему базы данных
- Триггеры для автоматического обновления балансов
- Начальные данные (склады, зоны, ячейки, группы товаров, пользователей)

### 4. Тестирование системы

```bash
python scripts/test_unified_system.py
```

### 5. Запуск API сервера

```bash
uvicorn warehouse_service.app:create_app --factory --reload
```

API будет доступно по адресу: http://localhost:8000

Документация: http://localhost:8000/docs

## 🔐 Система ролей и доступа

### Типы доступа
- **READ** - просмотр данных
- **WRITE** - создание и изменение
- **APPROVE** - подтверждение операций

### Области доступа
- **warehouse** - уровень склада
- **zone** - уровень зоны
- **bin_location** - уровень ячейки
- **item_group** - уровень группы товаров

### Пример предоставления доступа

```python
from warehouse_service.rbac.unified import RBACService

rbac = RBACService(session)

# Доступ к складу
rbac.grant_warehouse_access(
    user_id=user_id,
    warehouse_id=warehouse_id,
    can_read=True,
    can_write=True,
    can_approve=False
)

# Доступ к группе товаров
rbac.grant_item_group_access(
    user_id=user_id,
    warehouse_id=warehouse_id,
    item_group_id=electronics_group_id,
    can_read=True,
    can_write=True,
    can_approve=True
)
```

## 📦 Основные операции

### 1. Приемка товаров

```python
from warehouse_service.services import StockService

stock_service = StockService(session)

# Приемка из файла поставщика
movements = stock_service.process_goods_receipt(
    warehouse_id=warehouse_id,
    destination_bin_location_id=receiving_bin_id,
    items=[
        {
            "item_id": item_id,
            "quantity": Decimal('100'),
            "lot_code": "LOT-2024-001",
            "manufactured_at": datetime(2024, 1, 15),
            "expiration_date": datetime(2025, 1, 15),
        }
    ],
    actor_user_id=user_id,
    notes="Поставка от поставщика XYZ"
)
```

### 2. Создание и выполнение заказа

```python
from warehouse_service.services import SalesService

sales_service = SalesService(session)

# Создание заказа
order = sales_service.create_sales_order(
    warehouse_id=warehouse_id,
    sales_order_number="SO-2024-001",
    order_date=datetime.utcnow(),
    created_by_user_id=user_id,
    external_sales_channel="ozon",
    external_order_identifier="ozon-12345",
    line_items=[
        {
            "item_id": item_id,
            "quantity": Decimal('2'),
            "unit_price": Decimal('29.99')
        }
    ]
)

# Резервирование товара
reservations = sales_service.allocate_inventory(
    sales_order_id=order.sales_order_id,
    actor_user_id=user_id
)

# Отгрузка
movement_ids = sales_service.ship_sales_order(
    sales_order_id=order.sales_order_id,
    actor_user_id=user_id
)
```

### 3. Внутренние перемещения

```python
# Перемещение между ячейками
movement = stock_service.process_internal_transfer(
    warehouse_id=warehouse_id,
    source_bin_location_id=storage_bin_id,
    destination_bin_location_id=picking_bin_id,
    item_id=item_id,
    quantity=Decimal('10'),
    actor_user_id=user_id,
    notes="Перемещение для комплектации"
)
```

### 4. Ручные корректировки

```python
# Списание брака
adjustment = stock_service.process_manual_adjustment(
    warehouse_id=warehouse_id,
    bin_location_id=bin_id,
    item_id=item_id,
    adjustment_quantity=Decimal('-5'),  # Отрицательное для списания
    reason="Обнаружен брак при инвентаризации",
    actor_user_id=user_id
)
```

## 📊 Аналитика и отчеты

### 1. Аналитика продаж

```python
from warehouse_service.services import AnalyticsService

analytics_service = AnalyticsService(session)

# Продажи по дням
daily_sales = analytics_service.get_sales_analytics(
    warehouse_id=warehouse_id,
    user_id=user_id,
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31),
    group_by="day"
)

# Производительность маркетплейсов
marketplace_performance = analytics_service.get_marketplace_performance(
    warehouse_id=warehouse_id,
    user_id=user_id
)
```

### 2. Анализ оборачиваемости

```python
# Оборачиваемость товаров
turnover = analytics_service.get_inventory_turnover(
    warehouse_id=warehouse_id,
    user_id=user_id,
    period_days=90
)

# ABC анализ
abc_analysis = analytics_service.get_abc_analysis(
    warehouse_id=warehouse_id,
    user_id=user_id,
    period_days=365
)

# Медленно движущиеся товары
slow_moving = analytics_service.get_slow_moving_items(
    warehouse_id=warehouse_id,
    user_id=user_id,
    days_threshold=90
)
```

### 3. Рекомендации по закупкам

```python
# Автоматические рекомендации
recommendations = analytics_service.generate_purchase_recommendations(
    warehouse_id=warehouse_id,
    user_id=user_id,
    forecast_days=30,
    safety_stock_days=7
)
```

## 🎯 API Endpoints

### Основные операции
- `GET /api/v1/warehouses` - список складов
- `GET /api/v1/warehouses/{id}/stock-balance` - остатки на складе
- `POST /api/v1/stock-movements` - создание движения
- `GET /api/v1/warehouses/{id}/movements` - история движений

### Заказы
- `POST /api/v1/sales-orders` - создание заказа
- `POST /api/v1/sales-orders/{id}/allocate` - резервирование
- `POST /api/v1/sales-orders/{id}/ship` - отгрузка

### Аналитика
- `GET /api/v1/warehouses/{id}/analytics/sales` - аналитика продаж
- `GET /api/v1/warehouses/{id}/analytics/inventory-turnover` - оборачиваемость
- `GET /api/v1/warehouses/{id}/analytics/abc-analysis` - ABC анализ
- `POST /api/v1/warehouses/{id}/purchase-recommendations` - рекомендации

### Права доступа
- `GET /api/v1/users/{id}/permissions` - права пользователя

## 🔧 Конфигурация

### Политики обработки групп товаров

```json
{
  "prohibit_mixing_lots": true,
  "require_serial_tracking": false,
  "max_shelf_life_days": 365,
  "temperature_controlled": false,
  "hazardous_material": false
}
```

### Настройки ячеек

- `maximum_weight_kilograms` - максимальный вес
- `maximum_volume_cubic_meters` - максимальный объем
- `is_pick_face` - ячейка для комплектации
- `bin_location_type` - тип ячейки (pallet, shelf, flow_rack, staging)

## 🚨 Мониторинг и алерты

Система автоматически создает события для:
- Критически низких остатков
- Просроченных товаров
- Неуспешных операций
- Нарушений бизнес-правил

События можно обрабатывать через:
- Telegram уведомления
- Email алерты
- Webhook интеграции
- Celery задачи

## 🔄 Интеграции

### Маркетплейсы
- Ozon
- Wildberries
- Allegro
- Яндекс.Маркет
- Другие через API

### ERP системы
- 1С
- SAP
- Oracle
- Другие через REST API

### Логистика
- СДЭК
- Почта России
- DPD
- Другие курьерские службы

## 📈 Масштабирование

Система поддерживает:
- Горизонтальное масштабирование API
- Партиционирование больших таблиц
- Кэширование через Redis
- Асинхронную обработку через Celery
- Репликацию базы данных

## 🛡️ Безопасность

- Хэширование паролей через bcrypt
- JWT токены для API
- Аудит всех операций
- Контроль доступа на уровне данных
- Шифрование чувствительных данных
- HTTPS обязательно в продакшене

## 📚 Дополнительная документация

- [API Reference](docs/api.md)
- [Database Schema](docs/schema.md)
- [Business Rules](docs/business-rules.md)
- [Deployment Guide](docs/deployment.md)
- [Troubleshooting](docs/troubleshooting.md)

## 🤝 Поддержка

Для вопросов и поддержки:
- Создайте issue в репозитории
- Обратитесь к команде разработки
- Проверьте документацию и FAQ

---

**Unified Warehouse Management System** - современное решение для комплексного управления складскими операциями с полным аудитом и аналитикой.