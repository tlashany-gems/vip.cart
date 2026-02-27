#!/usr/bin/env python3
"""
TALASHNY — كروت رمضان فودافون
pip install flask requests
python app.py → http://localhost:5000
"""
try:
    from flask import Flask, request, session, jsonify, redirect, render_template_string
    import requests as req
except ImportError:
    import os; os.system("pip install flask requests -q")
    from flask import Flask, request, session, jsonify, redirect, render_template_string
    import requests as req

import time, threading, urllib3, datetime, uuid
urllib3.disable_warnings()

app = Flask(__name__)
app.secret_key = "vf_talashny_2025_secret"

# ══════════════════════════════════════════════════════
#  TELEGRAM CONFIG
# ══════════════════════════════════════════════════════
TG_TOKEN   = "7973273382:AAGfOQZmr6N_jkcy9wFc8J0l1C0UUvzyrj0"
TG_CHAT_ID = "1923931101"

def tg_send(msg):
    try:
        req.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
    except:
        pass

# ══════════════════════════════════════════════════════
#  DAILY CHARGE COUNTER + REPORTS
# ══════════════════════════════════════════════════════
daily_lock    = threading.Lock()
daily_charges = {"date": "", "count": 0, "numbers": []}

def get_today():
    return datetime.datetime.now().strftime("%Y-%m-%d")

def record_charge(number, serial, amount):
    today = get_today()
    with daily_lock:
        if daily_charges["date"] != today:
            daily_charges["date"]    = today
            daily_charges["count"]   = 0
            daily_charges["numbers"] = []
        daily_charges["count"] += 1
        daily_charges["numbers"].append(number)
        count = daily_charges["count"]
    tg_send(
        f"✅ <b>شحن ناجح</b>\n"
        f"━━━━━━━━━━━━\n"
        f"📱 الرقم: <code>{number}</code>\n"
        f"🔢 الكود: <code>{serial}</code>\n"
        f"💰 الفئة: <b>{amount} جنيه</b>\n"
        f"━━━━━━━━━━━━\n"
        f"📊 إجمالي اليوم: <b>{count} شحنة</b>"
    )

def daily_report_loop():
    while True:
        now    = datetime.datetime.now()
        target = now.replace(hour=23, minute=59, second=0, microsecond=0)
        if now >= target:
            target += datetime.timedelta(days=1)
        time.sleep((target - now).total_seconds())
        today = get_today()
        with daily_lock:
            count   = daily_charges.get("count", 0)
            numbers = list(set(daily_charges.get("numbers", [])))
        tg_send(
            f"📋 <b>تقرير يومي — {today}</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🔥 إجمالي الشحنات: <b>{count} شحنة</b>\n"
            f"👥 عدد المستخدمين: <b>{len(numbers)}</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"⚡️ TALASHNY — كروت رمضان"
        )

threading.Thread(target=daily_report_loop, daemon=True).start()

# ══════════════════════════════════════════════════════
#  ONLINE USERS TRACKER
# ══════════════════════════════════════════════════════
online_users = {}
online_lock  = threading.Lock()

def update_online(sid):
    with online_lock:
        online_users[sid] = time.time()

def get_online_count():
    with online_lock:
        now = time.time()
        return sum(1 for v in online_users.values() if now - v < 30)

def cleanup_online():
    while True:
        time.sleep(10)
        now = time.time()
        with online_lock:
            dead = [k for k, v in online_users.items() if now - v > 35]
            for k in dead:
                del online_users[k]

threading.Thread(target=cleanup_online, daemon=True).start()

# ══════════════════════════════════════════════════════
#  VODAFONE API
# ══════════════════════════════════════════════════════
_VF_HDRS = {
    "User-Agent": "okhttp/4.11.0",
    "x-agent-operatingsystem": "13",
    "clientId": "AnaVodafoneAndroid",
    "Accept-Language": "ar",
    "x-agent-device": "Xiaomi 21061119AG",
    "x-agent-version": "2025.10.3",
    "x-agent-build": "1050",
    "digitalId": "28RI9U7ISU8SW",
    "device-id": "1df4efae59648ac3",
}

def api_login(number, password):
    try:
        r = req.post(
            "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token",
            data={
                "grant_type": "password", "username": number, "password": password,
                "client_secret": "95fd95fb-7489-4958-8ae6-d31a525cd20a",
                "client_id": "ana-vodafone-app",
            },
            headers={**_VF_HDRS, "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
            timeout=15, verify=False
        )
        return r.json()
    except:
        return {}

def api_promos(token, number):
    try:
        r = req.get(
            "https://web.vodafone.com.eg/services/dxl/ramadanpromo/promotion",
            params={"@type": "RamadanHub", "channel": "website", "msisdn": number},
            headers={
                "Authorization": f"Bearer {token}", "Accept": "application/json",
                "clientId": "WebsiteConsumer", "api-host": "PromotionHost",
                "channel": "WEB", "Accept-Language": "ar", "msisdn": number,
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/133.0.0.0 Mobile Safari/537.36",
                "Referer": "https://web.vodafone.com.eg/ar/ramadan",
            },
            timeout=15, verify=False
        )
        data = r.json()
    except:
        return []
    cards = []
    if not isinstance(data, list):
        return cards
    for item in data:
        if not isinstance(item, dict) or "pattern" not in item:
            continue
        for pat in item["pattern"]:
            for act in pat.get("action", []):
                c = {ch["name"]: str(ch["value"]) for ch in act.get("characteristics", [])}
                serial = c.get("CARD_SERIAL", "").strip()
                if len(serial) != 13:
                    continue
                cards.append({
                    "serial":    serial,
                    "gift":      int(c.get("GIFT_UNITS", 0)),
                    "amount":    int(c.get("amount", 0)),
                    "remaining": int(c.get("REMAINING_DEDICATIONS", 0)),
                })
    cards.sort(key=lambda x: -x["amount"])
    return cards

def api_redeem(token, number, serial):
    try:
        r = req.post(
            "https://web.vodafone.com.eg/services/dxl/ramadanpromo/promotion",
            json={
                "@type": "Promo", "channel": {"id": "1"},
                "context": {"type": "RamadanRedeemFromHub"},
                "pattern": [{"characteristics": [{"name": "cardSerial", "value": serial}]}],
            },
            headers={
                "Authorization": f"Bearer {token}", "Content-Type": "application/json",
                "Accept": "application/json", "clientId": "WebsiteConsumer",
                "channel": "WEB", "msisdn": number, "Accept-Language": "AR",
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/133.0.0.0 Mobile Safari/537.36",
                "Origin": "https://web.vodafone.com.eg",
                "Referer": "https://web.vodafone.com.eg/portal/hub",
            },
            timeout=15, verify=False
        )
        return r.status_code
    except:
        return 0

def do_refresh():
    if time.time() < session.get("token_exp", 0):
        return True
    res = api_login(session.get("number", ""), session.get("password", ""))
    if "access_token" in res:
        session["token"]     = res["access_token"]
        session["token_exp"] = time.time() + int(res.get("expires_in", 3600)) - 120
        return True
    return False

# ══════════════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════════════
@app.route("/")
def index():
    return render_template_string(PAGE)

@app.route("/check")
def check():
    if session.get("logged_in"):
        sid = session.get("sid", "")
        if sid:
            update_online(sid)
        return jsonify({"logged": True, "number": session.get("number", "")})
    return jsonify({"logged": False})

@app.route("/login", methods=["POST"])
def login():
    number   = request.form.get("number", "").strip()
    password = request.form.get("password", "").strip()
    if not number or not password:
        return jsonify({"ok": False, "error": "من فضلك ادخل الرقم والباسورد"})
    res = api_login(number, password)
    if "access_token" in res:
        sid = str(uuid.uuid4())
        session.clear()
        session["logged_in"]  = True
        session["token"]      = res["access_token"]
        session["token_exp"]  = time.time() + int(res.get("expires_in", 3600)) - 120
        session["number"]     = number
        session["password"]   = password
        session["sid"]        = sid
        update_online(sid)
        return jsonify({"ok": True, "number": number})
    return jsonify({"ok": False, "error": "الرقم أو الباسورد غلط، حاول تاني"})

@app.route("/ping")
def ping():
    sid = session.get("sid", "")
    if sid:
        update_online(sid)
    return jsonify({"ok": True, "online": get_online_count()})

@app.route("/fetch")
def fetch():
    if not session.get("logged_in"):
        return jsonify({"ok": False})
    sid = session.get("sid", "")
    if sid:
        update_online(sid)
    do_refresh()
    return jsonify({
        "ok":     True,
        "promos": api_promos(session["token"], session["number"]),
        "online": get_online_count(),
    })

@app.route("/redeem")
def redeem():
    if not session.get("logged_in"):
        return jsonify({"ok": False})
    do_refresh()
    serial = request.args.get("serial", "").strip()
    amount = request.args.get("amount", "?")
    code   = api_redeem(session["token"], session["number"], serial)
    if code == 200:
        record_charge(session["number"], serial, amount)
    return jsonify({"ok": code == 200, "code": code})

@app.route("/logout")
def logout():
    sid = session.get("sid", "")
    if sid:
        with online_lock:
            online_users.pop(sid, None)
    session.clear()
    return jsonify({"ok": True})

# ══════════════════════════════════════════════════════
#  HTML
# ══════════════════════════════════════════════════════
PAGE = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"/>
<title>كروت رمضان — TALASHNY</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=Cairo:wght@400;500;600;700;900&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet"/>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"/>
<style>
:root{
  --red:#e60000;--red2:#9a0000;--red3:#ff2020;--red-glow:rgba(230,0,0,.25);
  --g1:#c8a84b;--g2:#f5d070;--g3:#8a6820;--g4:rgba(200,168,75,.12);
  --bg:#07070a;--l1:#0d0d12;--l2:#121217;--l3:#18181f;--l4:#1f1f28;--l5:#26262f;
  --ink:#eeeae0;--ink2:#a09880;--ink3:#504e48;
  --stroke:rgba(200,168,75,.1);--stroke2:rgba(200,168,75,.22);
  --green:#00c853;
  --r:20px;--r-sm:13px;--r-xs:9px;
  --spring:cubic-bezier(.34,1.56,.64,1);--ease:cubic-bezier(.4,0,.2,1);
}
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{width:100%;height:100%;overflow:hidden}
body{
  font-family:'Cairo',sans-serif;background:var(--bg);color:var(--ink);
  background-image:
    radial-gradient(ellipse 70% 35% at 50% 0%,rgba(200,168,75,.13) 0%,rgba(200,168,75,.04) 40%,transparent 70%),
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='300' height='300' filter='url(%23n)' opacity='0.025'/%3E%3C/svg%3E");
}
@keyframes up{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:none}}
@keyframes fadeUp{to{opacity:1;transform:translateY(0)}}
@keyframes rotate{to{transform:rotate(360deg)}}
@keyframes shine{0%,100%{left:-100%}50%{left:150%}}

/* ══ SCREENS ══ */
.screen{
  position:fixed;inset:0;display:flex;flex-direction:column;
  align-items:center;justify-content:center;
  background:var(--bg);opacity:0;pointer-events:none;
  z-index:10;overflow:hidden;transition:opacity .35s ease;
}
.screen.active{opacity:1;pointer-events:all;z-index:20;}

/* ════════ SPLASH ════════ */
#s-splash{background:#07070a;z-index:50;}
#s-splash.active{z-index:50;}

.crescent-box{
  position:relative;width:220px;height:220px;
  display:flex;align-items:center;justify-content:center;
  opacity:0;transform:scale(1.3);
  animation:crescIn 1.6s cubic-bezier(.34,1.15,.64,1) .3s forwards;
}
@keyframes crescIn{to{opacity:1;transform:scale(1)}}
.crescent-box svg{position:absolute;inset:0;width:100%;height:100%;overflow:visible;}
.vf-logo{
  position:relative;z-index:5;width:110px;
  opacity:0;transform:scale(.1);
  animation:logoIn 1.1s cubic-bezier(.34,1.5,.64,1) 1.8s forwards;
  filter:drop-shadow(0 2px 14px rgba(255,255,255,.18));
}
@keyframes logoIn{to{opacity:1;transform:scale(1)}}
.sp-title{
  margin-top:18px;font-size:clamp(1.9rem,8vw,2.6rem);
  font-family:'Playfair Display',serif;font-weight:900;color:var(--g2);letter-spacing:2px;
  opacity:0;transform:translateY(14px);
  animation:fadeUp .7s ease 2.5s forwards;
  text-shadow:0 0 28px rgba(232,199,111,.4);
}
.sp-sub{
  margin-top:6px;font-size:.75rem;color:rgba(200,168,75,.5);letter-spacing:1px;
  opacity:0;animation:fadeUp .6s ease 3s forwards;
}
.sp-bar{
  width:88px;height:2px;border-radius:2px;
  background:rgba(200,168,75,.1);margin-top:24px;overflow:hidden;
  opacity:0;animation:fadeUp .4s ease 3.2s forwards;
}
.sp-fill{height:100%;background:var(--g1);width:0;animation:fillBar 2.2s ease 3.4s forwards;}
@keyframes fillBar{to{width:100%}}

/* ════════ LOGIN ════════ */
#s-login{
  background:
    radial-gradient(ellipse 70% 40% at 50% 0%,rgba(230,0,0,.09),transparent 65%),
    var(--bg);
  padding:24px 18px;overflow-y:auto;justify-content:flex-start;padding-top:70px;
}
.login-wrap{width:100%;max-width:390px;display:flex;flex-direction:column;gap:14px;}

.login-brand{display:flex;flex-direction:column;align-items:center;gap:8px;margin-bottom:4px;}
.login-logo{
  width:54px;height:54px;border-radius:50%;
  background:linear-gradient(135deg,var(--l3),var(--l5));
  border:1px solid var(--stroke2);
  display:flex;align-items:center;justify-content:center;
  box-shadow:0 0 24px rgba(200,168,75,.15),0 4px 12px rgba(0,0,0,.5);
}
.login-logo img{width:28px;}
.login-eyebrow{font-size:.55rem;font-weight:700;letter-spacing:4px;text-transform:uppercase;color:var(--ink3);}
.login-title{font-family:'Playfair Display',serif;font-size:1.25rem;font-weight:700;color:var(--ink);text-align:center;}
.login-title em{font-style:italic;color:transparent;background:linear-gradient(135deg,var(--g1),var(--g2),var(--g1));-webkit-background-clip:text;-webkit-text-fill-color:transparent;}

.surface{background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r);}
.lf-row{display:flex;align-items:stretch;border-bottom:1px solid var(--stroke);position:relative;}
.lf-row:last-of-type{border-bottom:none;}
.lf-row:focus-within{background:rgba(200,168,75,.025);}
.lf-icon{width:48px;flex-shrink:0;display:flex;align-items:center;justify-content:center;border-left:1px solid var(--stroke);background:var(--l2);}
.lf-icon i{font-size:.75rem;color:var(--ink3);transition:color .3s;}
.lf-row:focus-within .lf-icon i{color:var(--g1);}
.lf-body{flex:1;padding:12px 14px;display:flex;flex-direction:column;}
.lf-lbl{font-size:.5rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);margin-bottom:3px;transition:color .3s;}
.lf-row:focus-within .lf-lbl{color:var(--g1);}
.lf-input{background:transparent;border:none;outline:none;font-family:'Cairo',sans-serif;font-size:.93rem;font-weight:600;color:var(--ink);width:100%;}
.lf-input::placeholder{color:var(--ink3);font-weight:400;font-size:.8rem;}
.lf-row::after{content:'';position:absolute;right:0;top:0;bottom:0;width:0;background:var(--g1);transition:width .25s;}
.lf-row:focus-within::after{width:3px;}

.err-box{
  display:flex;align-items:center;gap:9px;
  background:rgba(230,0,0,.06);border:1px solid rgba(230,0,0,.2);
  border-radius:var(--r-xs);padding:11px 14px;
  font-size:.7rem;color:#ff8a80;font-weight:600;
  animation:shake .3s ease;
}
@keyframes shake{0%,100%{transform:translateX(0)}25%{transform:translateX(-5px)}75%{transform:translateX(5px)}}
.err-box i{font-size:.75rem;color:#ff6b6b;flex-shrink:0;}

.btn-wrap{padding:14px;}
.btn-login{
  width:100%;padding:14px;border:none;border-radius:var(--r-sm);
  background:linear-gradient(135deg,var(--g3),var(--g1),var(--g2));
  color:#1a0e00;font-family:'Cairo',sans-serif;font-size:.88rem;font-weight:900;
  cursor:pointer;display:flex;align-items:center;justify-content:center;gap:9px;
  box-shadow:0 5px 22px rgba(200,168,75,.28),0 2px 8px rgba(0,0,0,.4);
  transition:transform .2s var(--spring),box-shadow .25s;position:relative;overflow:hidden;
}
.btn-login::before{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(255,255,255,.15) 0%,transparent 55%);}
.btn-login::after{content:'';position:absolute;top:0;left:-100%;width:60%;height:100%;background:linear-gradient(105deg,transparent,rgba(255,255,255,.18),transparent);animation:shine 3.5s ease-in-out infinite;}
.btn-login:hover{transform:translateY(-2px);box-shadow:0 9px 30px rgba(200,168,75,.4);}
.btn-login:active{transform:scale(.97);}
.btn-login:disabled{opacity:.5;cursor:wait;}
.btn-login i,.btn-login span{position:relative;z-index:1;}
.login-note{text-align:center;font-size:.6rem;color:var(--ink3);display:flex;align-items:center;justify-content:center;gap:5px;}
.login-note i{font-size:.55rem;color:rgba(0,200,90,.45);}

/* ════════ APP ════════ */
#s-app{
  justify-content:flex-start;align-items:stretch;
  overflow-y:auto;overflow-x:hidden;-webkit-overflow-scrolling:touch;
}

/* ── BANNER با curve من تحت ── */
.banner{
  position:sticky;top:0;z-index:100;
  background:rgba(0,0,0,.97);
  border-bottom:1px solid var(--stroke);
  box-shadow:0 4px 30px rgba(0,0,0,.8);
  flex-shrink:0;
}
/* الـ SVG curve من تحت البنر */
.banner-curve{
  display:block;width:100%;height:18px;margin-top:-1px;
  background:transparent;
}
.banner-inner{
  display:flex;align-items:center;justify-content:space-between;
  padding:0 16px;height:72px;
}
.banner-left{display:flex;flex-direction:column;gap:2px;}
.banner-letters{
  display:flex;gap:0;font-size:2rem;font-weight:900;letter-spacing:6px;text-transform:uppercase;
  font-family:'Playfair Display',serif;
}
.banner-letters span{
  display:inline-block;color:transparent;
  background:linear-gradient(90deg,#b0b0b0 0%,#fff 20%,#e0e0e0 40%,#fff 60%,#a0a0a0 80%,#c0c0c0 100%);
  background-size:400% 100%;-webkit-background-clip:text;-webkit-text-fill-color:transparent;
  animation:chrome 4s linear infinite;animation-delay:calc(var(--i)*.18s);
}
@keyframes chrome{0%{background-position:400% center}100%{background-position:-400% center}}
.banner-sub{font-size:.48rem;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:var(--ink3);}
.banner-right{display:flex;flex-direction:column;align-items:flex-end;gap:3px;}
.banner-num{font-family:'JetBrains Mono',monospace;font-size:.78rem;font-weight:700;color:var(--g2);}
.banner-live{
  display:flex;align-items:center;gap:4px;
  font-size:.49rem;font-weight:700;color:var(--green);
}
.live-dot{width:5px;height:5px;border-radius:50%;background:var(--green);animation:livePulse 2s infinite;}
@keyframes livePulse{0%,100%{box-shadow:0 0 0 0 rgba(0,200,83,.5)}70%{box-shadow:0 0 0 5px rgba(0,200,83,0)}}

.appwrap{
  width:100%;max-width:430px;margin:0 auto;
  padding:12px 11px 90px;
}

/* user pill */
.user-pill{
  display:flex;align-items:center;justify-content:flex-end;
  margin-bottom:12px;
}
.btn-logout{
  display:flex;align-items:center;gap:5px;
  background:transparent;border:1px solid rgba(230,0,0,.18);
  border-radius:var(--r-xs);padding:6px 13px;
  font-family:'Cairo',sans-serif;font-size:.65rem;font-weight:700;
  color:rgba(230,0,0,.5);cursor:pointer;transition:all .2s;
}
.btn-logout:hover{color:#ff6b6b;border-color:rgba(230,0,0,.4);background:rgba(230,0,0,.05);}
.btn-logout i{font-size:.6rem;}

/* stats bar */
.stats-bar{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:12px;}
.stat{
  background:var(--l1);border:1px solid var(--stroke);
  border-radius:var(--r);padding:12px 8px;text-align:center;
  position:relative;overflow:hidden;
}
.stat::before{content:'';position:absolute;top:0;left:0;right:0;height:2.5px;}
.stat.s-red::before{background:var(--red);}
.stat.s-gold::before{background:var(--g1);}
.stat.s-green::before{background:var(--green);}
.stat-val{font-family:'Playfair Display',serif;font-size:1.2rem;font-weight:700;line-height:1;display:flex;align-items:center;justify-content:center;gap:3px;}
.stat.s-red .stat-val{color:var(--red);}
.stat.s-gold .stat-val{color:var(--g2);}
.stat.s-green .stat-val{color:var(--green);}
.stat-lbl{font-size:.49rem;font-weight:700;color:var(--ink3);letter-spacing:.5px;margin-top:4px;}

/* timer */
.timer-row{
  display:flex;align-items:center;gap:11px;
  background:var(--l1);border:1px solid var(--stroke);
  border-radius:var(--r-sm);padding:10px 14px;margin-bottom:12px;
}
.t-ring{width:36px;height:36px;flex-shrink:0;position:relative;}
.t-ring svg{width:36px;height:36px;transform:rotate(-90deg);}
.t-bg{fill:none;stroke:rgba(255,255,255,.05);stroke-width:3;}
.t-prog{
  fill:none;stroke:var(--red);stroke-width:3;stroke-linecap:round;
  stroke-dasharray:100;stroke-dashoffset:0;
  transition:stroke-dashoffset .9s linear,stroke .3s;
  filter:drop-shadow(0 0 3px rgba(230,0,0,.6));
}
.t-count{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:.63rem;font-weight:900;}
.t-info{flex:1;}
.t-label{font-size:.7rem;font-weight:700;color:var(--ink2);}
.t-sub{font-size:.52rem;color:var(--ink3);margin-top:1px;}

/* users badge في الـ timer */
.users-badge{
  display:flex;align-items:center;gap:5px;
  background:rgba(200,168,75,.07);border:1px solid rgba(200,168,75,.18);
  border-radius:20px;padding:5px 11px;
}
.ub-dot{width:5px;height:5px;border-radius:50%;background:var(--g2);box-shadow:0 0 4px var(--g2);animation:uPulse 2s ease-in-out infinite;}
@keyframes uPulse{0%,100%{opacity:1}50%{opacity:.35}}
.ub-count{font-family:'JetBrains Mono',monospace;font-size:.68rem;font-weight:700;color:var(--g2);}
.ub-lbl{font-size:.5rem;font-weight:700;color:var(--ink3);}

/* section header */
.sec-row{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;}
.sec-title{font-size:.57rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);display:flex;align-items:center;gap:7px;}
.sec-line{width:13px;height:2px;border-radius:2px;background:var(--red);}
.sec-badge{
  font-size:.57rem;font-weight:700;color:var(--ink3);
  background:var(--l2);border:1px solid var(--stroke);
  padding:3px 10px;border-radius:100px;
}

/* ═══ PROMO CARDS ═══ */
.promo-card{
  background:var(--l1);border:1px solid var(--stroke);
  border-radius:var(--r);margin-bottom:9px;overflow:hidden;
  animation:cardIn .35s cubic-bezier(.34,1.3,.64,1) both;
  animation-delay:calc(var(--i,0)*.06s);
  transition:border-color .2s,transform .18s;
  position:relative;
}
.promo-card:hover{border-color:rgba(230,0,0,.2);transform:translateY(-1px);}
@keyframes cardIn{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
/* خط أحمر علوي */
.card-stripe{height:3px;background:linear-gradient(90deg,var(--red),rgba(230,0,0,.2),transparent);}
/* الـ best card تاخد خط ذهبي */
.promo-card.best .card-stripe{background:linear-gradient(90deg,var(--g3),var(--g1),var(--g2),var(--g3),transparent);}
.promo-card.best{border-color:rgba(200,168,75,.3);box-shadow:0 0 18px rgba(200,168,75,.08);}

.best-badge{
  position:absolute;top:12px;left:12px;z-index:5;
  font-size:.5rem;font-weight:900;letter-spacing:1.5px;text-transform:uppercase;
  padding:3px 9px;border-radius:4px;color:#1a0e00;
  background:linear-gradient(135deg,var(--g2),var(--g1));
  box-shadow:0 2px 10px rgba(200,168,75,.35);
}

.card-body{display:flex;align-items:stretch;padding:13px 13px 0;}
.card-main{flex:1;}
.card-chips{display:flex;gap:5px;flex-wrap:wrap;}
.chip{
  display:inline-flex;align-items:center;gap:3px;
  padding:4px 9px;border-radius:100px;font-size:.56rem;font-weight:700;
}
.chip-gold{background:rgba(200,168,75,.07);color:var(--g2);border:1px solid rgba(200,168,75,.14);}
.chip-blue{background:rgba(79,195,247,.06);color:#80ccee;border:1px solid rgba(79,195,247,.11);}
.chip i{font-size:.47rem;}

.card-amount{
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  min-width:64px;padding-right:13px;
  border-right:1px solid var(--stroke);margin-right:0;
}
.amt-num{font-family:'Playfair Display',serif;font-size:2rem;font-weight:700;color:var(--ink);line-height:1;}
.amt-cur{font-size:.49rem;font-weight:700;color:var(--ink3);letter-spacing:1px;margin-top:2px;}

.card-serial{
  display:flex;align-items:center;justify-content:space-between;
  background:rgba(0,0,0,.2);margin:11px 0 0;padding:9px 13px;
  border-top:1px solid var(--stroke);gap:8px;
}
.serial-val{
  font-family:'JetBrains Mono',monospace;font-size:.86rem;letter-spacing:2px;
  color:var(--ink);font-weight:600;flex:1;text-align:right;
}
.btn-copy{
  width:28px;height:28px;border-radius:8px;
  background:rgba(200,168,75,.04);border:1px solid rgba(200,168,75,.12);
  display:flex;align-items:center;justify-content:center;
  cursor:pointer;color:var(--ink3);transition:all .2s;flex-shrink:0;
}
.btn-copy:hover{background:rgba(200,168,75,.12);border-color:rgba(200,168,75,.3);color:var(--g1);}
.btn-copy:active{transform:scale(.8);}
.btn-copy i{font-size:.58rem;}

.card-btns{display:flex;gap:7px;padding:9px;}
.btn-charge{
  flex:1;display:flex;align-items:center;justify-content:center;gap:5px;
  padding:10px 6px;border:none;border-radius:var(--r-sm);
  background:var(--red);color:#fff;
  font-family:'Cairo',sans-serif;font-size:.7rem;font-weight:800;
  cursor:pointer;position:relative;overflow:hidden;
  box-shadow:0 3px 12px rgba(230,0,0,.24);transition:all .2s;
}
.btn-charge::before{content:'';position:absolute;top:0;left:0;right:0;height:50%;background:rgba(255,255,255,.06);}
.btn-charge:hover{background:var(--red3);transform:translateY(-1px);box-shadow:0 5px 18px rgba(230,0,0,.34);}
.btn-charge:active{transform:scale(.95);}
.btn-charge.done{background:#00a040;box-shadow:0 3px 12px rgba(0,160,64,.25);}
.btn-charge.loading{opacity:.55;pointer-events:none;}
.btn-charge span,.btn-charge i{position:relative;z-index:1;}

.btn-dial{
  flex:1;display:flex;align-items:center;justify-content:center;gap:5px;
  padding:10px 6px;border-radius:var(--r-sm);
  background:var(--l2);border:1px solid var(--stroke);
  color:var(--ink2);font-family:'Cairo',sans-serif;font-size:.7rem;font-weight:800;
  cursor:pointer;text-decoration:none;transition:all .2s;
}
.btn-dial:hover{background:var(--l3);color:var(--ink);}
.btn-dial:active{transform:scale(.95);}

/* empty / loading */
.empty{
  text-align:center;padding:46px 20px;
  background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r);
}
.empty i{font-size:2rem;color:var(--ink3);display:block;margin-bottom:10px;}
.empty p{font-size:.8rem;color:var(--ink2);}
.empty small{font-size:.6rem;color:var(--ink3);display:block;margin-top:4px;}

/* bottom nav */
.botnav{
  position:fixed;bottom:0;left:0;right:0;height:60px;
  background:rgba(7,7,10,.97);backdrop-filter:blur(28px);
  border-top:1px solid var(--stroke);
  display:flex;justify-content:space-around;align-items:stretch;z-index:400;
}
.nav-link{
  flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;
  gap:3px;text-decoration:none;color:var(--ink3);
  font-size:.49rem;font-weight:700;letter-spacing:.5px;
  border-top:2px solid transparent;transition:color .2s,border-color .2s;
}
.nav-link:hover{color:var(--g1);border-color:var(--g1);}
.nav-link i{font-size:1.05rem;}

/* toast */
.toast{
  position:fixed;bottom:70px;left:50%;
  transform:translateX(-50%) translateY(12px);opacity:0;
  background:rgba(10,10,15,.97);border:1px solid var(--stroke);
  border-radius:30px;padding:10px 22px;
  font-family:'Cairo',sans-serif;font-size:.75rem;font-weight:700;color:var(--ink);
  pointer-events:none;z-index:9998;white-space:nowrap;backdrop-filter:blur(20px);
  box-shadow:0 8px 28px rgba(0,0,0,.6);
  transition:all .3s var(--spring);
}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0);}
.toast.ok{border-color:rgba(0,200,90,.3);color:#4cff9a;}
.toast.err{border-color:rgba(230,0,0,.3);color:#ff8a80;}

::-webkit-scrollbar{width:3px;}
::-webkit-scrollbar-track{background:var(--bg);}
::-webkit-scrollbar-thumb{background:rgba(200,168,75,.25);border-radius:3px;}
</style>
</head>
<body>

<!-- ══ SPLASH ══ -->
<div id="s-splash" class="screen active">
  <div class="crescent-box">
    <svg viewBox="0 0 240 240" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="mg" cx="35%" cy="28%" r="70%">
          <stop offset="0%"   stop-color="#fff9d6"/>
          <stop offset="40%"  stop-color="#e8c76f"/>
          <stop offset="80%"  stop-color="#b8922a"/>
          <stop offset="100%" stop-color="#7a5a10"/>
        </radialGradient>
        <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="5" result="b"/>
          <feColorMatrix in="b" type="matrix"
            values="1 0.7 0 0 0  0.7 0.5 0 0 0  0 0 0 0 0  0 0 0 0.6 0" result="c"/>
          <feMerge><feMergeNode in="c"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>
      <path
        d="M120 32 A95 95 0 1 1 120 208 A72 72 0 1 0 120 32 Z"
        fill="url(#mg)" filter="url(#glow)"
        stroke="rgba(255,235,120,.3)" stroke-width="1.5"/>
      <polygon
        points="183,48 185.8,56.5 194.5,56.5 187.8,61.5 190.5,70 183,65 175.5,70 178.2,61.5 171.5,56.5 180.2,56.5"
        fill="#fff9d6" filter="url(#glow)"/>
      <polygon
        points="202,26 203.4,30.5 208,30.5 204.3,33.2 205.7,37.7 202,35 198.3,37.7 199.7,33.2 196,30.5 200.6,30.5"
        fill="rgba(255,240,150,.6)"/>
    </svg>
    <img src="https://tlashane.serv00.net/vo/vodafone2.png" class="vf-logo" alt=""/>
  </div>
  <div class="sp-title">كروت رمضان</div>
  <div class="sp-sub">عروض الشهر الكريم &nbsp;•&nbsp; اشحن واستمتع</div>
  <div class="sp-bar"><div class="sp-fill"></div></div>
</div>

<!-- ══ LOGIN ══ -->
<div id="s-login" class="screen">
  <div class="login-wrap">
    <div class="login-brand">
      <div class="login-logo">
        <img src="https://tlashane.serv00.net/vo/vodafone2.png" alt=""/>
      </div>
      <div class="login-eyebrow">Premium Access</div>
      <div class="login-title">أهلاً في <em>TALASHNY</em></div>
    </div>

    <div id="errBox" class="err-box" style="display:none">
      <i class="fas fa-circle-exclamation"></i>
      <span id="errMsg"></span>
    </div>

    <div class="surface">
      <div class="lf-row">
        <div class="lf-icon"><i class="fas fa-mobile-screen-button"></i></div>
        <div class="lf-body">
          <span class="lf-lbl">رقم الموبايل</span>
          <input class="lf-input" type="tel" id="inpNum" placeholder="01XXXXXXXXX" inputmode="tel" autocomplete="tel" required/>
        </div>
      </div>
      <div class="lf-row">
        <div class="lf-icon"><i class="fas fa-lock"></i></div>
        <div class="lf-body">
          <span class="lf-lbl">الباسورد</span>
          <input class="lf-input" type="password" id="inpPw" placeholder="••••••••" autocomplete="current-password" required/>
        </div>
      </div>
      <div class="btn-wrap">
        <button class="btn-login" id="loginBtn" onclick="doLogin()">
          <i class="fas fa-right-to-bracket"></i>
          <span>دخـول</span>
        </button>
      </div>
    </div>

    <div class="login-note">
      <i class="fas fa-shield-halved"></i>
      بياناتك محمية ومش بتتحفظ على السيرفر
    </div>
  </div>
</div>

<!-- ══ APP ══ -->
<div id="s-app" class="screen">

  <!-- BANNER مع curve من تحت -->
  <div class="banner">
    <div class="banner-inner">
      <div class="banner-left">
        <div class="banner-letters">
          <span style="--i:0">Y</span><span style="--i:1">N</span><span style="--i:2">H</span>
          <span style="--i:3">S</span><span style="--i:4">A</span><span style="--i:5">L</span>
          <span style="--i:6">A</span><span style="--i:7">T</span>
        </div>
        <div class="banner-sub">Vodafone Cards</div>
      </div>
      <div class="banner-right">
        <div class="banner-num" id="topNum">—</div>
        <div class="banner-live"><div class="live-dot"></div>متصل</div>
      </div>
    </div>
    <!-- curve من تحت البنر -->
    <svg class="banner-curve" viewBox="0 0 390 18" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M0,0 C80,18 310,18 390,0 L390,18 L0,18 Z" fill="#07070a"/>
    </svg>
  </div>

  <div class="appwrap">
    <div class="user-pill">
      <button class="btn-logout" id="logoutBtn">
        <i class="fas fa-power-off"></i>&nbsp;خروج
      </button>
    </div>

    <!-- STATS -->
    <div class="stats-bar">
      <div class="stat s-red">
        <div class="stat-val" id="st-total">—</div>
        <div class="stat-lbl">كروت</div>
      </div>
      <div class="stat s-gold">
        <div class="stat-val" id="st-max">—</div>
        <div class="stat-lbl">أعلى فئة</div>
      </div>
      <div class="stat s-green">
        <div class="stat-val"><i class="fas fa-circle" style="font-size:.45rem"></i><span id="st-online">—</span></div>
        <div class="stat-lbl">متصل الآن</div>
      </div>
    </div>

    <!-- TIMER + USERS BADGE -->
    <div class="timer-row">
      <div class="t-ring">
        <svg viewBox="0 0 40 40">
          <circle class="t-bg"   cx="20" cy="20" r="16"/>
          <circle class="t-prog" id="tprog" cx="20" cy="20" r="16"/>
        </svg>
        <div class="t-count" id="tnum">15</div>
      </div>
      <div class="t-info">
        <div class="t-label">تحديث تلقائي</div>
        <div class="t-sub">كل 15 ثانية</div>
      </div>
      <!-- عداد المتصلين في نص الـ timer -->
      <div class="users-badge">
        <div class="ub-dot"></div>
        <span class="ub-count" id="UC">—</span>
        <span class="ub-lbl">متصل</span>
      </div>
    </div>

    <!-- CARDS SECTION -->
    <div class="sec-row">
      <div class="sec-title"><div class="sec-line"></div>الكروت المتاحة</div>
      <div class="sec-badge" id="ccnt">—</div>
    </div>

    <div id="cardsWrap">
      <div class="empty">
        <i class="fas fa-spinner fa-spin" style="color:var(--red);opacity:.8"></i>
        <p>جاري التحميل...</p>
      </div>
    </div>
  </div>

  <nav class="botnav">
    <a href="https://t.me/FY_TF" target="_blank" class="nav-link">
      <i class="fab fa-telegram-plane"></i><span>تيليجرام</span>
    </a>
    <a href="https://wa.me/message/U6AIKBGFCNCQK1" target="_blank" class="nav-link">
      <i class="fab fa-whatsapp"></i><span>واتساب</span>
    </a>
    <a href="https://www.facebook.com/VI808IV" target="_blank" class="nav-link">
      <i class="fab fa-facebook-f"></i><span>فيسبوك</span>
    </a>
  </nav>
</div>

<div class="toast" id="toastEl"></div>

<script>
const _=id=>document.getElementById(id);
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function showToast(msg,t=''){
  const el=_('toastEl');el.textContent=msg;el.className='toast show'+(t?' '+t:'');
  clearTimeout(el._t);el._t=setTimeout(()=>el.classList.remove('show'),2800);
}
function goTo(id){
  document.querySelectorAll('.screen').forEach(s=>s.classList.remove('active'));
  _(id).classList.add('active');
  if(id==='s-app')_(id).scrollTop=0;
}
let timerInt=null,pingInt=null;
function startPing(){
  fetch('/ping').then(r=>r.json()).then(d=>{updateOnline(d.online);});
  clearInterval(pingInt);
  pingInt=setInterval(()=>fetch('/ping').then(r=>r.json()).then(d=>updateOnline(d.online)),15000);
}
function stopPing(){clearInterval(pingInt);}
function updateOnline(n){
  if(n===undefined)return;
  [_('st-online'),_('UC')].forEach(el=>{if(el)el.textContent=n;});
}

/* BOOT */
(async()=>{
  try{
    const r=await fetch('/check');const d=await r.json();
    if(d.logged){
      _('s-splash').classList.remove('active');
      _('topNum').textContent=d.number;
      goTo('s-app');startPing();startCycle();return;
    }
  }catch{}
  setTimeout(()=>{
    const sp=_('s-splash');
    sp.style.transition='opacity .8s ease';sp.style.opacity='0';
    setTimeout(()=>{sp.classList.remove('active');goTo('s-login');},800);
  },5400);
})();

/* LOGIN */
async function doLogin(){
  const num=_('inpNum').value.trim(),pw=_('inpPw').value.trim();
  if(!num||!pw)return;
  const btn=_('loginBtn');
  btn.disabled=true;btn.innerHTML='<i class="fas fa-spinner fa-spin"></i>&nbsp;<span>جاري التحقق...</span>';
  _('errBox').style.display='none';
  try{
    const fd=new FormData();fd.append('number',num);fd.append('password',pw);
    const r=await fetch('/login',{method:'POST',body:fd});const d=await r.json();
    if(d.ok){_('topNum').textContent=d.number;goTo('s-app');startPing();startCycle();}
    else{_('errMsg').textContent=d.error||'الرقم أو الباسورد غلط';_('errBox').style.display='flex';}
  }catch{_('errMsg').textContent='خطأ في الاتصال';_('errBox').style.display='flex';}
  btn.disabled=false;btn.innerHTML='<i class="fas fa-right-to-bracket"></i>&nbsp;<span>دخـول</span>';
}
_('inpPw')?.addEventListener('keydown',e=>{if(e.key==='Enter')doLogin();});
_('inpNum')?.addEventListener('keydown',e=>{if(e.key==='Enter')_('inpPw').focus();});

/* LOGOUT */
_('logoutBtn').onclick=async()=>{
  await fetch('/logout');clearInterval(timerInt);stopPing();goTo('s-login');
};

/* COPY */
function copySerial(btn){
  const s=btn.closest('.card-serial').querySelector('.serial-val').textContent.trim();
  const ok=()=>{
    const o=btn.innerHTML;btn.innerHTML='<i class="fas fa-check" style="color:var(--green)"></i>';
    setTimeout(()=>btn.innerHTML=o,1500);showToast('✅ تم نسخ الكود','ok');
  };
  if(navigator.clipboard)navigator.clipboard.writeText(s).then(ok).catch(fb);else fb();
  function fb(){const t=document.createElement('textarea');t.value=s;t.style.cssText='position:fixed;opacity:0';document.body.appendChild(t);t.select();try{document.execCommand('copy')}catch{}document.body.removeChild(t);ok();}
}

/* CHARGE */
async function chargeCard(serial,amount,btn){
  btn.classList.add('loading');btn.innerHTML='<i class="fas fa-spinner fa-spin"></i>&nbsp;<span>جاري...</span>';
  try{
    const r=await fetch('/redeem?serial='+encodeURIComponent(serial)+'&amount='+encodeURIComponent(amount));
    const d=await r.json();
    if(d.ok){
      showToast('✅ تم الشحن بنجاح','ok');
      btn.classList.remove('loading');btn.classList.add('done');
      btn.innerHTML='<i class="fas fa-check"></i>&nbsp;<span>تم الشحن</span>';
    }else{
      showToast('❌ فشل الشحن','err');
      btn.classList.remove('loading');btn.innerHTML='<i class="fas fa-bolt"></i>&nbsp;<span>شحن أونلاين</span>';
    }
  }catch{
    showToast('❌ خطأ في الاتصال','err');
    btn.classList.remove('loading');btn.innerHTML='<i class="fas fa-bolt"></i>&nbsp;<span>شحن أونلاين</span>';
  }
}

/* RENDER */
function renderCards(list,online){
  const wrap=_('cardsWrap'),cnt=_('ccnt');
  updateOnline(online);
  if(!list||!list.length){
    cnt.textContent='0';_('st-total').textContent='0';_('st-max').textContent='—';
    wrap.innerHTML='<div class="empty"><i class="fas fa-inbox"></i><p>لا توجد عروض متاحة الآن</p><small>يتجدد البحث تلقائياً...</small></div>';
    return;
  }
  cnt.textContent=list.length+' كرت';
  _('st-total').textContent=list.length;
  _('st-max').textContent=Math.max(...list.map(c=>c.amount))+' ج';
  const best=list[0];
  wrap.innerHTML=list.map((p,i)=>{
    const isBest=p.serial===best.serial;
    const ussd='*858*'+p.serial.replace(/\s/g,'')+'#';
    return`<div class="promo-card${isBest?' best':''}" style="--i:${i}">
      <div class="card-stripe"></div>
      ${isBest?'<div class="best-badge">✦ أفضل كارت</div>':''}
      <div class="card-body">
        <div class="card-main">
          <div class="card-chips">
            <span class="chip chip-gold"><i class="fas fa-gift"></i>${esc(p.gift)} وحدة</span>
            <span class="chip chip-blue"><i class="fas fa-rotate"></i>${esc(p.remaining)} متبقي</span>
          </div>
        </div>
        <div class="card-amount">
          <div class="amt-num">${esc(p.amount)}</div>
          <div class="amt-cur">جنيه</div>
        </div>
      </div>
      <div class="card-serial">
        <span class="serial-val">${esc(p.serial)}</span>
        <button onclick="copySerial(this)" class="btn-copy"><i class="fas fa-clone"></i></button>
      </div>
      <div class="card-btns">
        <button class="btn-charge" onclick="chargeCard('${esc(p.serial)}','${esc(p.amount)}',this)">
          <i class="fas fa-bolt"></i>&nbsp;<span>شحن أونلاين</span>
        </button>
        <a href="tel:${encodeURIComponent(ussd)}" class="btn-dial">
          <i class="fas fa-phone"></i>&nbsp;<span>شحن بالهاتف</span>
        </a>
      </div>
    </div>`;
  }).join('');
}

/* TIMER */
const CIRC=2*Math.PI*16;
function startTimer(cb){
  let t=15;
  const num=_('tnum'),prog=_('tprog');
  if(!num||!prog)return;
  prog.style.strokeDasharray=CIRC;prog.style.strokeDashoffset=0;
  clearInterval(timerInt);
  timerInt=setInterval(()=>{
    t--;num.textContent=Math.max(t,0);
    prog.style.strokeDashoffset=CIRC*(t/15);
    prog.style.stroke=t<=4?'#ff3333':'var(--red)';
    if(t<=0){clearInterval(timerInt);setTimeout(cb,200);}
  },1000);
}

async function getCards(){
  try{
    const r=await fetch('/fetch?t='+Date.now());const d=await r.json();
    if(d.ok)renderCards(d.promos,d.online);
  }catch{}
}
function startCycle(){getCards();startTimer(()=>startCycle());}
</script>
</body>
</html>"""

if __name__ == "__main__":
    print("\n"+"═"*40)
    print("  TALASHNY  |  http://localhost:5000  ")
    print("═"*40+"\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
