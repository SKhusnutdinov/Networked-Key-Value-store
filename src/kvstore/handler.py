

from .commands import Command
from .domain import KeyValueStore
from .errors import KVStoreError
from .protocol import Request, Response


async def handle(request: Request, store: KeyValueStore) -> Response:
    try:
        return await _dispatch(request, store)
    except KVStoreError as e:
        return Response("error", error=e.code)

async def _dispatch(request: Request, store: KeyValueStore) -> Response:
    if request.command is Command.SET:
        store.set(request.key, request.value)
        return Response(status="success")
    if request.command is Command.GET:
        value = store.get(request.key)
        if value is None:
            return Response(status="error", error="not_found")
        return Response(status="success", value=value)
    if request.command is Command.DELETE:
        deleted = store.delete(request.key)
        return Response(status="success", deleted=deleted)
    if request.command is Command.EXISTS:
        exists = store.exists(request.key)
        return Response(status="success", exists=exists)
    if request.command is Command.INCR:
        value = store.incr(request.key)
        return Response(status="success", value=str(value))
    raise AssertionError(f"unhandled command {request.command}")