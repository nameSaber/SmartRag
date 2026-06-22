# SmartRag / PaiSmart FastAPI 开发续接说明

## 当前目标

根据 `D:\Project\Github\PaiSmart-main\PaiSmart-main\docs\fastapi-refactor-technical-spec.md`，在本仓库从零实现 PaiSmart 的 FastAPI 后端，接口、权限语义、响应结构、数据模型和 Docker 部署方式需要尽量 1:1 兼容原 PaiSmart 前端。

## 用户硬性要求

- 禁止批量删除文件或目录。
- 不要使用 `del /s`、`rd /s`、`rmdir /s`、`Remove-Item -Recurse`、`rm -rf`。
- 需要删除文件时，只能一次删除一个明确路径的文件，例如 `Remove-Item "C:\path\to\file.txt"`。
- 如果需要批量删除文件，必须停止操作并询问用户，让用户手动删除。
- 开发环境已通过 Docker 部署，参考文档中的 `docker-compose.yaml`。
- 本项目自身也必须支持 Docker 部署。
- 每完成一个模块或接口，必须先测试通过，再开发下一个模块或接口。
- 每完成一个模块或接口，提交至github
- 代码中需要有合理的简体中文注释。

## 已启动的实现路线

1. 先搭建 `backend_fastapi/` 工程骨架。
2. 完成公共底座：配置、数据库、统一响应、异常处理、JWT、安全依赖。
3. 完成认证与用户模块：
   - `POST /api/v1/users/register`
   - `POST /api/v1/users/login`
   - `GET /api/v1/users/me`
   - `GET /api/v1/users/org-tags`
   - `PUT /api/v1/users/primary-org`
   - `GET /api/v1/users/usage`
   - `GET /api/v1/users/upload-orgs`
   - `POST /api/v1/users/logout`
   - `POST /api/v1/users/logout-all`
   - `GET /api/v1/users/token-records`
   - `POST /api/v1/auth/refreshToken`
   - `GET /api/v1/auth/error`
4. 每个模块完成后运行对应 pytest。
5. 后续模块顺序：上传/文档/检索 -> 聊天/会话 -> 管理后台 -> 充值支付 -> Docker 全量联调。

## Docker 依赖摘要

外部依赖由用户已有 compose 提供：

- MySQL: `localhost:3306`，root 密码 `PaiSmart2025`
- Redis: `localhost:6379`，密码 `PaiSmart2025`
- Elasticsearch: `localhost:9200`，密码 `PaiSmart2025`
- Kafka: `localhost:9092`
- MinIO: `localhost:19000`，账号 `admin`，密码 `PaiSmart2025`

本项目需要提供自己的 Dockerfile 和 compose 服务，用来连接上述依赖。

## 接口响应约定

常规成功响应：

```json
{"code": 200, "message": "success", "data": {}}
```

失败响应也保留 `data`：

```json
{"code": 400, "message": "error message", "data": null}
```

## 当前实现状态

- 本文件已创建，用于后续续接。
- 已创建 `backend_fastapi/` FastAPI 工程骨架、`Dockerfile`、项目级 `docker-compose.yaml`。
- 已完成公共底座：配置、数据库、统一响应、业务异常、JWT、安全依赖。
- 已完成并测试通过认证与用户模块。
- 已完成并测试通过上传/文档/检索模块的第一版闭环：chunk 上传、状态、合并、预览、下载、可访问文档、关键字检索。
- 已完成并测试通过聊天与会话模块的第一版闭环：会话创建/列表/历史/归档、生成快照、反馈、WebSocket `/chat/{token}`。
- 已完成并测试通过管理后台与充值支付第一版：管理员用户列表、状态、组织标签、token 增发、套餐、下单、支付回调、订单查询。
- 已完成并推送 Alembic 迁移模块：Docker 启动执行 `alembic upgrade head`，本地/测试保留 `AUTO_CREATE_SCHEMA` 快速建表。
- 已完成并推送依赖健康检查模块：MySQL/Redis/Elasticsearch/Kafka/MinIO 状态通过 `/health/dependencies` 和 `/api/v1/admin/status` 返回。
- 已完成并推送 MinIO 对象存储后端：Docker 环境可通过 `OBJECT_STORAGE_BACKEND=minio` 将分片和合并文件写入 MinIO。
- 已完成并推送 Elasticsearch 检索后端：Docker 环境可通过 `SEARCH_BACKEND=elasticsearch` 写入和查询 ES 索引。
- 已完成并推送 LLM 网关与 token 消耗：支持 `mock` 和 OpenAI-compatible 调用结构，对话会写入 LLM token 消费账本。
- 已完成并推送管理后台配置扩展：邀请函、限流配置、模型供应商、用户组织标签分配。
- 已完成并推送支付回调签名校验：支持 `WX_PAY_CALLBACK_SECRET` HMAC 验签，未配置时允许本地开发跳过。
- 已完成并推送部署 `README.md`。
- 已完成并推送 Redis 限流模块：注册、登录、聊天入口已接入滑动窗口和日窗口限流。
- 已完成并推送 Kafka 文件处理与 Embedding 网关：支持发布文件处理任务、mock/OpenAI-compatible embedding、embedding token 消耗和切块向量持久化。
- 已完成并推送 WebSocket 流式输出与取消状态。
- 已完成并推送后台运维模块：会话管理、MinIO 迁移、审计日志、高危清理开关。
- 用户已选择 LLM 使用 DeepSeek；配置示例切到 `https://api.deepseek.com` 和 `deepseek-v4-flash`。
- 已完成并推送独立 Kafka 文件处理消费者入口，可用 `python -m app.consumers.file_processing_consumer` 启动。
- 已完成并推送 TXT/Markdown/PDF/DOCX 文件解析器。
- 已完成并推送 Elasticsearch 关键词 + 向量混合检索，并记录查询 embedding token 消耗。
- 当前测试命令：在 `backend_fastapi/` 执行 `python -m pytest -q`。
- 最近一次结果：`25 passed`。

## 后续优先级

1. 将 WebSocket 生成流程重构为边流式生成边持久化，避免 DeepSeek 非流式与流式双路径割裂。
2. PDF/DOCX 解析继续增强页码、标题层级、anchor 定位。
3. 使用用户 Docker 依赖环境做一次端到端联调。
