# Deployment Guide

## Локальная Настройка (Development)

### Рекомендации

- **Docker Compose**: Определенная выставка
- **Resources**: 4GB RAM мин, 2 CPU
- **OS**: Linux, macOS, Windows (WSL2)

### Как запустить

```bash
docker-compose up -d

# Проверить
 docker-compose ps
```

## Производственная Настройка (Production)

### Минимальные Рекомендации

- **PostgreSQL**: Отдельный сервер
- **Kafka**: Кластер деталяю до 3-чные брокеры
- **API**: 2-4 реплики за ладонью / группию
- **Orchestrator**: 2 экземпляра
- **Runner**: Маслтабируемая выпуск

### Kubernetes Deployment

```yaml
# api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vap-api
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: api
        image: vap-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: kafka-cluster:9092
```

### Мониторинг и Логки

- **Prometheus**: Осталометры (latency, throughput)
- **ELK Stack**: Логи даоснения
- **Grafana**: Dashboards

## Хлады Ошибки

- **Recovery**: Leader election для Orchestrator
- **Failover**: Health checks для всех сервисов
- **Data Loss Prevention**: Transactional Outbox
