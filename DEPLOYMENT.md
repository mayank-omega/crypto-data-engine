# See artifact: crypto_deployment_guide
# Deployment Guide - Crypto Data Engine

Complete production deployment guide for the Crypto Data Engine microservice.

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [AWS Deployment](#aws-deployment)
4. [Monitoring & Maintenance](#monitoring--maintenance)
5. [Troubleshooting](#troubleshooting)

## Local Development

### Setup

1. **Clone and Install**
```bash
git clone <repo-url>
cd crypto-data-engine
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your local settings
```

3. **Start Dependencies**
```bash
# Start PostgreSQL
docker run -d \
  --name crypto-postgres \
  -e POSTGRES_USER=cryptouser \
  -e POSTGRES_PASSWORD=cryptopass \
  -e POSTGRES_DB=crypto_data \
  -p 5432:5432 \
  postgres:15-alpine

# Start Redis
docker run -d \
  --name crypto-redis \
  -p 6379:6379 \
  redis:7-alpine
```

4. **Run Migrations**
```bash
alembic upgrade head
```

5. **Start Application**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

6. **Verify**
```bash
curl http://localhost:8000/health
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov httpx

# Create test database
createdb crypto_data_test

# Run tests
pytest -v

# With coverage
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## Docker Deployment

### Single Host Deployment

1. **Configure Environment**
```bash
cp .env.example .env
# Edit with production values
# IMPORTANT: Use strong passwords!
```

2. **Start All Services**
```bash
docker-compose up -d
```

3. **Run Migrations**
```bash
docker-compose --profile migrations up migrations
```

4. **Verify Deployment**
```bash
# Check all services are running
docker-compose ps

# Check logs
docker-compose logs -f crypto-data-engine

# Test health endpoint
curl http://localhost:8000/health
```

5. **Start Data Collection**
```bash
curl -X POST http://localhost:8000/api/v1/collectors/start \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"]}'
```

### Production Docker Configuration

For production, customize docker-compose.yml:

```yaml
services:
  crypto-data-engine:
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

## AWS Deployment

### Architecture

```
Internet → ALB → ECS/Fargate → RDS PostgreSQL
                              → ElastiCache Redis
```

### Prerequisites

- AWS CLI configured
- ECR repository created
- RDS PostgreSQL instance
- ElastiCache Redis cluster
- ECS cluster
- Application Load Balancer

### Step-by-Step Deployment

#### 1. Build and Push Docker Image

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build image
docker build -t crypto-data-engine:latest .

# Tag image
docker tag crypto-data-engine:latest \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com/crypto-data-engine:latest

# Push to ECR
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/crypto-data-engine:latest
```

#### 2. Create RDS PostgreSQL Database

```bash
aws rds create-db-instance \
  --db-instance-identifier crypto-data-db \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 15.3 \
  --master-username cryptouser \
  --master-user-password <secure-password> \
  --allocated-storage 100 \
  --storage-type gp3 \
  --backup-retention-period 7 \
  --multi-az \
  --vpc-security-group-ids sg-xxxxxxxx \
  --db-subnet-group-name crypto-db-subnet
```

#### 3. Create ElastiCache Redis Cluster

```bash
aws elasticache create-replication-group \
  --replication-group-id crypto-redis-cluster \
  --replication-group-description "Crypto Data Engine Cache" \
  --engine redis \
  --cache-node-type cache.t3.medium \
  --num-cache-clusters 2 \
  --automatic-failover-enabled \
  --at-rest-encryption-enabled \
  --transit-encryption-enabled \
  --security-group-ids sg-xxxxxxxx \
  --cache-subnet-group-name crypto-cache-subnet
```

#### 4. Store Secrets in AWS Secrets Manager

```bash
# Database credentials
aws secretsmanager create-secret \
  --name crypto-data-engine/database \
  --secret-string '{
    "username":"cryptouser",
    "password":"<secure-password>",
    "host":"<rds-endpoint>",
    "port":5432,
    "database":"crypto_data"
  }'

# Redis credentials
aws secretsmanager create-secret \
  --name crypto-data-engine/redis \
  --secret-string '{
    "host":"<redis-endpoint>",
    "port":6379,
    "password":"<redis-password>"
  }'

# API keys
aws secretsmanager create-secret \
  --name crypto-data-engine/api-keys \
  --secret-string '{
    "binance_api_key":"<key>",
    "binance_api_secret":"<secret>",
    "coingecko_api_key":"<key>"
  }'
```

#### 5. Create ECS Task Definition

Create `task-definition.json`:

```json
{
  "family": "crypto-data-engine",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "executionRoleArn": "arn:aws:iam::<account>:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::<account>:role/cryptoDataEngineTaskRole",
  "containerDefinitions": [
    {
      "name": "crypto-data-engine",
      "image": "<account>.dkr.ecr.us-east-1.amazonaws.com/crypto-data-engine:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "secrets": [
        {
          "name": "POSTGRES_USER",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:crypto-data-engine/database:username::"
        },
        {
          "name": "POSTGRES_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:crypto-data-engine/database:password::"
        }
      ],
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "LOG_LEVEL", "value": "INFO"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/crypto-data-engine",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

Register task definition:

```bash
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

#### 6. Create ECS Service

```bash
aws ecs create-service \
  --cluster crypto-cluster \
  --service-name crypto-data-engine \
  --task-definition crypto-data-engine:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --platform-version LATEST \
  --network-configuration "awsvpcConfiguration={
    subnets=[subnet-xxx,subnet-yyy],
    securityGroups=[sg-zzz],
    assignPublicIp=DISABLED
  }" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...,
    containerName=crypto-data-engine,
    containerPort=8000" \
  --health-check-grace-period-seconds 60
```

#### 7. Run Database Migrations

Create a one-time ECS task to run migrations:

```bash
aws ecs run-task \
  --cluster crypto-cluster \
  --task-definition crypto-data-engine-migrations:1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={
    subnets=[subnet-xxx],
    securityGroups=[sg-zzz],
    assignPublicIp=DISABLED
  }"
```

#### 8. Configure Auto Scaling

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/crypto-cluster/crypto-data-engine \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 10

# Create scaling policy
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/crypto-cluster/crypto-data-engine \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name cpu-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
    },
    "ScaleOutCooldown": 60,
    "ScaleInCooldown": 300
  }'
```

## Monitoring & Maintenance

### CloudWatch Metrics

Key metrics to monitor:

- CPU utilization
- Memory utilization
- Request count
- Error rate
- Database connections
- Redis connection count

### CloudWatch Alarms

```bash
# High CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name crypto-data-engine-high-cpu \
  --alarm-description "Alert when CPU > 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

### Application Logs

View logs:

```bash
# Recent logs
aws logs tail /ecs/crypto-data-engine --follow

# Filter errors
aws logs filter-log-events \
  --log-group-name /ecs/crypto-data-engine \
  --filter-pattern "ERROR"
```

### Database Maintenance

Schedule regular maintenance:

```sql
-- Run weekly
VACUUM ANALYZE;

-- Check table sizes
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check index usage
SELECT 
  schemaname,
  tablename,
  indexname,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;
```

## Troubleshooting

### Service Won't Start

1. Check logs:
```bash
docker-compose logs crypto-data-engine
```

2. Verify database connection:
```bash
psql -h localhost -U cryptouser -d crypto_data
```

3. Check Redis:
```bash
redis-cli ping
```

### High Memory Usage

1. Check for memory leaks:
```bash
docker stats crypto-data-engine
```

2. Review collector intervals - may be collecting too frequently

3. Adjust cache TTL values

### Slow API Responses

1. Check database query performance:
```sql
SELECT * FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;
```

2. Verify indexes are being used:
```sql
EXPLAIN ANALYZE 
SELECT * FROM ohlcv 
WHERE symbol = 'BTCUSDT' 
ORDER BY timestamp DESC 
LIMIT 100;
```

3. Check Redis hit rate

### Collector Failures

1. Check collector status:
```bash
curl http://localhost:8000/api/v1/collectors/status
```

2. Review error logs

3. Verify API keys are valid

4. Check rate limits

### WebSocket Connection Issues

1. Verify WebSocket endpoint is accessible

2. Check for firewall/load balancer WebSocket support

3. Monitor connection count:
```bash
curl http://localhost:8000/api/v1/ws/status
```

## Backup and Recovery

### Database Backups

```bash
# Manual backup
pg_dump -h <host> -U cryptouser crypto_data | gzip > backup_$(date +%Y%m%d).sql.gz

# Automated via RDS
aws rds create-db-snapshot \
  --db-instance-identifier crypto-data-db \
  --db-snapshot-identifier crypto-data-snapshot-$(date +%Y%m%d)
```

### Restore from Backup

```bash
# Restore local
gunzip -c backup_20260111.sql.gz | psql -h localhost -U cryptouser crypto_data

# Restore RDS
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier crypto-data-db-restored \
  --db-snapshot-identifier crypto-data-snapshot-20260111
```

## Security Checklist

- [ ] All secrets stored in AWS Secrets Manager
- [ ] Database in private subnet
- [ ] Redis authentication enabled
- [ ] TLS/SSL for all connections
- [ ] Security groups properly configured
- [ ] API authentication implemented
- [ ] Rate limiting enabled
- [ ] Regular security updates
- [ ] Monitoring and alerting configured
- [ ] Backup strategy implemented

## Support

For issues:
- Check logs first
- Review this guide
- Contact: devops@your-company.com