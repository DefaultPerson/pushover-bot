<p align="center">
  <img src="assets/header.png" alt="Pushover Bot" />
</p>

<p align="center">
  <a href="https://t.me/PushoverABot">@PushoverABot</a>
</p>

> **Warning:** Бот находится в процессе разработки. История сообщений и настройки могут быть сброшены.

## Описание

Telegram-бот для доставки emergency-уведомлений через [Pushover](https://pushover.net/). Разбудит вас сиреной, даже если звук на телефоне выключен. Добавьте бота в группу — и любой участник сможет отправить экстренное уведомление всем или конкретному человеку.

## Privacy Mode

> **Важно:** В BotFather у бота должен быть **выключен** Group Privacy Mode. Иначе бот не получает сообщения в группах, кроме команд и reply. Если privacy mode был включен, нужно удалить бота из группы и добавить заново.

## Возможности

- **Emergency уведомления** — Priority 2, обходят тихие часы, повторяются каждые 30 секунд до подтверждения
- **Групповые чаты** — `/gm` отправляет сирену всем участникам с включенными уведомлениями
- **Таргетированные уведомления** — `/gm @username`, `/gm user_id` или `/gm username`
- **Кастомный текст** — `/gm привет` или `/gm @username wake up`
- **Архивирование сообщений** — сохранение всех сообщений из групп в БД с медиафайлами
- **HTML экспорт** — красивый экспорт архива с поиском и фильтрацией
- **Broadcast** — массовая рассылка для администраторов
- **Rate limiting** — защита от спама
- **Мультиязычность** — русский, английский, украинский

## Быстрый старт

### 1. Получение токенов

**Telegram Bot Token:**
1. Напишите [@BotFather](https://t.me/BotFather)
2. Создайте нового бота: `/newbot`
3. Скопируйте токен

**Pushover App Token:**
1. Зарегистрируйтесь на [pushover.net](https://pushover.net)
2. [Создайте приложение](https://pushover.net/apps/build)
3. Скопируйте **API Token/Key**

### 2. Запуск с Docker Compose (полный стек)

```bash
git clone https://github.com/DefaultPerson/pushover-bot.git
cd pushover-bot

cp .env.example .env
nano .env  # заполните BOT_TOKEN, PUSHOVER_APP_TOKEN, DB_PASSWORD

docker compose -f docker-compose.full.yml up -d
```

`docker-compose.full.yml` поднимает PostgreSQL, Redis и бота — всё в одном.

## Команды бота

### В личных сообщениях

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и инструкция |
| `/key` | Настроить Pushover User Key |
| `/list` | Список групп с уведомлениями |
| `/test_alarm` | Тестовая сирена |
| `/language` | Сменить язык |
| `/help` | Справка |

### В групповых чатах

| Команда | Описание |
|---------|----------|
| `/gm` | Отправить уведомление всем |
| `/gm текст` | Отправить кастомный текст всем |
| `/gm @username` | Отправить конкретному по username |
| `/gm @username текст` | С кастомным текстом |
| `/gm user_id` | По ID |
| `/gm user_id текст` | По ID с кастомным текстом |
| `/enable` | Включить уведомления |
| `/disable` | Выключить уведомления |
| `/test_alarm` | Тестовая сирена себе |
| `/only_admin` | Только админы могут /gm |
| `/language` | Сменить язык группы |

### Администрирование

| Команда | Описание |
|---------|----------|
| `/broadcast` | Массовая рассылка (только для ADMIN_IDS) |
| `/stats` | Статистика бота |

## Развертывание на VPS

Скрипт для быстрого деплоя на чистый VPS (Ubuntu/Debian):

```bash
bash scripts/deploy.sh
```

Скрипт установит Docker (если нет), склонирует репо, создаст `.env` и запустит все сервисы.

## Docker Compose

| Файл | Описание |
|------|----------|
| `docker-compose.yml` | Только бот. Подключается к внешним PostgreSQL и Redis |
| `docker-compose.full.yml` | Полный стек: PostgreSQL + Redis + бот |

## Конфигурация

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `BOT_TOKEN` | Telegram Bot Token | (обязательно) |
| `PUSHOVER_APP_TOKEN` | Pushover Application Token | (обязательно) |
| `DB_HOST` | PostgreSQL host | `localhost` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `DB_NAME` | Database name | `pushover` |
| `DB_USER` | Database user | `bot` |
| `DB_PASSWORD` | Database password | (обязательно) |
| `REDIS_HOST` | Redis host | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `REDIS_DB` | Redis database | `0` |
| `ADMIN_IDS` | Telegram IDs админов (через запятую) | |
| `LOG_LEVEL` | Уровень логирования | `INFO` |
| `GM_RATE_LIMIT` | Макс. вызовов /gm за окно | `3` |
| `GM_RATE_WINDOW` | Окно rate limit в секундах | `300` |
| `ARCHIVE_ENABLED` | Архивировать сообщения | `false` |
| `ARCHIVE_MEDIA_PATH` | Путь для медиа | `archive/media` |

## Архивирование сообщений

Бот может сохранять все сообщения из групп в базу данных.

### Включение

```env
ARCHIVE_ENABLED=true
ARCHIVE_MEDIA_PATH=archive/media
```

### Экспорт архива

```bash
./scripts/export.sh

# Конкретная группа
./scripts/export.sh . --group -1001234567890
```

Результат: `archive.html` + `archive_media/`

## Разработка

### Установка зависимостей

```bash
# aiogram-broadcast из libs/
uv pip install -e ../../libs/aiogram-broadcast

# Основные зависимости
uv pip install -e .
```

### Запуск локально

```bash
make run
```

### Линтинг

```bash
make lint       # проверка
make lint-fix   # автоисправление
```

## Структура проекта

```
pushover-bot/
├── Dockerfile
├── docker-compose.yml
├── docker-compose.full.yml
├── src/
│   ├── main.py
│   ├── config.py
│   ├── bot/
│   │   ├── handlers/
│   │   ├── middlewares/
│   │   ├── keyboards/
│   │   └── filters/
│   ├── services/
│   │   ├── pushover.py
│   │   ├── notification.py
│   │   └── broadcast.py
│   ├── db/
│   │   ├── database.py
│   │   ├── models.py
│   │   └── repositories/
│   └── i18n/
│       └── locales/
├── scripts/
│   ├── deploy.sh
│   ├── export.sh
│   └── export_archive.py
├── migrations/
└── assets/
```
