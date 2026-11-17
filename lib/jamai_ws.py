#!/usr/bin/env python3
"""jamai_ws — talk to the score open in MuseScore, through its plugin's WebSocket.

The MuseScore plugin (musescore/musescore-mcp-websocket.qml) listens on port 8765 once it is
started from MuseScore's Plugins menu. It takes one JSON command per message,
{"action": "...", "params": {...}}, applies it to the open score and answers
{"status": "success", "result": ...} or {"status": "error", "message": ...}.

  jamai_ws.py ping
  jamai_ws.py getScore
  jamai_ws.py addNote '{"pitch": 60, "duration": {"numerator": 1, "denominator": 4}}'

A minimal WebSocket client, standard library only: text frames, masked as a client must,
pings answered, a message split into several frames joined. No TLS, no extensions: it only
ever talks to MuseScore on this machine.
"""
import base64
import hashlib
import json
import os
import socket
import struct
import sys

HOST = "127.0.0.1"
NOT_RUNNING = (
    "MuseScore is not listening on port {port}. In MuseScore: Home → Plugins, enable "
    "\"MuseScore API Server\", then start it from the Plugins menu (Plugins → MuseScore API Server). "
    "If it is not in the list, install it with: jamai-musescore --install-plugin, then restart MuseScore."
)


class WebSocketError(Exception):
    pass


def default_port():
    try:
        return int(os.environ.get("JAMAI_MUSESCORE_LIVE_PORT", "8765"))
    except ValueError:
        return 8765


class Client:
    def __init__(self, host=HOST, port=None, timeout=15.0):
        self.host, self.port, self.timeout = host, port or default_port(), timeout
        self.sock, self._rest = None, b""

    def connect(self):
        try:
            sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        except OSError:
            raise WebSocketError(NOT_RUNNING.format(port=self.port))
        key = base64.b64encode(os.urandom(16)).decode()
        sock.sendall(("GET / HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                      "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n"
                      % (self.host, self.port, key)).encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = sock.recv(4096)
            if not chunk:
                sock.close()
                raise WebSocketError("port %d answered, but closed during the WebSocket handshake" % self.port)
            head += chunk
            if len(head) > 65536:
                sock.close()
                raise WebSocketError("the handshake reply is too long")
        header, self._rest = head.split(b"\r\n\r\n", 1)
        lines = header.decode("latin-1").split("\r\n")
        status = lines[0].split()
        if len(status) < 2 or status[1] != "101":
            sock.close()
            raise WebSocketError("port %d is not a WebSocket server: %s" % (self.port, lines[0][:80]))
        fields = {}
        for line in lines[1:]:
            if ":" in line:
                name, value = line.split(":", 1)
                fields[name.strip().lower()] = value.strip()
        expected = base64.b64encode(hashlib.sha1(
            (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
        if fields.get("sec-websocket-accept") != expected:
            sock.close()
            raise WebSocketError("the handshake reply does not match the key sent")
        self.sock = sock
        return self

    def _send_frame(self, opcode, payload):
        head = bytearray([0x80 | opcode])
        size = len(payload)
        if size < 126:
            head.append(0x80 | size)
        elif size < 65536:
            head.append(0x80 | 126)
            head += struct.pack(">H", size)
        else:
            head.append(0x80 | 127)
            head += struct.pack(">Q", size)
        mask = os.urandom(4)
        head += mask
        self.sock.sendall(bytes(head) + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def _recv_exact(self, size):
        data, self._rest = self._rest[:size], self._rest[size:]
        while len(data) < size:
            chunk = self.sock.recv(size - len(data))
            if not chunk:
                raise WebSocketError("MuseScore closed the connection")
            data += chunk
        return data

    def send_text(self, text):
        self._send_frame(0x1, text.encode("utf-8"))

    def recv_text(self):
        parts = []
        while True:
            first, second = self._recv_exact(2)
            final, opcode = first & 0x80, first & 0x0F
            size = second & 0x7F
            if size == 126:
                size = struct.unpack(">H", self._recv_exact(2))[0]
            elif size == 127:
                size = struct.unpack(">Q", self._recv_exact(8))[0]
            mask = self._recv_exact(4) if second & 0x80 else None
            data = self._recv_exact(size)
            if mask:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            if opcode == 0x9:                       # ping: answer it and keep reading
                self._send_frame(0xA, data)
                continue
            if opcode == 0xA:                       # pong
                continue
            if opcode == 0x8:
                raise WebSocketError("MuseScore closed the connection")
            parts.append(data)
            if final:
                return b"".join(parts).decode("utf-8", errors="replace")

    def command(self, action, params=None):
        """Send one command and return MuseScore's answer, parsed."""
        self.send_text(json.dumps({"action": action, "params": params or {}}))
        reply = self.recv_text()
        try:
            return json.loads(reply)
        except ValueError:
            return {"status": "error", "message": "not JSON: " + reply[:200]}

    def close(self):
        if self.sock:
            try:
                self._send_frame(0x8, b"")
            except OSError:
                pass
            self.sock.close()
            self.sock = None


def call(action, params=None, port=None):
    """One command on a fresh connection. Raises WebSocketError when MuseScore is not reachable."""
    client = Client(port=port).connect()
    try:
        return client.command(action, params)
    finally:
        client.close()


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    action = argv[0]
    try:
        params = json.loads(argv[1]) if len(argv) > 1 else {}
    except ValueError as exc:
        print("jamai_ws: the parameters are not JSON: %s" % exc, file=sys.stderr)
        return 2
    try:
        reply = call(action, params)
    except (WebSocketError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 3
    print(json.dumps(reply, ensure_ascii=False, indent=1))
    return 0 if reply.get("status") == "success" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
