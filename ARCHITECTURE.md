# Архитектура Подробно

## Микросервисная Архитектура

```
╭───────────────╮
│   API Service      │
│   (FastAPI)        │
╭───────────────╮
    └───────────────────────────────────┴───────────────╮
                                              │
                    ╭───────────────────────┴
                    │ PostgreSQL          │
                    │ Kafka              │
                    ╮───────────────────────╯
                         │
    ╭────────────────────────┴
    │ Orchestrator                │
    │ (Consumer/Producer)        │
    ╮────────────────────────╯
         │
    ╭────────────────────────┴
    │ Runner (multiprocessing)  │
    │ - Worker Processes       │
    │ - Frame Extraction       │
    │ - Inference              │
    ╮────────────────────────╯
```

## Жизненные Циклы

### State Machine

```
init_startup ──> in_startup_processing ──> active
                                               │
                                               │ (processing)
                                               │
                                         init_shutdown
                                               │
                                    in_shutdown_processing
                                               │
                                            inactive
```

## Reliability Patterns

### Transactional Outbox (API → Kafka)

```
╭──────────────────╮
│ 1. Write to scenarios  │
│ 2. Write to outbox     │  ←─ Single Transaction
│    (same TX)          │
╮──────────────────╯
         │
         │
╭────▼────────────────╮
│ 3. Read from outbox   │
│ 4. Send to Kafka      │  ←─ Separate Process
│ 5. Mark published     │
╮──────────────────╯
         │
         │ (GUARANTEED DELIVERY)
         ┃
╭────▼────────────────╮
│ buf Kafka Topic        │
╮──────────────────╯
```

### Idempotent Inbox (Kafka → API)

```
╭──────────────────╮
│ Kafka: results topic  │
╮──────────────────╯
         │
         │
╭────▼────────────────╮
│ Try INSERT with       │
│ UNIQUE(scenario_uuid  │  ←─ Deduplication
│          frame_number)│
╮──────────────────╯
         │
    ┌───────────────┬───────────────┐
    │                      │
 SUCCESS (new)         CONFLICT (duplicate)
    │                      │
 INSERT                UPDATE
    │                      │
    └───────────────┴───────────────┘
                     │
            ╭────▼─────╮
            │ AT-LEAST-ONCE  │
            │ PROCESSING     │
            ╮──────────╯
```

## Scaling Strategy

### Horizontal Scaling

- **API**: Лавансин зад лыбой реплики
- **Orchestrator**: Multiple instances (leader election)
- **Runner**: Scales automatically (MAX_WORKERS limit)

### Vertical Scaling

- **Runner**: Increase `MAX_WORKERS` for more concurrent video processing
- **PostgreSQL**: Connection pool tuning
- **Kafka**: Partition count → parallel processing

## Data Flow

```
User Request
     │
     ↓
  API Service (POST /scenario/init)
     │
     ├────────────────────────┐
     │                                      │
     ↓                                      ↓
PostgreSQL                            Kafka: init_scenario
(Store scenario)                       │
     │                                      ↓
     │                         Orchestrator
     │                         (Read init_scenario)
     │                                      │
     │                                      ↓
     │                         Create Worker + Send Deploy
     └───────────────────────────────────────────────────┴────━
                                                  │
                                                  ↓
                                         Kafka: to_deploy
                                                  │
                                                  ↓
                                           Runner
                                    (Spawn Worker Process)
                                                  │
                                    ╭──────────────╮
                                    │ Per Worker:       │
                                    │ 1. Read video     │
                                    │ 2. Run inference  │
                                    │ 3. Send results   │
                                    ╮──────────────╯
                                                  │
                                                  ↓
                                          Kafka: results
                                                  │
                                                  ↓
                                           API Inbox
                                        (Store results)
                                                  │
                                                  ↓
                                          PostgreSQL
                                       (scenario_results)
                                                  │
                                                  ↓
                                        User reads
                                    (GET /prediction)
```

## Performance Characteristics

### Latency

- **Scenario creation**: <100ms
- **Deploy to processing**: <1s (Kafka + Orchestrator)
- **Video frame processing**: Variable (depends on inference model)
- **Result availability**: <100ms after processing

### Throughput

- **API**: 1000+ RPS (with proper load balancing)
- **Concurrent videos**: Limited by `MAX_WORKERS` and hardware
- **Frame processing**: FPS ис in `VIDEO_FPS` config

## Failure Recovery

1. **API fails**: PostgreSQL has all data, clients retry
2. **Orchestrator fails**: Kafka retains messages, another instance picks up
3. **Runner fails**: Worker process terminates, no automatic restart (upgrade needed)
4. **Kafka fails**: Outbox pattern prevents data loss
5. **PostgreSQL fails**: Backup strategy needed for production
