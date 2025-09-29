# Руководство по развёртыванию Stock Warehouse

Это руководство поможет вам развернуть проект Warehouse Stock в различных окружениях.

## 🏠 Локальная разработка

### Быстрый старт

```bash
# 1. Настройка окружения
make setup-local-env
# Отредактируйте .env при необходимости

# 2. Запуск полного стека
make local-up

# Доступ к сервисам:
# Frontend (React): http://localhost:5173
# Backend API: http://localhost:8000  
# API Документация: http://localhost:8000/docs
# База данных: localhost:5432
```

### Разработка только фронтенда

```bash
# Если бэкенд уже запущен
make local-frontend
```

### Полезные команды

```bash
make local-logs          # Просмотр логов
make local-down          # Остановка стека
make local-migrate       # Применить миграции БД
make local-create-admin  # Создать админа
```

## 🚀 Продакшен для stock.yarganix.com

### Настройка окружения

```bash
# 1. Настройка продакшена
make setup-prod-env
# Обязательно заполните .env.production

# 2. Настройка реверс-прокси (Nginx/Apache)
# Frontend должен обслуживаться статически
# API на вашем домене должен проксироваться на бэкенд
```

### Структура продакшена

```
stock.yarganix.com/
├── / (фронтенд React - статические файлы)
└── /api/ (API бэкенд через прокси)
```

### Nginx конфигурация

```nginx
server {
    listen 80;
    listen 443 ssl http2;
    server_name stock.yarganix.com www.stock.yarganix.com;

    # SSL сертификаты
    ssl_certificate /path/to/ssl/cert.pem;
    ssl_certificate_key /path/to/ssl/key.pem;

    # Статический фронтенд
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
        
        # Отключить кэш в режиме разработки
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
    }

    # API проксирование
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket поддержка для HMR (если нужно)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # GraphQL эндпоинт (если используется)
    location /graphql {
        proxy_pass http://localhost:8000/graphql;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Запуск продакшена

```bash
# 1. Билд продакшен образа фронтенда
make prod-build

# 2. Запуск продакшен стека
make prod-up

# 3. Создание админа продакшена
make prod-create-admin
```

### Переменные окружения для продакшена

Обязательные параметры в `.env.production`:

```bash
# Домен фронтенда для CORS
FRONTEND_URL=stock.yarganix.com

# Безопасные пароли и секреты
SUPERADMIN_PASSWORD=very_strong_password_here
JWT_SECRET=very_long_random_string_256_bits

# Реальные Telegram данные
TELEGRAM_BOT_TOKEN=real_telegram_bot_token
TELEGRAM_CRITICAL_CHAT_ID=actual_chat_id
TELEGRAM_HEALTH_CHAT_ID=actual_chat_id

# База данных продакшена
DATABASE_URL=postgresql://user:password@prod_db_host:5432/warehouse_prod
```

## 🔧 Различия между окружениями

| Параметр | Локальная разработка | Продакшен |
|----------|---------------------|-----------|
| **Фронтенд** | Vite dev server | Статические файлы |
| **API URL** | http://localhost:8000/api | https://stock.yarganix.com/api |
| **CORS Origins** | localhost:5173, localhost:4173 | stock.yarganix.com |
| **SSL** | HTTP | HTTPS обязательно |
| **Логи** | DEBUG | INFO/ERROR |
| **База данных** | Postgres в Docker | Продакшен Postgres |

## 🚨 Безопасность продакшена

1. **Никогда не коммитьте** `.env.production` в git
2. **Используйте сильные пароли** (минимум 16 символов)
3. **Настройте SSL** для HTTPS
4. **Ограничьте доступ** к базе данных по IP
5. **Настройте бэкапы** базы данных
6. **Мониторинг** - подключите Sentry

## 🔍 Мониторинг и логи

```bash
# Просмотр логов продакшена
make prod-logs

# Проверка статуса сервисов
docker ps --filter "label=com.docker.compose.project=warehouse-prod"

# CPU и память
docker stats --filter "label=com.docker.compose.project=warehouse-prod"
```

## 📡 API Endpoints

После развёртывания доступны следующие эндпоинты:

- **Аутентификация**: `POST /api/auth/login`, `POST /api/auth/register`
- **Администрирование**: `GET /api/admin/users`, `POST /api/admin/users`
- **Склад**: `GET /api/v1/warehouses`, `POST /api/v1/stock-movements`
- **Документация**: `GET /docs`, `GET /redoc`

## 🆘 Troubleshooting

### Проблема: CORS ошибки
**Решение**: Проверьте что `FRONTEND_URL` правильно настроен в продакшене

### Проблема: Не работает логин
**Решение**: Проверьте что `JWT_SECRET` одинаковый в продакшене

### Проблема: Нет доступа к БД
**Решение**: Проверьте `DATABASE_URL` и убедитесь что БД доступна

### Проблема: Фронтенд не загружается
**Решение**: Проверьте Nginx конфигурацию и путь к статическим файлам
