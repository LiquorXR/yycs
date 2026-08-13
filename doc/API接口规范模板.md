# API 接口规范文档

> 本文档为接口规范模板，使用时复制一份并按实际项目填写。未确定的字段保留占位符。

## 文档信息

| 项目 | 内容 |
|---|---|
| 项目名称 | 振凡命理 |
| 文档版本 | v1.0.0 |
| 编写人 |  |
| 编写日期 | 2026-08-11 |
| 审核人 |  |
| 状态 | 已发布 |

### 变更记录

| 版本 | 日期 | 变更说明 | 作者 |
|---|---|---|---|
| v1.0.0 | 2026-08-11 | 初版：模板落地，按本项目填充通用约定、错误码体系与全部接口 |  |
| v1.0.1 | 2026-08-12 | 补充接口实现状态标注（A 阶段已实现 / B 阶段未实现 / 预留）；创建订单请求参数补充 amount（防改价） |  |
| v1.0.2 | 2026-08-13 | 与代码实现核对同步：补齐全部已实现接口状态标注、订单详情字段、创建订单 A 阶段返回形态（payType 等为 null）、关单响应；修正生产 Base URL（同域反代）与限流实现状态说明 |  |

---

## 1. 通用约定

### 1.1 环境与 Base URL

| 环境 | Base URL |
|---|---|
| 开发环境（dev） | `http://127.0.0.1:8000/api`（后端本地）；前端 Vite dev server 代理转发 `/api` |
| 测试环境（staging） | `https://staging.<域名>/api` |
| 生产环境（prod） | `https://<域名>/api`（同域部署：nginx 托管静态 + 反代 /api） |

> 约定：所有接口路径统一以 `/api` 开头（或网关统一剥离）。
> 注：`<域名>` 为 ICP 备案后实际域名（办理中），域名就绪后替换。

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

- Token 有效期：120 分钟；刷新方式：`POST /api/auth/refresh`（预留，本期无登录体系不实现）。
- 未认证返回 `401 Unauthorized`；无权限返回 `403 Forbidden`。
- **公开接口免鉴权**：本期投放侧 H5 接口全部公开（无用户登录），依靠风控策略（限流、金额白名单、渠道校验）防护，无需携带 Token。鉴权仅用于后续商家后台接口，届时在「鉴权要求」列标注。

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
> 例外：三方回调接口（微信支付 `POST /api/pay/notify`、退款 `POST /api/refund/notify`、企业微信 `POST /api/wecom/notify`）不遵循统一包装，按微信/企微协议返回（`SUCCESS`/`FAIL`、`echostr`/`success`），见 §2.10~2.12。

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

- 默认限流：每 IP+UA 组合 60 次/分钟；下单类接口（`POST /api/orders`）限制 10 次/分钟；数值按风控策略可调。
- 触发限流返回 HTTP `429 Too Many Requests`，响应头携带 `Retry-After`，业务 code `10006`。
- **实现状态：规划中（本期未实现）**——错误码 `10006` 与 429 映射已预留（errors.py），限流中间件待风控策略落地。

---

## 2. 接口文档

> 公开接口默认免鉴权（见 §1.3）；回调接口见 §2.10~2.12（例外协议，不遵循统一包装）。

### 2.1 产品列表

#### 基本信息

| 项目 | 内容 |
|---|---|
| 接口名称 | 产品列表 |
| 接口地址 | `GET /api/products` |
| 鉴权要求 | 公开（免鉴权） |
| 实现状态 | **A 阶段已实现** |
| 版本 | v1 |

#### 请求参数

Query 参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| page | int | 否 | 1 | 页码 |
| pageSize | int | 否 | 20 | 每页条数，最大 100 |
| type | int | 否 | - | 产品类型：0-免费档，1-付费档 |

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "list": [
      { "id": 1, "name": "姻缘测算完整报告", "price": 9900, "type": 1, "freeFlag": 0, "status": 1 }
    ],
    "total": 1,
    "page": 1,
    "pageSize": 20
  }
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| data.list[].id | int | 产品 ID |
| data.list[].name | string | 产品名称 |
| data.list[].price | int | 价格（单位：分，禁止浮点） |
| data.list[].type | int | 类型：0-免费档，1-付费档 |
| data.list[].freeFlag | int | 免费标识：1-免费，0-付费 |
| data.list[].status | int | 状态：0-禁用（下架），1-启用 |

#### 错误响应

| HTTP 状态码 | 业务 code | message | 说明 |
|---|---|---|---|
| 500 | 50000 | 服务器内部错误 | 联系管理员 |

### 2.2 产品详情

#### 基本信息

| 项目 | 内容 |
|---|---|
| 接口名称 | 产品详情 |
| 接口地址 | `GET /api/products/{id}` |
| 鉴权要求 | 公开（免鉴权） |
| 实现状态 | **A 阶段已实现** |
| 版本 | v1 |

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "name": "姻缘测算完整报告",
    "price": 9900,
    "type": 1,
    "freeFlag": 0,
    "status": 1
  }
}
```

#### 错误响应

| HTTP 状态码 | 业务 code | message | 说明 |
|---|---|---|---|
| 404 | 13001 | 产品不存在或已下架 | 产品 ID 无效或已禁用 |
| 500 | 50000 | 服务器内部错误 | 联系管理员 |

### 2.3 提交测算信息

#### 基本信息

| 项目 | 内容 |
|---|---|
| 接口名称 | 提交测算信息（生成预览报告） |
| 接口地址 | `POST /api/profiles` |
| 鉴权要求 | 公开（免鉴权） |
| 实现状态 | **A 阶段已实现** |
| 版本 | v1 |

#### 请求参数

Body（JSON）：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| nameA | string | 是 | 甲方姓名（2~20 字符） |
| birthA | string | 是 | 甲方出生日期，`YYYY-MM-DD` |
| birthHourA | string | 否 | 甲方出生时辰（如 `子`/`午`，可空） |
| nameB | string | 是 | 乙方姓名（2~20 字符） |
| birthB | string | 是 | 乙方出生日期，`YYYY-MM-DD` |
| birthHourB | string | 否 | 乙方出生时辰（可空） |
| isLunar | boolean | 否 | 出生日期是否农历（默认 false，服务端换算） |

> 请求头：`Idempotency-Key` 可选（服务端 24 小时内同键返回首次结果；未携带则不幂等去重）。与创建订单（§2.5 强制必填）不同，本接口不强制。

#### 请求示例

```
POST /api/profiles
Content-Type: application/json
Idempotency-Key: 8f14e45f-8b32-4d3a-9c1d-7e2b3a4c5d6e

{
  "nameA": "张三",
  "birthA": "1995-08-15",
  "birthHourA": "子",
  "nameB": "李四",
  "birthB": "1997-02-03",
  "isLunar": false
}
```

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "profileId": "P2026080900123",
    "previewReport": {
      "title": "属相猪配牛·姻缘测算预览",
      "contentUrl": "/static/reports/P2026080900123_preview.html",
      "locked": true,
      "lockedNote": "完整版需付费解锁"
    }
  }
}
```

#### 错误响应

| HTTP 状态码 | 业务 code | message | 说明 |
|---|---|---|---|
| 400 | 10001 | 参数校验失败 | 参数缺失或格式错误 |
| 422 | 14001 | 测算信息无效 | 生辰/姓名校验失败 |
| 429 | 10006 | 请求过于频繁 | 触发限流 |
| 500 | 50000 | 服务器内部错误 | 联系管理员 |

### 2.4 重新获取预览报告

#### 基本信息

| 项目 | 内容 |
|---|---|
| 接口名称 | 重新获取预览报告 |
| 接口地址 | `GET /api/profiles/{profileId}/preview` |
| 鉴权要求 | 公开（免鉴权） |
| 实现状态 | **A 阶段已实现** |
| 版本 | v1 |

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "profileId": "P2026080900123",
    "previewReport": {
      "title": "属相猪配牛·姻缘测算预览",
      "contentUrl": "/static/reports/P2026080900123_preview.html",
      "locked": true,
      "lockedNote": "完整版需付费解锁"
    }
  }
}
```

#### 错误响应

| HTTP 状态码 | 业务 code | message | 说明 |
|---|---|---|---|
| 404 | 10004 | 资源不存在 | profileId 不存在 |
| 500 | 50000 | 服务器内部错误 | 联系管理员 |

### 2.5 创建订单

#### 基本信息

| 项目 | 内容 |
|---|---|
| 接口名称 | 创建订单 |
| 接口地址 | `POST /api/orders` |
| 鉴权要求 | 公开（免鉴权） |
| 实现状态 | **A 阶段已实现** |
| 版本 | v1 |

#### 请求参数

Body（JSON）：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| profileId | string | 是 | 测算信息 ID |
| productId | int | 是 | 产品 ID（金额以服务端产品表为准，杜绝前端改价） |
| paymentMethod | string | 否 | `auto`（默认，服务端路由）/ `h5` / `native` |
| adParams | object | 否 | 磁力投放归因：`{ad_id, creative_id, campaign_id, ...}` |
| amount | int | 否 | 防改价校验用：携带时须与产品表价格一致，否则返回 12001；不携带则以后端产品表为准 |

请求头：`Idempotency-Key` 必填（服务端 24 小时内同键返回首次结果）。

#### 请求示例

```
POST /api/orders
Content-Type: application/json
Idempotency-Key: 8f14e45f-8b32-4d3a-9c1d-7e2b3a4c5d6e

{
  "profileId": "P2026080900123",
  "productId": 1,
  "paymentMethod": "auto",
  "adParams": {"ad_id": "x", "creative_id": "y", "campaign_id": "z"}
}
```

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "orderNo": "S20260809001",
    "amount": 9900,
    "payType": null,
    "payUrl": null,
    "codeUrl": null
  }
}
```

> A 阶段（支付模块未落地）：`payType/payUrl/codeUrl` 恒为 `null`；B 阶段统一下单后填充（见响应字段说明）。

#### 响应字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| data.orderNo | string | 内部订单号 |
| data.amount | int | 实际应付金额（分） |
| data.payType | string \| null | A 阶段恒为 `null`；B 阶段为 `h5`（拉起微信）/ `native`（扫码） |
| data.payUrl | string \| null | H5 支付跳转 URL（B 阶段 payType=h5 时）；A 阶段为 null |
| data.codeUrl | string \| null | 扫码支付二维码内容（B 阶段 payType=native 时）；A 阶段为 null |

#### 错误响应

| HTTP 状态码 | 业务 code | message | 说明 |
|---|---|---|---|
| 400 | 10001 | 参数校验失败 | `Idempotency-Key` 缺失或 `paymentMethod` 非法（需为 auto/h5/native） |
| 400 | 12001 | 金额校验失败 | 防改价：下单金额与产品表不一致 |
| 404 | 10004 | 资源不存在 | profileId 不存在 |
| 404 | 13001 | 产品不存在或已下架 | 产品下架 |
| 429 | 10006 | 请求过于频繁 | 触发限流（规划中，本期未实现） |
| 500 | 50000 | 服务器内部错误 | 联系管理员 |

### 2.6 订单详情

#### 基本信息

| 项目 | 内容 |
|---|---|
| 接口名称 | 订单详情/状态 |
| 接口地址 | `GET /api/orders/{orderNo}` |
| 鉴权要求 | 公开（免鉴权） |
| 实现状态 | **A 阶段已实现** |
| 版本 | v1 |

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "orderNo": "S20260809001",
    "profileId": "P2026080900123",
    "productId": 1,
    "outTradeNo": "S20260809001",
    "amount": 9900,
    "state": "CREATED",
    "payType": "auto",
    "openid": "",
    "adParams": null,
    "failReason": null,
    "createdAt": "2026-08-09T04:12:00Z",
    "paidAt": null
  }
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| data.productId | int | 产品 ID |
| data.outTradeNo | string | 微信商户订单号（A 阶段 = orderNo） |
| data.state | string | 状态机：CREATED/PAID/UNLOCKED/DELIVERED/ADDED_WECOM/CLOSED/REFUNDING/REFUNDED |
| data.payType | string | 创建订单时传入的支付方式：auto / h5 / native |
| data.openid | string | 微信 openid（A 阶段为空串） |
| data.adParams | object \| null | 磁力投放归因参数（原样返回，未传为 null） |
| data.failReason | string \| null | 失败原因（正常为 null） |

#### 错误响应

| HTTP 状态码 | 业务 code | message | 说明 |
|---|---|---|---|
| 404 | 10004 | 资源不存在 | 订单不存在 |
| 500 | 50000 | 服务器内部错误 | 联系管理员 |

### 2.7 关单

#### 基本信息

| 项目 | 内容 |
|---|---|
| 接口名称 | 关单（超时/取消） |
| 接口地址 | `POST /api/orders/{orderNo}/close` |
| 鉴权要求 | 公开（免鉴权） |
| 实现状态 | **A 阶段已实现** |
| 版本 | v1 |

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "orderNo": "S20260809001",
    "state": "CLOSED"
  }
}
```

#### 错误响应

| HTTP 状态码 | 业务 code | message | 说明 |
|---|---|---|---|
| 404 | 10004 | 资源不存在 | 订单不存在 |
| 409 | 12002 | 订单已支付 | 已支付订单不可关单 |
| 409 | 12003 | 订单状态不允许操作 | 非 CREATED 状态不可关单 |
| 500 | 50000 | 服务器内部错误 | 联系管理员 |

### 2.8 获取报告

#### 基本信息

| 项目 | 内容 |
|---|---|
| 接口名称 | 获取报告（含企微活码） |
| 接口地址 | `GET /api/orders/{orderNo}/report` |
| 鉴权要求 | 公开（免鉴权），服务端强制校验订单支付状态与 profile 归属 |
| 实现状态 | **B 阶段未实现**（前端报告页已接入该接口，后端待实现） |
| 版本 | v1 |

#### 响应示例（付费已解锁）

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "orderNo": "S20260809001",
    "state": "DELIVERED",
    "report": { "title": "紫微缘分配对报告", "contentUrl": "/static/reports/S20260809001.html" },
    "wecom": {
      "addWay": "contact_way",
      "qrcodeUrl": "https://qywx...",
      "state": "S20260809001",
      "note": "已生成专属客服码,扫码添加后由人工为您深度测算"
    }
  }
}
```

#### 响应示例（未付费/未解锁）

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "orderNo": "S20260809001",
    "state": "CREATED",
    "report": {
      "title": "紫微缘分配对报告（预览）",
      "contentUrl": "/static/reports/P2026080900123_preview.html",
      "locked": true
    },
    "wecom": null
  }
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| data.report | object | 报告内容；未解锁时为预览掩码（locked=true） |
| data.report.contentUrl | string | 报告内容 URL（脱敏展示） |
| data.wecom | object \| null | 企微「联系我」活码；未解锁/未生成为 null |
| data.wecom.qrcodeUrl | string | 活码二维码 URL |
| data.wecom.state | string | 活码 state（=订单号，用于加好友归因） |

#### 错误响应

| HTTP 状态码 | 业务 code | message | 说明 |
|---|---|---|---|
| 403 | 14002 | 报告未解锁 | 未支付或他人 profile 越权拉取 |
| 404 | 10004 | 资源不存在 | 订单不存在 |
| 500 | 50000 | 服务器内部错误 | 联系管理员 |

### 2.9 交付状态

#### 基本信息

| 项目 | 内容 |
|---|---|
| 接口名称 | 交付状态/企微添加状态 |
| 接口地址 | `GET /api/orders/{orderNo}/delivery` |
| 鉴权要求 | 公开（免鉴权） |
| 实现状态 | **B 阶段未实现** |
| 版本 | v1 |

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "orderNo": "S20260809001",
    "state": "DELIVERED",
    "wecomAdded": false,
    "addedAt": null
  }
}
```

#### 错误响应

| HTTP 状态码 | 业务 code | message | 说明 |
|---|---|---|---|
| 404 | 10004 | 资源不存在 | 订单不存在 |
| 500 | 50000 | 服务器内部错误 | 联系管理员 |

### 2.10 微信支付回调

#### 基本信息

| 项目 | 内容 |
|---|---|
| 接口名称 | 微信支付结果回调 |
| 接口地址 | `POST /api/pay/notify` |
| 鉴权要求 | 无（微信平台证书/公钥验签） |
| 实现状态 | **B 阶段未实现**（支付模块） |
| 版本 | v1 |
| 协议 | **例外**：不遵循统一包装，返回 `{"code":"SUCCESS"}` / `{"code":"FAIL"}` |

#### 处理流程

1. 验签：`Wechatpay-Signature` 头 + 微信平台证书验签，失败返回 `FAIL`
2. 解密：`resource` 字段 AES-256-GCM 解密出明文（transaction_id、amount.total、out_trade_no、trade_state）
3. 幂等：订单已 PAID 直接返回 `SUCCESS`（不重复解锁）
4. 一致性：`amount.total` 与订单金额比对，不一致告警并拒绝
5. 成功：事务内解锁完整报告（CAS）+ 生成企微「联系我」活码（state=订单号）

#### 错误响应

| HTTP 状态码 | body | 说明 |
|---|---|---|
| 200 | `{"code":"SUCCESS"}` | 处理成功 |
| 200 | `{"code":"FAIL"}` | 验签/解密/业务校验失败，微信将重试 |

### 2.11 退款结果回调（预留）

#### 基本信息

| 项目 | 内容 |
|---|---|
| 接口名称 | 退款结果回调 |
| 接口地址 | `POST /api/refund/notify` |
| 鉴权要求 | 无（微信平台证书验签） |
| 实现状态 | **预留**（本期退款为人工审核后发起，回调逻辑预留） |
| 版本 | v1 |
| 协议 | **例外**：不遵循统一包装，返回 `SUCCESS`/`FAIL` |

> 本期退款流程为人工审核后发起，回调逻辑预留，接口可先返回 `FAIL` 占位。

### 2.12 企业微信事件回调

#### 基本信息

| 项目 | 内容 |
|---|---|
| 接口名称 | 企业微信事件回调 |
| 接口地址 | `POST /api/wecom/notify`（GET 用于 URL 验证） |
| 鉴权要求 | 无（msg_signature + Token + EncodingAESKey 验签） |
| 实现状态 | **B 阶段未实现**（企业微信服务模块） |
| 版本 | v1 |
| 协议 | **例外**：GET 校验返回 `echostr`；POST 事件处理成功返回 `success` |

#### 处理流程

1. GET 回调验证：`msg_signature` 校验后返回解密出的 `echostr`
2. POST 事件：验签解密 XML 明文，解析 `change_external_contact` / `AddExternalContact`
3. 归因：`state` 字段匹配 `WECOM_CONTACTS.state` → 更新订单外部联系人记录
4. 幂等：同 `external_userid` 重复事件不重复写
5. 处理失败返回非 `success`，企微将重推（最长 3 天）

---

## 3. 命名规范

### 3.1 URL 命名

- 资源使用复数名词，kebab-case（短横线分隔）：`/api/user-profiles`；本项目现有路径沿用既有命名（如 `/api/profiles`、路径参数 camelCase `{orderNo}`），新接口按本规范命名。
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

- 错误码为 5 位整数：`模块号(2位) + 序号(3位)`。
- 模块号分配：

| 模块号 | 模块 | 说明 |
|---|---|---|
| 10 | 通用 | 参数校验、认证、资源、限流等（见 §4.2） |
| 11 | 用户 | 预留（本期无登录体系） |
| 12 | 订单/支付 | 金额校验、状态冲突、支付拉起、回调验签 |
| 13 | 商品 | 产品不存在/下架 |
| 14 | 测算/报告 | 测算信息校验、报告解锁 |
| 15 | 企业微信 | 预留（活码/事件错误） |

- 业务错误码明细见 §4.3。
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

### 4.3 业务错误码表

| 业务 code | HTTP 状态码 | message | 说明 |
|---|---|---|---|
| 12001 | 400 | 金额校验失败 | 防改价：下单金额与产品表不一致 |
| 12002 | 409 | 订单已支付 | 重复支付/已支付订单操作冲突 |
| 12003 | 409 | 订单状态不允许操作 | 状态机约束（如非 CREATED 关单） |
| 12004 | 502 | 支付拉起失败 | H5 拉起微信失败，请改用扫码 |
| 12005 | 400 | 回调验签失败 | 微信回调验签/解密失败 |
| 13001 | 404 | 产品不存在或已下架 | 产品 ID 无效或已禁用 |
| 14001 | 422 | 测算信息无效 | 生辰/姓名校验失败 |
| 14002 | 403 | 报告未解锁 | 未支付或越权访问完整报告 |

---

## 5. 其他约定（按需补充）

- 日志与追踪：请求头携带 `X-Request-Id`，响应头原样返回，便于链路追踪。
- 接口废弃：先标记 `Deprecated` 并在响应头 `Deprecation` 中给出过期日期，保留 `xx` 个月后移除。
- 版本演进：破坏性变更提升 URL 主版本（`/api/v2/...`）；非破坏性变更原地演进。
