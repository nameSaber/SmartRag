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
DATABASE_URL=mysql+pymysql://root:PaiSmart2025@host.docker.internal:3306/pai_smart_fastapi?charset=utf8mb4
JWT_SECRET_KEY=change-me-in-production
AUTO_CREATE_SCHEMA=false
OBJECT_STORAGE_BACKEND=minio
SEARCH_BACKEND=elasticsearch
LLM_BACKEND=mock
```

构建镜像：

```powershell
docker build -t smart-rag-fastapi:latest .
```

启动 API 服务：

```powershell
docker compose up -d --build
```

服务启动时会自动执行：

```text
alembic upgrade head
```

因此生产和 Docker 环境不依赖应用启动时自动建表。

## 环境变量说明

| 变量 | 说明 | 示例 |
| --- | --- | --- |
| `DATABASE_URL` | MySQL 或 SQLite 连接串 | `mysql+pymysql://root:PaiSmart2025@host.docker.internal:3306/pai_smart_fastapi?charset=utf8mb4` |
| `JWT_SECRET_KEY` | JWT 签名密钥，生产必须修改 | `your-secret` |
| `AUTO_CREATE_SCHEMA` | 是否启动时自动建表，Docker 建议 `false` | `false` |
| `REDIS_URL` | Redis 连接串 | `redis://:PaiSmart2025@host.docker.internal:6379/0` |
| `ES_URL` | Elasticsearch 地址 | `http://elastic:PaiSmart2025@host.docker.internal:9200` |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka 地址 | `host.docker.internal:9092` |
| `MINIO_ENDPOINT` | MinIO 地址 | `host.docker.internal:19000` |
| `MINIO_ACCESS_KEY` | MinIO 账号 | `admin` |
| `MINIO_SECRET_KEY` | MinIO 密码 | `PaiSmart2025` |
| `MINIO_BUCKET` | 对象存储桶 | `pai-smart` |
| `OBJECT_STORAGE_BACKEND` | 文件存储后端：`database` 或 `minio` | `minio` |
| `SEARCH_BACKEND` | 检索后端：`database` 或 `elasticsearch` | `elasticsearch` |
| `ES_INDEX_NAME` | ES 索引名 | `pai_smart_documents` |
| `LLM_BACKEND` | LLM 后端：`mock` 或 `openai_compatible` | `mock` |
| `LLM_API_BASE_URL` | OpenAI-compatible API 地址 | `https://example.com/v1` |
| `LLM_API_KEY` | LLM API Key | `sk-...` |
| `LLM_MODEL_NAME` | LLM 模型名 | `gpt-compatible` |
| `WX_PAY_CALLBACK_SECRET` | 支付回调 HMAC 验签密钥 | `your-secret` |

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
- 若启用 `OBJECT_STORAGE_BACKEND=minio`，请确保 MinIO 可访问且账号密码正确。
- 若启用 `SEARCH_BACKEND=elasticsearch`，请确保 Elasticsearch 已启动并允许当前服务连接。
- 当前微信支付回调使用 HMAC 验签占位实现，接入真实微信平台证书时需要替换验签逻辑。

