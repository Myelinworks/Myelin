"""Supabase Storage proxy for the quarter-report PDF export.

Same shape as `auth_service.py`'s `SupabaseAuthClient`: a thin `httpx` wrapper around Supabase's
own REST API (not the `supabase-py` SDK, to stay consistent with how this backend already talks
to Supabase), exposed as a FastAPI dependency so tests can swap in a fake via
`app.dependency_overrides`. Uses `settings.supabase_secret_key` (the service-role key) because
writing to a private bucket has to bypass RLS -- this backend is the only writer, the frontend
never talks to Supabase Storage directly.
"""

from typing import Protocol

import httpx
from fastapi import Depends

from app.core.config import Settings, get_settings

REPORT_BUCKET = "quarter-reports"


class SupabaseStorageError(Exception):
    """A non-2xx response from Supabase Storage itself (bad bucket, oversized upload, real
    outage) -- carries the raw status/body so the route can decide 502 vs 500 without this
    module needing to know about HTTP responses."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class SupabaseStorageClient(Protocol):
    async def upload(self, bucket: str, path: str, data: bytes, *, content_type: str) -> None: ...
    async def create_signed_url(self, bucket: str, path: str, *, expires_in: int = 3600) -> str: ...


class HttpxSupabaseStorageClient:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None):
        self._base_url = settings.supabase_url
        self._api_key = settings.supabase_secret_key
        # None means "real network" -- only ever overridden by tests, same convention as
        # HttpxSupabaseAuthClient._transport.
        self._transport = transport

    def _headers(self, content_type: str | None = None) -> dict:
        headers = {"Authorization": f"Bearer {self._api_key}", "apikey": self._api_key}
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    async def _ensure_bucket(self, client: httpx.AsyncClient, bucket: str) -> None:
        """Idempotent create -- checked with a GET first rather than parsing Supabase's
        create-error body for "already exists", which isn't a stable contract to depend on."""
        existing = await client.get(f"{self._base_url}/storage/v1/bucket/{bucket}", headers=self._headers())
        if existing.status_code == 200:
            return
        created = await client.post(
            f"{self._base_url}/storage/v1/bucket",
            json={"id": bucket, "name": bucket, "public": False},
            headers=self._headers("application/json"),
        )
        if created.status_code >= 400:
            raise SupabaseStorageError(created.status_code, created.text)

    async def upload(self, bucket: str, path: str, data: bytes, *, content_type: str) -> None:
        async with httpx.AsyncClient(transport=self._transport, timeout=30.0) as client:
            await self._ensure_bucket(client, bucket)
            response = await client.post(
                f"{self._base_url}/storage/v1/object/{bucket}/{path}",
                content=data,
                headers={**self._headers(content_type), "x-upsert": "true"},
            )
        if response.status_code >= 400:
            raise SupabaseStorageError(response.status_code, response.text)

    async def create_signed_url(self, bucket: str, path: str, *, expires_in: int = 3600) -> str:
        async with httpx.AsyncClient(transport=self._transport, timeout=30.0) as client:
            response = await client.post(
                f"{self._base_url}/storage/v1/object/sign/{bucket}/{path}",
                json={"expiresIn": expires_in},
                headers=self._headers("application/json"),
            )
        if response.status_code >= 400:
            raise SupabaseStorageError(response.status_code, response.text)
        # Supabase returns a path relative to /storage/v1 (e.g. "/object/sign/bucket/path?token=...").
        return f"{self._base_url}/storage/v1{response.json()['signedURL']}"


def get_supabase_storage_client(settings: Settings = Depends(get_settings)) -> SupabaseStorageClient:
    """FastAPI dependency -- same reasoning as `get_supabase_auth_client`: a bare import would
    make the real client impossible to swap out in tests via `app.dependency_overrides`."""
    return HttpxSupabaseStorageClient(settings)
