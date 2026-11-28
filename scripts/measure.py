#!/usr/bin/env python3
"""Medir um endpoint, antes e depois · measure an endpoint, before and after (Aula 09).

    python scripts/measure.py http://localhost:8000/api/v1/orders/ -u ana -p pass1234
    python scripts/measure.py http://localhost/api/v1/lab/orders-nplus1/ \\
        -u gestora -p pass1234 -n 50 -c 4

PT: só biblioteca-padrão. Faz login (JWT), repete o pedido N vezes com C clientes em
paralelo e mostra mediana, p95 e o que o servidor disse no cabeçalho `Server-Timing`
(queries e tempo na base de dados). Uma medição só vale com dados em volume e repetida:
o primeiro pedido paga ligações e caches frias — por isso há aquecimento.
EN: standard library only. Logs in (JWT), repeats the request N times with C parallel
clients and prints median, p95 and what the server reported in `Server-Timing` (queries
and database time). A measurement only counts with volume and repetition: the first
request pays for cold connections and caches — hence the warm-up.

Ficha 06 (DriveNow): copiado de aula-09/scripts/measure.py (dwfa-2627-solucoes), mais a
opção --row PAPEL, que imprime a linha da tabela de base de docs/ficha-06.md.
"""

import argparse
import json
import re
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit


def login(base: str, username: str, password: str, path: str) -> str:
    body = json.dumps({"username": username, "password": password}).encode()
    request = urllib.request.Request(
        base + path, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.load(response)["access"]
    except urllib.error.HTTPError as error:
        # o login tem limite de tentativas (Ficha 03): 429 → esperar um minuto ou usar --token
        # login is rate-limited (Ficha 03): 429 → wait a minute or pass --token
        raise SystemExit(f"login falhou · login failed: HTTP {error.code} em · at {path}") from None


def fetch(url: str, token: str | None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    request = urllib.request.Request(url, headers=headers)
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=60) as r:
            size, status, timing = len(r.read()), r.status, r.headers.get("Server-Timing", "")
    except urllib.error.HTTPError as error:
        size, status, timing = 0, error.code, ""
    return (time.perf_counter() - start) * 1000, status, size, timing


def percentile(values, p):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(p / 100 * (len(ordered) - 1)))]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("url")
    parser.add_argument("-n", type=int, default=30, help="pedidos · requests (30)")
    parser.add_argument("-c", type=int, default=1, help="em paralelo · parallel clients (1)")
    parser.add_argument("-u", "--username")
    parser.add_argument("-p", "--password")
    parser.add_argument("--token", help="um access token já obtido · an access token you have")
    parser.add_argument("--token-path", default="/api/v1/auth/token/")
    # Ficha 06 (DriveNow): escreve também a linha da tabela de docs/ficha-06.md, em Markdown.
    parser.add_argument("--row", metavar="PAPEL", help="imprime a linha da tabela, com o papel")
    args = parser.parse_args()

    parts = urlsplit(args.url)
    token = args.token
    if args.username and not token:
        base = f"{parts.scheme}://{parts.netloc}"
        token = login(base, args.username, args.password, args.token_path)

    for _ in range(3):  # aquecimento · warm-up
        fetch(args.url, token)
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.c) as pool:
        results = list(pool.map(lambda _: fetch(args.url, token), range(args.n)))
    elapsed = time.perf_counter() - started

    times = [r[0] for r in results]
    statuses = sorted({r[1] for r in results})
    timings = [r[3] for r in results]
    queries = [int(m.group(1)) for t in timings if (m := re.search(r'desc="(\d+) queries"', t))]
    db = [float(m.group(1)) for t in timings if (m := re.search(r"db;dur=([\d.]+)", t))]
    print(args.url)
    print(f"  {args.n} pedidos · requests, {args.c} em paralelo · parallel, HTTP {statuses}")
    print(f"  resposta · response  {results[0][2] / 1024:8.1f} kB")
    print(f"  mediana · median     {statistics.median(times):8.1f} ms")
    print(f"  p95                  {percentile(times, 95):8.1f} ms")
    print(f"  max                  {max(times):8.1f} ms")
    print(f"  débito · throughput  {args.n / elapsed:8.1f} req/s")
    if queries:
        print(
            f"  servidor · server    {statistics.median(queries):8.0f} queries, "
            f"{statistics.median(db):.1f} ms na BD · in the DB"
        )
    if args.row:
        q = f"{statistics.median(queries):.0f}" if queries else "?"
        d = f"{statistics.median(db):.1f}" if db else "?"
        print(
            f"| `GET {parts.path}{'?' + parts.query if parts.query else ''}` | {args.row} | {q} "
            f"| {d} | {statistics.median(times):.1f} | {percentile(times, 95):.1f} |"
        )


if __name__ == "__main__":
    main()
