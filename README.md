# Networked Key-Value Store

A small key-value store: an asyncio TCP server speaking a JSON-line
protocol, with append-only persistence, atomic `INCR`, TTL expiration, and
snapshot/log compaction. Built as a learning project to demonstrate networking,
concurrency, and storage-engine fundamentals in Python.

## Features

- `SET`, `GET`, `DELETE`, `EXISTS`, `INCR`, `EXPIRE` over a JSON-line TCP protocol
- Async server handling many concurrent clients, one asyncio task per connection
- Append-only write-ahead log with crash-safe recovery on restart
- Atomic `INCR` guarded by an `asyncio.Lock`
- TTL expiration: absolute timestamps, lazy checks on access, background sweep task
- Snapshot + log compaction with atomic file replacement (write temp file, `os.replace`)
- A reusable async client library and a small interactive CLI built on it

## Architecture

```
Multiple clients
       |
       | JSON-line messages over TCP
       v
Async TCP server (server.py)
  -> Request validation & framing (protocol.py)
  -> Command dispatch (handler.py)
       v
StatefulStore (store.py)
  -> asyncio.Lock guarding read-modify-write ops
  -> In-memory engine (domain.py) + TTL metadata (expiration.py)
       v
Persistence (persistence/)
  -> Append-only log (append_log.py)
  -> Snapshots (snapshot.py)
  -> Startup recovery (recovery.py)
```

## Requirements

- Python 3.12+

## Setup

```bash
uv sync
```

## Running the server

```bash
uv run python -m kvstore.server --host 127.0.0.1 --port 6379 --data-dir ./data
```

Data (the append log and snapshots) is stored under `--data-dir`; restarting
the server with the same data directory replays the log and restores state.

The server binds to `127.0.0.1` by default.

## Using the CLI

```bash
uv run python -m kvstore.cli localhost 6379
```

```
kv> SET name Player
success
kv> GET name
Player
kv> EXISTS name
true
kv> DELETE name
success
kv> GET name
Value not found
kv> exit
```

## Running the tests

```bash
uv run pytest -v
```

## Project structure

```
src/kvstore/
    domain.py                in-memory storage engine + validation
    errors.py                typed exceptions
    protocol.py              request/response dataclasses, JSON-line parsing
    commands.py              Command enum
    handler.py               request -> store -> response dispatch
    store.py                 StatefulStore: lock + persistence + TTL integration
    expiration.py            TTL metadata, lazy checks, background sweep
    server.py                asyncio TCP server
    client.py                reusable async client
    cli.py                   interactive REPL built on the client
    persistence/
        append_log.py        write-ahead log, replay
        snapshot.py          atomic snapshot write/read
        recovery.py          snapshot + log-tail recovery orchestration
tests/                       storage, protocol, persistence, TTL, server+client, concurrency, restart, snapshot recovery
```
