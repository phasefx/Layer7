import sys
import json

class NativeMCPServer:
    """
    A lightweight dependency-free MCP JSON-RPC 2.0 stdio server.
    """
    def __init__(self, registry):
        self.registry = registry

    def serve_stdio(self):
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_id = req.get("id")
            method = req.get("method")
            params = req.get("params", {})

            if method == "initialize":
                self._send_response(msg_id, {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "Layer7", "version": "0.8.0"}
                })
            elif method == "tools/list":
                self._send_response(msg_id, {"tools": self.registry.get_tools()})
            elif method == "tools/call":
                t_name = params.get("name")
                t_args = params.get("arguments", {})
                try:
                    res = self.registry.call_tool(t_name, t_args)
                    self._send_response(msg_id, {
                        "content": [
                            {"type": "text", "text": json.dumps(res, indent=2)}
                        ]
                    })
                except ValueError as e:
                    self._send_error(msg_id, -32601, str(e))
                except Exception as e:
                    self._send_error(msg_id, -32603, str(e))
            else:
                self._send_error(msg_id, -32601, f"Method '{method}' not found.")

    def _send_response(self, msg_id, result):
        if msg_id is not None:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result}) + "\n")
            sys.stdout.flush()

    def _send_error(self, msg_id, code, message):
        if msg_id is not None:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}) + "\n")
            sys.stdout.flush()
