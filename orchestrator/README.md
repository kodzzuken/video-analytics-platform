# Orchestrator Service

Микросервис оркестрации - точка координации между API и Runner.

## 🚀 Быстрый старт

### Локально

```bash
cd orchestrator
python -m venv venv
source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt

export DATABASE_URL=postgresql://vap_user:vap_password@localhost:5432/vap_db
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092

python -m orchestrator.main
```

### Docker

```bash
docker build -t vap-orchestrator .
docker run -e DATABASE_URL=postgresql://user:pass@host/db \
           -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
           vap-orchestrator
```

## 📊 Архитектура

### Что она делает

1. **Получает инициализацию** из Kafka топика `init_scenario`
2. **Сохраняет Worker** в таблице workers с статусом `pending`
3. **Отправляет Deploy Order** в Kafka топик `to_deploy`
4. **Обновляет статус** Worker на `deployed`

### Поток данных

```
API (init_scenario topic)
    ↓ (Kafka)
Orchestrator Consumer
    ↓
Create Worker Record
    ↓
Send Deploy Order
    ↓ (Kafka: to_deploy topic)
Runner
```

## 💾 База данных

### workers таблица

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

**Статусы**:
- `pending` - Worker не начал работу
- `deployed` - Deploy order сохранен
- `running` - Process работает
- `failed` - Ошибка запуска
- `stopped` - Process остановлен

## 🏗️ Kafka Топики

### Получаемые топикы

**init_scenario**
```json
{
  "scenario_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "camera_url": "rtsp://example.com/stream"
}
```

### Отправляемые топикы

**to_deploy**
```json
{
  "worker_id": "11223344-5566-7788-99aa-bbccddeeeff0",
  "scenario_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "camera_url": "rtsp://example.com/stream"
}
```

## 🔐 Environment Variables

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/vap_db
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
LOG_LEVEL=INFO
CONSUMER_GROUP=orchestrator-group
```

## 🐛 Troubleshooting

| Проблема | Решение |
|----------|----------|
| `Connection refused` (Kafka) | Проверьте KAFKA_BOOTSTRAP_SERVERS |
| `psycopg2.OperationalError` | Проверьте DATABASE_URL |
| Не получает сообщения | Проверьте, что API отправляет в init_scenario |
| Worker не сохраняется | Проверьте таблицу workers в БД |

## 📝 Примечания

- Orchestrator работает в потоке, ожидая сообщения
- Не очистюют Worker с статусом `failed` автоматически
- Каждые worker_id уникальны
