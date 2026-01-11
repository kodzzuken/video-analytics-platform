# Video Analytics Platform (VAP)

Распределённая платформа анализа видеопотоков с управлением сценариями, оркестрацией и инференсом.

## 📋 Архитектура

┌─────────────────────────────────────────────────────────────────┐
│                     EXTERNAL CLIENTS (Users)                    │
│                      HTTP/REST Requests                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        LOAD BALANCER                            │
│                   (Optional in production)                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
  ┌──────────┐         ┌──────────┐         ┌──────────┐
  │   API    │         │   API    │ ...     │   API    │
  │ Instance │         │ Instance │         │ Instance │
  │    #1    │         │    #2    │         │    #N    │
  └────┬─────┘         └────┬─────┘         └────┬─────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌────────────────┐   ┌──────────────┐
│   PostgreSQL │   │  Apache Kafka  │   │  Redis/Cache │
│   (Primary)  │   │   (3 brokers)  │   │  (Optional)  │
└──────────────┘   └────────────────┘   └──────────────┘
        │                   │
        │                   │
        └───────────┬───────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
        ▼           ▼           ▼
  ┌───────────┐ ┌───────────┐ ┌─────────────┐
  │Orchestr.  │ │Orchestr.  │ │ Orchestr.   │
  │Instance 1 │ │Instance 2 │ │ (Standby)   │
  └───────┬───┘ └───────┬───┘ └─────────────┘
          │             │
          └──────┬──────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
    [Kafka Topics:]
    - to_deploy
        │
        │ (Multiple Consumers)
        │
  ┌─────┴─────┬─────┬─────┬─────┐
  │     │     │     │     │     │
  ▼     ▼     ▼     ▼     ▼     ▼
┌─────────────────────────────────────┐
│   Runner Service (1 Instance)       │
│   ├── Consumer Thread (Blocking)    │
│   ├── WorkerManager (State)         │
│   └── Worker Processes Pool:        │
│       ├── Process #1 (Video 1)      │
│       ├── Process #2 (Video 2)      │
│       ├── Process #3 (Video 3)      │
│       └── MAX_WORKERS limit         │
└─────────────────────────────────────┘
          │
          │ Results published to Kafka
          ▼
      [results topic]
          │
  ┌───────┴────────┐
  │                │
  ▼                ▼
(Read by)      (Read by)
API Inbox      Monitoring
Consumer       System
  │
  ▼
PostgreSQL
scenario_results


## 🏗️ Компоненты

### 1. **API Service** (`api/`)
- `POST /api/v1/scenario/init` - инициализация нового сценария
- `GET /api/v1/prediction/{scenario_uuid}` - получение результатов
- Использует Outbox паттерн для гарантированной доставки сообщений
- Сохраняет сценарии в PostgreSQL

**Таблицы:**
- `scenarios` - информация о сценариях
- `outbox_scenario` - очередь для Kafka (transactional)
- `scenario_results` - результаты предсказаний

### 2. **Orchestrator Service** (`orchestrator/`)
- Читает `init_scenario` топик из Kafka
- Регистрирует воркеров в таблице `workers`
- Публикует в `to_deploy` топик информацию о развёртывании

**Таблицы:**
- `workers` - статус и информация о воркерах (url, scenario_uuid, status)

### 3. **Runner/Inference Service** (`runner/`)
- Читает `to_deploy` топик
- Создаёт новый **Process** (multiprocessing) для каждого сценария
- Подключается к видеопотоку по URL
- Выполняет инференс (mock detection)
- Публикует результаты в `results` топик

## 🚀 Быстрый старт

### Требования
- Python 3.9+
- PostgreSQL 12+
- Kafka 3.0+
- Docker & Docker Compose (опционально)

### Использование Docker Compose

```bash
# Запуск всей инфраструктуры
docker-compose up -d

# Просмотр логов
docker-compose logs -f api
docker-compose logs -f orchestrator
docker-compose logs -f runner

# Остановка
docker-compose down
```

### Запуск локально (без Docker)

#### 1. PostgreSQL & Kafka

```bash
# PostgreSQL
docker run -d -p 5432:5432 \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=vap_db \
  postgres:15

# Kafka (требует Zookeeper)
docker run -d -p 9092:9092 -e KAFKA_ZOOKEEPER_CONNECT=localhost:2181 confluentinc/cp-kafka:7.5.0
```

#### 2. API Service

```bash
cd api
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или venv\Scripts\activate (Windows)
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Endpoint: `http://localhost:8000/docs` (Swagger UI)

#### 3. Orchestrator Service

```bash
cd orchestrator
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m orchestrator.main
```

#### 4. Runner/Inference Service

```bash
cd runner
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m runner.main
```

## 📊 System Specification

### Жизненный цикл сценария

```
State Transitions:
init_startup → in_startup_processing → active → init_shutdown → in_shutdown_processing → inactive
```

### Статусы

| Статус | Описание |
|--------|---------|
| `init_startup` | Инициализация запуска сценария |
| `in_startup_processing` | Процесс запуска в progress |
| `active` | Сценарий активен, выполняется инференс |
| `init_shutdown` | Инициализация остановки |
| `in_shutdown_processing` | Процесс остановки в progress |
| `inactive` | Сценарий неактивен |

### Kafka Топики

| Топик | Направление | Структура |
|-------|-----------|-----------|
| `init_scenario` | API → Orchestrator | `{scenario_uuid, camera_url}` |
| `to_deploy` | Orchestrator → Runner | `{scenario_uuid, camera_url, worker_id}` |
| `results` | Runner → API | `{scenario_uuid, frame_number, detections, timestamp}` |

### Таблицы БД

#### scenarios
```sql
CREATE TABLE scenarios (
  id SERIAL PRIMARY KEY,
  scenario_uuid UUID UNIQUE NOT NULL,
  camera_url TEXT NOT NULL,
  status VARCHAR(50) NOT NULL DEFAULT 'init_startup',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

#### outbox_scenario
```sql
CREATE TABLE outbox_scenario (
  id SERIAL PRIMARY KEY,
  scenario_uuid UUID NOT NULL,
  payload JSONB NOT NULL,
  published BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);
```

#### scenario_results
```sql
CREATE TABLE scenario_results (
  id SERIAL PRIMARY KEY,
  scenario_uuid UUID NOT NULL,
  frame_number INTEGER NOT NULL,
  detections JSONB NOT NULL,
  timestamp TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
```

#### workers
```sql
CREATE TABLE workers (
  id SERIAL PRIMARY KEY,
  worker_id UUID UNIQUE NOT NULL,
  scenario_uuid UUID NOT NULL,
  camera_url TEXT NOT NULL,
  status VARCHAR(50) NOT NULL DEFAULT 'pending',
  process_pid INTEGER,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

## 🧪 Testing Guide

### 1. Unit Tests

```bash
# API tests
cd api && pytest tests/

# Orchestrator tests
cd orchestrator && pytest tests/

# Runner tests
cd runner && pytest tests/
```

### 2. Integration Tests

```bash
# Полный flow тест (требует запущенные сервисы)
cd tests && pytest integration_tests/
```

### 3. Manual Testing

#### Создание сценария

```bash
curl -X POST http://localhost:8000/api/v1/scenario/init \
  -H "Content-Type: application/json" \
  -d '{
    "camera_url": "rtsp://example.com/stream"
  }'

# Ответ:
# {
#   "scenario_uuid": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "init_startup"
# }
```

#### Получение результатов

```bash
curl http://localhost:8000/api/v1/prediction/550e8400-e29b-41d4-a716-446655440000

# Ответ:
# {
#   "scenario_uuid": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "active",
#   "results": [
#     {
#       "frame_number": 1,
#       "detections": [{"class": "person", "confidence": 0.95, "bbox": [10, 20, 100, 150]}],
#       "timestamp": "2026-01-11T16:30:00Z"
#     }
#   ]
# }
```

### 4. Kafka Monitoring

```bash
# Просмотр топиков
kafka-topics --bootstrap-server localhost:9092 --list

# Консьюм топика
kafka-console-consumer --bootstrap-server localhost:9092 --topic init_scenario --from-beginning

# Produce сообщение (debug)
kafka-console-producer --bootstrap-server localhost:9092 --topic to_deploy
```

## 📁 Структура проекта

```
video-analytics-platform/
├── api/                          # API Service
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI приложение
│   │   ├── config.py            # Конфигурация
│   │   ├── database.py          # SQLAlchemy setup
│   │   ├── models.py            # ORM модели
│   │   ├── schemas.py           # Pydantic схемы
│   │   ├── routes.py            # API endpoints
│   │   ├── services.py          # Бизнес-логика
│   │   └── kafka_producer.py    # Kafka интеграция
│   ├── tests/
│   ├── requirements.txt
│   ├── .env.example
│   ├── Dockerfile
│   └── README.md
│
├── orchestrator/                 # Orchestrator Service
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   ├── main.py              # Точка входа
│   │   ├── config.py            # Конфигурация
│   │   ├── database.py          # SQLAlchemy setup
│   │   ├── models.py            # ORM модели
│   │   ├── kafka_consumer.py    # Kafka консьюмер
│   │   └── orchestrator_logic.py # Основная логика
│   ├── tests/
│   ├── requirements.txt
│   ├── .env.example
│   ├── Dockerfile
│   └── README.md
│
├── runner/                       # Runner/Inference Service
│   ├── runner/
│   │   ├── __init__.py
│   │   ├── main.py              # Точка входа
│   │   ├── config.py            # Конфигурация
│   │   ├── kafka_consumer.py    # Kafka консьюмер
│   │   ├── video_processor.py   # Обработка видеопотока
│   │   ├── inference.py         # Mock inference модель
│   │   └── worker.py            # Process wrapper
│   ├── tests/
│   ├── requirements.txt
│   ├── .env.example
│   ├── Dockerfile
│   └── README.md
│
├── docker-compose.yml            # Полная инфраструктура
├── tests/
│   └── integration_tests/
├── .gitignore
└── README.md
```

## 🔄 Гарантии доставки

### Outbox Pattern (API → Kafka)
- Запись в `scenarios` и `outbox_scenario` выполняется в одной транзакции
- Отдельный сервис читает `outbox_scenario` и публикует в Kafka
- После успешной публикации запись помечается как `published=true`

### Идемпотентный Inbox (Kafka → API)
- Каждое сообщение имеет уникальный ID
- Проверка на дубликат перед обработкой
- Результаты хранятся с `scenario_uuid` как ключом уникальности

## 📝 Демонстрация преподавателю

### Сценарий демо (5-10 минут)

1. **Запуск инфраструктуры** (30 сек)
   ```bash
   docker-compose up -d
   docker-compose ps  # Проверить, что все сервисы запущены
   ```

2. **Создание сценария** (1 мин)
   ```bash
   curl -X POST http://localhost:8000/api/v1/scenario/init \
     -H "Content-Type: application/json" \
     -d '{"camera_url": "rtsp://example.com/stream"}'
   ```

3. **Мониторинг потока данных** (2-3 мин)
   - Kafka: просмотр сообщений в топиках
   - PostgreSQL: проверка таблиц
   - Логи: просмотр работы сервисов

4. **Получение результатов** (1 мин)
   ```bash
   curl http://localhost:8000/api/v1/prediction/{scenario_uuid}
   ```

5. **Остановка сценария** (1 мин)
   ```bash
   curl -X POST http://localhost:8000/api/v1/scenario/{scenario_uuid}/shutdown
   ```

### Что демонстрирует

✅ Асинхронная обработка (Kafka)  
✅ Управление жизненным циклом (State Machine)  
✅ Масштабируемость (multiprocessing)  
✅ Reliability (Transactional Outbox, идемпотентный Inbox)  
✅ Микросервисная архитектура  
✅ Полная трассировка данных

## 🛠️ Troubleshooting

| Проблема | Решение |
|----------|---------|
| `Connection refused` (Kafka) | Проверить, что Kafka запущена: `docker ps` |
| `psycopg2.OperationalError` | Проверить PostgreSQL: `docker logs postgres` |
| `ModuleNotFoundError` | Установить зависимости: `pip install -r requirements.txt` |
| Worker не запускается | Проверить URL видеопотока, смотреть логи runner |
| Результаты не появляются | Проверить логи orchestrator и runner, Kafka топики |

## 📚 Дополнительная документация

- [API Documentation](api/README.md)
- [Orchestrator Documentation](orchestrator/README.md)
- [Runner Documentation](runner/README.md)

## 🔐 Переменные окружения

Все сервисы используют `.env` файлы. Примеры в каждой папке сервиса.

```env
DATABASE_URL=postgresql://user:password@localhost:5432/vap_db
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
LOG_LEVEL=INFO
```

## 📄 Лицензия

MIT

---

**Разработано для курса по распределённым системам**
