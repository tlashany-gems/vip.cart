import time
import json
import os
import urllib.request
import urllib.parse
import ssl
import threading

# ══════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════
BOT_TOKEN      = "7973273382:AAGfOQZmr6N_jkcy9wFc8J0l1C0UUvzyrj0"
CHANNEL_ID     = "@FY_TF"
CHECK_INTERVAL = 5
MIN_GIFT       = 200          # ✅ كروت أكبر من 130 بس
MAX_CARDS      = 2
RECHARGE_URL   = "https://telegrambot.serv00.net/recharge.php"

ACCOUNTS = [
    {"phone": "01008967492", "password": "##1122334455Qq"},
    {"phone": "01018529827", "password": "1052003Mm@#$"},
    {"phone": "01003971136", "password": "1052003Mm$#@"},
]

STATE_FILE  = "bot_state.json"
OFFSET_FILE = "tg_offset.txt"
TG_URL      = f"https://api.telegram.org/bot{BOT_TOKEN}/"

tokens = [{"token": None, "expiry": 0} for _ in ACCOUNTS]

CURRENT_ACCOUNT = 0

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode    = ssl.CERT_NONE

# ══════════════════════════════════════════
#  LOGGER
# ══════════════════════════════════════════
def log(level, msg):
    print(f"[{time.strftime('%H:%M:%S')}] [{level}] {msg}", flush=True)

# ══════════════════════════════════════════
#  HTTP
# ══════════════════════════════════════════
def http_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as res:
        return res.read().decode()

def http_post(url, data, headers=None):
    body = urllib.parse.urlencode(data).encode()
    req  = urllib.request.Request(url, data=body, headers=headers or {}, method="POST")
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as res:
        return res.read().decode()

def http_post_json(url, payload):
    body = json.dumps(payload).encode()
    req  = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as res:
        return res.read().decode()

# ══════════════════════════════════════════
#  TELEGRAM
# ══════════════════════════════════════════
def tg(method, **params):
    try:
        raw = http_post_json(TG_URL + method, params)
        d   = json.loads(raw)
        if not d.get("ok"):
            desc = d.get("description", "")
            if "not modified" not in desc and "not found" not in desc:
                log("WARN", f"TG[{method}]: {desc}")
            return None
        return d.get("result")
    except Exception as e:
        log("ERR", f"TG[{method}]: {e}")
        return None

# ══════════════════════════════════════════
#  VODAFONE
# ══════════════════════════════════════════
def vf_login(idx):
    acc = ACCOUNTS[idx]
    try:
        raw = http_post(
            "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token",
            data={
                "grant_type":    "password",
                "username":      acc["phone"],
                "password":      acc["password"],
                "client_secret": "95fd95fb-7489-4958-8ae6-d31a525cd20a",
                "client_id":     "ana-vodafone-app"
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept":       "application/json",
                "User-Agent":   "okhttp/4.11.0"
            }
        )
        data       = json.loads(raw)
        token      = data.get("access_token")
        expires_in = data.get("expires_in", 3600)
        if token:
            tokens[idx]["token"]  = token
            tokens[idx]["expiry"] = time.time() + expires_in - 180
            log("INFO", f"✅ Login OK [{acc['phone']}] ~{expires_in//60} min")
            return token
        log("ERR", f"❌ Login failed [{acc['phone']}]: {data.get('error_description','?')}")
        return None
    except Exception as e:
        log("ERR", f"vf_login[{idx}]: {e}")
        return None

def get_token(idx):
    t = tokens[idx]
    if t["token"] and time.time() < t["expiry"]:
        return t["token"]
    log("INFO", f"🔑 Refreshing [{ACCOUNTS[idx]['phone']}]...")
    return vf_login(idx)

def vf_promos(token, phone):
    try:
        raw_text = http_get(
            f"https://web.vodafone.com.eg/services/dxl/ramadanpromo/promotion"
            f"?@type=RamadanHub&channel=website&msisdn={phone}",
            headers={
                "Authorization":   f"Bearer {token}",
                "User-Agent":      "Mozilla/5.0",
                "Accept":          "application/json",
                "clientId":        "WebsiteConsumer",
                "api-host":        "PromotionHost",
                "channel":         "WEB",
                "Accept-Language": "ar",
                "msisdn":          phone,
                "Content-Type":    "application/json",
                "Referer":         "https://web.vodafone.com.eg/ar/ramadan"
            }
        )
        data  = json.loads(raw_text)
        cards = []

        for item in data:
            if not isinstance(item, dict) or "pattern" not in item:
                continue
            for pat in item["pattern"]:
                for action in pat.get("action", []):
                    c = {x["name"]: str(x["value"])
                         for x in action.get("characteristics", [])}
                    if not c:
                        continue
                    try:
                        gift = int(c.get("GIFT_UNITS", 0))
                    except:
                        continue

                    # ✅ فلتر: gift لازم يكون أكبر من 130
                    if gift <= MIN_GIFT:
                        continue

                    serial = str(c.get("CARD_SERIAL", "")).strip()
                    if len(serial) != 13:
                        continue
                    try:
                        amount    = int(c.get("amount", 0))
                        remaining = int(c.get("REMAINING_DEDICATIONS", 0))
                    except:
                        continue
                    cards.append({
                        "serial":    serial,
                        "gift":      gift,
                        "amount":    amount,
                        "remaining": remaining,
                    })

        cards.sort(key=lambda x: (x["gift"], x["amount"]), reverse=True)
        return raw_text, cards

    except Exception as e:
        log("WARN", f"vf_promos[{phone}]: {e}")
        return None, []

# ══════════════════════════════════════════
#  MESSAGE
# ══════════════════════════════════════════
def build_msg(card):
    serial = str(card["serial"]).strip()
    ussd   = "*858*" + serial + "#"
    link   = f"{RECHARGE_URL}?serial={serial}"

    text = (
        "*╭────═⌁TALASHNY⌁═────⟤*\n"
        "*│╭✦───✦──────✦───⟢*\n"
        f"*╞╡ Value ➜ جنيه* `{card['amount']}`\n"
        f"*╞╡ Gift Units ➜ وحده* `{card['gift']}`\n"
        f"*╞╡ Remaining ➜ متبقي* `{card['remaining']}`\n"
        "*│╰✦────✦─⟐─✦────✦╮*\n"
        "*│╭✦────✦─⟐─✦────✦╯*\n"
        f"*╞╡ Code ➜* `{ussd}`\n"
        "*│╰✦───✦──────✦───⟢*\n"
        "*╰────═⌁TALASHNY⌁═────⟤*"
    )

    keyboard = {
        "inline_keyboard": [[
            {
                "text": "⌁ اضغط لشحن اسرع ⌁",
                "url":  link
            }
        ]]
    }

    return text, keyboard

# ══════════════════════════════════════════
#  STATE
# ══════════════════════════════════════════
def load_state():
    return json.load(open(STATE_FILE, encoding="utf-8")) \
           if os.path.exists(STATE_FILE) else {}

def save_state(s):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)

def load_offset():
    return int(open(OFFSET_FILE).read().strip()) \
           if os.path.exists(OFFSET_FILE) else 0

def save_offset(o):
    open(OFFSET_FILE, "w").write(str(o))

def clear_pending():
    res = tg("getUpdates", offset=-1, limit=1)
    if res:
        last = res[0]["update_id"]
        tg("getUpdates", offset=last + 1)
        save_offset(last + 1)
        log("INFO", f"🧹 Cleared — offset={last+1}")
    else:
        save_offset(0)

# ══════════════════════════════════════════
#  ✅ LONG POLLING — thread منفصل
#  البوت بيستقبل التحديثات من السيرفر على طول
# ══════════════════════════════════════════
def long_poll_loop():
    log("INFO", "📡 Long polling started — waiting for server updates...")
    while True:
        try:
            offset  = load_offset()
            # timeout=30 → السيرفر بيستنى 30 ثانية لو ما فيش updates
            updates = tg(
                "getUpdates",
                offset=offset,
                limit=100,
                timeout=30,
                allowed_updates=["callback_query", "message"]
            )
            if updates:
                for upd in updates:
                    uid = upd["update_id"]
                    save_offset(uid + 1)
                    log("INFO", f"📩 Update received: {uid}")
        except Exception as e:
            log("ERR", f"LongPoll: {e}")
            time.sleep(3)

# ══════════════════════════════════════════
#  MAIN CHECK
# ══════════════════════════════════════════
def check_and_update():
    global CURRENT_ACCOUNT

    idx   = CURRENT_ACCOUNT
    phone = ACCOUNTS[idx]["phone"]
    log("INFO", f"🔄 [{idx+1}/3] {phone}")

    CURRENT_ACCOUNT = (CURRENT_ACCOUNT + 1) % len(ACCOUNTS)

    token = get_token(idx)
    if not token:
        log("ERR", f"❌ No token [{phone}]")
        return

    raw_text, all_cards = vf_promos(token, phone)
    if raw_text is None:
        return

    log("INFO", f"🔁 [{phone}] — {len(all_cards)} cards with gift > {MIN_GIFT}")

    target     = all_cards[:MAX_CARDS]
    target_map = {c["serial"]: c for c in target}
    state      = load_state()

    # ✅ حذف الكروت اللي remaining=0 أو اختفت من السيرفر
    for mid in list(state.keys()):
        serial = state[mid]["serial"]
        live   = target_map.get(serial)

        should_delete = (
            live is None or        # اختفى من السيرفر
            live["remaining"] <= 0 # ✅ المتبقي وصل صفر
        )

        if should_delete:
            tg("deleteMessage", chat_id=CHANNEL_ID, message_id=int(mid))
            del state[mid]
            reason = "remaining=0" if (live and live["remaining"] <= 0) else "gone from server"
            log("INFO", f"🗑️ Deleted msg={mid} serial={serial} [{reason}]")

    # ✅ بعت الكروت الجديدة (gift > 130 فقط)
    sent = {v["serial"] for v in state.values()}
    for serial, card in target_map.items():
        if len(state) >= MAX_CARDS:
            break
        if serial not in sent and card["remaining"] > 0:
            txt, kb = build_msg(card)
            res = tg("sendMessage", chat_id=CHANNEL_ID,
                     text=txt, parse_mode="Markdown",
                     reply_markup=kb)
            if res and "message_id" in res:
                state[str(res["message_id"])] = card.copy()
                log("INFO", f"📤 Sent [{serial}] gift={card['gift']} remaining={card['remaining']} | {phone}")

    save_state(state)
    log("INFO", f"✅ Done — {len(state)} active")

# ══════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════
if __name__ == "__main__":
    log("INFO", f"🚀 TALASHNY | MIN_GIFT > {MIN_GIFT} | Long Polling ON | Auto Delete remaining=0")

    # login كل الحسابات
    for i in range(len(ACCOUNTS)):
        vf_login(i)

    clear_pending()

    # ✅ شغّل long polling في thread منفصل عشان ما يوقفش الـ main loop
    poll_thread = threading.Thread(target=long_poll_loop, daemon=True)
    poll_thread.start()

    last_check = 0
    fail_count = 0

    while True:
        try:
            if time.time() - last_check >= CHECK_INTERVAL:
                check_and_update()
                last_check = time.time()
            fail_count = 0
            time.sleep(1)

        except KeyboardInterrupt:
            log("INFO", "🛑 Stopped")
            break
        except Exception as e:
            fail_count += 1
            log("ERR", f"Error #{fail_count}: {e}")
            time.sleep(5 if fail_count < 10 else 30)