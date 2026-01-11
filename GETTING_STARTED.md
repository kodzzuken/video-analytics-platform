# Video Analytics Platform - Он Начинающих

## Шаг 1: Клонирование и Подготовка

```bash
# Клонируем репозиторий
git clone https://github.com/kodzzuken/video-analytics-platform.git
cd video-analytics-platform

# Обработтаем develop ветки
git checkout develop
```

## Шаг 2: запуск под Docker (Recommended)

```bash
# Установка Docker & Docker Compose
# macOS: brew install docker docker-compose
# Linux: apt-get install docker.io docker-compose
# Windows: https://docs.docker.com/desktop/install/windows-install/

# Генерируем всю инфраструктуру
docker-compose up -d

# Проверяем сервисы
docker-compose ps

# Открываемся Кай API
open http://localhost:8000/docs
```

## Шаг 3: Экспресс-Объяснение Источник Архитектуры

### Что там работает?

1. **API Service** (:8000)
   - Получает запросы составить сценарии и сохраняет в PostgreSQL
   - Публикует эвенты в Kafka
   - Консюмирует результаты из Kafka

2. **Orchestrator Service**
   - Нслушивает эвенты составить сценариа
   - Пооправляет мессажи деволи Runnerсам

3. **Runner Service** (multiprocessing)
   - Нслушивает денотивания
   - Новое Process на сценарий
   - Читает видео OpenCV
   - Выполняет inference и публикует результаты

4. **Infrastructure**
   - PostgreSQL - сохранение данных
   - Kafka - асинхронная коммуникация
   - Kafka UI - мониторинг (:8080)

## Шаг 4: Проверка Работы

### Кратить Сценарий

```bash
curl -X POST http://localhost:8000/api/v1/scenario/init \
  -H "Content-Type: application/json" \
  -d '{
    "camera_url": "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4"
  }'

# Ответ (сохранят scenario_uuid):
# {
#   "scenario_uuid": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "init_startup",
#   ...
# }
```

### Мониторинг

```bash
# Просмотр логов
docker-compose logs -f api
docker-compose logs -f orchestrator
docker-compose logs -f runner

# Kafka UI
open http://localhost:8080

# Цдравнять топики
docker exec vap-kafka kafka-topics \
  --bootstrap-server localhost:9092 --list
```

### Получить Результаты

```bash
curl http://localhost:8000/api/v1/prediction/550e8400-e29b-41d4-a716-446655440000
```

## Шаг 5: результатов

```bash
# Настройка всех сервисов
docker-compose down

# Поровыренно важные темы:
# - Маркерования жизненных циклов
# - Transactional Outbox
# - Idempotent Inbox
# - Multiprocessing scaling
# - Full asynchronous flow
```

## Устранение Неполадок

### Экраны Видинычные

```bash
# Превраю проблемы с PostgreSQL?
docker logs vap-postgres

# Kafka не стартует?
docker logs vap-kafka

# API не отвечает?
curl http://localhost:8000/health
```

## Настройки Всех Параметров

См респективные энвиронмент вариаблес:

- `api/.env` - API конфигурация
- `orchestrator/.env` - Orchestrator конфигурация
- `runner/.env` - Runner конфигурация

## Наслия Скрипты

```bash
# Полные тесты
python tests/integration_tests.py

# Cleanup
docker-compose down -v  # Очистить томас
```

## Формат Папки

```
video-analytics-platform/
├── api/                    → API Service
├── orchestrator/            → Orchestrator Service  
├── runner/                 → Runner/Inference Service
├── docker-compose.yml      → Infrastructure
├── init_db.sql             → Database setup
├── tests/                  → Integration tests
└── README.md               → Полная документация
```

Уся готово! Это все работает.
