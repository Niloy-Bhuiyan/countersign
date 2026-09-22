"""Durable storage for reviewer workspaces: decisions and uploaded documents.

Backed by a private Vercel Blob store. Every read goes through the API with the
store token; a blob URL on its own returns 403, so nothing a reviewer records is
readable by guessing a link.

Decisions are append-only. A new decision, or a withdrawal, is a new object; none
is ever overwritten. The current decision for an invoice is the latest event, and
the full list is the audit trail.

``MemoryBlob`` implements the same interface for tests and for running the API
locally without a token.
"""

from __future__ import annotations

import json
from typing import Protocol

import httpx

API = "https://vercel.com/api/blob"
API_VERSION = "12"


class StorageError(RuntimeError):
    """The store could not be reached or refused the request."""


class BlobExists(StorageError):
    """A write to a pathname that already holds an object. Objects are never replaced."""


class BlobStore(Protocol):
    def put(self, pathname: str, data: bytes, content_type: str) -> None: ...
    def list(self, prefix: str) -> list[str]: ...
    def get(self, pathname: str) -> bytes | None: ...


def _checked(response: httpx.Response) -> httpx.Response:
    if response.is_error:
        raise StorageError(f"storage refused the request ({response.status_code})")
    return response


class VercelBlob:
    def __init__(self, token: str, timeout: float = 20.0) -> None:
        self._auth = {"authorization": f"Bearer {token}"}
        self._client = httpx.Client(timeout=timeout)
        self._urls: dict[str, str] = {}

    def put(self, pathname: str, data: bytes, content_type: str) -> None:
        try:
            response = self._client.put(
                f"{API}/",
                params={"pathname": pathname},
                content=data,
                headers={
                    **self._auth,
                    "x-api-version": API_VERSION,
                    "x-content-type": content_type,
                    "x-add-random-suffix": "0",
                    "x-allow-overwrite": "0",
                    "x-vercel-blob-access": "private",
                },
            )
        except httpx.HTTPError as exc:
            raise StorageError("storage is unreachable") from exc
        if response.status_code in (400, 409) and "exist" in response.text.lower():
            raise BlobExists(pathname)
        self._urls[pathname] = _checked(response).json()["url"]

    def list(self, prefix: str) -> list[str]:
        pathnames: list[str] = []
        cursor = None
        while True:
            params = {"prefix": prefix, "limit": "1000"}
            if cursor:
                params["cursor"] = cursor
            try:
                response = self._client.get(
                    f"{API}/", params=params, headers={**self._auth, "x-api-version": API_VERSION}
                )
            except httpx.HTTPError as exc:
                raise StorageError("storage is unreachable") from exc
            body = _checked(response).json()
            for blob in body["blobs"]:
                self._urls[blob["pathname"]] = blob["url"]
                pathnames.append(blob["pathname"])
            if not body.get("hasMore"):
                return sorted(pathnames)
            cursor = body["cursor"]

    def get(self, pathname: str) -> bytes | None:
        url = self._urls.get(pathname)
        if url is None:
            self.list(pathname)
            url = self._urls.get(pathname)
        if url is None:
            return None
        try:
            response = self._client.get(url, headers=self._auth)
        except httpx.HTTPError as exc:
            raise StorageError("storage is unreachable") from exc
        if response.status_code == 404:
            return None
        return _checked(response).content


class MemoryBlob:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put(self, pathname: str, data: bytes, content_type: str) -> None:
        # Same rule as the Vercel store: an existing object is never replaced.
        if pathname in self.objects:
            raise BlobExists(pathname)
        self.objects[pathname] = (data, content_type)

    def list(self, prefix: str) -> list[str]:
        return sorted(p for p in self.objects if p.startswith(prefix))

    def get(self, pathname: str) -> bytes | None:
        found = self.objects.get(pathname)
        return found[0] if found else None


def put_json(store: BlobStore, pathname: str, payload) -> None:
    store.put(pathname, json.dumps(payload, separators=(",", ":")).encode(), "application/json")


def get_json(store: BlobStore, pathname: str):
    data = store.get(pathname)
    return None if data is None else json.loads(data)
