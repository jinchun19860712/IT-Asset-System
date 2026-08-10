# IT 资产管理系统 — 部署指南

> 纯 Python（FastAPI）+ Vue3 源码项目，**不含任何 PyInstaller / 打包成 EXE 的代码或配置**。
> 启动入口唯一为 `backend/app.py`。

---

## 1. 环境要求

| 组件 | 版本要求 | 说明 |
|---|---|---|
| Python | **3.12（推荐）**；3.9+ 理论兼容但未实测 | 本机 venv 基于 3.12.10 构建 |
| Node.js | 18+ | 仅用于前端 vite 开发 / 构建 |
| 数据库 | 默认 SQLite（零配置）；可选 MySQL / SQL Server | SQLite 无需额外安装 |

---

## 2. 后端部署

### 2.1 创建虚拟环境

```bash
cd backend
python -m venv venv
```

### 2.2 激活虚拟环境

- **Windows（CMD / PowerShell）**

  ```bat
  venv\Scripts\activate
  ```

- **macOS / Linux（bash / zsh）**

  ```bash
  source venv/bin/activate
  ```

激活后命令行前缀会出现 `(venv)`。退出虚拟环境用 `deactivate`。

### 2.3 安装依赖

```bash
pip install -r requirements.txt
```

> `requirements.txt` 仅含运行期依赖，已剔除 `pyinstaller` 及其全部传递依赖（打包库），
> 用 `pip freeze` 过滤导出，可直接在干净环境复现。

### 2.4 初始化数据库

- **默认 SQLite**：无需手工建库。启动后端时会自动 `Base.metadata.create_all` 建表，
  并在首次启动时创建默认管理员账号。
- **默认管理员**：用户名 `admin`，密码 `admin123`（首次启动自动创建，请登录后及时修改）。
- **可选 — 灌入示例数据**（部门文件夹 / 设备状态 / 示例设备）：

  ```bash
  python init_db.py
  ```

- **可选 — 历史库修补**（幂等，可重复执行；用于老库补 `folder.path`、建机柜表等）：

  ```bash
  # 在项目根目录执行
  python migrate_db.py
  ```

### 2.5 启动后端

```bash
python app.py
```

默认监听 `0.0.0.0:8000`。可用环境变量覆盖：

```bash
ITASSET_HOST=127.0.0.1 ITASSET_PORT=9000 python app.py
```

- API 文档（Swagger）：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

---

## 3. 前端部署（开发模式）

```bash
cd frontend
npm install      # 首次需安装依赖
npm run dev      # 启动 vite 开发服务器
```

- vite 默认端口 **5173**；若被占用会自动顺延（如 **5174**），以启动日志中的 `Local:` 地址为准。
- 前端通过 vite 代理把 `/api` 请求转发到后端 `localhost:8000`，因此前后端需同时运行。

---

## 4. 访问系统

开发模式下，浏览器打开**前端地址**（即 vite 输出的地址）：

```
http://localhost:5173/      # 或 http://localhost:5174/（端口被占用时）
```

即可使用系统。后端 API 根地址为 http://localhost:8000/ 。

> ⚠️ 说明：本项目的 `python app.py` 启动的是**后端（端口 8000）**，前端页面由 vite 提供（5173/5174）。
> 两者是独立进程，需分别启动。若希望"一个命令搞定"，见下方第 5 节的生产式托管。

---

## 5. （可选）生产式单进程托管

不想同时开两个终端时，可先构建前端、再由后端直接托管前端页面：

```bash
cd frontend
npm install
npm run build          # 生成 frontend/dist

cd ../backend
python app.py          # 后端检测到 frontend/dist 后自动托管前端
```

此时浏览器直接访问 **http://localhost:8000/** 即可使用整套系统，无需再开 vite。

补充说明：此方式仅适合本地演示或轻量测试。如需在生产环境长期运行，建议前端使用 nginx 托管 frontend/dist 文件夹，后端仅提供 API 服务。
---

## 6. 项目结构与启动入口说明

```
it-asset-system/
├── backend/                # FastAPI 后端（Python 包）
│   ├── app.py              # ★ 唯一启动入口：python app.py
│   ├── requirements.txt    # 运行依赖（无打包库）
│   ├── app/                # 应用代码（main / models / routers / ...）
│   ├── init_db.py          # 可选：灌示例数据（维护脚本，非入口）
│   └── venv/               # 虚拟环境（部署时自建）
├── frontend/               # Vue3 前端（vite）
│   ├── package.json
│   ├── src/
│   └── vite.config.js
├── migrate_db.py           # 可选：历史库修补脚本（幂等，非入口）
└── DEPLOY.md
```

- **唯一应用入口**：`backend/app.py`。
- `backend/init_db.py` 与根 `migrate_db.py` 是可选的数据库维护脚本，**不是应用启动入口**。
- 前端静态资源由 `frontend/dist` 提供，路径基于 `__file__` 相对计算，
  部署到任意目录均可正常运行（无硬编码绝对路径）。

---

## 7. 常见问题

- **启动报 `No Python at ...\Python312\python.exe`**：venv 的基础解释器被移除。
  重新创建 venv 即可：`python -m venv backend/venv` 后重跑 `pip install -r requirements.txt`。
- **前端能开但接口 401 / 连不上**：确认后端 `python app.py` 已启动在 8000，且 vite 代理正常。
- **换 MySQL / SQL Server**：修改后端数据库连接配置并安装对应驱动（依赖已含 `PyMySQL` / `pymssql`）。
