# Docker Setup for Lang2Query

🐳 **Complete Docker setup** for running Lang2Query with all dependencies and services.

## 🚀 Quick Start

### Prerequisites

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **Git**

### Production Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/lang2query.git
   cd lang2query
   ```

2. **Set environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start all services:**
   ```bash
   docker-compose up -d
   ```

4. **Access the application:**
   - **Frontend**: http://localhost:3000
   - **Backend API**: http://localhost:8000
   - **API Docs**: http://localhost:8000/docs
   - **ChromaDB**: http://localhost:8001

### Development Setup

For development with hot reload:

```bash
docker-compose -f docker-compose.dev.yml up -d
```

## 📁 Docker Files

### Backend Dockerfile (`Dockerfile`)

- **Base**: Python 3.11-slim
- **Features**: Multi-stage build, non-root user, health checks
- **Port**: 8000
- **Volumes**: Knowledge base, input/output directories

### Frontend Dockerfile (`app/Dockerfile`)

- **Base**: Node.js 20-alpine
- **Features**: Multi-stage build, standalone output, optimized for production
- **Port**: 3000
- **Build**: Next.js with standalone output

### Development Dockerfile (`app/Dockerfile.dev`)

- **Base**: Node.js 20-alpine
- **Features**: Development mode with hot reload
- **Volumes**: Source code mounted for live updates

## 🐳 Docker Compose Services

### Production (`docker-compose.yml`)

| Service | Description | Port | Image |
|---------|-------------|------|-------|
| `backend` | Lang2Query Python API | 8000 | Custom |
| `frontend` | Next.js React App | 3000 | Custom |
| `redis` | Redis Cache | 6379 | redis:7-alpine |
| `chromadb` | Vector Database | 8001 | chromadb/chroma |

### Development (`docker-compose.dev.yml`)

| Service | Description | Port | Features |
|---------|-------------|------|----------|
| `backend-dev` | Python API (Dev) | 8000 | Hot reload, volume mounts |
| `frontend-dev` | React App (Dev) | 3000 | Hot reload, volume mounts |
| `redis` | Redis Cache | 6379 | Development data |
| `chromadb` | Vector Database | 8001 | Development data |

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o

# Backend Configuration
PROVIDER=chatgpt
KB_DIRECTORY=/app/src/kb
COLLECTION_NAME=sql_generation_kb

# Frontend Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws

# Production URLs (for deployment)
PRODUCTION_API_URL=https://your-api-domain.com
PRODUCTION_WS_URL=wss://your-api-domain.com/ws
```

### Volume Mounts

The following directories are mounted as volumes:

- `./src/kb` → `/app/src/kb` (Knowledge base)
- `./src/retreiver/input` → `/app/src/retreiver/input` (Input docs)
- `./src/retreiver/output` → `/app/src/retreiver/output` (Generated chunks)

## 🛠️ Docker Commands

### Basic Commands

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d backend

# View logs
docker-compose logs -f backend

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Development Commands

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# View development logs
docker-compose -f docker-compose.dev.yml logs -f

# Rebuild services
docker-compose build --no-cache

# Execute commands in running container
docker-compose exec backend python -m src.main
docker-compose exec frontend npm run build
```

### Maintenance Commands

```bash
# Clean up unused containers and images
docker system prune -a

# Remove all volumes
docker volume prune

# View resource usage
docker stats

# Access container shell
docker-compose exec backend bash
docker-compose exec frontend sh
```

## 🔧 Customization

### Adding New Services

To add a new service (e.g., PostgreSQL):

```yaml
# Add to docker-compose.yml
postgres:
  image: postgres:15-alpine
  container_name: lang2query-postgres
  environment:
    POSTGRES_DB: lang2query
    POSTGRES_USER: user
    POSTGRES_PASSWORD: password
  volumes:
    - postgres_data:/var/lib/postgresql/data
  networks:
    - lang2query-network
  ports:
    - "5432:5432"
```

### Custom Build Arguments

```yaml
# In docker-compose.yml
backend:
  build:
    context: .
    dockerfile: Dockerfile
    args:
      - PYTHON_VERSION=3.11
      - NODE_VERSION=20
```

### Health Checks

All services include health checks:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/system/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

## 🚀 Deployment

### Production Deployment

1. **Set production environment variables:**
   ```bash
   export OPENAI_API_KEY="your-production-key"
   export PRODUCTION_API_URL="https://your-domain.com"
   export PRODUCTION_WS_URL="wss://your-domain.com/ws"
   ```

2. **Build and deploy:**
   ```bash
   docker-compose -f docker-compose.yml up -d --build
   ```

3. **Set up reverse proxy** (nginx example):
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://localhost:3000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
       
       location /api/ {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

### Cloud Deployment

#### AWS ECS

```yaml
# ecs-task-definition.json
{
  "family": "lang2query",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "your-registry/lang2query-backend:latest",
      "portMappings": [{"containerPort": 8000}]
    },
    {
      "name": "frontend", 
      "image": "your-registry/lang2query-frontend:latest",
      "portMappings": [{"containerPort": 3000}]
    }
  ]
}
```

#### Google Cloud Run

```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/lang2query', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/lang2query']
  - name: 'gcr.io/cloud-builders/gcloud'
    args: ['run', 'deploy', 'lang2query', '--image', 'gcr.io/$PROJECT_ID/lang2query']
```

## 🐛 Troubleshooting

### Common Issues

1. **Port conflicts:**
   ```bash
   # Check what's using the port
   lsof -i :8000
   # Change ports in docker-compose.yml
   ```

2. **Permission issues:**
   ```bash
   # Fix volume permissions
   sudo chown -R $USER:$USER ./src/kb
   ```

3. **Out of memory:**
   ```bash
   # Increase Docker memory limit
   # Docker Desktop → Settings → Resources → Memory
   ```

4. **Build failures:**
   ```bash
   # Clean build cache
   docker-compose build --no-cache
   docker system prune -a
   ```

### Debugging

```bash
# View detailed logs
docker-compose logs --tail=100 -f

# Check container status
docker-compose ps

# Inspect container
docker inspect lang2query-backend

# Check resource usage
docker stats lang2query-backend
```

## 📊 Monitoring

### Health Checks

All services include health checks accessible at:

- **Backend**: `http://localhost:8000/api/system/health`
- **Frontend**: `http://localhost:3000`
- **ChromaDB**: `http://localhost:8001/api/v1/heartbeat`

### Logging

```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs backend
docker-compose logs frontend

# Follow logs in real-time
docker-compose logs -f --tail=100
```

## 🔒 Security

### Best Practices

1. **Use non-root users** in containers
2. **Set resource limits** to prevent resource exhaustion
3. **Use secrets** for sensitive data
4. **Regular updates** of base images
5. **Network isolation** with custom networks

### Security Scanning

```bash
# Scan for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image lang2query-backend:latest

# Scan all images
docker-compose config --services | xargs -I {} docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image lang2query-{}:latest
```

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Next.js Docker Documentation](https://nextjs.org/docs/deployment#docker-image)
- [FastAPI Docker Documentation](https://fastapi.tiangolo.com/deployment/docker/)
