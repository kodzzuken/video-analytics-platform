# Video Analytics Platform 

```bash
# 1. Клонировать
git clone https://github.com/kodzzuken/video-analytics-platform.git
cd video-analytics-platform

# 2. Открыть в VS Code
code .

# 3. Запустить проект
docker-compose up -d

# 4. Проверить работу
docker-compose ps
```

## Шаг 1: Клонирование и Подготовка

```bash
# Клонируем репозиторий
git clone https://github.com/kodzzuken/video-analytics-platform.git
cd video-analytics-platform

# Обработаем develop ветку
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

# Открываемся 
open http://localhost:8000/docs
```

## Шаг 3: Экспресс-Объяснение Источник Архитектуры

### Что там работает?

1. **API Service** (:8000)
   - Получает запросы на создание сценариев и сохраняет в PostgreSQL
   - Публикует события в Kafka
   - Потребляет результаты из Kafka

2. **Orchestrator Service**
   - Слушает события создания сценария
   - Отправляет сообщения deploy Runner'ам

3. **Runner Service** (multiprocessing)
   - Слушает задачи на деплой
   - Новый Process на каждый сценарий
   - Читает видео через OpenCV
   - Выполняет inference и публикует результаты

4. **Infrastructure**
   - PostgreSQL - сохранение данных
   - Kafka - асинхронная коммуникация
   - Kafka UI - мониторинг (:8080)

## Шаг 4: Проверка Работы

### Создать Сценарий

```bash
curl -X POST http://localhost:8000/api/v1/scenario/init \
  -H "Content-Type: application/json" \
  -d '{
    "camera_url": "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4"
  }'

# Ответ (сохраните scenario_uuid):
# {
#   "scenario_uuid": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "init_startup",
#   ...
# }
```

Уся готово! Это все работает.
