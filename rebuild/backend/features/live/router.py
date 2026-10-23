"""Cookie-authenticated, origin-bound per-tank WebSockets (HTTP middleware is bypassed)."""
import asyncio
from contextlib import suppress
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from backend.core.security import token_hash, valid_token
from backend.features.accounts.errors import AuthError
from backend.features.registry.errors import RegistryError
from .cursor import InvalidStreamCursor
from .service import LiveService

router = APIRouter()


async def send(websocket, message, timeout):
    await asyncio.wait_for(websocket.send_json(message), timeout)


async def close(websocket, *, code, reason="", timeout=5):
    # The peer may disconnect while a threaded access check or send is pending.
    with suppress(TimeoutError, WebSocketDisconnect, OSError, RuntimeError):
        await asyncio.wait_for(websocket.close(code=code, reason=reason), timeout)


@router.websocket("/api/v1/hatcheries/{hatchery_id}/tanks/{tank_id}/stream")
async def stream(websocket: WebSocket, hatchery_id: UUID, tank_id: UUID):
    runtime = websocket.app.state.account_runtime
    settings = runtime.settings
    # Reject before accepting; never trust forwarded proto headers here.
    if (settings is None or len(websocket.headers.getlist("origin")) != 1
        or websocket.headers.get("origin") not in settings.origins
        or (settings.development and websocket.url.hostname not in ("127.0.0.1", "localhost", "::1"))
        or (not settings.development and websocket.url.scheme != "wss")):
        await close(websocket, code=1008)
        return
    token = websocket.cookies.get(settings.cookie_name)
    if not valid_token(token):
        await close(websocket, code=1008)
        return
    policy, connections = websocket.app.state.live_policy, websocket.app.state.live_connections
    identity = token_hash(token)
    if not connections.acquire(identity, policy):
        await close(websocket, code=1013)
        return
    receiver = None
    try:
        accounts = await run_in_threadpool(runtime.get)
        service = LiveService(accounts, policy)
        if len(websocket.query_params.getlist("cursor")) != 1:
            raise InvalidStreamCursor("invalid_stream_cursor")
        position = service.cursor.open(websocket.query_params["cursor"], hatchery_id, tank_id)
        messages, following = await run_in_threadpool(service.batch, token, hatchery_id, tank_id, position)
        await asyncio.wait_for(websocket.accept(), policy.send_timeout)
        receiver = asyncio.create_task(websocket.receive())
        await send(websocket, dict(v=1, type="ready", cursor=service.cursor.seal(hatchery_id, tank_id, position)), policy.send_timeout)
        loop = asyncio.get_running_loop()
        heartbeat_at = loop.time() + policy.heartbeat_seconds
        while True:
            if messages is None:
                await send(websocket, dict(v=1, type="resync_required", reason="fresh_history_required"), policy.send_timeout)
                await close(websocket, code=1000, timeout=policy.send_timeout)
                return
            for message in messages:
                if receiver.done():
                    if receiver.result()["type"] != "websocket.disconnect":
                        await close(websocket, code=1008, reason="server_push_only", timeout=policy.send_timeout)
                    return
                await send(websocket, message, policy.send_timeout)
            position = following
            if loop.time() >= heartbeat_at:
                await send(websocket, dict(v=1, type="heartbeat",
                    cursor=service.cursor.seal(hatchery_id, tank_id, position)), policy.send_timeout)
                heartbeat_at = loop.time() + policy.heartbeat_seconds
            # Also observes idle disconnects; no DB session survives a wait/send.
            done, _ = await asyncio.wait({receiver}, timeout=policy.poll_seconds)
            if done:
                if receiver.result()["type"] != "websocket.disconnect":
                    await close(websocket, code=1008, reason="server_push_only", timeout=policy.send_timeout)
                return
            messages, following = await run_in_threadpool(service.batch, token, hatchery_id, tank_id, position)
    except (AuthError, RegistryError):
        await close(websocket, code=1008, reason="access_unavailable", timeout=policy.send_timeout)
    except InvalidStreamCursor:
        await close(websocket, code=1008, reason="invalid_stream_cursor", timeout=policy.send_timeout)
    except SQLAlchemyError:
        await close(websocket, code=1013, reason="stream_unavailable", timeout=policy.send_timeout)
    except TimeoutError:
        # A cancelled send must not leave a slow socket occupying a slot.
        await close(websocket, code=1013, reason="slow_client", timeout=policy.send_timeout)
    except (WebSocketDisconnect, OSError):
        pass
    finally:
        try:
            if receiver is not None:
                receiver.cancel()
                with suppress(asyncio.CancelledError, WebSocketDisconnect):
                    await receiver
        finally:
            connections.release(identity)
