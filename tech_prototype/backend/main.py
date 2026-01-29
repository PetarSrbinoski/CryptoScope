from __future__ import annotations

import asyncio
import sys
import time
import os
from typing import Optional
import requests
import functools
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.router import router as api_router
from .core.config import CORS_ALLOW_ORIGINS, TECHNICAL_MS_URL, LSTM_MS_URL
from .db.init_db import init_db

app = FastAPI(title="CryptoScope API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
async def root() -> dict:
    """Root endpoint - API health check."""
    return {
        "status": "ok",
        "message": "CryptoScope API is running",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


@app.get("/health")
async def health() -> JSONResponse:
    """Health check endpoint for Azure."""
    return JSONResponse(status_code=200, content={"status": "healthy"})


@app.on_event("startup")
def _startup() -> None:
    """Initialize DB and start pipeline in background."""
    init_db()
    # Schedule pipeline to run later (non-blocking) so container startup is fast.
    # Use PIPELINE_START_DELAY (seconds) env var to control the delay.
    delay = int(os.getenv("PIPELINE_START_DELAY", "60"))
    asyncio.create_task(_schedule_pipeline(delay))


async def _run_pipeline_background() -> None:
    """Run data pipeline in background (non-blocking)."""
    try:
        print("[Pipeline] Starting background pipeline task...", file=sys.stderr)
        # Import here to avoid circular imports
        from .pipeline.run_pipeline import main as run_pipeline

        # Wait for dependent microservices to be available before running pipeline
        await _wait_for_dependencies()

        # Run pipeline (it's a sync function, so wrap it)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, run_pipeline)
        print("[Pipeline] Background pipeline completed successfully", file=sys.stderr)
    except Exception as e:
        print(f"[Pipeline] Background pipeline failed: {e}", file=sys.stderr)


async def _wait_for_dependencies(timeout: int = 300, interval: float = 2.0) -> None:
    """Poll TECHNICAL_MS_URL and LSTM_MS_URL until both respond or timeout.

    This ensures the pipeline runs after dependent microservices are up.
    """
    services = []
    if TECHNICAL_MS_URL:
        services.append(TECHNICAL_MS_URL)
    if LSTM_MS_URL:
        services.append(LSTM_MS_URL)

    if not services:
        return

    deadline = time.time() + timeout
    loop = asyncio.get_running_loop()
    for svc in services:
        ok = False
        while time.time() < deadline:
            try:
                # try /health then root using requests in executor to avoid blocking event loop
                for path in ("/health", "/"):
                    url = svc.rstrip("/") + path
                    try:
                        func = functools.partial(requests.get, url, timeout=3)
                        resp = await loop.run_in_executor(None, func)
                    except Exception:
                        resp = None

                    if resp is not None and getattr(resp, "status_code", 500) < 500:
                        ok = True
                        break
                if ok:
                    print(f"[Pipeline] Dependency {svc} is healthy", file=sys.stderr)
                    break
            except Exception:
                pass
            await asyncio.sleep(interval)
        if not ok:
            print(f"[Pipeline] Timeout waiting for {svc}; continuing anyway", file=sys.stderr)


async def _schedule_pipeline(delay_seconds: int = 60) -> None:
    """Wait `delay_seconds` then run the pipeline in a thread executor.

    This ensures the web app has time to become healthy and answer requests
    before the potentially heavy pipeline starts.
    """
    try:
        print(f"[Pipeline] Delaying pipeline start by {delay_seconds}s", file=sys.stderr)
        await asyncio.sleep(delay_seconds)

        # Run the same background pipeline runner (which will wait for deps)
        await _run_pipeline_background()
    except Exception as e:
        print(f"[Pipeline] Scheduled pipeline failed: {e}", file=sys.stderr)
