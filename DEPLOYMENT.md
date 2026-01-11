# Deployment Guide

## Локальная Настройка

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

## Production

### Минимальные Рекомендации

- **PostgreSQL**: Отдельный сервер
- **Kafka**: Кластер деталяю до 3-чные брокеры
- **API**: 2-4 
- **Orchestrator**: 2 экземпляра
- **Runner**: Масштабируемый выпуск

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

### Мониторинг и Логи

- **Prometheus**: Осталометры (latency, throughput)
- **ELK Stack**: Логи даоснения
- **Grafana**: Dashboards

## Ошибки

- **Recovery**: Leader election для Orchestrator
- **Failover**: Health checks для всех сервисов
- **Data Loss Prevention**: Transactional Outbox
