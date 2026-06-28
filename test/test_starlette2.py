import asyncio
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import Response
import httpx

class EmptyResponse(Response):
    async def __call__(self, scope, receive, send):
        pass

async def handle_post_message(scope, receive, send):
    # simulate ASGI sending response
    await send({"type": "http.response.start", "status": 202, "headers": []})
    await send({"type": "http.response.body", "body": b"Accepted"})

async def handle_messages(request: Request):
    await handle_post_message(request.scope, request.receive, request._send)
    return EmptyResponse()

app = Starlette(routes=[Route("/", handle_messages, methods=["POST"])])

import threading
import uvicorn
import time

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8999, log_level="critical")

t = threading.Thread(target=run_server, daemon=True)
t.start()
time.sleep(1)
resp = httpx.post("http://127.0.0.1:8999/")
print("Status:", resp.status_code)
print("Body:", resp.text)
