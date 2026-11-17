#!/usr/bin/env python3
"""fake_musescore.py — stands in for MuseScore's plugin in the self-test.

  fake_musescore.py <port> <log file>

A WebSocket server on 127.0.0.1:<port> that answers the way the plugin does:
"ping" → {"status": "success", "result": "pong"}, any other action →
{"status": "success", "result": {"received": <the command>}}. Each command it receives is
appended to the log, one JSON line each. Standard library only.
"""
import base64
import hashlib
import json
import socketserver
import struct
import sys

PORT, LOG = int(sys.argv[1]), sys.argv[2]


def recv_exact(sock, size):
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionError
        data += chunk
    return data


def send_text(sock, text):
    payload = text.encode("utf-8")
    head = bytearray([0x81])
    if len(payload) < 126:
        head.append(len(payload))
    elif len(payload) < 65536:
        head.append(126)
        head += struct.pack(">H", len(payload))
    else:
        head.append(127)
        head += struct.pack(">Q", len(payload))
    sock.sendall(bytes(head) + payload)


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        sock = self.request
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = sock.recv(4096)
            if not chunk:
                return
            head += chunk
        key = ""
        for line in head.decode("latin-1").split("\r\n"):
            if line.lower().startswith("sec-websocket-key:"):
                key = line.split(":", 1)[1].strip()
        accept = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
        sock.sendall(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                      "Sec-WebSocket-Accept: %s\r\n\r\n" % accept).encode())
        try:
            while True:
                first, second = recv_exact(sock, 2)
                opcode, size = first & 0x0F, second & 0x7F
                if size == 126:
                    size = struct.unpack(">H", recv_exact(sock, 2))[0]
                elif size == 127:
                    size = struct.unpack(">Q", recv_exact(sock, 8))[0]
                if not second & 0x80:
                    return                          # a client frame must be masked
                mask = recv_exact(sock, 4)
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(recv_exact(sock, size)))
                if opcode == 0x8:
                    return
                if opcode != 0x1:
                    continue
                command = json.loads(data)
                with open(LOG, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(command) + "\n")
                result = "pong" if command.get("action") == "ping" else {"received": command}
                send_text(sock, json.dumps({"status": "success", "result": result}))
        except (ConnectionError, OSError, ValueError):
            return


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


Server(("127.0.0.1", PORT), Handler).serve_forever()
