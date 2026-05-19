"""
FlowRPA Engine Entry Point
Starts FastAPI + WebSocket server for communication with Electron frontend.
"""
import logging
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure engine package is importable
sys.path.insert(0, str(Path(__file__).parent))

from api.routes import router as rest_router
from api.websocket import router as ws_router
from utils.config import load_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("flowrpa.engine")


def create_app() -> FastAPI:
    config = load_config()

    app = FastAPI(
        title="FlowRPA Engine",
        version="0.1.0",
        description="Browser automation engine powered by DrissionPage",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(rest_router)
    app.include_router(ws_router)

    app.state.config = config

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()


if __name__ == "__main__":
    cfg = load_config()
    host = cfg.get("server", {}).get("host", "127.0.0.1")
    port = cfg.get("server", {}).get("port", 9222)
    logger.info(f"FlowRPA Engine starting on {host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=False, log_level="info")
