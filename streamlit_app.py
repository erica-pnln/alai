"""Alai ASGI launcher with root-scoped PWA endpoints."""

from pathlib import Path

import streamlit as st
from starlette.requests import Request
from starlette.responses import FileResponse
from starlette.routing import Route


APP_DIR = Path(__file__).resolve().parent


async def service_worker(_: Request) -> FileResponse:
    """Serve the worker at / so it can control the whole app origin."""
    return FileResponse(
        APP_DIR / "sw.js",
        media_type="text/javascript",
        headers={
            "Cache-Control": "no-cache",
            "Service-Worker-Allowed": "/",
        },
    )


async def web_manifest(_: Request) -> FileResponse:
    """Serve the PWA manifest at a stable, origin-root URL."""
    return FileResponse(
        APP_DIR / "static" / "manifest.webmanifest",
        media_type="application/manifest+json",
        headers={"Cache-Control": "no-cache"},
    )


app = st.App(
    str(APP_DIR / "alai_ui.py"),
    routes=[
        Route("/sw.js", service_worker, methods=["GET", "HEAD"]),
        Route("/manifest.webmanifest", web_manifest, methods=["GET", "HEAD"]),
    ],
)
