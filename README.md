# 振凡命理 · 正缘姻缘测算 · 桃花期与正缘画像

> 快手磁力智投姻缘测算 H5。姻缘正缘画像、桃花旺衰、婚后走势与相处之道，预览报告免费，完整姻缘天书付费解锁后由企微人工交付。

## 技术栈

- **前端** `src/`：React 19 + Vite 8 + TypeScript 6 + Tailwind 4 + React Router 7
- **后端** `app/`：FastAPI + SQLAlchemy + SQLite + Alembic + AES-256-GCM 加密
- 单 `package.json` / `requirements.txt`，路径别名 `@` → `src/`（`vite.config.ts:11`）

## 快速开始（Windows PowerShell）

```powershell
# 前端
npm install
npm run dev                 # Vite :5173，代理 /api → 127.0.0.1:8000

# 后端（免激活 .venv）
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt -r requirements-dev.txt
.venv\Scripts\python -m uvicorn app.main:app --reload          # :8000
.venv\Scripts\python -m pytest

# 生产迁移
alembic upgrade head
.venv\Scripts\python scripts/init_prod.py
```

## 环境配置

复制 `.env.example` → `.env`（生产用 `.env.production.example`）。`app/core/config.py:11` `extra="ignore"` 容忍 `VITE_*` 共存。

| 变量 | 说明 |
|---|---|
| `DATABASE_URL` | 默认 `sqlite:///./app.db`（gitignored），生产必须 `sqlite:////data/app.db` |
| `BIRTH_DATA_KEY` | base64 32B AES-256-GCM，`openssl rand -base64 32`；dev 为空自动生成临时密钥，prod 缺失直接 `RuntimeError` |
| `CORS_ORIGINS` | JSON 数组，如 `["http://localhost:5173"]` |
| `VITE_API_BASE_URL` | 默认 `/api`（`src/api/http.ts:3`），Vite 代理已配置 |
| `WXPAY_*` | 均可选，未配时订单可创建但 `payType/payUrl/codeUrl=null` 优雅降级 |
| `RECONCILE_ENABLED` | 默认 `false`，生产 `true`（每 300s 扫描超时 `CREATED` 订单） |

## 项目结构

```
src/pages/        Landing / Calc / Order / Pay / Report
src/components/   生辰选择、装饰、UI 原语
src/api/          http / profiles / orders / products
app/routers/      health / products / profiles / orders / pay
app/services/     divination / report / order_service / pay_service / wechatpay / reconcile
app/models/       ORM（Profile / Order / Product / Report / PayTransaction 等）
```

## 文档

`doc/本地开发文档.md`、`doc/开发文档.md`、`doc/生产部署文档.md`、`doc/API接口规范模板.md`（信封 `{code,message,data}` 与错误码 100xx/120xx/130xx/50000）

## Docker

```powershell
docker compose up --build
```

`frontend-build`（`npm run build` → `frontend_dist`）与 `migrate`（`init_prod.py`）完成后启动 `backend`（`:8000`），单副本 SQLite。宿主机 nginx 仅做 TLS + 反代到 `<host-IP>:8000`。
