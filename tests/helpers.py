from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import anyio
import httpx
import os
import subprocess
import sys
from httpx import AsyncClient

from template_fastapi_mcp.config import Settings


@asynccontextmanager
async def live_server(
    settings: Settings, overrides: dict[str, str] | None = None
) -> AsyncIterator[str]:
    settings.assert_test_target()
    child_env = dict(os.environ, APP_DB_NAME=settings.test_db_name)
    if overrides:
        for key, value in overrides.items():
            if key not in ("POSTGRES_HOST", "POSTGRES_PORT"):
                raise ValueError(
                    "Only POSTGRES_HOST/POSTGRES_PORT overrides are supported"
                )
            child_env[key] = value
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "template_fastapi_mcp.main:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(settings.test_http_port),
        ],
        env=child_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    url = f"http://127.0.0.1:{settings.test_http_port}"
    try:
        with anyio.fail_after(10):
            async with AsyncClient(timeout=0.5) as probe:
                while True:
                    if process.poll() is not None:
                        raise RuntimeError("Test application exited before readiness")
                    try:
                        response = await probe.get(url + "/health")
                        if response.status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    await anyio.sleep(0.1)
        yield url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
