"""Bitta xizmat: 3D ofis sayti + AI uchun API + Telegram bot.
Ishga tushirish: python server.py  (Render'da PORT avtomatik beriladi)"""
import os, json, time, hmac, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import anthropic, bot

client = anthropic.Anthropic()
INDEX = open(os.path.join(os.path.dirname(__file__), "index.html"), "rb").read()
hits = []

class H(BaseHTTPRequestHandler):
    def reply(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        if self.path in ("/", "/index.html"): self.reply(200, INDEX, "text/html")
        elif self.path == "/health": self.reply(200, b"ok", "text/plain")
        else: self.reply(404, {"error": "topilmadi"})
    def do_POST(self):
        try:
            d = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        except Exception:
            return self.reply(400, {"error": "noto'g'ri so'rov"})
        if not hmac.compare_digest(str(d.get("pw", "")), bot.PASSWORD):
            return self.reply(401, {"error": "parol noto'g'ri"})
        if self.path == "/api/auth": return self.reply(200, {"ok": True})
        if self.path != "/api/ai": return self.reply(404, {"error": "topilmadi"})
        now = time.time(); hits[:] = [t for t in hits if now - t < 60]
        if len(hits) >= 30: return self.reply(429, {"error": "juda ko'p so'rov, biroz kuting"})
        hits.append(now)
        try:
            r = client.messages.create(model=bot.MODEL, max_tokens=6000,
                messages=[{"role": "user", "content": str(d.get("prompt", ""))[:20000]}])
            self.reply(200, {"text": r.content[0].text})
        except Exception as e:
            print("AI xato:", e); self.reply(500, {"error": "AI xatosi, API kalitni tekshiring"})
    def log_message(self, *a): pass

if __name__ == "__main__":
    threading.Thread(target=bot.run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 8000))
    print("Sayt ishga tushdi, port", port)
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()
