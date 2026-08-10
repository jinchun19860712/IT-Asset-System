"""IT 资产管理系统 - 开发启动入口。

直接用 uvicorn 跑 app.main:app；开发时建议配合前端 vite dev server（npm run dev）。
可通过环境变量覆盖：ITASSET_HOST / ITASSET_PORT。
"""
from __future__ import annotations

import os


def main() -> None:
    import uvicorn

    host = os.environ.get("ITASSET_HOST", "0.0.0.0")
    port = int(os.environ.get("ITASSET_PORT", "8000"))
    print(f"[IT-Asset] 启动中... 监听 {host}:{port}")
    print(f"[IT-Asset] 浏览器访问: http://localhost:{port}/")
    print(f"[IT-Asset] API 文档: http://localhost:{port}/docs")
    uvicorn.run("app.main:app", host=host, port=port)


if __name__ == "__main__":
    main()
