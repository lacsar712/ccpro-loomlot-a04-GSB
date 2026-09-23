# LoomLot-01 · 染坊缸染、色牢度抽检与回修复染

靛蓝染坊台：按 **染坊 → 染缸 → 染程 → 色牢度** 工序推进，异常时走 **回修复染** 旁支（复染挂原染程、双检结案、锁定染缸）。聚焦缸染调度与抽检，不是库存出入库系统。

## 技术栈

| 层 | 技术 |
| --- | --- |
| Backend | FastAPI + SQLAlchemy 2 + Pydantic v2 + Postgres + JWT |
| Frontend | Svelte 4 + Vite + svelte-spa-router |
| 部署 | docker-compose（db + backend + frontend/nginx） |

## 端口

| 服务 | 端口 |
| --- | --- |
| 前端 | **3600** |
| 后端 API | **8600** |
| PostgreSQL | **5439** |

数据库账号：`loomlot` / `loomlot` / 库名 `loomlot`。

## 演示账号

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| `admin` | `123456` | 染坊主管 |
| `dyer` | `123456` | 染程操作员 |

容器启动时 entrypoint 自动建表并 seed。

## 快速启动

```bash
cd D:\work\document\bytecode\claudeCodePro\LoomLot\LoomLot-01
docker compose up -d --build
```

浏览器：http://localhost:3600  
API：http://localhost:8600/api/health

停止：

```bash
docker compose down
```

## 业务实体

1. **DyeHouse** — `name`, `waterNote`, `notes`
2. **Vat** — `dyeHouseId`, `vatCode`, `fiberType`, `capacityL`, `status` ∈ `ready|dyeing|drain`，附带 `hasOpenRedye`（是否挂未结案复染，只读标记）
3. **DyeLot** — `vatId`, `recipeName`, `fabricKg`, `startedAt`, `operatorName`，附带 `hasOpenRedye`（只读标记）
4. **FastnessCheck** — `dyeLotId`, `checkedAt`, `washFastness`(1–5), `rubFastness`(>0), `tempC`, `notes`
5. **RedyeTicket（回修复染单）** — `dyeLotId`（原染程）、`vatId`（对账用，只读）、`defectDesc`（≥8 字）、`openedAt`（开单时刻，服务端生成）、`closedAt`（结案时刻，可空）、`openerName`（开单人）、`closerName`（结案人，可空）、`hasOpenRedye`

### 规则

**染程**

- 仅当染缸状态为 `ready` 或 `dyeing` 时可新建染程，否则 409
- 新建染程后，染缸状态自动设为 `dyeing`
- 可选接口：`POST /api/vats/{id}/drain` 将染缸置为 `drain`

**回修复染**

- 复染单挂在原染程上；缺陷说明至少 8 个字，开单时刻由服务端记录，开单人取当前登录用户，结案时刻可空
- 同一原染程存在未结案复染单时不可再开（应用层 409 + Postgres 部分唯一索引 `uq_open_redye_per_lot` 双重保证）
- **开立互不拦截**：复染单挂原染程，不改变染坊/染缸/染程的正常开立；染程开立只受染缸上“是否有未结案复染”约束
- **锁定**：存在未结案复染单的染缸，禁止再新建染程（409，含改挂到该缸）；复染结案后自动恢复
- **结案双检**：原染程上至少有两条色牢度抽检，且最新一条耐洗等级不低于上一条（按检测时间、再按 id 定序），否则结案返回 400
- **权限**：任意登录用户（操作员）均可开单；结案仅主管（`admin` 角色），否则 403
- **单一口径**：染程开立拦截、染程/染缸列表的 `hasOpenRedye` 标记、看板 `openRedyeCount` 计数全部复用后端 `app/services/redye.py` 的同一组查询，看板计数与复染单未结案列表严格一致，禁止各算

### 种子

初始数据含 **1 张未结案回修复染单**：挂在染缸 `V-01` 的原染程「靛蓝冷染三浸」上（锁定该缸）。该原染程有双检（耐洗 3 → 4，未回落），用主管账号对其结案即可演示解锁；操作员账号可演示开单但结案会被 403 拦截。

## 主要 API

- `POST /api/auth/login`（OAuth2 表单）
- `GET /api/auth/me`
- `GET/POST/PUT/DELETE /api/dye-houses`
- `GET/POST/PUT/DELETE /api/vats` · `POST /api/vats/{id}/drain`（列表与单查均带 `hasOpenRedye`）
- `GET/POST/PUT/DELETE /api/dye-lots`（列表与单查均带 `hasOpenRedye`；POST 在染缸挂未结案复染时返回 409）
- `GET/POST/PUT/DELETE /api/fastness-checks`
- `GET/POST /api/redye-tickets` · `GET /api/redye-tickets/{id}` · `POST /api/redye-tickets/{id}/close`
  - `GET /api/redye-tickets` 支持 `?open=true`（仅未结案）、`?dyeLotId=`、`?vatId=`（与染缸列表对账）
  - `POST` 开单（操作员即可）；同染程未结案重复开立 409；`/close` 仅主管，双检不达标 400
- `GET /api/dashboard/stats`（新增 `openRedyeCount`，与未结案复染单列表同口径）

除登录外需 `Authorization: Bearer <token>`。字段对外为 camelCase。

## 目录

```
LoomLot-01/
├── docker-compose.yml
├── backend/          # FastAPI
├── frontend/         # Svelte 4 + Vite + nginx
└── README.md
```

## 本地开发

### 数据库

```bash
docker compose up -d db
```

### 后端

```bash
cd backend
python -m venv .venv
# Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
$env:DATABASE_URL="postgresql+psycopg2://loomlot:loomlot@127.0.0.1:5439/loomlot"
python -c "from app.database import Base, engine; from app import models; Base.metadata.create_all(bind=engine)"
python -c "from app.seed import seed; seed()"
uvicorn app.main:app --reload --port 8600
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

开发态 Vite 将 `/api` 代理到 `http://127.0.0.1:8600`。
