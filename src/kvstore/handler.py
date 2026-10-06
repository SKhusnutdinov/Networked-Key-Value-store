import time

from .metrics import REQUESTS, REQUEST_DURATION
from .commands import Command
from .errors import KVStoreError
from .protocol import Request, Response
from .store import StatefulStore


async def handle(request: Request, store: StatefulStore) -> Response:
    command = request.command.value
    start = time.perf_counter()
    try:
        response = await _dispatch(request, store)
    except KVStoreError as e:
        response = Response("error", error=e.code)
    REQUEST_DURATION.labels(command=command).observe(time.perf_counter() - start)
    REQUESTS.labels(command=command, status=response.status).inc()
    return response

async def _dispatch(request: Request, store: StatefulStore) -> Response:
    if request.command is Command.SET:
        await store.set(request.key, request.value)
        return Response(status="success")
    if request.command is Command.GET:
        value = store.get(request.key)
        if value is None:
            return Response(status="error", error="not_found")
        return Response(status="success", value=value)
    if request.command is Command.DELETE:
        deleted = await store.delete(request.key)
        return Response(status="success", deleted=deleted)
    if request.command is Command.EXISTS:
        exists = store.exists(request.key)
        return Response(status="success", exists=exists)
    if request.command is Command.INCR:
        value = await store.incr(request.key)
        return Response(status="success", value=str(value))
    if request.command is Command.EXPIRE:
        success = await store.expire(request.key, request.ttl)
        return Response(status="success" if success else "error", error=None if success else "not_found")
    raise AssertionError(f"unhandled command {request.command}")