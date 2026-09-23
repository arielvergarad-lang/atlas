# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///
"""Busca links externos rotos en el contenido de Atlas.

Uso:  uv run tools/check_links.py        (sale con código 1 si hay links rotos)

Un link cuenta como roto con 404/410 o si el dominio no responde. 403/429 y similares se
reportan como "dudosos" sin fallar: muchos sitios bloquean bots y el link sí funciona.
"""

import asyncio
import re
import sys
from pathlib import Path

import httpx

DOCS = Path(__file__).resolve().parent.parent / "site/src/content/docs"
URL = re.compile(r"https?://[^\s)\"'<>`\]]+")
HEADERS = {"User-Agent": "Mozilla/5.0 (Atlas link checker; +https://github.com/arielvergarad-lang/atlas)"}


async def check(client: httpx.AsyncClient, sem: asyncio.Semaphore, url: str) -> tuple[str, str]:
    async with sem:
        try:
            r = await client.head(url)
            if r.status_code >= 400:  # hay servidores que responden mal a HEAD (Kaggle da 404); se confirma con GET
                r = await client.get(url)
        except httpx.HTTPError as e:
            return url, f"roto ({type(e).__name__})"
    if r.status_code in (404, 410):
        return url, f"roto ({r.status_code})"
    if r.status_code >= 400:
        return url, f"dudoso ({r.status_code})"
    return url, "ok"


async def main() -> int:
    where: dict[str, set[str]] = {}
    for path in DOCS.rglob("*.md*"):
        for url in URL.findall(path.read_text(encoding="utf-8")):
            where.setdefault(url.rstrip(".,;:"), set()).add(str(path.relative_to(DOCS)))

    sem = asyncio.Semaphore(8)
    async with httpx.AsyncClient(follow_redirects=True, timeout=15, headers=HEADERS) as client:
        results = await asyncio.gather(*(check(client, sem, u) for u in sorted(where)))

    broken = 0
    for url, status in results:
        if status != "ok":
            broken += status.startswith("roto")
            print(f"{status:14} {url}  ← {', '.join(sorted(where[url]))}")
    print(f"{len(results)} links revisados, {broken} rotos")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
