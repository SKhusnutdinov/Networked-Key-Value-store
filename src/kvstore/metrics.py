from prometheus_client import Counter, Gauge, Histogram

REQUESTS = Counter(
    "kvstore_requests_total",
    "Total number of KV store requests",
    ["command", "status"],
)

REQUEST_DURATION = Histogram(
    "kvstore_request_duration_seconds",
    "Request duration",
    ["command"],
    buckets=(
        0.0001,   # 0.1 ms
        0.00025,  # 0.25 ms
        0.0005,   # 0.5 ms
        0.001,    # 1 ms
        0.002,    # 2 ms
        0.005,    # 5 ms
        0.010,    # 10 ms
        0.025,    # 25 ms
        0.050,    # 50 ms
        0.100,    # 100 ms
        0.250,
        0.500,
        1.000,
    ),
)

ACTIVE_CONNECTIONS = Gauge(
    "kvstore_active_connections",
    "Number of currently active client connections",
)