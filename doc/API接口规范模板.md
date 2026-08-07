# API 接口规范文档

> 本文档为接口规范模板，使用时复制一份并按实际项目填写。未确定的字段保留占位符。

## 文档信息

| 项目 | 内容 |
|---|---|
| 项目名称 |  |
| 文档版本 | v1.0.0 |
| 编写人 |  |
| 编写日期 |  |
| 审核人 |  |
| 状态 | 草稿 / 评审中 / 已发布 |

### 变更记录

| 版本 | 日期 | 变更说明 | 作者 |
|---|---|---|---|
| v1.0.0 |  | 初版 |  |

---

## 1. 通用约定

### 1.1 环境与 Base URL

| 环境 | Base URL |
|---|---|
| 开发环境（dev） | `http://dev.example.com/api` |
| 测试环境（staging） | `https://staging.example.com/api` |
| 生产环境（prod） | `https://api.example.com` |

> 约定：所有接口路径统一以 `/api` 开头（或网关统一剥离）。

### 1.2 协议与编码

- 传输协议：HTTPS（生产强制，开发环境除外）。
- 请求/响应格式：`application/json; charset=utf-8`。
- 文件上传：`multipart/form-data`。
- 时间格式：ISO 8601，统一为 UTC，形如 `2026-08-07T12:00:00Z`；需要本地时间时由前端自行转换。

### 1.3 认证方式

- 认证类型：Bearer Token（JWT），请求头携带：

```
Authorization: Bearer <token>
```

- Token 有效期：`xx` 分钟；刷新方式：`POST /api/auth/refresh`。
- 未认证返回 `401 Unauthorized`；无权限返回 `403 Forbidden`。

### 1.4 统一响应结构

所有接口（除文件流下载外）返回统一包装：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 业务状态码，`0` 表示成功，非 0 表示失败（见错误码表） |
| message | string | 提示信息，成功为 `success`，失败为可展示的错误说明 |
| data | object \| null | 业务数据；失败时为 `null` |

成功示例：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "name": "示例"
  }
}
```

失败示例：

```json
{
  "code": 10001,
  "message": "参数校验失败：name 不能为空",
  "data": null
}
```

> 约定：HTTP 状态码表达传输层结果（2xx 成功、4xx 客户端错误、5xx 服务端错误）；业务状态码表达业务层结果（始终随 body 返回）。

### 1.5 分页约定

列表类接口统一支持分页，请求参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| page | int | 否 | 1 | 页码，从 1 开始 |
| pageSize | int | 否 | 20 | 每页条数，最大值 100 |

分页响应 `data` 结构：

```json
{
  "data": {
    "list": [],
    "total": 0,
    "page": 1,
    "pageSize": 20
  }
}
```

| 字段 | 说明 |
|---|---|
| list | 当前页数据数组 |
| total | 满足条件的总条数 |
| page | 当前页码 |
| pageSize | 每页条数 |

### 1.6 过滤与排序

- 过滤参数命名：字段名直接作为查询参数，如 `?status=1&categoryId=3`。
- 排序参数：`sort=field1,-field2`（负号表示降序），如 `?sort=-createdAt`。

### 1.7 幂等与重试

- 幂等操作：写操作（POST/PUT/DELETE）支持幂等键请求头 `Idempotency-Key`，服务端 24 小时内对相同键返回首次结果。
- 客户端重试：仅对网络层错误（超时、5xx）重试，最多 3 次，间隔递增；4xx 不重试。

### 1.8 限流

- 默认限流：每 IP `xx` 次/分钟；登录等敏感接口额外限制 `xx` 次/分钟。
- 触发限流返回 HTTP `429 Too Many Requests`，响应头携带 `Retry-After`。

---

## 2. 接口文档模板

> 每个接口按下面结构单独一节。正文中「示例」二字表示示例接口，使用时替换。

### 2.1 获取示例列表

#### 基本信息

| 项目 | 内容 |
|---|---|
| 接口名称 | 获取示例列表 |
| 接口地址 | `GET /api/examples` |
| 鉴权要求 | 需要登录（Bearer Token） |
| 权限说明 | 需要 `example:read` 权限 |
| 版本 | v1 |
| 更新日期 |  |

#### 请求参数

Query 参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| page | int | 否 | 1 | 页码 |
| pageSize | int | 否 | 20 | 每页条数 |
| status | int | 否 | - | 状态：0-禁用，1-启用 |
| keyword | string | 否 | - | 关键字模糊搜索 |
| sort | string | 否 | -createdAt | 排序字段 |

Body/Path 参数（如适用）：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| （无） |  |  |  |  |

#### 请求示例

```
GET /api/examples?page=1&pageSize=10&status=1
Authorization: Bearer <token>
```

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "list": [
      {
        "id": 1,
        "name": "示例",
        "status": 1,
        "createdAt": "2026-08-07T12:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "pageSize": 10
  }
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| data.list[].id | int | 主键 ID |
| data.list[].name | string | 名称 |
| data.list[].status | int | 状态：0-禁用，1-启用 |
| data.list[].createdAt | string | 创建时间（ISO 8601 UTC） |

#### 错误响应

| HTTP 状态码 | 业务 code | message | 说明 |
|---|---|---|---|
| 401 | 40100 | 未认证或 Token 过期 | 需重新登录 |
| 403 | 40300 | 无权限 | 缺少 example:read 权限 |
| 500 | 50000 | 服务器内部错误 | 请联系管理员 |

---

## 3. 命名规范

### 3.1 URL 命名

- 资源使用复数名词，kebab-case（短横线分隔）：`/api/user-profiles`。
- 嵌套资源用路径层级表达：`/api/users/{userId}/orders`。
- 动词仅用于动作类接口：`POST /api/auth/login`、`POST /api/orders/{orderId}/cancel`。

### 3.2 方法与语义

| 方法 | 语义 |
|---|---|
| GET | 查询（幂等） |
| POST | 新建 / 触发动作（不幂等） |
| PUT | 全量更新（幂等） |
| PATCH | 部分更新 |
| DELETE | 删除（幂等） |

### 3.3 字段命名

- 请求/响应字段统一 camelCase：`createdAt`、`pageSize`。
- 数据库字段 snake_case，由后端在序列化时转换。
- 布尔字段以 `is`/`has`/`can` 开头：`isActive`、`canEdit`。

### 3.4 错误码规范

- 错误码为 5 位整数：`模块号(2位) + 序号(3位)`，如 `10xxx` 通用、`11xxx` 用户、`12xxx` 订单。
- `code=0` 保留给成功；`code<0` 不使用。

---

## 4. 附录

### 4.1 HTTP 状态码速查表

| 状态码 | 含义 | 典型场景 |
|---|---|---|
| 200 | 成功 | GET/PUT/PATCH 成功 |
| 201 | 已创建 | POST 新建成功 |
| 204 | 无内容 | DELETE 成功 |
| 400 | 请求错误 | 参数缺失或格式错误 |
| 401 | 未认证 | Token 缺失/过期 |
| 403 | 无权限 | 已认证但权限不足 |
| 404 | 资源不存在 | 路径错误或 ID 不存在 |
| 409 | 冲突 | 唯一约束冲突、状态冲突 |
| 422 | 校验失败 | 业务规则校验不通过 |
| 429 | 限流 | 请求过于频繁 |
| 500 | 服务器错误 | 未捕获异常 |

### 4.2 通用错误码表

| 业务 code | HTTP 状态码 | message | 说明 |
|---|---|---|---|
| 10001 | 400 | 参数校验失败 | 参数缺失或格式错误 |
| 10002 | 401 | 未认证或登录过期 | 需要重新登录 |
| 10003 | 403 | 无权限访问 | 权限不足 |
| 10004 | 404 | 资源不存在 | 目标资源未找到 |
| 10005 | 409 | 资源冲突 | 唯一约束或状态冲突 |
| 10006 | 429 | 请求过于频繁 | 触发限流 |
| 50000 | 500 | 服务器内部错误 | 未捕获异常，联系管理员 |

---

## 5. 其他约定（按需补充）

- 日志与追踪：请求头携带 `X-Request-Id`，响应头原样返回，便于链路追踪。
- 接口废弃：先标记 `Deprecated` 并在响应头 `Deprecation` 中给出过期日期，保留 `xx` 个月后移除。
- 版本演进：破坏性变更提升 URL 主版本（`/api/v2/...`）；非破坏性变更原地演进。
