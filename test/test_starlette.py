import asyncio
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

async def asgi_app(scope, receive, send):
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"Hello World"})

app = Starlette(routes=[Route("/", asgi_app, methods=["POST", "GET"])])

client = TestClient(app)
print(client.post("/").text)
