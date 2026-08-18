# API 接口规范文档

> 本文档为接口规范模板，使用时复制一份并按实际项目填写。未确定的字段保留占位符。

## 文档信息

| 项目 | 内容 |
|---|---|
| 项目名称 | 振凡命理 |
| 文档版本 | v1.0.5 |
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
| v1.0.3 | 2026-08-13 | 同步简版报告契约与 focusTags：提交测算信息新增 focusTags（定制报告章节）；获取报告标记为 A 阶段已实现（简版契约：score/rank/scoreNote/analysis/karma/lockedPreview，含解锁/未解锁两态与 wecom 占位说明）；新增 dev 模拟解锁接口 pay-success-mock（仅 APP_ENV=dev 注册，生产 404） |  |
| v1.0.4 | 2026-08-16 | 测算单人化：提交测算信息（§2.3）与重新获取预览报告（§2.4）由双人（nameA/nameB/birthA/birthB）改为单人（name/birth/birthHour），focusTags 取值更新为单人 5 键；报告契约内容单人化（§2.8：title 为「姓名 · 八字命盘详批（姻缘预览）」、rank 五档、karma 三章节、lockedPreview 两章节） |  |
| v1.0.5 | 2026-08-16 | 删除预览报告 contentUrl 字段（§2.3/§2.4 响应示例）：静态报告文件未落地，契约内容全部内联返回；同步移除前端 /static 代理与后端静态文件服务说明 |  |
| v1.0.6 | 2026-08-16 | 生产同域部署：前端静态产物改由 backend 托管（/assets + SPA 回退 index.html），nginx 仅 TLS 反代 |  |
| v1.0.7 | 2026-08-18 | 微信支付 V3 支付闭环落地：创建订单（§2.5）支付配置齐全时返回真实 payType/payUrl/codeUrl（H5/Native），否则 null 降级；微信支付回调（§2.10）改为已实现（验签/AES-GCM 解密/幂等/恰好一次解锁）；新增查单与对账补偿说明；关单同步调用微信关单；删除 §2.11 退款回调（产品决策移除退款功能，退款接口/回调/模型/配置全部下线） |  |
| v1.0.8 | 2026-08-18 | 报告交付模式变更：获取报告（§2.8）改为**一律返回锁定态**（title + locked=true + lockedPreview），不再下发 score/rank/analysis/karma 等完整内容——付费后由人工经企业微信交付完整结果；wecom 字段改为「已支付 + 配置企微二维码」时返回；§2.8 错误响应移除 14002（该错误码定义保留于 §4.3，接口不再抛出） |  |

---

## 1. 通用约定

### 1.1 环境与 Base URL

| 环境 | Base URL |
|---|---|
| 开发环境（dev） | `http://127.0.0.1:8000/api`（后端本地）；前端 Vite dev server 代理转发 `/api` |
| 测试环境（staging） | `https://staging.<域名>/api` |
| 生产环境（prod） | `https://<域名>/api`（同域部署：nginx/NPM 仅反代，前端静态由 backend 托管） |

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
> 例外：回调接口（微信支付 `POST /api/pay/notify`、企业微信 `POST /api/wecom/notify`）不遵循统一包装，按微信/企微协议返回（`SUCCESS`/`FAIL`、`echostr`/`success`），见 §2.10~2.11。

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

> 公开接口默认免鉴权（见 §1.3）；回调接口见 §2.10~2.11（例外协议，不遵循统一包装）。

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
| name | string | 是 | 姓名/昵称（2~20 字符，中文/英文/间隔号） |
| birth | string | 是 | 出生日期，`YYYY-MM-DD`（1900-01-01 至今天） |
| birthHour | string | 否 | 出生时辰（十二时辰之一：`子`~`亥`；不填或空串视为时辰不详） |
| isLunar | boolean | 否 | 出生日期是否农历（默认 false，服务端换算） |
| focusTags | string[] | 否 | 关注点标签数组，用于定制报告章节，取值：`正缘桃花期`/`婚后财运旺衰`/`性格解析`/`事业运势`/`避坑锦囊`；不传则按默认章节生成 |

> 请求头：`Idempotency-Key` 可选（服务端 24 小时内同键返回首次结果；未携带则不幂等去重）。与创建订单（§2.5 强制必填）不同，本接口不强制。

#### 请求示例

```
POST /api/profiles
Content-Type: application/json
Idempotency-Key: 8f14e45f-8b32-4d3a-9c1d-7e2b3a4c5d6e

{
  "name": "张三",
  "birth": "1995-08-15",
  "birthHour": "子",
  "isLunar": false,
  "focusTags": ["正缘桃花期", "婚后财运旺衰"]
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
      "title": "张三 · 姻缘运势测算预览",
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
    "name": "张三",
    "birth": "1995-08-15",
    "previewReport": {
      "title": "张三 · 姻缘运势测算预览",
      "locked": true,
      "lockedNote": "完整版需付费解锁"
    }
  }
}
```

> 响应说明：`name`/`birth` 为脱敏展示用字段（前端自行掩码：姓名留首字打星号、日期仅显年月）；后端仅返回明文供前端脱敏渲染，不含密文。

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
    "payType": "h5",
    "payUrl": "https://wx.tenpay.com/cgi-bin/mmpayweb-bin/checkmweb?...",
    "codeUrl": null
  }
}
```

> 支付配置齐全（微信支付商户参数就绪）时：`payType` 为 `h5`（拉起微信）或 `native`（扫码），对应填充 `payUrl`/`codeUrl`；配置未就绪时三字段恒为 `null` 降级（订单仍可创建，前端展示待支付）。

#### 响应字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| data.orderNo | string | 内部订单号 |
| data.amount | int | 实际应付金额（分） |
| data.payType | string \| null | `h5`（拉起微信）/ `native`（扫码）；支付配置未就绪时为 `null` |
| data.payUrl | string \| null | H5 支付跳转 URL（payType=h5 时）；否则 null |
| data.codeUrl | string \| null | 扫码支付二维码内容（payType=native 时）；否则 null |

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
    "payType": "h5",
    "payUrl": "https://wx.tenpay.com/cgi-bin/mmpayweb-bin/checkmweb?...",
    "codeUrl": null,
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
| data.outTradeNo | string | 微信商户订单号（= orderNo） |
| data.state | string | 状态机：CREATED/PAID/UNLOCKED/DELIVERED/ADDED_WECOM/CLOSED |
| data.payType | string \| null | 实际支付方式：`auto` 请求会被服务端路由为 `h5`/`native` 并回写；支付配置未就绪时为 `null` |
| data.payUrl | string \| null | H5 支付跳转 URL（payType=h5 时）；否则 null |
| data.codeUrl | string \| null | 扫码支付二维码内容（payType=native 时）；否则 null |
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

> 支付配置就绪时同步调用微信关单接口（微信关单失败不阻塞本地关单，由对账补偿兜底）；仅 CREATED 可关，已支付 12002，其余状态 12003。

#### 错误响应

| HTTP 状态码 | 业务 code | message | 说明 |
|---|---|---|---|
| 404 | 10004 | 资源不存在 | 订单不存在 |
| 409 | 12002 | 订单已支付 | 已支付订单不可关单 |
| 409 | 12003 | 订单状态不允许操作 | 非 CREATED 状态不可关单 |
| 500 | 50000 | 服务器内部错误 | 联系管理员 |

### 2.8 获取报告（含企微活码）

#### 基本信息

| 项目 | 内容 |
|---|---|
| 接口名称 | 获取报告（含企微活码） |
| 接口地址 | `GET /api/orders/{orderNo}/report` |
| 鉴权要求 | 公开（免鉴权），服务端强制校验订单支付状态与 profile 归属 |
| 实现状态 | **A 阶段已实现** |
| 版本 | v1 |

> 说明：**本期系统不在页面下发完整测算结果**（评分/总评/章节详批等），付费后由人工通过企业微信交付完整结果。因此本接口**无论订单状态如何，一律返回锁定态**：`title` + `locked=true` + `lockedPreview`（2 条预览章节，付费前后一致）。`wecom` 字段仅在订单已支付（PAID/UNLOCKED/DELIVERED/ADDED_WECOM）且配置了企微二维码时返回；否则为 `null`。

#### 响应示例（已支付，返回企微引导）

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "orderNo": "S20260809001",
    "state": "UNLOCKED",
    "report": {
      "title": "张三 · 八字命盘详批（姻缘预览）",
      "locked": true,
      "lockedPreview": [
        { "title": "正缘画像与桃花旺衰节点", "body": "完整版将生成你的专属正缘画像，推演未来数年桃花旺衰与脱单关键节点，并给出应期把握之法。付费解锁后即可查看。" },
        { "title": "婚后财运走势与家庭财富规划", "body": "完整版将测算婚后财运旺衰与家庭财富走势，助力家宅兴旺、财库充盈。付费解锁后即可查看。" }
      ]
    },
    "wecom": {
      "qrcodeUrl": "https://qywx.../contact",
      "note": "已生成专属客服码,扫码添加后由人工为您深度测算"
    }
  }
}
```

#### 响应示例（未支付 / 未配置企微）

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "orderNo": "S20260809001",
    "state": "CREATED",
    "report": {
      "title": "张三 · 八字命盘详批（姻缘预览）",
      "locked": true,
      "lockedPreview": [
        { "title": "正缘画像与桃花旺衰节点", "body": "完整版将生成你的专属正缘画像，推演未来数年桃花旺衰与脱单关键节点，并给出应期把握之法。付费解锁后即可查看。" },
        { "title": "婚后财运走势与家庭财富规划", "body": "完整版将测算婚后财运旺衰与家庭财富走势，助力家宅兴旺、财库充盈。付费解锁后即可查看。" }
      ]
    },
    "wecom": null
  }
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| data.state | string | 订单状态：CREATED/PAID/UNLOCKED/DELIVERED/ADDED_WECOM/CLOSED；已支付态为 PAID/UNLOCKED/DELIVERED/ADDED_WECOM |
| data.report | object | 报告内容；**恒为锁定态**：仅含 title/locked/lockedPreview（locked=true），不再返回 score/rank/analysis/karma 等完整字段 |
| data.report.title | string | 报告标题（`姓名 · 八字命盘详批（姻缘预览）`）；报告记录缺失时返回兜底标题 |
| data.report.locked | boolean | 恒为 `true`（完整结果由人工企微交付，页面不展示） |
| data.report.lockedPreview | array | 锁定预览 `[{title, body}]`（2 条：正缘画像与桃花旺衰节点 / 婚后财运走势与家庭财富规划），付费前后均返回；报告记录缺失时返回默认预览 |
| data.wecom | object \| null | 企微加好友信息；已支付且配置 `WECOM_QRCODE_URL` 时返回，否则 null |
| data.wecom.qrcodeUrl | string | 企微二维码 URL。当前为配置占位 URL（环境变量 `WECOM_QRCODE_URL`）；企微真活码（state=订单号归因）后续接入后填充 |
| data.wecom.note | string | 加好友提示语 |

#### 错误响应

| HTTP 状态码 | 业务 code | message | 说明 |
|---|---|---|---|
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
| 实现状态 | **A 阶段已实现** |
| 版本 | v1 |
| 协议 | **例外**：不遵循统一包装，返回 `{"code":"SUCCESS"}` / `{"code":"FAIL"}` |

#### 处理流程

1. 验签：`Wechatpay-Signature` 头 + 微信平台证书验签，失败返回 `FAIL`
2. 解密：`resource` 字段 AES-256-GCM 解密出明文（transaction_id、amount.total、out_trade_no、trade_state）
3. 幂等：订单已支付/已解锁直接返回 `SUCCESS`（不重复解锁）
4. 一致性：`amount.total` 与订单金额比对，不一致告警并拒绝（防改价/防串单）
5. 成功：事务内 CAS（`UPDATE ... WHERE state='CREATED'`）推进订单状态并解锁完整报告，保证并发回调「恰好一次」解锁；重复回调幂等返回 `SUCCESS`

#### 错误响应

| HTTP 状态码 | body | 说明 |
|---|---|---|
| 200 | `{"code":"SUCCESS"}` | 处理成功 |
| 200 | `{"code":"FAIL"}` | 验签/解密/业务校验失败，微信将重试 |

> 对账兜底：支付配置就绪时后台定时任务（每 5 分钟）扫描超 30 分钟仍为 CREATED 的订单，调用微信查单接口按结果推进状态；微信平台证书未配置时回调一律返回 `FAIL`（不静默放行）。

### 2.11 企业微信事件回调

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

### 2.12 模拟支付成功（dev 联调专用）

#### 基本信息

| 项目 | 内容 |
|---|---|
| 接口名称 | 模拟支付成功（解锁报告） |
| 接口地址 | `POST /api/orders/{orderNo}/pay-success-mock` |
| 鉴权要求 | 公开（免鉴权） |
| 实现状态 | **仅开发环境可用**（APP_ENV=dev 时注册路由；生产返回 404） |
| 版本 | v1 |

> 说明：仅用于本地联调打通「解锁 → 获取报告」链路。开发/联调环境通过本接口模拟支付成功，将订单置为已解锁并落 mock 支付流水。生产环境（APP_ENV=prod）路由不注册，请求返回 HTTP 404（FastAPI 默认响应，无统一业务包装）；正式支付走 §2.10 微信支付回调。

#### 请求示例

```
POST /api/orders/S20260809001/pay-success-mock
```

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "orderNo": "S20260809001",
    "state": "UNLOCKED"
  }
}
```

> 响应 `state` 为 `UNLOCKED`（模拟支付成功后订单进入已支付态）；报告接口不展示完整内容，正式支付链路见 §2.8 与 §2.10。

#### 错误响应

| HTTP 状态码 | 业务 code | message | 说明 |
|---|---|---|---|
| 404 | 10004 | 资源不存在 | 订单不存在（dev 环境） |
| 500 | 50000 | 服务器内部错误 | 联系管理员 |

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
