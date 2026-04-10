import httpx
from fastapi import Request

from core.config import BACKEND_URL

HTTPX_TIMEOUT = httpx.Timeout(5.0)
HTTPX_LIMITS = httpx.Limits(max_keepalive_connections=10, max_connections=50)
client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global client
    if client is None:
        client = httpx.AsyncClient(timeout=HTTPX_TIMEOUT, limits=HTTPX_LIMITS)
    return client


def sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in headers.items()
        if key.lower() not in ["host", "authorization", "content-length"]
    }


async def forward_request(request: Request, path: str, body: bytes | None = None) -> httpx.Response:
    url = f"{BACKEND_URL}/{path}"
    if body is None:
        body = await request.body()

    return await get_client().request(
        method=request.method,
        url=url,
        headers=sanitize_headers(request.headers),
        content=body,
        params=request.query_params,
    )


async def close_client() -> None:
    global client
    if client is not None:
        await client.aclose()
        client = None
