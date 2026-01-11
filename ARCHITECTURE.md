# Video Analytics Platform - Детальная Архитектура

## Оглавление
1. [Общая архитектура системы](#общая-архитектура-системы)
2. [API Service - Подробно](#api-service---подробно)
3. [Orchestrator Service - Подробно](#orchestrator-service---подробно)
4. [Runner Service - Подробно](#runner-service---подробно)
5. [Kafka Integration](#kafka-integration)
6. [PostgreSQL Schema](#postgresql-schema)
7. [Reliability Patterns](#reliability-patterns)
8. [State Machines](#state-machines)
9. [Execution Flows](#execution-flows)
10. [Error Handling](#error-handling)

---

## Общая архитектура системы

### Уровни системы

```
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
```

### Компоненты системы

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          SYSTEM COMPONENTS                               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  API SERVICE (FastAPI)                                                  │
│  ├─ HTTP Server (port 8000)                                             │
│  ├─ Request Handler (async)                                             │
│  ├─ SQLAlchemy ORM Layer                                                │
│  ├─ Kafka Producer (Outbox)                                             │
│  ├─ Inbox Consumer Thread                                               │
│  │  └─ Kafka Consumer (results topic)                                   │
│  └─ PostgreSQL Connector Pool                                           │
│                                                                          │
│  ORCHESTRATOR SERVICE (Python)                                          │
│  ├─ Kafka Consumer (init_scenario topic)                                │
│  ├─ Consumer Thread (blocking loop)                                     │
│  ├─ SQLAlchemy ORM Layer                                                │
│  ├─ Kafka Producer (to_deploy topic)                                    │
│  └─ PostgreSQL Connector Pool                                           │
│                                                                          │
│  RUNNER SERVICE (Python)                                                │
│  ├─ Kafka Consumer (to_deploy topic)                                    │
│  ├─ Consumer Thread (blocking loop)                                     │
│  ├─ WorkerManager                                                        │
│  │  └─ Process Pool Management                                          │
│  │     ├─ Track active processes                                        │
│  │     ├─ Enforce MAX_WORKERS limit                                     │
│  │     └─ Handle process lifecycle                                      │
│  ├─ Worker Process Template                                             │
│  │  ├─ VideoProcessor (OpenCV)                                          │
│  │  │  ├─ cv2.VideoCapture                                              │
│  │  │  ├─ Frame extraction with FPS control                             │
│  │  │  └─ Stream management                                             │
│  │  ├─ InferenceModel (Mock)                                            │
│  │  │  ├─ Detection generation                                          │
│  │  │  └─ Confidence scoring                                            │
│  │  └─ Kafka Producer (results topic)                                   │
│  └─ PostgreSQL Connector Pool (per-process)                             │
│                                                                          │
│  DATABASE LAYER (PostgreSQL)                                            │
│  ├─ Connection Pool                                                      │
│  │  ├─ Min connections: 10                                              │
│  │  └─ Max connections: 50                                              │
│  ├─ Table: scenarios                                                    │
│  ├─ Table: outbox_scenario (Transactional Outbox)                       │
│  ├─ Table: scenario_results (Results Storage)                           │
│  ├─ Table: workers (Worker Tracking)                                    │
│  └─ Indices for fast queries                                            │
│                                                                          │
│  MESSAGE BROKER (Apache Kafka)                                          │
│  ├─ Zookeeper Coordination                                              │
│  ├─ Broker 1 (Leader)                                                   │
│  ├─ Broker 2 (Replica)                                                  │
│  ├─ Broker 3 (Replica)                                                  │
│  ├─ Topic: init_scenario                                                │
│  │  ├─ Partitions: 3 (for parallelism)                                  │
│  │  └─ Replication factor: 3                                            │
│  ├─ Topic: to_deploy                                                    │
│  │  ├─ Partitions: 3                                                    │
│  │  └─ Replication factor: 3                                            │
│  └─ Topic: results                                                      │
│     ├─ Partitions: 3                                                    │
│     └─ Replication factor: 3                                            │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## API Service - Подробно

### Архитектура API Service

```
┌─────────────────────────────────────────────────────────────────┐
│                         HTTP Request                            │
│                    (e.g., POST /scenario/init)                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Application                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                     routes.py                          │   │
│  │  ├─ @app.post("/api/v1/scenario/init")                │   │
│  │  │  └─ init_scenario(request: ScenarioInitRequest)    │   │
│  │  │     ├─ Validate request                            │   │
│  │  │     ├─ Call ScenarioService.init_scenario()        │   │
│  │  │     └─ Return ScenarioResponse (200 OK)            │   │
│  │  │                                                     │   │
│  │  ├─ @app.get("/api/v1/scenario/{uuid}")               │   │
│  │  │  └─ get_scenario(uuid: str, db: Session)           │   │
│  │  │     ├─ Query DB                                    │   │
│  │  │     └─ Return ScenarioResponse                     │   │
│  │  │                                                     │   │
│  │  └─ @app.get("/api/v1/prediction/{uuid}")             │   │
│  │     └─ get_predictions(uuid: str, db: Session)        │   │
│  │        ├─ Query scenario                              │   │
│  │        ├─ Query all results for scenario              │   │
│  │        └─ Return PredictionResponse                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                             │                                  │
│                             ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    services.py                         │   │
│  │                  ScenarioService                       │   │
│  │  ├─ init_scenario(db, request)                         │   │
│  │  │  ├─ Generate UUID for scenario                      │   │
│  │  │  ├─ BEGIN TRANSACTION:                              │   │
│  │  │  │  ├─ INSERT INTO scenarios (...)                  │   │
│  │  │  │  ├─ db.flush() [ensure written]                 │   │
│  │  │  │  ├─ INSERT INTO outbox_scenario (...)            │   │
│  │  │  │  ├─ db.commit() [one transaction]                │   │
│  │  │  ├─ END TRANSACTION                                 │   │
│  │  │  ├─ kafka_producer.send_init_scenario()             │   │
│  │  │  ├─ Mark outbox as published=true                   │   │
│  │  │  └─ Return scenario_uuid                            │   │
│  │  │                                                     │   │
│  │  ├─ get_scenario(db, uuid)                             │   │
│  │  │  └─ Query: SELECT * FROM scenarios WHERE uuid=?    │   │
│  │  │                                                     │   │
│  │  ├─ get_predictions(db, uuid)                          │   │
│  │  │  ├─ Query scenario                                 │   │
│  │  │  ├─ Query: SELECT * FROM scenario_results ...      │   │
│  │  │  ├─ Build FrameResult objects                      │   │
│  │  │  └─ Return PredictionResponse                      │   │
│  │  │                                                     │   │
│  │  └─ save_result(db, scenario_uuid, frame_number, ...) │   │
│  │     ├─ Check if result exists (idempotent)            │   │
│  │     ├─ IF EXISTS: UPDATE detections                   │   │
│  │     ├─ IF NOT: INSERT new result                      │   │
│  │     └─ db.commit()                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                             │                                  │
│                             ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  database.py                           │   │
│  │  ├─ SessionLocal() - DB Session Factory                │   │
│  │  ├─ get_db() - Dependency for routes                   │   │
│  │  └─ Base - SQLAlchemy declarative base                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                             │                                  │
│                             ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   models.py                            │   │
│  │  ├─ class Scenario(Base)                               │   │
│  │  │  ├─ id (PK)                                         │   │
│  │  │  ├─ scenario_uuid (UNIQUE)                          │   │
│  │  │  ├─ camera_url                                      │   │
│  │  │  ├─ status                                          │   │
│  │  │  ├─ created_at                                      │   │
│  │  │  └─ updated_at                                      │   │
│  │  │                                                     │   │
│  │  ├─ class OutboxScenario(Base)                         │   │
│  │  │  ├─ id (PK)                                         │   │
│  │  │  ├─ scenario_uuid                                   │   │
│  │  │  ├─ payload (JSONB)                                 │   │
│  │  │  ├─ published (Boolean)                             │   │
│  │  │  ├─ created_at                                      │   │
│  │  │  └─ published_at                                    │   │
│  │  │                                                     │   │
│  │  └─ class ScenarioResult(Base)                         │   │
│  │     ├─ id (PK)                                         │   │
│  │     ├─ scenario_uuid                                   │   │
│  │     ├─ frame_number                                    │   │
│  │     ├─ detections (JSONB)                              │   │
│  │     ├─ timestamp                                       │   │
│  │     ├─ created_at                                      │   │
│  │     └─ UNIQUE(scenario_uuid, frame_number)             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                             │                                  │
│                             ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 schemas.py (Pydantic)                  │   │
│  │  ├─ ScenarioInitRequest                                │   │
│  │  │  └─ camera_url: str                                 │   │
│  │  │                                                     │   │
│  │  ├─ ScenarioResponse                                   │   │
│  │  │  ├─ scenario_uuid: UUID                             │   │
│  │  │  ├─ camera_url: str                                 │   │
│  │  │  ├─ status: str                                     │   │
│  │  │  ├─ created_at: datetime                            │   │
│  │  │  └─ updated_at: datetime                            │   │
│  │  │                                                     │   │
│  │  ├─ DetectionResult                                    │   │
│  │  │  ├─ class_label: str                                │   │
│  │  │  ├─ confidence: float                               │   │
│  │  │  └─ bbox: List[float] (x_min, y_min, x_max, y_max) │   │
│  │  │                                                     │   │
│  │  ├─ FrameResult                                        │   │
│  │  │  ├─ frame_number: int                               │   │
│  │  │  ├─ detections: List[DetectionResult]               │   │
│  │  │  └─ timestamp: datetime                             │   │
│  │  │                                                     │   │
│  │  └─ PredictionResponse                                 │   │
│  │     ├─ scenario_uuid: UUID                             │   │
│  │     ├─ status: str                                     │   │
│  │     ├─ total_frames_processed: int                     │   │
│  │     └─ results: List[FrameResult]                      │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐  ┌──────────────┐   ┌──────────────────────┐
│ PostgreSQL   │  │ Kafka        │   │ Inbox Consumer       │
│              │  │ (init_scen.) │   │ (Thread)             │
│ Transaction: │  │              │   │ ├─ Kafka Consumer    │
│ ├─ scenarios │  │ Produce:     │   │ ├─ results topic     │
│ ├─ outbox_..│  │ {            │   │ └─ Save results      │
│ └─ committed │  │   uuid,      │   │    to scenario_..    │
│              │  │   camera_url │   │    table             │
└──────────────┘  │ }            │   └──────────────────────┘
                  └──────────────┘
```

### API Request/Response Flow

```
1. POST /api/v1/scenario/init
   Request Body:
   {
     "camera_url": "rtsp://example.com/stream"
   }
   
   ↓ (validate via ScenarioInitRequest schema)
   
   ↓ (call ScenarioService.init_scenario)
   
   ↓ BEGIN TRANSACTION:
     INSERT INTO scenarios VALUES (
       id = AUTO_INCREMENT,
       scenario_uuid = UUID('550e8400-e29b-41d4-a716-446655440000'),
       camera_url = 'rtsp://example.com/stream',
       status = 'init_startup',
       created_at = NOW(),
       updated_at = NOW()
     )
     
     INSERT INTO outbox_scenario VALUES (
       id = AUTO_INCREMENT,
       scenario_uuid = UUID('550e8400-e29b-41d4-a716-446655440000'),
       payload = '{"scenario_uuid": "...", "camera_url": "..."}',
       published = false,
       created_at = NOW()
     )
   COMMIT TRANSACTION
   
   ↓ (outside transaction)
   
   ↓ kafka_producer.send_init_scenario(
       "550e8400-e29b-41d4-a716-446655440000",
       "rtsp://example.com/stream"
     )
   
   ↓ (KafkaProducer.send to 'init_scenario' topic)
   
   ↓ Update outbox:
     UPDATE outbox_scenario SET
       published = true,
       published_at = NOW()
     WHERE scenario_uuid = '550e8400-e29b-41d4-a716-446655440000'
   
   ↓ Return HTTP 200:
   {
     "scenario_uuid": "550e8400-e29b-41d4-a716-446655440000",
     "camera_url": "rtsp://example.com/stream",
     "status": "init_startup",
     "created_at": "2026-01-11T16:30:00Z",
     "updated_at": "2026-01-11T16:30:00Z"
   }
```

### Inbox Consumer (Background Thread)

```
┌─────────────────────────────────────────────────────────────┐
│          InboxConsumer (runs on startup_event)             │
│          ├─ Thread #1 (Main thread): FastAPI               │
│          └─ Thread #2 (Daemon): Inbox Consumer             │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│         KafkaConsumer(group_id='api-inbox-group')          │
│  ├─ bootstrap_servers = ['kafka:9092']                     │
│  ├─ topics = ['results']                                   │
│  ├─ auto_offset_reset = 'earliest'                         │
│  ├─ enable_auto_commit = True                              │
│  └─ session_timeout_ms = 30000                             │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────┐
              │   Infinite Loop:         │
              │   for message in consumer│
              └──────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────────────┐
              │   Parse Kafka Message:               │
              │   {                                  │
              │     "scenario_uuid": "...",          │
              │     "frame_number": 1,               │
              │     "detections": [...],             │
              │     "timestamp": "2026-01-11T...Z"   │
              │   }                                  │
              └──────────────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────────────┐
              │   Validate Message                   │
              │   ├─ Check scenario_uuid not null    │
              │   ├─ Check frame_number not null     │
              │   └─ Check timestamp present         │
              └──────────────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────────────┐
              │   Try SAVE Result (Idempotent):      │
              │                                      │
              │   TRY:                               │
              │     db.session.add(ScenarioResult(   │
              │       scenario_uuid = ...,           │
              │       frame_number = ...,            │
              │       detections = [...],            │
              │       timestamp = ...                │
              │     ))                               │
              │     db.commit()                      │
              │                                      │
              │   CATCH UniqueViolation:             │
              │     (frame already exists)           │
              │     result = db.query(...).first()   │
              │     result.detections = new_data     │
              │     result.timestamp = new_time      │
              │     db.commit() # UPDATE             │
              └──────────────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────────────┐
              │   Continue Loop (fetch next message) │
              └──────────────────────────────────────┘
```

---

## Orchestrator Service - Подробно

### Архитектура Orchestrator

```
┌──────────────────────────────────────────────────────────┐
│        Orchestrator Service Startup                      │
│  ├─ Load config from .env                               │
│  ├─ Create SQLAlchemy engine                            │
│  ├─ Create table: workers                               │
│  └─ Start OrchestratorService()                          │
└──────────────────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│   KafkaConsumer(topic='init_scenario')                  │
│  ├─ bootstrap_servers = ['kafka:9092']                  │
│  ├─ group_id = 'orchestrator-group'                     │
│  ├─ auto_offset_reset = 'earliest'                      │
│  ├─ enable_auto_commit = True                           │
│  └─ Infinite blocking loop                              │
└──────────────────────────────────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │   Receive init_scenario msg: │
              │   {                          │
              │     "scenario_uuid": "...",  │
              │     "camera_url": "rtsp://" │
              │   }                          │
              └──────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │   process_scenario()         │
              │                              │
              │   ├─ Generate worker_id      │
              │   │  (UUID)                  │
              │   │                          │
              │   ├─ BEGIN:                  │
              │   │   INSERT INTO workers    │
              │   │   VALUES (               │
              │   │     worker_id,           │
              │   │     scenario_uuid,       │
              │   │     camera_url,          │
              │   │     status='pending',    │
              │   │     created_at=NOW()     │
              │   │   )                      │
              │   │   db.commit()            │
              │   │                          │
              │   ├─ kafka_producer.send(   │
              │   │   topic='to_deploy',     │
              │   │   {                      │
              │   │     worker_id,           │
              │   │     scenario_uuid,       │
              │   │     camera_url           │
              │   │   }                      │
              │   │ )                        │
              │   │                          │
              │   ├─ UPDATE workers SET      │
              │   │   status='deployed'      │
              │   │ WHERE worker_id=?        │
              │   │ db.commit()              │
              │   │                          │
              │   └─ log("Sent deploy")     │
              │                              │
              └──────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │   Continue listening         │
              │   (next message or timeout)  │
              └──────────────────────────────┘
```

### Worker Lifecycle

```
Database (workers table):
┌─────────────────────────────────────────────────────────┐
│ id │ worker_id │ scenario_uuid │ camera_url │ status    │
├────┼───────────┼───────────────┼────────────┼───────────┤
│ 1  │ UUID-1    │ SCENARIO-1    │ rtsp://... │ pending   │ ← Created
│    │           │               │            │ deployed  │ ← Updated
│    │           │               │            │ running   │ ← Will be set by Runner
│    │           │               │            │ stopped   │ ← Final state
│    │           │               │            │ failed    │ ← On error
└────┴───────────┴───────────────┴────────────┴───────────┘

Status Transitions:
pending → deployed → running → stopped/failed
         ^          ^
         │          └─ Orchestrator sends to_deploy
         └─ Worker created in DB
```

---

## Runner Service - Подробно

### Архитектура Runner

```
┌────────────────────────────────────────────────────────────┐
│            Runner Service Initialization                  │
│  ├─ Load config (MAX_WORKERS, VIDEO_FPS, etc)            │
│  ├─ Create KafkaConsumer(topic='to_deploy')              │
│  ├─ Create WorkerManager(max_workers=4)                  │
│  └─ Set up signal handlers                               │
└────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────┐
│   KafkaConsumer Loop (Main Thread - BLOCKING)            │
│                                                           │
│   ├─ Consumer group: 'runner-group'                       │
│   ├─ Topics: ['to_deploy']                                │
│   ├─ Partition assignment: Auto                           │
│   └─ Infinite loop:                                       │
│       while True:                                         │
│           for message in consumer:                        │
│               payload = message.value                     │
│               worker_id = payload['worker_id']            │
│               scenario_uuid = payload['scenario_uuid']    │
│               camera_url = payload['camera_url']          │
│               ↓                                            │
│               WorkerManager.start_worker(...)             │
└────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────┐
│   WorkerManager.start_worker()                            │
│                                                           │
│   ├─ Check: active_workers_count < MAX_WORKERS           │
│   │  ├─ If True: proceed                                 │
│   │  └─ If False: log warning, return False              │
│   │                                                       │
│   ├─ Create multiprocessing.Process:                      │
│   │  ├─ target = worker_process                          │
│   │  ├─ args = (worker_id, scenario_uuid, camera_url)    │
│   │  ├─ name = f"worker-{scenario_uuid}"                 │
│   │  └─ daemon = False                                    │
│   │                                                       │
│   ├─ process.start()                                      │
│   │  └─ ✓ NEW PROCESS SPAWNED                            │
│   │                                                       │
│   ├─ self.processes[scenario_uuid] = process             │
│   │  └─ Track in dictionary                              │
│   │                                                       │
│   └─ log(f"Started worker PID={process.pid}")            │
└────────────────────────────────────────────────────────────┘
                             │
       ┌─────────────────────┴─────────────────────┐
       │                                            │
       ▼ (Main Process)                             ▼ (New Child Process)
       │                                            │
       │  Continue listening                       │  WORKER PROCESS EXECUTION
       │  (blocking on Kafka                       │
       │   consumer.next())                        │
       │                                            │
       │                                            ├─ subprocess init
       │                                            ├─ logger setup
       │                                            ├─ model = MockInferenceModel()
       │                                            ├─ producer = KafkaProducer()
       │                                            │
       │                                            ├─ VideoProcessor.open(camera_url)
       │                                            │  ├─ cv2.VideoCapture(camera_url)
       │                                            │  ├─ Get original FPS
       │                                            │  ├─ Calculate frame skip
       │                                            │  │  (skip = orig_fps / target_fps)
       │                                            │  └─ Success: return True
       │                                            │
       │                                            ├─ For each frame:
       │                                            │  ├─ VideoProcessor.read_frame()
       │                                            │  │  ├─ ret, frame = cap.read()
       │                                            │  │  └─ Return frame
       │                                            │  │
       │                                            │  ├─ Skip frame logic
       │                                            │  │  ├─ skip_counter += 1
       │                                            │  │  ├─ If skip_counter >= skip:
       │                                            │  │  │  ├─ skip_counter = 0
       │                                            │  │  │  └─ Process this frame
       │                                            │  │  └─ Else: continue
       │                                            │  │
       │                                            │  ├─ model.predict(frame)
       │                                            │  │  ├─ height, width = frame.shape
       │                                            │  │  ├─ num_detections = random(0-3)
       │                                            │  │  ├─ For each detection:
       │                                            │  │  │  ├─ class_id = random
       │                                            │  │  │  ├─ confidence = random(0.7-0.99)
       │                                            │  │  │  ├─ bbox = random coordinates
       │                                            │  │  │  └─ detections.append(...)
       │                                            │  │  └─ Return detections
       │                                            │  │
       │                                            │  └─ producer.send_result(
       │                                            │      scenario_uuid,
       │                                            │      frame_number,
       │                                            │      detections,
       │                                            │      timestamp
       │                                            │    )
       │                                            │     ├─ Kafka msg to 'results'
       │                                            │     └─ Log sent
       │                                            │
       │                                            ├─ producer.flush()
       │                                            ├─ processor.close()
       │                                            └─ ✓ PROCESS EXITS
       │
       └─ Clean finished processes from dict
          (check if process.is_alive())
```

### Worker Process Execution

```
MULTIPROCESSING WORKER PROCESS:

┌────────────────────────────────────────────────────────────┐
│  def worker_process(worker_id, scenario_uuid, camera_url):│
│                                                            │
│    try:                                                    │
│      logger.info(f"Worker {worker_id} starting...")        │
│                                                            │
│      # Initialize per-process resources                   │
│      model = MockInferenceModel()                          │
│      producer = KafkaProducer(...)                         │
│                                                            │
│      # Open video stream                                  │
│      for frame, frame_number, timestamp in \              │
│          extract_frames(camera_url, fps_target=2):        │
│                                                            │
│        # Perform inference                                │
│        detections = model.predict(frame)                  │
│                                                            │
│        # Send results                                     │
│        producer.send_result(                              │
│          scenario_uuid,                                   │
│          frame_number,                                    │
│          detections,                                      │
│          timestamp                                        │
│        )                                                  │
│                                                            │
│        frame_count += 1                                   │
│                                                            │
│      producer.flush(timeout=10)                           │
│      logger.info(f"Worker finished: {frame_count} frames")│
│                                                            │
│    except Exception as e:                                 │
│      logger.error(f"Worker failed: {str(e)}")             │
│                                                            │
│    finally:                                               │
│      logger.info(f"Worker {worker_id} process ended")     │
│                                                            │
└────────────────────────────────────────────────────────────┘

VIDEO FRAME EXTRACTION (extract_frames generator):

┌────────────────────────────────────────────────────────────┐
│  def extract_frames(video_url, fps_target, max_frames):   │
│                                                            │
│    processor = VideoProcessor(video_url, fps_target)      │
│    processor.open()  # cv2.VideoCapture                   │
│                                                            │
│    frame_index = 0                                        │
│    skip_counter = 0                                       │
│                                                            │
│    while True:                                            │
│      frame = processor.read_frame()                       │
│      if frame is None:                                    │
│        break                                              │
│                                                            │
│      skip_counter += 1                                    │
│                                                            │
│      if skip_counter >= processor.frame_skip:             │
│        skip_counter = 0                                   │
│        frame_index += 1                                   │
│                                                            │
│        yield (frame, frame_index, timestamp)              │
│                                                            │
│        if frame_index >= max_frames:                      │
│          break                                            │
│                                                            │
│    processor.close()                                      │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## Kafka Integration

### Topic Configuration

```
TOPIC: init_scenario
├─ Partitions: 3
├─ Replication Factor: 3
├─ Min In-Sync Replicas: 2
├─ Retention: 24 hours
├─ Compression: snappy
└─ Message Format: JSON
    {
      "scenario_uuid": "550e8400-e29b-41d4-a716-446655440000",
      "camera_url": "rtsp://example.com/stream"
    }

TOPIC: to_deploy
├─ Partitions: 3
├─ Replication Factor: 3
├─ Min In-Sync Replicas: 2
├─ Retention: 24 hours
├─ Compression: snappy
└─ Message Format: JSON
    {
      "worker_id": "11223344-5566-7788-99aa-bbccddeeeff0",
      "scenario_uuid": "550e8400-e29b-41d4-a716-446655440000",
      "camera_url": "rtsp://example.com/stream"
    }

TOPIC: results
├─ Partitions: 3
├─ Replication Factor: 3
├─ Min In-Sync Replicas: 2
├─ Retention: 7 days
├─ Compression: snappy
└─ Message Format: JSON
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
      "timestamp": "2026-01-11T16:30:05.123Z"
    }
```

### Consumer Group Configuration

```
CONSUMER GROUP: api-inbox-group
├─ Members: 1 (API Inbox Consumer)
├─ Topics subscribed: [results]
├─ Partition assignment: range
├─ Auto offset reset: earliest
├─ Enable auto commit: true
├─ Auto commit interval: 1000ms
├─ Session timeout: 30000ms
└─ Max poll records: 500

CONSUMER GROUP: orchestrator-group
├─ Members: 1+ (Orchestrator instances)
├─ Topics subscribed: [init_scenario]
├─ Partition assignment: range/roundrobin
├─ Auto offset reset: earliest
├─ Enable auto commit: true
├─ Auto commit interval: 1000ms
└─ Session timeout: 30000ms

CONSUMER GROUP: runner-group
├─ Members: 1 (Runner service)
├─ Topics subscribed: [to_deploy]
├─ Partition assignment: range
├─ Auto offset reset: earliest
├─ Enable auto commit: true
├─ Auto commit interval: 1000ms
└─ Session timeout: 30000ms
```

### Message Flow Timeline

```
T0: User calls POST /api/v1/scenario/init
    ├─ API creates scenario UUID
    ├─ BEGIN TRANSACTION
    │  ├─ INSERT scenarios
    │  └─ INSERT outbox_scenario (published=false)
    ├─ COMMIT
    └─ RETURN 200 OK with UUID

T0+50ms: KafkaProducer sends message
    ├─ PUBLISH to init_scenario topic
    │  ├─ Partition 0,1,2 (round-robin by key)
    │  ├─ Replica 1 (Leader)
    │  ├─ Replica 2 (ISR)
    │  └─ Replica 3 (ISR)
    └─ ACK from ISR

T0+100ms: Update outbox
    ├─ UPDATE outbox_scenario
    │  ├─ published = true
    │  └─ published_at = NOW()
    └─ COMMIT

T0+150ms: Orchestrator consumer fetches
    ├─ Poll Kafka broker
    ├─ Get batch of 500 messages (configurable)
    └─ Start processing

T0+200ms: Orchestrator processes message
    ├─ Parse payload
    ├─ BEGIN TRANSACTION
    │  ├─ Generate worker_id (UUID)
    │  └─ INSERT workers (status=pending)
    ├─ COMMIT
    ├─ KafkaProducer sends to_deploy
    │  └─ Publish to to_deploy topic
    └─ UPDATE workers (status=deployed)

T0+250ms: Runner consumer fetches
    ├─ Poll Kafka broker
    └─ Get to_deploy message

T0+300ms: Runner spawns worker process
    ├─ Create Process(target=worker_process)
    ├─ process.start() [FORK]
    └─ Add to process pool

T0+350ms onwards: Worker process executes
    ├─ VideoProcessor.open(camera_url)
    ├─ Loop: extract_frames()
    │  ├─ Read frame from OpenCV
    │  ├─ Skip frame if needed
    │  ├─ model.predict(frame)
    │  ├─ KafkaProducer.send_result()
    │  │  └─ Publish to results topic
    │  └─ Log detection
    └─ Continue until stream ends

T0+400ms (approx): API Inbox consumer fetches
    ├─ Poll Kafka broker (results topic)
    ├─ Get results message
    └─ Parse payload

T0+450ms: API Inbox saves result
    ├─ BEGIN TRANSACTION
    ├─ TRY: INSERT scenario_results
    ├─ ON UNIQUE VIOLATION: UPDATE scenario_results
    ├─ COMMIT
    └─ Log saved

T0+500ms: User calls GET /api/v1/prediction/{uuid}
    ├─ API queries scenario_results
    ├─ BUILD PredictionResponse
    │  ├─ For each result:
    │  │  ├─ Create FrameResult
    │  │  └─ Create DetectionResult objects
    │  └─ Return response
    └─ RETURN 200 OK with results
```

---

## PostgreSQL Schema

### Detailed Table Definitions

```sql
-- Table 1: scenarios
CREATE TABLE scenarios (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    
    -- Scenario Identifier (UUID)
    scenario_uuid UUID UNIQUE NOT NULL,
    -- Used as foreign key reference in other tables
    -- Indexed for fast lookups
    
    -- Video Configuration
    camera_url TEXT NOT NULL,
    -- RTSP, HTTP, or local file path
    -- e.g., "rtsp://example.com/stream"
    
    -- State Management
    status VARCHAR(50) NOT NULL DEFAULT 'init_startup',
    -- States: init_startup, in_startup_processing, active,
    --         init_shutdown, in_shutdown_processing, inactive
    
    -- Audit Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW() ON UPDATE NOW()
);

-- Indices
CREATE INDEX idx_scenarios_uuid ON scenarios(scenario_uuid);
CREATE INDEX idx_scenarios_status ON scenarios(status);
-- Why: Fast lookups by UUID (Primary lookup)
--      Fast status-based queries (Filtering)


-- Table 2: outbox_scenario (Transactional Outbox Pattern)
CREATE TABLE outbox_scenario (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    
    -- Reference to Scenario
    scenario_uuid UUID NOT NULL,
    -- References scenarios.scenario_uuid (no FK constraint for performance)
    -- Allows orphaned records if scenario deleted
    
    -- Event Payload
    payload JSONB NOT NULL,
    -- JSON: {"scenario_uuid": "...", "camera_url": "..."}
    -- JSONB for indexing and queries
    
    -- Publishing Status
    published BOOLEAN DEFAULT FALSE,
    -- FALSE = Not yet sent to Kafka
    -- TRUE = Sent and acknowledged
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    published_at TIMESTAMP NULL,
    -- published_at = when message was successfully sent

    -- Check Constraint
    CHECK (published = FALSE OR published_at IS NOT NULL)
    -- If published=TRUE, published_at must have value
);

-- Indices
CREATE INDEX idx_outbox_published ON outbox_scenario(published);
-- Why: Scan for unpublished messages (select * where published=false)


-- Table 3: scenario_results (Inference Results)
CREATE TABLE scenario_results (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    
    -- Reference to Scenario
    scenario_uuid UUID NOT NULL,
    -- References scenarios.scenario_uuid
    
    -- Frame Information
    frame_number INTEGER NOT NULL,
    -- Frame sequence number (1, 2, 3, ...)
    -- Combined with scenario_uuid for uniqueness
    
    -- Detection Results
    detections JSONB NOT NULL,
    -- JSON array of detections:
    -- [
    --   {
    --     "class": "person",
    --     "confidence": 0.95,
    --     "bbox": [10, 20, 100, 150]
    --   },
    --   ...
    -- ]
    
    -- Timestamp of Processing
    timestamp TIMESTAMP NOT NULL,
    -- When the frame was processed in Runner
    -- ISO format: "2026-01-11T16:30:05.123Z"
    
    -- Record Creation Time
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Unique Constraint (Idempotent Inbox)
    UNIQUE(scenario_uuid, frame_number)
    -- Ensures no duplicate results for same frame
    -- On duplicate: UPDATE instead of INSERT
);

-- Indices
CREATE INDEX idx_results_uuid ON scenario_results(scenario_uuid);
-- Why: Query results for specific scenario
--      (used in GET /prediction/{uuid})

CREATE INDEX idx_results_frame ON scenario_results(scenario_uuid, frame_number);
-- Why: Composite index for duplicate checking
--      (when Inbox consumer checks if frame exists)


-- Table 4: workers (Worker Process Tracking)
CREATE TABLE workers (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    
    -- Worker Identifier
    worker_id UUID UNIQUE NOT NULL,
    -- Unique ID for this worker instance
    -- Generated by Orchestrator
    
    -- Reference to Scenario
    scenario_uuid UUID NOT NULL,
    -- References scenarios.scenario_uuid
    -- Allows one-to-one mapping: worker → scenario
    
    -- Video Configuration
    camera_url TEXT NOT NULL,
    -- RTSP stream URL from scenario
    
    -- Worker State
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    -- States:
    --   pending       - Just created
    --   deployed      - Deploy message sent to Kafka
    --   running       - Process started
    --   stopped       - Process ended normally
    --   failed        - Process ended with error
    
    -- Process Information
    process_pid INTEGER NULL,
    -- Operating System Process ID
    -- Set by Runner when process.start()
    -- Used for monitoring/debugging
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW() ON UPDATE NOW()
    -- Audit trail for worker lifecycle
);

-- Indices
CREATE INDEX idx_workers_scenario ON workers(scenario_uuid);
-- Why: Find worker for specific scenario

CREATE INDEX idx_workers_status ON workers(status);
-- Why: Find all workers in specific state
--      (monitoring, cleanup tasks)


-- Transaction Example: init_scenario operation
/*
BEGIN TRANSACTION ISOLATION LEVEL READ COMMITTED;

-- Step 1: Insert scenario
INSERT INTO scenarios (
    scenario_uuid,
    camera_url,
    status,
    created_at,
    updated_at
) VALUES (
    '550e8400-e29b-41d4-a716-446655440000',
    'rtsp://example.com/stream',
    'init_startup',
    NOW(),
    NOW()
);

-- Step 2: Flush (ensure step 1 is written)
FLUSH; -- (SQLAlchemy operation)

-- Step 3: Insert to outbox (same transaction)
INSERT INTO outbox_scenario (
    scenario_uuid,
    payload,
    published,
    created_at
) VALUES (
    '550e8400-e29b-41d4-a716-446655440000',
    '{"scenario_uuid": "550e8400-e29b-41d4-a716-446655440000", 
      "camera_url": "rtsp://example.com/stream"}',
    false,
    NOW()
);

COMMIT; -- Atomic: both inserts succeed or both fail
*/

-- Idempotent Save Result Example:
/*
-- Try INSERT with UNIQUE constraint
INSERT INTO scenario_results (
    scenario_uuid,
    frame_number,
    detections,
    timestamp,
    created_at
) VALUES (
    '550e8400-e29b-41d4-a716-446655440000',
    1,
    '[{"class": "person", "confidence": 0.95, "bbox": [...]}]',
    '2026-01-11T16:30:05.123Z',
    NOW()
)
ON CONFLICT (scenario_uuid, frame_number)
DO UPDATE SET
    detections = EXCLUDED.detections,
    timestamp = EXCLUDED.timestamp;
    -- If duplicate: UPDATE with new values
*/
```

### Query Patterns

```sql
-- Query 1: Get scenario
SELECT * FROM scenarios
WHERE scenario_uuid = '550e8400-e29b-41d4-a716-446655440000';
-- Uses: idx_scenarios_uuid
-- Result: 1 row (UNIQUE constraint)


-- Query 2: Get all results for scenario
SELECT * FROM scenario_results
WHERE scenario_uuid = '550e8400-e29b-41d4-a716-446655440000'
ORDER BY frame_number ASC;
-- Uses: idx_results_uuid
-- Result: N rows (ordered by frame number)


-- Query 3: Get unpublished outbox records
SELECT * FROM outbox_scenario
WHERE published = false
ORDER BY created_at ASC
LIMIT 100;
-- Uses: idx_outbox_published
-- Result: Batch of unpublished messages


-- Query 4: Check if result exists (for idempotency)
SELECT 1 FROM scenario_results
WHERE scenario_uuid = '550e8400-e29b-41d4-a716-446655440000'
AND frame_number = 1
LIMIT 1;
-- Uses: idx_results_frame (composite)
-- Result: Exists? 0 or 1 row


-- Query 5: Get active workers
SELECT * FROM workers
WHERE status IN ('pending', 'deployed', 'running');
-- Uses: idx_workers_status
-- Result: N rows


-- Query 6: Find worker for scenario
SELECT * FROM workers
WHERE scenario_uuid = '550e8400-e29b-41d4-a716-446655440000';
-- Uses: idx_workers_scenario
-- Result: 1 row (one-to-one)
```

---

(Продолжение в следующем сообщении из-за размера...)

## Reliability Patterns

### Transactional Outbox Pattern

```
PROBLEM:
If we write to DB and then send to Kafka:
├─ Write to DB: ✓ SUCCESS
├─ Send to Kafka: ✗ FAILURE (Kafka down)
└─ Result: Data in DB but never sent to Kafka

SOLUTION: Transactional Outbox

┌─────────────────────────────────────────────┐
│  Atomic Transaction (single DB commit)     │
│                                             │
│  ├─ Write to scenarios table                │
│  ├─ Write to outbox_scenario table          │
│  │  (published = false)                     │
│  └─ COMMIT (atomic)                         │
│                                             │
│  Result: Both succeed or both fail          │
└─────────────────────────────────────────────┘
          │
          ▼ (After commit)
┌─────────────────────────────────────────────┐
│  Separate background service:               │
│                                             │
│  ├─ Query unpublished records:              │
│  │  SELECT * FROM outbox_scenario           │
│  │  WHERE published = false                 │
│  │                                          │
│  ├─ For each record:                        │
│  │  ├─ Send to Kafka                        │
│  │  ├─ IF success:                          │
│  │  │  └─ UPDATE published = true           │
│  │  └─ IF failure:                          │
│  │     └─ Retry later                       │
│  │                                          │
│  └─ Loop forever (or interval-based)       │
└─────────────────────────────────────────────┘

BENEFITS:
✓ If API crashes after DB write: Message in outbox
✓ If Kafka down: Message remains in outbox for retry
✓ EXACTLY-ONCE guarantee (no duplicates)
✓ Simple failure recovery

TRADE-OFF:
⚠ Increased DB storage (outbox table)
⚠ Latency (delay between DB write and Kafka publish)
```

### Idempotent Inbox Pattern

```
PROBLEM:
Kafka guarantees at-least-once delivery:
├─ Message sent: ✓
├─ Received: ✓
├─ Processed: ✓
├─ Offset committed: ✗ FAILURE (network issue)
└─ Result: Message redelivered → DUPLICATE PROCESSING

SOLUTION: Idempotent Inbox

┌─────────────────────────────────────────────┐
│  Consumer receives message:                 │
│  {                                          │
│    "scenario_uuid": "...",                  │
│    "frame_number": 1,                       │
│    "detections": [...],                     │
│    "timestamp": "..."                       │
│  }                                          │
└─────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────┐
│  Database has UNIQUE constraint:            │
│  UNIQUE(scenario_uuid, frame_number)        │
│                                             │
│  First attempt:                             │
│  ├─ TRY INSERT new record                   │
│  └─ ✓ Success (no duplicate yet)            │
│                                             │
│  Duplicate arrives (re-delivered):          │
│  ├─ TRY INSERT same record                  │
│  ├─ ✗ UNIQUE constraint violation           │
│  ├─ CATCH: Do UPDATE instead                │
│  │  (same result, no duplicate)             │
│  └─ ✓ Idempotent                            │
└─────────────────────────────────────────────┘

IMPLEMENTATION:

# Python code
try:
    db.session.add(ScenarioResult(
        scenario_uuid = uuid,
        frame_number = frame_num,
        detections = detections,
        timestamp = timestamp
    ))
    db.commit()  # INSERT
except IntegrityError:  # UNIQUE constraint
    db.rollback()
    existing = db.query(ScenarioResult).filter(
        ScenarioResult.scenario_uuid == uuid,
        ScenarioResult.frame_number == frame_num
    ).first()
    existing.detections = detections
    existing.timestamp = timestamp
    db.commit()  # UPDATE

BENEFITS:
✓ Safe from Kafka redelivery
✓ No duplicate results
✓ AT-LEAST-ONCE + Idempotency = EXACTLY-ONCE

TRADE-OFF:
⚠ Requires UNIQUE constraint
⚠ Slight performance overhead (handle exception)
```

---

Эта архитектура обеспечивает полный контроль над системой и надежность доставки сообщений!
