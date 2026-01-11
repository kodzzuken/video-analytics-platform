# API Service

Микросервис для управления сценариями видеоанализа и получения результатов предсказаний.

## 🚀 Быстрый старт

### Локально

```bash
cd api
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или venv\Scripts\activate (Windows)

pip install -r requirements.txt

# Убедитесь, что PostgreSQL и Kafka запущены
export DATABASE_URL=postgresql://vap_user:vap_password@localhost:5432/vap_db
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092

python -m uvicorn app.main:app --reload --port 8000
```

### Docker

```bash
docker build -t vap-api .
docker run -e DATABASE_URL=postgresql://user:pass@postgres:5432/db \
           -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
           -p 8000:8000 vap-api
```

## 📚 API Endpoints

### 1. Инициализация сценария

**POST** `/api/v1/scenario/init`

Тело запроса:
```json
{
  "camera_url": "rtsp://example.com/stream"
}
```

Ответ (201):
```json
{
  "scenario_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "camera_url": "rtsp://example.com/stream",
  "status": "init_startup",
  "created_at": "2026-01-11T12:30:00Z",
  "updated_at": "2026-01-11T12:30:00Z"
}
```

### 2. Получение информации о сценарии

**GET** `/api/v1/scenario/{scenario_uuid}`

Ответ (200):
```json
{
  "scenario_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "camera_url": "rtsp://example.com/stream",
  "status": "active",
  "created_at": "2026-01-11T12:30:00Z",
  "updated_at": "2026-01-11T12:35:00Z"
}
```

### 3. Получение результатов предсказаний

**GET** `/api/v1/prediction/{scenario_uuid}`

Ответ (200):
```json
{
  "scenario_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "total_frames_processed": 5,
  "results": [
    {
      "frame_number": 1,
      "detections": [
        {
          "class_label": "person",
          "confidence": 0.95,
          "bbox": [10, 20, 100, 150]
        }
      ],
      "timestamp": "2026-01-11T12:30:05Z"
    }
  ]
}
```

## 🏗️ Архитектура

### Компоненты

1. **FastAPI Application** - REST API с асинхронной обработкой
2. **SQLAlchemy ORM** - Работа с PostgreSQL
3. **Kafka Producer** - Отправка сообщений инициализации (transactional outbox)
4. **Kafka Consumer (Inbox)** - Получение результатов от Runner

### Жизненный цикл сценария

```
POST /scenario/init
    ↓
[Transactional Outbox]
  - Сохранить scenario в scenarios
  - Сохранить outbox_scenario
  - Отправить в init_scenario топик
    ↓
Orchestr читает init_scenario
    ↓
Runner получает to_deploy и создает Process
    ↓
Runner отправляет results в результаты топик
    ↓
Inbox Consumer читает results
    ↓
Сохраняет в scenario_results (идемпотентно)
    ↓
GET /prediction/{scenario_uuid} возвращает результаты
```

## 💾 База данных

### Таблицы

#### scenarios
```sql
CREATE TABLE scenarios (
  id SERIAL PRIMARY KEY,
  scenario_uuid UUID UNIQUE NOT NULL,
  camera_url TEXT NOT NULL,
  status VARCHAR(50) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

#### outbox_scenario (Transactional Outbox)
```sql
CREATE TABLE outbox_scenario (
  id SERIAL PRIMARY KEY,
  scenario_uuid UUID NOT NULL,
  payload JSONB NOT NULL,
  published BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW(),
  published_at TIMESTAMP
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
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(scenario_uuid, frame_number)
);
```

## 🔄 Гарантии доставки

### Outbox Pattern (API → Kafka)

1. **Атомарность**: Запись в `scenarios` и `outbox_scenario` в одной транзакции
2. **Гарантия доставки**: Отдельный сервис читает `outbox_scenario` и отправляет в Kafka
3. **Идемпотентность**: После успешной отправки записываем `published=true`

### Idempotent Inbox (Kafka → API)

1. **Уникальный ключ**: `(scenario_uuid, frame_number)` с UNIQUE constraint
2. **Deduplication**: Попытка вставить дубликат приводит к UPDATE
3. **Гарантия обработки**: Все сообщения обрабатываются хотя бы один раз

## 🧪 Тестирование

```bash
# Unit tests
pytest tests/ -v

# Integration tests с Docker Compose
docker-compose up -d
pytest tests/integration/ -v

# Manual testing с curl
curl -X POST http://localhost:8000/api/v1/scenario/init \
  -H "Content-Type: application/json" \
  -d '{"camera_url": "rtsp://example.com/stream"}'
```

## 🔐 Environment Variables

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/vap_db
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
LOG_LEVEL=INFO
DEBUG=False
```

## 📊 Мониторинг

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 🐛 Troubleshooting

| Проблема | Решение |
|----------|----------|
| `Connection refused` | Проверьте, запущены ли PostgreSQL и Kafka |
| `psycopg2.OperationalError` | Проверьте DATABASE_URL и доступ к БД |
| `KafkaError` | Проверьте KAFKA_BOOTSTRAP_SERVERS |
| Результаты не появляются | Проверьте логи Runner и убедитесь, что Inbox Consumer работает |

## 📝 Примечания

- Inbox Consumer запускается в отдельном потоке при старте приложения
- Все UUID хранятся как UUID тип в PostgreSQL для оптимизации
- Детекции хранятся в формате JSONB для гибкой обработки
