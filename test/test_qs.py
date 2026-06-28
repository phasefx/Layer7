from starlette.requests import Request

scope = {"type": "http", "method": "POST", "query_string": b""}
request1 = Request(scope)

# modify scope
scope["query_string"] = b"session_id=123"

request2 = Request(scope)
print("Request2:", request2.query_params)
