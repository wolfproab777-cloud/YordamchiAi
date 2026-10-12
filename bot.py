"""AI ofis Telegram boti. Ishga tushirish:
  pip install requests anthropic
  (.env.example ni .env ga nusxalab to'ldiring)  ->  python bot.py
Tokenni kodga yozmang, faqat .env yoki muhit o'zgaruvchisida saqlang."""
import os, re, time, json, html, datetime, requests, anthropic

def load_env():
    if os.path.exists(".env"):
        for l in open(".env", encoding="utf-8"):
            if "=" in l and not l.startswith("#"):
                k, v = l.strip().split("=", 1); os.environ.setdefault(k, v)
load_env()
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
PASSWORD = os.environ.get("BOT_PASSWORD", "")
OWNER = os.environ.get("OWNER_USERNAME", "lGhostN1l").lstrip("@").lower()
API = f"https://api.telegram.org/bot{TOKEN}"
ai = anthropic.Anthropic()
MODEL = "claude-sonnet-5-5"
STATE_FILE = "state.json"
SYSTEM = ("Sen AI ofisning bosh dasturchisisan, professional veb-dasturchi va dizayner. O'zbek tilida, do'stona va aniq yoz. "
          "Agar foydalanuvchi sayt, sahifa yoki ilova so'rasa: 2 jumla izoh yoz, so'ng to'liq ishlaydigan, zamonaviy, "
          "mobilga moslashgan bitta HTML faylni (inline CSS va JS) ```html blokida ber. Boshqa savollarga qisqa javob ber.")

state = json.load(open(STATE_FILE)) if os.path.exists(STATE_FILE) else {"auth": {}, "owner_chat": None, "last_report": ""}
hist = {}
def save(): json.dump(state, open(STATE_FILE, "w"))

def tg(method, **kw):
    r = requests.post(f"{API}/{method}", timeout=70, **kw)
    return r.json()
def send(chat, text):
    for i in range(0, len(text), 4000):
        tg("sendMessage", data={"chat_id": chat, "text": text[i:i+4000]})
def send_code(chat, code):
    for i in range(0, len(code), 3500):
        tg("sendMessage", data={"chat_id": chat, "parse_mode": "HTML", "text": "<pre>" + html.escape(code[i:i+3500]) + "</pre>"})

def authed(chat):
    t = state["auth"].get(str(chat))
    return t and time.time() - t < 24 * 3600

def answer(chat, text):
    h = hist.setdefault(chat, [])
    h.append({"role": "user", "content": text}); del h[:-10]
    r = ai.messages.create(model=MODEL, max_tokens=8000, system=SYSTEM, messages=h)
    out = r.content[0].text
    h.append({"role": "assistant", "content": out})
    m = re.search(r"```html\s*(.*?)```", out, re.S)
    if m:
        code = m.group(1).strip()
        send(chat, re.sub(r"```html.*?```", "(kod pastda va fayl sifatida)", out, flags=re.S))
        tg("sendDocument", data={"chat_id": chat, "caption": "Tayyor sayt (HTML)"}, files={"document": ("sayt.html", code.encode("utf-8"), "text/html")})
        send_code(chat, code)
    else:
        send(chat, out)

def handle(msg):
    chat = msg["chat"]["id"]; text = (msg.get("text") or "").strip()
    user = (msg["from"].get("username") or "").lower()
    if not text: return
    if text == "/start" or not authed(chat):
        if text == PASSWORD:
            state["auth"][str(chat)] = time.time()
            if user == OWNER: state["owner_chat"] = chat
            save(); send(chat, "Parol to'g'ri. Gaplashishingiz mumkin. Sayt so'rang, men tayyorlab beraman."); return
        send(chat, "Parolni kiriting (24 soatda bir marta so'raladi)."); return
    if text == "/hisobot": send(chat, report()); return
    answer(chat, text)

def report():
    r = ai.messages.create(model=MODEL, max_tokens=500, system=SYSTEM,
        messages=[{"role": "user", "content": "AI ofis direktoriga bugungi ish bo'yicha qisqa hisobot yoz (menejer, dasturchi, tahlilchi, dizayner nomidan)."}])
    return r.content[0].text

def daily_report():
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=5)  # Toshkent
    key = now.strftime("%Y-%m-%d")
    if now.hour >= 18 and state["last_report"] != key and state["owner_chat"]:
        state["last_report"] = key; save(); send(state["owner_chat"], "Kunlik hisobot:\n\n" + report())

def run_bot():
    if not TOKEN:
        print("TELEGRAM_BOT_TOKEN yo'q, bot o'chirilgan (sayt ishlayveradi)"); return
    offset = None
    print("Bot ishga tushdi")
    while True:
        try:
            upd = tg("getUpdates", params={"timeout": 50, "offset": offset})
            for u in upd.get("result", []):
                offset = u["update_id"] + 1
                if "message" in u: handle(u["message"])
            daily_report()
        except Exception as e:
            print("xato:", e); time.sleep(5)

if __name__ == "__main__":
    run_bot()
