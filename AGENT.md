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
- 当前测试命令：在 `backend_fastapi/` 执行 `python -m pytest -q`。
- 最近一次结果：`6 passed`。

## 后续优先级

1. 将当前直接建表迁移为 Alembic 版本化迁移。
2. 接入真实 MySQL、Redis、Elasticsearch、Kafka、MinIO 客户端与健康检查。
3. 上传模块从数据库分片存储替换为 MinIO 分片/合并对象存储。
4. 检索模块从数据库 LIKE 替换为 Elasticsearch 关键字 + 向量混合检索。
5. 聊天模块接入真实 LLM 流式响应、生成取消、token 消耗与限流。
6. 管理后台继续补齐邀请函 CRUD、模型供应商 CRUD/测试、限流配置更新、会话管理、MinIO 迁移、全量清理的环境开关和审计日志。
7. 充值模块接入真实微信支付签名校验。
8. 使用用户 Docker 依赖环境做一次端到端联调。
