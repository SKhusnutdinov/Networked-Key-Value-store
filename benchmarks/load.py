import argparse
import asyncio
import json
import math
import random
import time
from dataclasses import dataclass, field


@dataclass
class Stats:
    requests: int = 0
    application_errors: int = 0
    transport_errors: int = 0
    latencies: list[float] = field(default_factory=list)


def percentile(values: list[float], p: float) -> float:
    """Nearest-rank percentile; `p` is in [0, 1]. Returns 0.0 for no data."""
    if not values:
        return 0.0

    ordered = sorted(values)
    rank = max(1, math.ceil(p * len(ordered)))
    return ordered[rank - 1]


async def send_request(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    payload: dict,
    timeout: float,
) -> dict:
    data = json.dumps(payload).encode() + b"\n"

    writer.write(data)
    await writer.drain()

    response = await asyncio.wait_for(
        reader.readline(),
        timeout=timeout,
    )

    if not response:
        raise ConnectionError("server closed connection")

    return json.loads(response)


def make_request(client_id: int) -> dict:
    value_key = f"bench:value:{client_id}"
    counter_key = f"bench:counter:{client_id}"

    x = random.random()

    # 60% GET
    if x < 0.60:
        return {
            "command": "GET",
            "key": value_key,
        }

    # 25% SET
    if x < 0.85:
        return {
            "command": "SET",
            "key": value_key,
            "value": str(random.randint(0, 1_000_000)),
        }

    # 10% EXISTS
    if x < 0.95:
        return {
            "command": "EXISTS",
            "key": value_key,
        }

    # 5% INCR
    return {
        "command": "INCR",
        "key": counter_key,
    }


async def worker(
    client_id: int,
    host: str,
    port: int,
    deadline: float,
    timeout: float,
    stats: Stats,
) -> None:
    while time.perf_counter() < deadline:
        writer = None

        try:
            reader, writer = await asyncio.open_connection(host, port)

            # Make sure this client's keys exist.
            await send_request(
                reader,
                writer,
                {
                    "command": "SET",
                    "key": f"bench:value:{client_id}",
                    "value": "0",
                },
                timeout,
            )

            await send_request(
                reader,
                writer,
                {
                    "command": "SET",
                    "key": f"bench:counter:{client_id}",
                    "value": "0",
                },
                timeout,
            )

            while time.perf_counter() < deadline:
                request = make_request(client_id)

                request_start = time.perf_counter()
                response = await send_request(
                    reader,
                    writer,
                    request,
                    timeout,
                )
                stats.latencies.append(time.perf_counter() - request_start)

                stats.requests += 1

                if response.get("status") == "error":
                    stats.application_errors += 1

        except (
            ConnectionError,
            asyncio.TimeoutError,
            OSError,
            json.JSONDecodeError,
        ):
            stats.transport_errors += 1

            # Don't spin aggressively if the server is unavailable.
            await asyncio.sleep(0.05)

        finally:
            if writer is not None:
                writer.close()

                try:
                    await writer.wait_closed()
                except OSError:
                    pass


async def reporter(stats: Stats, deadline: float) -> None:
    previous = 0

    while time.perf_counter() < deadline:
        await asyncio.sleep(1)

        current = stats.requests
        rps = current - previous
        previous = current

        print(
            f"{rps:>7} req/s | "
            f"total={stats.requests:<10} | "
            f"app_errors={stats.application_errors:<6} | "
            f"transport_errors={stats.transport_errors}"
        )


async def run(args: argparse.Namespace) -> None:
    stats = Stats()

    start = time.perf_counter()
    deadline = start + args.duration

    print(
        f"Starting load test: "
        f"{args.clients} clients for {args.duration}s"
    )

    workers = [
        asyncio.create_task(
            worker(
                client_id=i,
                host=args.host,
                port=args.port,
                deadline=deadline,
                timeout=args.timeout,
                stats=stats,
            )
        )
        for i in range(args.clients)
    ]

    report_task = asyncio.create_task(
        reporter(stats, deadline)
    )

    await asyncio.gather(*workers)
    await report_task

    elapsed = time.perf_counter() - start
    average_rps = stats.requests / elapsed

    print()
    print("Finished")
    print(f"Requests:         {stats.requests}")
    print(f"Average req/s:    {average_rps:.2f}")
    print(f"App errors:       {stats.application_errors}")
    print(f"Transport errors: {stats.transport_errors}")
    print(f"p50 latency:      {percentile(stats.latencies, 0.50) * 1000:.3f} ms")
    print(f"p95 latency:      {percentile(stats.latencies, 0.95) * 1000:.3f} ms")
    print(f"p99 latency:      {percentile(stats.latencies, 0.99) * 1000:.3f} ms")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=6379)
    parser.add_argument("--clients", type=int, default=10)
    parser.add_argument("--duration", type=float, default=30)
    parser.add_argument("--timeout", type=float, default=5)

    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))