from prometheus_client import Counter, Gauge, Histogram

REQUESTS = Counter(
    "kvstore_requests_total",
    "Total number of KV store requests",
    ["command", "status"],
)

REQUEST_DURATION = Histogram(
    "kvstore_request_duration_seconds",
    "Time spent processing KV store requests",
    ["command"],
)

ACTIVE_CONNECTIONS = Gauge(
    "kvstore_active_connections",
    "Number of currently active client connections",
)