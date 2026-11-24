#!/usr/bin/env python3
"""jamai-suno (suno/) tests against a local mock of an OAuth-protected MCP server.

The mock follows what api.suno.com showed on 2026-11-23 (401 + resource_metadata, protected-resource
and authorization-server metadata, dynamic registration, PKCE S256). Its tool names are invented:
Suno's real ones are only visible after sign-in.

  python3 tests/test_suno.py
"""
import base64
import hashlib
import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "suno"))
CLI = [str(ROOT / "suno" / "jamai-suno")]          # the command, as install.sh and the .deb link it
GOOD = "good-token"


class Mock(http.server.BaseHTTPRequestHandler):
    state: dict = {}

    def log_message(self, *a):
        pass

    @property
    def base(self):
        return f"http://127.0.0.1:{self.server.server_port}"

    def _json(self, code, obj, headers=None):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlsplit(self.path)
        if u.path == "/.well-known/oauth-protected-resource/mcp":
            return self._json(200, {"resource": f"{self.base}/mcp", "authorization_servers": [f"{self.base}/oauth"],
                                    "scopes_supported": ["api:v0", "credits:spend", "offline_access"]})
        if u.path == "/.well-known/oauth-authorization-server/oauth":
            return self._json(200, {"issuer": f"{self.base}/oauth",
                                    "authorization_endpoint": f"{self.base}/oauth/authorize/",
                                    "token_endpoint": f"{self.base}/oauth/token/",
                                    "registration_endpoint": f"{self.base}/oauth/register/",
                                    "code_challenge_methods_supported": ["S256"]})
        if u.path == "/oauth/authorize/":
            q = dict(urllib.parse.parse_qsl(u.query))
            assert q["code_challenge_method"] == "S256" and q["client_id"] == "mock-client"
            assert q["resource"] == f"{self.base}/mcp", q
            Mock.state["challenge"] = q["code_challenge"]
            Mock.state["authorize_redirect"] = q["redirect_uri"]
            self.send_response(302)
            self.send_header("Location", q["redirect_uri"] + "?" + urllib.parse.urlencode(
                {"code": "the-code", "state": q["state"]}))
            self.end_headers()
            return
        if u.path == "/audio/c1.mp3":
            body = b"ID3mock-audio"
            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._json(404, {"error": "not found"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n)
        u = urllib.parse.urlsplit(self.path)
        if u.path == "/oauth/register/":
            reg = json.loads(raw)
            assert reg["token_endpoint_auth_method"] == "none"
            Mock.state["registered_redirects"] = reg["redirect_uris"]
            return self._json(201, {"client_id": "mock-client", "redirect_uris": reg["redirect_uris"]})
        if u.path == "/oauth/token/":
            f = dict(urllib.parse.parse_qsl(raw.decode()))
            if f["grant_type"] == "authorization_code":
                Mock.state["token_redirect"] = f["redirect_uri"]
                ch = base64.urlsafe_b64encode(hashlib.sha256(f["code_verifier"].encode()).digest()).rstrip(b"=")
                if ch.decode() != Mock.state.get("challenge") or f["code"] != "the-code":
                    return self._json(400, {"error": "invalid_grant"})
                return self._json(200, {"access_token": GOOD, "refresh_token": "r1", "expires_in": 3600})
            if f["grant_type"] == "refresh_token" and f["refresh_token"] == "r1":
                return self._json(200, {"access_token": GOOD, "expires_in": 3600})
            return self._json(400, {"error": "unsupported"})
        if u.path != "/mcp":
            return self._json(404, {"error": "not found"})
        if self.headers.get("Authorization") != f"Bearer {GOOD}":
            return self._json(401, {"error": "sign in to Suno to use this server"}, {
                "WWW-Authenticate": f'Bearer resource_metadata="{self.base}/.well-known/oauth-protected-resource/mcp"'})
        msg = json.loads(raw)
        m = msg.get("method")
        if m == "initialize":
            return self._json(200, {"jsonrpc": "2.0", "id": msg["id"], "result": {
                "protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                "serverInfo": {"name": "mock-suno", "version": "0"}}}, {"Mcp-Session-Id": "sess-1"})
        assert self.headers.get("Mcp-Session-Id") == "sess-1", "session id not echoed"
        if m == "notifications/initialized":
            self.send_response(202)
            self.end_headers()
            return
        if m == "tools/list":
            return self._json(200, {"jsonrpc": "2.0", "id": msg["id"], "result": {"tools": [
                {"name": "create_song", "description": "Make a song",
                 "inputSchema": {"type": "object", "required": ["style"], "properties": {
                     "title": {"type": "string"}, "style": {"type": "string", "maxLength": 1000},
                     "lyrics": {"type": "string"}, "instrumental": {"type": "boolean"},
                     "is_public": {"type": "boolean"}}}},
                {"name": "get_credits", "description": "Credits left", "inputSchema": {"type": "object"}}]}})
        if m == "tools/call":
            Mock.state["call"] = msg["params"]
            result = {"content": [{"type": "text", "text": json.dumps(
                {"clips": [{"id": "c1", "audio_url": f"{self.base}/audio/c1.mp3"}]})}]}
            events = [{"jsonrpc": "2.0", "method": "notifications/progress", "params": {"progress": 1}},
                      {"jsonrpc": "2.0", "id": msg["id"], "result": result}]
            body = "".join(f"event: message\ndata: {json.dumps(e)}\n\n" for e in events).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._json(200, {"jsonrpc": "2.0", "id": msg.get("id"), "error": {"code": -32601, "message": m}})


class BridgeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Mock)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_port}/mcp"
        cls.tmp = Path(tempfile.mkdtemp(prefix="jamai-suno-test-"))
        # The module reads its config folder at import: never the person's own tokens.
        os.environ["JAMAI_SUNO_CONFIG_DIR"] = str(cls.tmp / "cfg-import")
        comp = cls.tmp / "op-test"
        (comp / "suno").mkdir(parents=True)
        (comp / "suno" / "request.json").write_text(json.dumps({
            "suno": {"title": "Test", "style": "nylon guitar; 80 BPM", "instrumental": True},
            "variants": {"lyrics": {"title": "Test", "style": "voice", "instrumental": False, "lyrics": "la la"}}}))
        cls.comp = comp

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        shutil.rmtree(cls.tmp)

    def run_cli(self, *args, token=None):
        env = dict(os.environ, JAMAI_SUNO_MCP_URL=self.url, JAMAI_SUNO_CONFIG_DIR=str(self.tmp / "cfg"))
        env.pop("SUNO_MCP_TOKEN", None)
        if token:
            env["SUNO_MCP_TOKEN"] = token
        return subprocess.run(CLI + list(args), capture_output=True, text=True, env=env, timeout=60)

    def test_1_unauthorized_stops_cleanly(self):
        r = self.run_cli("generate", str(self.comp))
        self.assertEqual(r.returncode, 3, r.stderr)
        self.assertIn("authorization required", r.stderr)
        logs = list((self.comp / "suno" / "log").glob("*-generate.jsonl"))
        self.assertTrue(logs)

    def test_2_no_tool_named_lists_live_tools(self):
        r = self.run_cli("generate", str(self.comp), token=GOOD)
        self.assertEqual(r.returncode, 4, r.stderr)
        self.assertIn("create_song", r.stderr)
        self.assertTrue((self.comp / "suno" / "tools.json").is_file())

    def test_3_plan_sends_no_call(self):
        Mock.state.pop("call", None)
        r = self.run_cli("generate", str(self.comp), "--tool", "create_song", "--plan", token=GOOD)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('"instrumental": true', r.stdout)
        self.assertNotIn("call", Mock.state)

    def test_4_generate_lyrics_downloads_audio(self):
        r = self.run_cli("generate", str(self.comp), "--tool", "create_song", "--variant", "lyrics", token=GOOD)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertEqual(Mock.state["call"]["arguments"],
                         {"lyrics": "la la", "title": "Test", "style": "voice", "instrumental": False,
                          "is_public": False})
        takes = list(self.comp.glob("suno/*-lyrics/take-1.mp3"))
        self.assertEqual(len(takes), 1)
        self.assertEqual(takes[0].read_bytes(), b"ID3mock-audio")
        log = next(self.comp.glob("suno/log/*.jsonl")).read_text()
        self.assertNotIn(GOOD, log, "the token must never reach the log")

    def test_5_login_saves_token_then_status_is_authorized(self):
        import jamai_suno as js
        cfg = self.tmp / "cfg-login"
        js.MCP_URL, js.CONFIG_DIR, js.TOKEN_FILE = self.url, cfg, cfg / "oauth.json"
        os.environ.pop("SUNO_MCP_TOKEN", None)

        def fake_browser(url):
            threading.Thread(target=lambda: urllib.request.urlopen(url, timeout=10).read(), daemon=True).start()
            return True

        js.webbrowser.open = fake_browser
        self.assertEqual(js.main(["login", "--port", "41798", "--timeout", "20"]), 0)
        saved = json.loads((cfg / "oauth.json").read_text())
        self.assertEqual(saved["access_token"], GOOD)
        self.assertEqual(oct((cfg / "oauth.json").stat().st_mode & 0o777), "0o600")
        saved["expires_at"] = 0       # force the refresh path
        (cfg / "oauth.json").write_text(json.dumps(saved))
        tok, src = js.load_token()
        self.assertEqual(tok, GOOD)
        self.assertIn("refreshed", src)
        self.assertEqual(js.main(["status"]), 0)

    def test_6_login_with_public_redirect_uri(self):
        import jamai_suno as js
        cfg = self.tmp / "cfg-public"
        js.MCP_URL, js.CONFIG_DIR, js.TOKEN_FILE = self.url, cfg, cfg / "oauth.json"
        os.environ.pop("SUNO_MCP_TOKEN", None)
        public, port = "https://jamai.example.test/suno-callback", 41797

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None

        def fake_phone_and_mux(url):
            def go():
                import time
                time.sleep(0.3)
                # A stray hit on the public route first: it must not end the login.
                try:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/callback?state=wrong&code=x", timeout=5)
                except urllib.error.HTTPError as e:
                    assert e.code == 400
                try:
                    urllib.request.build_opener(NoRedirect).open(url, timeout=10)
                except urllib.error.HTTPError as e:
                    loc = e.headers["Location"]
                assert loc.startswith(public + "?"), loc
                # The mux: public path → loopback /callback, query string kept.
                urllib.request.urlopen(f"http://127.0.0.1:{port}/callback?" + loc.split("?", 1)[1], timeout=10).read()
            threading.Thread(target=go, daemon=True).start()
            return True

        js.webbrowser.open = fake_phone_and_mux
        self.assertEqual(js.main(["login", "--port", str(port), "--timeout", "20", "--redirect-uri", public]), 0)
        self.assertEqual(Mock.state["registered_redirects"], [public])
        self.assertEqual(Mock.state["authorize_redirect"], public)
        self.assertEqual(Mock.state["token_redirect"], public)
        self.assertEqual(json.loads((cfg / "oauth.json").read_text())["access_token"], GOOD)


if __name__ == "__main__":
    unittest.main(verbosity=2)
