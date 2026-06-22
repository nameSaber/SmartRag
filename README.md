# SmartRag FastAPI Backend

SmartRag 是按 PaiSmart FastAPI 1:1 技术文档开发的后端服务，当前工程主体位于 `backend_fastapi/`，使用 FastAPI、SQLAlchemy、Alembic、Redis、Elasticsearch、Kafka、MinIO 和 Docker 部署。

## 目录结构

```text
backend_fastapi/
  app/                  # FastAPI 应用代码
  migrations/           # Alembic 数据库迁移
  tests/                # pytest 测试
  Dockerfile            # API 镜像构建文件
  docker-compose.yaml   # API 服务部署文件
  .env.example          # 环境变量示例
```

## 外部依赖

请先启动 PaiSmart 文档中提供的基础设施 `docker-compose.yaml`，它应提供：

- MySQL: `localhost:3306`
- Redis: `localhost:6379`
- Elasticsearch: `localhost:9200`
- Kafka: `localhost:9092`
- MinIO: `localhost:19000`

默认账号密码按技术文档约定：

- MySQL root 密码：`PaiSmart2025`
- MySQL 应用账号：`smart_rag`
- MySQL 应用密码：`SmartRag2026`
- Redis 密码：`PaiSmart2025`
- Elasticsearch elastic 密码：`PaiSmart2025`
- MinIO 账号：`admin`
- MinIO 密码：`PaiSmart2025`

## 本地开发

进入后端目录：

```powershell
cd D:\Project\My\SmartRag\backend_fastapi
```

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

运行测试：

```powershell
python -m pytest -q
```

本地快速启动默认使用 SQLite 并自动建表：

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

访问健康检查：

```text
http://localhost:8000/health
http://localhost:8000/health/dependencies
```

## Docker 部署

复制环境变量示例：

```powershell
Copy-Item .env.example .env
```

根据实际部署环境修改 `.env`。Docker 部署推荐至少配置：

```env
DATABASE_URL=mysql+pymysql://smart_rag:SmartRag2026@mysql:3306/pai_smart_fastapi?charset=utf8mb4
JWT_SECRET_KEY=change-me-in-production
AUTO_CREATE_SCHEMA=false
OBJECT_STORAGE_BACKEND=minio
SEARCH_BACKEND=elasticsearch
LLM_BACKEND=openai_compatible
LLM_API_BASE_URL=https://api.deepseek.com
LLM_API_KEY=your-deepseek-api-key
LLM_MODEL_NAME=deepseek-v4-flash
```

构建镜像：

```powershell
docker build -t smart-rag-fastapi:latest .
```

启动 API 服务：

```powershell
docker compose up -d --build
```

本项目 compose 默认接入外部基础设施网络 `pai_smart_default`，并通过容器名连接依赖：

- MySQL: `mysql:3306`
- Redis: `redis:6379`
- Elasticsearch: `es:9200`
- Kafka: `kafka:9092`
- MinIO: `minio:19000`

默认会启动本项目 API 容器：

- `smart-rag-fastapi`：FastAPI API 服务。

如需启用 Kafka 文件处理消费者，请确认 Kafka 的 advertised listener 对容器可达，然后额外启动：

```powershell
docker compose --profile consumer up -d --build file-consumer
```

消费者容器：

- `smart-rag-file-consumer`：Kafka 文件处理消费者，消费 `file-processing` 主题。

服务启动时会自动执行：

```text
alembic upgrade head
```

因此生产和 Docker 环境不依赖应用启动时自动建表。

## 环境变量说明

| 变量 | 说明 | 示例 |
| --- | --- | --- |
| `DATABASE_URL` | MySQL 或 SQLite 连接串 | `mysql+pymysql://smart_rag:SmartRag2026@mysql:3306/pai_smart_fastapi?charset=utf8mb4` |
| `JWT_SECRET_KEY` | JWT 签名密钥，生产必须修改 | `your-secret` |
| `AUTO_CREATE_SCHEMA` | 是否启动时自动建表，Docker 建议 `false` | `false` |
| `REDIS_URL` | Redis 连接串 | `redis://:PaiSmart2025@redis:6379/0` |
| `ES_URL` | Elasticsearch 地址 | `http://elastic:PaiSmart2025@es:9200` |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka 地址 | `kafka:9092` |
| `FILE_PROCESSING_BACKEND` | 文件处理后端：`local` 或 `kafka` | `kafka` |
| `FILE_PROCESSING_TOPIC` | Kafka 文件处理主题 | `file-processing` |
| `MINIO_ENDPOINT` | MinIO 地址 | `minio:19000` |
| `MINIO_ACCESS_KEY` | MinIO 账号 | `admin` |
| `MINIO_SECRET_KEY` | MinIO 密码 | `PaiSmart2025` |
| `MINIO_BUCKET` | 对象存储桶 | `pai-smart` |
| `OBJECT_STORAGE_BACKEND` | 文件存储后端：`database` 或 `minio` | `minio` |
| `SEARCH_BACKEND` | 检索后端：`database` 或 `elasticsearch` | `elasticsearch` |
| `ES_INDEX_NAME` | ES 索引名 | `pai_smart_documents` |
| `LLM_BACKEND` | LLM 后端：`mock` 或 `openai_compatible` | `openai_compatible` |
| `LLM_API_BASE_URL` | DeepSeek/OpenAI-compatible API 地址 | `https://api.deepseek.com` |
| `LLM_API_KEY` | DeepSeek API Key | `sk-...` |
| `LLM_MODEL_NAME` | DeepSeek 模型名 | `deepseek-v4-flash` |
| `EMBEDDING_BACKEND` | Embedding 后端：`mock` 或 `openai_compatible` | `mock` |
| `EMBEDDING_API_BASE_URL` | OpenAI-compatible Embedding API 地址 | `https://example.com/v1` |
| `EMBEDDING_API_KEY` | Embedding API Key | `sk-...` |
| `EMBEDDING_MODEL_NAME` | Embedding 模型名 | `embedding-compatible` |
| `EMBEDDING_DIMENSION` | Embedding 维度 | `8` |
| `WX_PAY_CALLBACK_SECRET` | 支付回调 HMAC 验签密钥 | `your-secret` |
| `RATE_LIMIT_BACKEND` | 限流后端：`memory` 或 `redis` | `redis` |
| `ADMIN_DANGEROUS_OPERATIONS_ENABLED` | 是否启用全量清理等高危管理接口 | `false` |

## 数据库迁移

手动执行迁移：

```powershell
python -m alembic upgrade head
```

创建新迁移时，应先修改 SQLAlchemy 模型，再生成或编写 Alembic revision，并运行测试。

## 验证部署

启动后执行：

```powershell
curl http://localhost:8000/health
curl http://localhost:8000/health/dependencies
```

若依赖未全部连通，`/health/dependencies` 会返回 `DEGRADED`，并在各依赖项中给出错误信息。

## 注意事项

- 生产环境必须修改 `JWT_SECRET_KEY`。
- Docker 部署建议使用 MySQL 和 Alembic，不建议使用 SQLite。
- 若使用已有 MySQL 容器，请先创建应用账号并授权：

```sql
CREATE DATABASE IF NOT EXISTS pai_smart_fastapi CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'smart_rag'@'%' IDENTIFIED BY 'SmartRag2026';
GRANT CREATE ON *.* TO 'smart_rag'@'%';
GRANT ALL PRIVILEGES ON pai_smart_fastapi.* TO 'smart_rag'@'%';
FLUSH PRIVILEGES;
```

- 若启用 `OBJECT_STORAGE_BACKEND=minio`，请确保 MinIO 可访问且账号密码正确。
- 若启用 `SEARCH_BACKEND=elasticsearch`，请确保 Elasticsearch 已启动并允许当前服务连接。
- LLM 已按 DeepSeek OpenAI-compatible API 配置，部署前必须设置 `LLM_API_KEY` 或宿主环境变量 `DEEPSEEK_API_KEY`。
- 上传解析支持 TXT、Markdown、PDF、DOCX；PDF/DOCX 解析依赖已随后端镜像安装。
- Elasticsearch 检索会使用查询 embedding 参与混合排序，并消耗 Embedding token。
- 当前微信支付回调使用 HMAC 验签占位实现，接入真实微信平台证书时需要替换验签逻辑。
- `ADMIN_DANGEROUS_OPERATIONS_ENABLED` 默认必须保持 `false`，仅在明确维护窗口中临时开启。
- `FILE_PROCESSING_BACKEND=kafka` 时，上传合并后会发布文件处理任务，需要单独运行消费者进程接收 Kafka 消息并调用文件处理任务：

```powershell
python -m app.consumers.file_processing_consumer
```

若在 Docker 中运行消费者，请使用：

```powershell
docker compose --profile consumer up -d --build file-consumer
```

注意：如果 Kafka 在基础设施 compose 中把 advertised listener 配成 `localhost:9092`，容器内消费者会在读取 broker 元数据后连接到自身的 `localhost`，导致连接失败。此时请将 Kafka advertised listener 调整为容器可访问的主机名，或在宿主机直接运行消费者进程。
