"""Assemble the deployment directory: static console plus the Python API.

    python -m scripts.assemble_deploy
    cd deploy && vercel deploy --prod

``deploy/`` keeps its ``.vercel`` link between runs; everything else is replaced.
The function bundles only what the API imports: ``countersign`` and the lab's part
of ``data``, under ``api/_pkg`` (the static console already serves ``/data/``, and
Vercel never turns underscore-prefixed paths under ``api/`` into routes), plus the
snapshot in ``api/_data``. Local environment files never upload.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

DEPLOY = Path("deploy")
KEEP = {".vercel", ".env.local", ".gitignore"}

DATA_MODULES = ["__init__.py", "catalogue.py", "records.py", "invoices.py", "lab.py", "render"]

REQUIREMENTS = """\
fastapi>=0.115
pydantic>=2.9
pydantic-settings>=2.6
pdfplumber>=0.11
openpyxl>=3.1
reportlab>=4.2
httpx>=0.27
python-multipart>=0.0.9
"""

VERCEL = {
    "functions": {
        "api/index.py": {
            "includeFiles": "api/{_pkg,_data}/**",
            "maxDuration": 30,
        }
    },
    "rewrites": [{"source": "/api/(.*)", "destination": "/api/index"}],
    "headers": [
        {
            "source": "/(.*)",
            "headers": [
                {"key": "X-Content-Type-Options", "value": "nosniff"},
                {"key": "Referrer-Policy", "value": "strict-origin-when-cross-origin"},
            ],
        }
    ],
}


def _ignore(_dir, names):
    return [n for n in names if n == "__pycache__" or n.endswith(".pyc")]


def main() -> None:
    DEPLOY.mkdir(exist_ok=True)
    for child in DEPLOY.iterdir():
        if child.name not in KEEP:
            shutil.rmtree(child) if child.is_dir() else child.unlink()

    shutil.copytree("web/out", DEPLOY, dirs_exist_ok=True)
    pkg = DEPLOY / "api" / "_pkg"
    pkg.mkdir(parents=True)
    shutil.copyfile("api/index.py", DEPLOY / "api" / "index.py")
    shutil.copytree("api/_data", DEPLOY / "api" / "_data")
    shutil.copytree("countersign", pkg / "countersign", ignore=_ignore)
    (pkg / "data").mkdir()
    for name in DATA_MODULES:
        source = Path("data") / name
        target = pkg / "data" / name
        if source.is_dir():
            shutil.copytree(source, target, ignore=_ignore)
        else:
            shutil.copyfile(source, target)

    (DEPLOY / "requirements.txt").write_text(REQUIREMENTS, encoding="utf-8")
    (DEPLOY / "vercel.json").write_text(json.dumps(VERCEL, indent=2) + "\n", encoding="utf-8")
    (DEPLOY / ".vercelignore").write_text(".env*\n*.pyc\n__pycache__\n", encoding="utf-8")

    files = sum(1 for p in DEPLOY.rglob("*") if p.is_file() and ".vercel" not in p.parts)
    print(f"assembled {files} files in {DEPLOY}/")


if __name__ == "__main__":
    main()
