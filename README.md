# LoomLot-01 · 染坊缸染、色牢度抽检与回修复染

靛蓝染坊台：按 **染坊 → 染缸 → 染程 → 色牢度 → 回修复染** 工序推进，聚焦缸染调度、抽检与缺陷回修，不是库存出入库系统。

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
2. **Vat** — `dyeHouseId`, `vatCode`, `fiberType`, `capacityL`, `status` ∈ `ready|dyeing|drain`，输出附带 `hasOpenRework`
3. **DyeLot** — `vatId`, `recipeName`, `fabricKg`, `startedAt`, `operatorName`，输出附带 `hasOpenRework`
4. **FastnessCheck** — `dyeLotId`, `checkedAt`, `washFastness`(1–5), `rubFastness`(>0), `tempC`, `notes`
5. **ReworkTicket（回修复染单）** — `dyeLotId`（原染程编号）、`defectNote`（缺陷说明，至少 8 字）、`openedAt`（开单时刻）、`closedAt`（结案时刻，可空）、`openerName`（开单人）

### 规则

- 仅当染缸状态为 `ready` 或 `dyeing` 时可新建染程，否则 409
- 新建染程后，染缸状态自动设为 `dyeing`
- 可选接口：`POST /api/vats/{id}/drain` 将染缸置为 `drain`

#### 回修复染

- 复染单挂在**原染程**上；同一原染程存在未结案复染单时不可再开，409
- 操作员（dyer）可开单，开单人记录为当前登录用户；**结案仅主管（admin）**，否则 403
- 结案条件：原染程上**至少两条**色牢度抽检，且较新一条**耐洗等级不低于**较旧一条，否则 400
- 存在未结案复染的染缸，**禁止再新建染程**（409，改挂染程同样拦截）；主管结案后恢复
- 染程页、染缸列表均显示「挂未结案复染」标记；看板的未结案复染条数与列表、拦截判断共用同一对账来源（`app/services/rework.py`），不另算
- 种子数据含一单未结案复染（挂在 V-01 的染程上，该染程仅一条色牢度，故无法结案，演示冻结态）

## 主要 API

- `POST /api/auth/login`（OAuth2 表单）
- `GET /api/auth/me`
- `GET/POST/PUT/DELETE /api/dye-houses`
- `GET/POST/PUT/DELETE /api/vats` · `POST /api/vats/{id}/drain`
- `GET/POST/PUT/DELETE /api/dye-lots`
- `GET/POST/PUT/DELETE /api/fastness-checks`
- `GET/POST /api/rework-tickets` · `POST /api/rework-tickets/{id}/close`（仅主管）· 支持 `?dyeLotId=`、`?openOnly=` 过滤
- `GET /api/dashboard/stats`（含 `openReworkCount`）

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
