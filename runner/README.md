# Runner/Inference Service

Микросервис для выполнения инференса на видеопотоках и отправки результатов.

## 🚀 Быстрый старт

### Локально

```bash
cd runner
python -m venv venv
source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt

export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export LOG_LEVEL=INFO
export MAX_WORKERS=4
export VIDEO_FPS=2

python -m runner.main
```

### Docker

```bash
docker build -t vap-runner .
docker run -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
           -e MAX_WORKERS=4 \
           -e VIDEO_FPS=2 \
           vap-runner
```

## 🏗️ Архитектура

### Компоненты

#### 1. **RunnerConsumer**
- Получает мессажи из Kafka топика `to_deploy`
- Отдельный worker process для каждого сценария

#### 2. **WorkerManager**
- Управляет multiprocessing.Process инстанциями
- Ограничивает максимальное количество работающих workerов

#### 3. **Worker Process**
- Подключается к видеопотоку по URL (OpenCV)
- Читает кадры с указанным FPS
- Выполняет inference (мок)
- Публикует результаты в Kafka

#### 4. **VideoProcessor**
- OpenCV библиотека для работы с видео
- Поддерживает RTSP, HTTP, локальные файлы

#### 5. **MockInferenceModel**
- Имитирует реальные детекции
- Легко заменяется на YOLOv5, TensorFlow, и т.д.

### Поток выполнения

```
Kafka: to_deploy topic
    ↓
RunnerConsumer reads message
    ↓
WorkerManager.start_worker()
    ↓
multiprocessing.Process spawned
    ↓
worker_process():
    - VideoProcessor.open(camera_url)
    - For each frame:
        - model.predict(frame)
        - producer.send_result(detections)
    ↓
Kafka: results topic
    ↓
API Inbox receives result
```

## 💾 Гарантии масштабируемости

### Один сценарий = Один Process

- **Каждый сценарий запускается в отдельном Process** (NOT coroutine/thread)
- Не бывает дубликатных заданий для одного сценария
- Целостность данных и ресурсов

### Контроль конкурренции

- **MAX_WORKERS** граница до ОН-Офф воркеров одновременно
- Преовы будут дожидаться свободных worker slot
- CPU-bound оптимизация автоматическая

## 🏗️ Kafka Топики

### Получаемые топикы

**to_deploy**
```json
{
  "worker_id": "11223344-5566-7788-99aa-bbccddeeeff0",
  "scenario_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "camera_url": "rtsp://example.com/stream"
}
```

### Отправляемые топикы

**results**
```json
{
  "scenario_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "frame_number": 1,
  "detections": [
    {
      "class": "person",
      "confidence": 0.95,
      "bbox": [10, 20, 100, 150]
    }
  ],
  "timestamp": "2026-01-11T12:30:05.123Z"
}
```

## 🔐 Environment Variables

```env
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
LOG_LEVEL=INFO
CONSUMER_GROUP=runner-group
MAX_WORKERS=4          # Макс одновременных workerов
VIDEO_FPS=2            # Целевая FPS для экспорта кадров
```

## 🧪 Тестирование

### Unit tests

```bash
pytest tests/ -v
```

### Manual testing

```bash
# Мониторинг results топика
kafka-console-consumer --bootstrap-server localhost:9092 --topic results --from-beginning
```

## 🔄 Testing Video URLs

### Local file (for testing)

```bash
# Скачай тестовый видео
# и используй формат: file:///path/to/video.mp4
```

### RTSP stream

```bash
# тест ртсп способности:
rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4
```

### HTTP stream

```bash
# MJPEG и другие HTTP потоки
http://example.com/stream.mjpg
```

## 🐛 Troubleshooting

| Проблема | Решение |
|----------|----------|
| `Failed to open video` | Проверьте URL видео, ассе к OpenCV |
| `ModuleNotFoundError: cv2` | `pip install opencv-python` |
| `Connection refused` (Kafka) | Проверьте KAFKA_BOOTSTRAP_SERVERS |
| Worker отказывается | Может быть реачы граница MAX_WORKERS |
| Результаты не появляются | Проверьте логи runner, консумируются ли мессажи из to_deploy |

## 📚 Примечания

### Почему multiprocessing?

- **GIL в Python**: Треады не дадут трудов для CPU-intensive задачи (inference)
- **Process isolation**: Каждый сценарий от OpenCV вытягивают ресурсы
- **True parallelism**: Несколько workerов работают на всех CPU ядрах

### Формат результата

Каждая детекция:
```python
{
    "class": "person",        # Тип объекта
    "confidence": 0.95,       # Уверенность (0.0-1.0)
    "bbox": [x_min, y_min, x_max, y_max]  # Координаты в пикселах
}
```

### Поддерживаемые видеоформаты

- RTSP streams (IP cameras)
- HTTP/MJPEG streams
- Local MP4, AVI, MKV files
- Любые форматы, на которые ответит OpenCV
