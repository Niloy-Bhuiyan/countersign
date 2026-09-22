"""Serve the built console and the live API from one origin, as Vercel does.

    python -m scripts.serve_local            # http://localhost:4321

Uses the private Blob store if ``BLOB_READ_WRITE_TOKEN`` is set, and an in-memory
store otherwise, so a fresh clone runs it with no account.
"""

from __future__ import annotations

import sys

import uvicorn
from fastapi.staticfiles import StaticFiles

from api.index import app

app.mount("/", StaticFiles(directory="web/out", html=True), name="console")

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 4321
    uvicorn.run(app, host="127.0.0.1", port=port)
