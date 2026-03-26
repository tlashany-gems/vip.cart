#!/usr/bin/env python3
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

# ─── REAL ONLINE TRACKER ───────────────────────────────────────────
# كل مستخدم بيبعت ping كل 20 ثانية، السيرفر بيشيل اللي مبعتش في 35 ثانية
online_users = {}
online_lock  = threading.Lock()
PING_TIMEOUT = 35   # ثوان — لو مبعتش ping اعتبره اوفلاين

def ping_user(uid):
    """تحديث وقت آخر ping للمستخدم"""
    with online_lock:
        online_users[uid] = time.time()

def cleanup_online():
    while True:
        time.sleep(10)
        now = time.time()
        with online_lock:
            dead = [k for k,v in online_users.items() if now - v > PING_TIMEOUT]
            for k in dead:
                del online_users[k]

threading.Thread(target=cleanup_online, daemon=True).start()

def get_online_count():
    with online_lock:
        return len(online_users)
# ──────────────────────────────────────────────────────────────────

PAGE = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"/>
<title>TALASHNY — رمضان القادم</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=Cairo:wght@400;500;600;700;900&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet"/>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"/>
<style>
:root{
  --gold1:#c8a84b;--gold2:#f5d070;--gold3:#8a6820;--gold4:#e8c060;
  --gold-glow:rgba(200,168,75,.35);
  --bg:#06050a;--l1:#0a0908;--l2:#100e08;--l3:#161208;
  --ink:#f0ead8;--ink2:#c8b880;--ink3:#7a6a40;
  --stroke:rgba(200,168,75,.12);--stroke2:rgba(200,168,75,.28);
  --green:#00C853;--r:18px;--r-sm:12px;
}
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{height:100%;-webkit-font-smoothing:antialiased;}
body{font-family:'Cairo',sans-serif;background:var(--bg);color:var(--ink);overflow-x:hidden;touch-action:manipulation;background-image:radial-gradient(ellipse 80% 40% at 50% 0%,rgba(200,168,75,.18) 0%,rgba(200,168,75,.05) 45%,transparent 70%),radial-gradient(ellipse 50% 30% at 80% 100%,rgba(200,168,75,.08) 0%,transparent 60%);min-height:100vh;}
*{-webkit-user-select:none;-moz-user-select:none;user-select:none;}
input,textarea{-webkit-user-select:text;user-select:text;}

/* SPLASH */
#s-splash{position:fixed;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;background:radial-gradient(ellipse 120% 80% at 50% -10%,#1a1200 0%,#0a0800 35%,#06050a 70%);z-index:9999;overflow:hidden;transition:opacity .8s ease;}
#s-splash.fade-out{opacity:0;pointer-events:none;}
.sp-stars{position:absolute;inset:0;overflow:hidden;}
.sp-star{position:absolute;border-radius:50%;background:#fff;animation:starTwinkle var(--dur,3s) ease-in-out var(--delay,0s) infinite;}
@keyframes starTwinkle{0%,100%{opacity:var(--min-op,.1)}50%{opacity:var(--max-op,.8)}}
.sp-moon{position:absolute;top:6%;right:8%;width:60px;height:60px;border-radius:50%;background:linear-gradient(135deg,#f5d070,#c8a84b);box-shadow:0 0 40px rgba(200,168,75,.6);overflow:hidden;animation:moonFloat 4s ease-in-out infinite;}
.sp-moon::before{content:'';position:absolute;top:-5px;right:-5px;width:48px;height:48px;border-radius:50%;background:#0a0800;}
@keyframes moonFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}
.sp-lantern{position:absolute;animation:lanternSway var(--sw,6s) ease-in-out var(--sd,0s) infinite;}
@keyframes lanternSway{0%,100%{transform:rotate(-8deg)}50%{transform:rotate(8deg)}}
.sp-lantern svg{filter:drop-shadow(0 0 12px rgba(200,168,75,.8));}
.sp-arch{position:absolute;top:-30px;left:50%;transform:translateX(-50%);width:280px;height:160px;border-radius:0 0 50% 50%;background:linear-gradient(180deg,rgba(200,168,75,.15) 0%,transparent 100%);border:1px solid rgba(200,168,75,.15);border-top:none;}
.sp-stage{position:relative;z-index:2;display:flex;flex-direction:column;align-items:center;}
.sp-logo-wrap{position:relative;margin-bottom:32px;}
.sp-halo{position:absolute;inset:-28px;border-radius:50%;background:radial-gradient(circle,rgba(200,168,75,.3) 0%,transparent 70%);animation:haloPulse 2.8s ease-in-out infinite;}
@keyframes haloPulse{0%,100%{transform:scale(.9);opacity:.6}50%{transform:scale(1.1);opacity:1}}
.sp-spin-ring{position:absolute;inset:-10px;border-radius:50%;animation:spinRing 5s linear infinite;background:conic-gradient(from 0deg,rgba(200,168,75,0) 0deg,rgba(200,168,75,.9) 60deg,rgba(245,208,112,.7) 120deg,rgba(200,168,75,.9) 180deg,rgba(200,168,75,0) 240deg,rgba(200,168,75,0) 360deg);-webkit-mask:radial-gradient(farthest-side,transparent calc(100% - 2px),black calc(100% - 2px));mask:radial-gradient(farthest-side,transparent calc(100% - 2px),black calc(100% - 2px));}
@keyframes spinRing{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
.sp-icon{position:relative;width:120px;height:120px;border-radius:30px;background:linear-gradient(145deg,#1a1400 0%,#2a2000 30%,#1a1400 100%);border:2px solid rgba(200,168,75,.4);box-shadow:0 0 0 1px rgba(200,168,75,.1),0 20px 60px rgba(0,0,0,.8),0 0 40px rgba(200,168,75,.2);display:flex;align-items:center;justify-content:center;overflow:hidden;animation:iconDrop .9s cubic-bezier(.34,1.45,.64,1) .15s both;}
@keyframes iconDrop{from{opacity:0;transform:scale(.25) rotate(-20deg)}to{opacity:1;transform:scale(1) rotate(0)}}
.sp-icon::before{content:'';position:absolute;top:0;left:0;right:0;height:50%;background:linear-gradient(180deg,rgba(200,168,75,.1) 0%,transparent 100%);border-radius:30px 30px 0 0;}
.sp-icon img{width:78px;height:78px;object-fit:contain;position:relative;z-index:1;filter:drop-shadow(0 4px 16px rgba(200,168,75,.5));}
.sp-bolt{position:absolute;bottom:-10px;right:-10px;width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,#7a5c18,#f0cd60,#b8921e);border:3px solid #06050a;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 18px rgba(200,168,75,.7);animation:boltIn .6s cubic-bezier(.34,1.8,.64,1) 1.1s both;}
@keyframes boltIn{from{opacity:0;transform:scale(0) rotate(-60deg)}to{opacity:1;transform:scale(1) rotate(0)}}
.sp-bolt i{font-size:.65rem;color:#1a0e00;}
.sp-rk-badge{display:inline-flex;align-items:center;gap:6px;background:linear-gradient(135deg,rgba(200,168,75,.1),rgba(200,168,75,.05));border:1px solid rgba(200,168,75,.25);border-radius:100px;padding:5px 14px;font-size:.6rem;font-weight:800;color:var(--gold2);letter-spacing:1px;margin-bottom:14px;animation:textIn .4s ease 1.2s both;}
@keyframes textIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.sp-name{display:flex;align-items:baseline;margin-bottom:6px;animation:textIn .6s ease .75s both;}
.sp-nl{font-family:'Playfair Display',serif;font-size:3.2rem;font-weight:900;line-height:.95;color:transparent;background:linear-gradient(160deg,#a07828 0%,#c8a84b 20%,#f5d070 40%,#e8c060 55%,#f5d070 65%,#c8a84b 80%,#8a6820 100%);background-size:300% 100%;-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:goldFlow 5s linear infinite,nlIn .5s cubic-bezier(.34,1.5,.64,1) both;animation-delay:0s,calc(.75s + var(--n)*.07s);}
@keyframes nlIn{from{opacity:0;transform:translateY(28px) scaleY(.4)}to{opacity:1;transform:none}}
@keyframes goldFlow{0%{background-position:200% center}100%{background-position:-200% center}}
.sp-divider{display:flex;align-items:center;gap:8px;margin:14px 0 10px;animation:textIn .4s ease 1.1s both;}
.sp-div-line{width:45px;height:1px;background:linear-gradient(90deg,transparent,rgba(200,168,75,.4),transparent);}
.sp-div-gem{width:6px;height:6px;background:var(--gold1);transform:rotate(45deg);}
.sp-ramadan-label{font-family:'Cairo',sans-serif;font-size:.85rem;font-weight:800;color:transparent;background:linear-gradient(90deg,var(--gold3),var(--gold2),var(--gold4),var(--gold2),var(--gold3));background-size:300% 100%;-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:goldFlow 4s linear infinite,textIn .5s ease 1s both;margin-bottom:6px;}
.sp-sub{font-size:.6rem;font-weight:700;color:rgba(200,168,75,.4);letter-spacing:2px;animation:textIn .5s ease 1.3s both;}
.sp-foot{position:absolute;bottom:0;left:0;right:0;padding:0 28px 44px;}
.sp-bar-track{height:2px;background:rgba(200,168,75,.08);border-radius:2px;overflow:hidden;margin-bottom:14px;}
.sp-bar-fill{height:100%;background:linear-gradient(90deg,var(--gold3),var(--gold2),var(--gold4),var(--gold2));background-size:300%;animation:barGrow 2.4s cubic-bezier(.25,.46,.45,.94) .4s forwards,goldFlow 1.5s linear .4s infinite;width:0;}
@keyframes barGrow{0%{width:0%}30%{width:40%}65%{width:75%}85%{width:90%}100%{width:100%}}
.sp-meta{display:flex;align-items:center;justify-content:space-between;animation:textIn .4s ease 2s both;}
.sp-ver{font-size:.45rem;font-weight:700;color:rgba(200,168,75,.25);letter-spacing:1px;}
.sp-brand{display:flex;align-items:center;gap:5px;}
.sp-brand-dot{width:4px;height:4px;border-radius:50%;background:rgba(200,168,75,.4);}
.sp-brand-txt{font-size:.44rem;font-weight:800;letter-spacing:1.5px;color:rgba(200,168,75,.3);}

/* BANNER */
.banner{position:sticky;top:0;width:100%;background:rgba(6,5,10,.97);display:flex;justify-content:space-between;align-items:center;padding:0 16px;height:64px;z-index:100;border-bottom:1px solid var(--stroke);box-shadow:0 4px 30px rgba(0,0,0,.8);flex-shrink:0;}
.banner-left{display:flex;align-items:center;gap:10px;}
.banner-logo{width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,#1a1400,#2a2000);border:1px solid rgba(200,168,75,.25);display:flex;align-items:center;justify-content:center;box-shadow:0 0 16px rgba(200,168,75,.2);overflow:hidden;}
.banner-logo img{width:24px;height:24px;object-fit:contain;filter:drop-shadow(0 2px 6px rgba(200,168,75,.5));}
.banner-letters{display:flex;font-size:1.1rem;font-weight:900;letter-spacing:5px;}
.banner-letters span{display:inline-block;color:transparent;background:linear-gradient(90deg,#7a5c18 0%,#c8a84b 20%,#f5d070 40%,#e8c060 60%,#f5d070 75%,#8a6820 100%);background-size:400% 100%;-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:goldFlow 4s linear infinite;animation-delay:calc(var(--i)*.18s);}
.banner-right{display:flex;flex-direction:column;align-items:flex-end;gap:2px;}
.banner-season{font-size:.62rem;font-weight:800;color:var(--gold2);}
.banner-tag{font-size:.52rem;font-weight:700;color:var(--ink3);letter-spacing:1px;display:flex;align-items:center;gap:5px;}

/* ONLINE INLINE — جوه الـ ended-card */
.online-inline{
  display:inline-flex;align-items:center;justify-content:center;gap:7px;
  font-size:.7rem;font-weight:800;color:#00e676;
  margin-top:2px;
}
.online-inline-dot{
  width:7px;height:7px;border-radius:50%;
  background:#00C853;
  box-shadow:0 0 0 0 rgba(0,200,83,.6);
  animation:onlinePulse 1.8s infinite;
  flex-shrink:0;
}
@keyframes onlinePulse{
  0%{box-shadow:0 0 0 0 rgba(0,200,83,.6)}
  70%{box-shadow:0 0 0 7px rgba(0,200,83,0)}
  100%{box-shadow:0 0 0 0 rgba(0,200,83,0)}
}

/* PAGE */
.page-wrap{max-width:480px;margin:0 auto;padding:20px 14px 100px;}
.card-in{animation:cardIn .5s cubic-bezier(.34,1.2,.64,1) both;}
@keyframes cardIn{from{opacity:0;transform:translateY(24px) scale(.97)}to{opacity:1;transform:none}}

/* ENDED CARD */
.ended-card{background:var(--l1);border:1px solid var(--stroke2);border-radius:22px;padding:28px 20px;text-align:center;margin-bottom:14px;position:relative;overflow:hidden;}
.ended-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--gold3),var(--gold2),var(--gold4),var(--gold2),var(--gold3));}
.ended-card::after{content:'';position:absolute;inset:0;background:radial-gradient(ellipse 80% 60% at 50% 0%,rgba(200,168,75,.07) 0%,transparent 70%);pointer-events:none;}
.ended-moon-icon{font-size:3rem;margin-bottom:10px;display:block;filter:drop-shadow(0 0 20px rgba(200,168,75,.5));animation:moonBob 3s ease-in-out infinite;}
@keyframes moonBob{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}
.ended-title{font-family:'Playfair Display',serif;font-size:1.5rem;font-weight:900;color:transparent;background:linear-gradient(135deg,#a07828,#f5d070,#c8a84b);background-size:300%;-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:goldFlow 5s linear infinite;margin-bottom:6px;}
.ended-subtitle{font-size:.75rem;font-weight:700;color:var(--ink2);margin-bottom:16px;line-height:1.6;}
.ended-line{height:1px;background:linear-gradient(90deg,transparent,rgba(200,168,75,.3),transparent);margin:16px 0;}
.ended-note{font-size:.68rem;color:var(--ink3);line-height:1.7;}
.ended-note b{color:var(--gold2);font-weight:800;}

/* COUNTDOWN */
.countdown-card{background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r);padding:20px 16px;margin-bottom:14px;}
.cd-label{font-size:.54rem;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:var(--ink3);text-align:center;margin-bottom:16px;display:flex;align-items:center;gap:8px;justify-content:center;}
.cd-label-line{width:30px;height:1px;background:linear-gradient(90deg,transparent,rgba(200,168,75,.35),transparent);}
.cd-label-gem{width:5px;height:5px;background:var(--gold1);transform:rotate(45deg);}
.cd-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;}
.cd-unit{background:var(--l2);border:1px solid var(--stroke);border-radius:var(--r-sm);padding:14px 6px 10px;text-align:center;position:relative;overflow:hidden;}
.cd-unit::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--gold3),var(--gold2),var(--gold3));}
.cd-num{font-family:'Playfair Display',serif;font-size:2.1rem;font-weight:900;color:var(--gold2);line-height:1;transition:all .3s cubic-bezier(.34,1.4,.64,1);}
.cd-num.pop{animation:numPop .3s cubic-bezier(.34,1.6,.64,1);}
@keyframes numPop{0%{transform:scale(.7);opacity:.4}100%{transform:scale(1);opacity:1}}
.cd-lbl{font-size:.5rem;font-weight:700;color:var(--ink3);letter-spacing:.8px;margin-top:5px;}
.cd-date-row{display:flex;align-items:center;justify-content:center;margin-top:14px;padding-top:12px;border-top:1px solid var(--stroke);}
.cd-date-chip{display:inline-flex;align-items:center;gap:5px;background:rgba(200,168,75,.07);border:1px solid rgba(200,168,75,.15);border-radius:100px;padding:5px 14px;font-size:.62rem;font-weight:800;color:var(--gold2);}

/* PROGRESS */
.progress-card{background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r);padding:16px;margin-bottom:14px;}
.prog-row{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;}
.prog-label{font-size:.6rem;font-weight:700;color:var(--ink2);}
.prog-pct{font-size:.6rem;font-weight:800;color:var(--gold2);}
.prog-track{height:6px;background:rgba(255,255,255,.05);border-radius:3px;overflow:hidden;}
.prog-fill{height:100%;border-radius:3px;background:linear-gradient(90deg,var(--gold3),var(--gold2),var(--gold4));transition:width 1.2s cubic-bezier(.25,.46,.45,.94);}
.prog-note{font-size:.54rem;color:var(--ink3);margin-top:8px;text-align:center;}

/* STATUS */
.status-card{background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r);padding:18px;margin-bottom:14px;}
.status-row{display:flex;align-items:center;gap:12px;}
.status-icon-wrap{width:44px;height:44px;border-radius:12px;background:rgba(200,168,75,.08);border:1px solid rgba(200,168,75,.15);display:flex;align-items:center;justify-content:center;color:var(--gold1);font-size:1rem;flex-shrink:0;}
.status-title{font-size:.78rem;font-weight:800;color:var(--ink);margin-bottom:4px;}
.status-text{font-size:.62rem;color:var(--ink2);line-height:1.6;}
.status-text b{color:var(--gold2);font-weight:800;}

/* CONTACT */
.contact-title{font-size:.54rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);text-align:center;margin-bottom:10px;display:flex;align-items:center;gap:8px;justify-content:center;}
.contact-title::before,.contact-title::after{content:'';flex:1;height:1px;background:var(--stroke);}
.contact-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:14px;}
.contact-btn{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;padding:14px 8px;background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r-sm);text-decoration:none;transition:all .25s;}
.contact-btn:hover{border-color:var(--stroke2);background:rgba(200,168,75,.04);}
.contact-btn:active{transform:scale(.95);}
.cb-icon{width:38px;height:38px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:.95rem;}
.contact-btn.tg .cb-icon{background:rgba(41,182,246,.1);color:#29b6f6;border:1px solid rgba(41,182,246,.2);}
.contact-btn.wa .cb-icon{background:rgba(37,211,102,.1);color:#25d366;border:1px solid rgba(37,211,102,.2);}
.contact-btn.fb .cb-icon{background:rgba(24,119,242,.1);color:#1877f2;border:1px solid rgba(24,119,242,.2);}
.cb-label{font-size:.52rem;font-weight:700;color:var(--ink3);}

/* SLIDE NOTIFICATION */
.notif-slide{position:fixed;top:74px;left:-360px;width:320px;background:rgba(10,9,8,.98);border:1px solid var(--stroke);border-right:3px solid var(--gold1);border-radius:16px;padding:13px 14px 10px;z-index:9999;backdrop-filter:blur(24px);box-shadow:0 10px 40px rgba(0,0,0,.8);transition:left .45s cubic-bezier(.34,1.15,.64,1);pointer-events:none;}
.notif-slide.show{left:10px;pointer-events:all;}
.notif-slide.has-link{cursor:pointer;}
.notif-top-row{display:flex;align-items:flex-start;gap:11px;}
.notif-slide-icon{width:38px;height:38px;border-radius:10px;background:rgba(200,168,75,.1);border:1px solid rgba(200,168,75,.2);display:flex;align-items:center;justify-content:center;color:var(--gold1);font-size:.95rem;flex-shrink:0;overflow:hidden;}
.notif-slide-icon img{width:100%;height:100%;object-fit:cover;border-radius:10px;}
.notif-slide-body{flex:1;min-width:0;}
.notif-slide-title{font-size:.68rem;font-weight:800;color:var(--ink);display:flex;align-items:center;justify-content:space-between;gap:6px;margin-bottom:2px;}
.notif-slide-app{font-size:.48rem;color:var(--ink3);font-weight:700;letter-spacing:1px;}
.notif-slide-text{font-size:.62rem;color:var(--ink2);line-height:1.5;word-break:break-word;margin-top:2px;}
.notif-action-btn{display:flex;align-items:center;justify-content:center;gap:5px;margin-top:10px;padding:8px 14px;background:rgba(200,168,75,.08);border:1px solid rgba(200,168,75,.2);border-radius:8px;font-family:'Cairo',sans-serif;font-size:.62rem;font-weight:800;color:var(--gold2);cursor:pointer;text-decoration:none;transition:all .2s;width:100%;text-align:center;}
.notif-bar{position:absolute;bottom:0;left:0;right:0;height:2px;background:rgba(200,168,75,.1);border-radius:0 0 16px 16px;overflow:hidden;}
.notif-bar-fill{height:100%;background:var(--gold1);width:100%;transform-origin:right;}

/* FOOTER */
.footer{text-align:center;padding:10px 0 20px;}
.footer-brand{display:flex;align-items:center;justify-content:center;gap:6px;margin-bottom:6px;}
.footer-dot{width:4px;height:4px;border-radius:50%;background:rgba(200,168,75,.3);}
.footer-name{font-family:'Playfair Display',serif;font-size:.75rem;font-weight:700;color:rgba(200,168,75,.4);letter-spacing:3px;}
.footer-copy{font-size:.5rem;color:var(--ink3);}

/* BOTTOM NAV */
.botnav{position:fixed;bottom:0;left:0;right:0;height:60px;background:rgba(6,5,10,.97);backdrop-filter:blur(22px);border-top:1px solid var(--stroke);display:flex;justify-content:space-around;align-items:stretch;z-index:400;}
.nav-link{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;text-decoration:none;color:var(--ink3);font-family:'Cairo',sans-serif;font-size:.49rem;font-weight:700;letter-spacing:.5px;border-top:2px solid transparent;transition:color .2s,border-color .2s;}
.nav-link:hover{color:var(--gold1);border-color:var(--gold1);}
.nav-link i{font-size:1.05rem;}

/* TOAST */
.toast{position:fixed;bottom:70px;left:50%;transform:translateX(-50%) translateY(12px);opacity:0;background:rgba(8,7,10,.96);border:1px solid var(--stroke);border-radius:100px;padding:9px 22px;font-family:'Cairo',sans-serif;font-size:.7rem;font-weight:700;color:var(--ink);pointer-events:none;z-index:9998;white-space:nowrap;backdrop-filter:blur(20px);transition:all .3s cubic-bezier(.34,1.4,.64,1);}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0);}
.toast.ok{border-color:rgba(0,200,90,.3);color:var(--green);}
.toast.err{border-color:rgba(230,0,0,.3);color:#ff5555;}

/* ADMIN */
.admin-overlay{position:fixed;inset:0;background:rgba(0,0,0,.88);backdrop-filter:blur(18px);z-index:10000;display:flex;align-items:flex-end;justify-content:center;opacity:0;pointer-events:none;transition:opacity .3s ease;}
.admin-overlay.open{opacity:1;pointer-events:all;}
.admin-panel{width:100%;max-width:460px;background:var(--l1);border:1px solid var(--stroke);border-radius:22px 22px 0 0;box-shadow:0 -10px 60px rgba(0,0,0,.9);transform:translateY(100%);transition:transform .38s cubic-bezier(.34,1.1,.64,1);display:flex;flex-direction:column;height:92vh;max-height:92vh;overflow:hidden;}
.admin-overlay.open .admin-panel{transform:translateY(0);}
.admin-drag-bar{width:40px;height:4px;border-radius:2px;background:rgba(200,168,75,.15);margin:10px auto 0;flex-shrink:0;}
.admin-head{background:linear-gradient(135deg,rgba(200,168,75,.1),transparent);border-bottom:1px solid var(--stroke);padding:14px 18px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0;}
.admin-head-left{display:flex;align-items:center;gap:11px;}
.admin-head-icon{width:38px;height:38px;border-radius:10px;background:rgba(200,168,75,.1);border:1px solid rgba(200,168,75,.2);display:flex;align-items:center;justify-content:center;color:var(--gold1);font-size:.9rem;}
.admin-head-title{font-family:'Playfair Display',serif;font-size:.88rem;font-weight:900;letter-spacing:2px;color:var(--ink);}
.admin-head-sub{font-size:.52rem;color:var(--ink3);margin-top:2px;letter-spacing:1px;}
.admin-close{width:32px;height:32px;border-radius:8px;background:rgba(255,255,255,.04);border:1px solid var(--stroke);display:flex;align-items:center;justify-content:center;cursor:pointer;color:var(--ink3);font-size:.7rem;transition:all .2s;}
.admin-close:hover{background:rgba(200,168,75,.1);color:var(--gold2);}
.admin-auth{padding:22px 20px;overflow-y:auto;flex:1;}
.admin-auth-title{font-size:.65rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);text-align:center;margin-bottom:16px;}
.auth-err{font-size:.65rem;font-weight:700;color:#ff5555;text-align:center;margin-bottom:10px;opacity:0;transition:opacity .2s;}
.auth-err.show{opacity:1;}
.pw-field-wrap{background:var(--l2);border:1.5px solid var(--stroke);border-radius:var(--r-sm);display:flex;align-items:center;margin-bottom:13px;transition:border-color .25s;}
.pw-field-wrap:focus-within{border-color:rgba(200,168,75,.35);}
.pw-field-wrap input{flex:1;background:none;border:none;outline:none;font-family:'Cairo',sans-serif;font-size:.88rem;font-weight:700;color:var(--ink);padding:13px 14px;direction:ltr;letter-spacing:2px;text-align:center;}
.pw-field-wrap .ico{width:40px;text-align:center;color:var(--ink3);font-size:.75rem;flex-shrink:0;}
.btn-auth{width:100%;padding:13px;border:none;border-radius:var(--r-sm);background:linear-gradient(135deg,var(--gold3),var(--gold1),var(--gold2));color:#1a0e00;font-family:'Cairo',sans-serif;font-size:.85rem;font-weight:900;cursor:pointer;transition:all .2s;box-shadow:0 4px 16px rgba(200,168,75,.25);}
.admin-content{padding:0;display:none;overflow-y:auto;flex:1;flex-direction:column;}
.admin-content.visible{display:flex;}
.admin-tabs{display:flex;border-bottom:1px solid var(--stroke);flex-shrink:0;}
.admin-tab{flex:1;padding:10px 6px;text-align:center;font-family:'Cairo',sans-serif;font-size:.58rem;font-weight:700;color:var(--ink3);cursor:pointer;border-bottom:2px solid transparent;transition:all .2s;}
.admin-tab.active{color:var(--gold2);border-bottom-color:var(--gold1);}
.admin-tab-body{padding:16px 18px 40px;overflow-y:auto;}
.admin-field{margin-bottom:14px;}
.admin-label{font-size:.54rem;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--ink3);margin-bottom:7px;display:block;}
.admin-textarea{width:100%;background:var(--l2);border:1.5px solid var(--stroke);border-radius:var(--r-sm);padding:12px 14px;resize:none;font-family:'Cairo',sans-serif;font-size:.82rem;font-weight:700;color:var(--ink);direction:rtl;outline:none;line-height:1.6;transition:border-color .25s;}
.admin-textarea:focus{border-color:rgba(200,168,75,.35);}
.admin-input{width:100%;background:var(--l2);border:1.5px solid var(--stroke);border-radius:var(--r-sm);padding:11px 14px;font-family:'Cairo',sans-serif;font-size:.82rem;font-weight:700;color:var(--ink);direction:rtl;outline:none;transition:border-color .25s;}
.admin-input:focus{border-color:rgba(200,168,75,.35);}
input[type="datetime-local"]{color-scheme:dark;}
.admin-type-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px;margin-bottom:14px;}
.type-btn{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:5px;padding:10px 6px;border-radius:var(--r-sm);background:var(--l2);border:1.5px solid var(--stroke);cursor:pointer;transition:all .2s;font-family:'Cairo',sans-serif;font-size:.56rem;font-weight:700;color:var(--ink3);}
.type-btn i{font-size:.85rem;}
.type-btn.active-info{background:rgba(79,195,247,.07);border-color:rgba(79,195,247,.3);color:#80ccee;}
.type-btn.active-ok{background:rgba(0,200,90,.07);border-color:rgba(0,200,90,.3);color:var(--green);}
.type-btn.active-err{background:rgba(230,0,0,.07);border-color:rgba(230,0,0,.3);color:#ff8888;}
.admin-dur-grid{display:flex;gap:6px;flex-wrap:wrap;}
.dur-btn{flex:1;min-width:42px;padding:8px 4px;text-align:center;background:var(--l2);border:1.5px solid var(--stroke);border-radius:8px;cursor:pointer;font-family:'Cairo',sans-serif;font-size:.62rem;font-weight:700;color:var(--ink3);transition:all .2s;}
.dur-btn.active{background:rgba(200,168,75,.08);border-color:rgba(200,168,75,.35);color:var(--gold2);}
.admin-sep{font-size:.5rem;font-weight:700;letter-spacing:2px;color:var(--ink3);display:flex;align-items:center;gap:8px;text-transform:uppercase;margin:14px 0;}
.admin-sep::before,.admin-sep::after{content:'';flex:1;height:1px;background:var(--stroke);}
.admin-btns{display:flex;gap:8px;margin-top:4px;}
.btn-send-notif{flex:1;padding:13px;border:none;border-radius:var(--r-sm);background:linear-gradient(135deg,var(--gold3),var(--gold1),var(--gold2));color:#1a0e00;font-family:'Cairo',sans-serif;font-size:.78rem;font-weight:800;cursor:pointer;transition:all .2s;display:flex;align-items:center;justify-content:center;gap:6px;}
.btn-clear-notif{padding:13px 16px;border-radius:var(--r-sm);background:var(--l2);border:1px solid var(--stroke);color:var(--ink3);cursor:pointer;transition:all .2s;font-family:'Cairo',sans-serif;font-size:.7rem;font-weight:700;}

/* ADMIN STATS — عداد أكبر وأوضح */
.admin-stats{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:14px;padding-top:14px;border-top:1px solid var(--stroke);}
.adm-stat{background:var(--l2);border:1px solid var(--stroke);border-radius:10px;padding:10px 12px;text-align:center;position:relative;overflow:hidden;}
.adm-stat.online-stat{border-color:rgba(0,200,83,.25);background:rgba(0,200,83,.04);}
.adm-stat-val{font-family:'Playfair Display',serif;font-size:1.1rem;font-weight:900;color:var(--gold2);}
.adm-stat.online-stat .adm-stat-val{color:#00C853;}
.adm-stat-lbl{font-size:.5rem;color:var(--ink3);margin-top:3px;}
.adm-online-dot{display:inline-block;width:5px;height:5px;border-radius:50%;background:#00C853;margin-left:3px;vertical-align:middle;animation:onlinePulse 2s infinite;}

.notif-preview{background:var(--l2);border:1px solid var(--stroke);border-radius:10px;padding:11px 13px;display:flex;align-items:flex-start;gap:9px;border-right:3px solid var(--gold1);}
.notif-preview.type-ok{border-right-color:var(--green);}
.notif-preview.type-err{border-right-color:#ff5555;}
.prev-icon{width:28px;height:28px;border-radius:7px;background:rgba(200,168,75,.1);display:flex;align-items:center;justify-content:center;color:var(--gold1);font-size:.7rem;flex-shrink:0;}
.prev-app{font-size:.48rem;color:var(--ink3);margin-bottom:4px;}
.prev-title{font-size:.65rem;font-weight:800;color:var(--ink);margin-bottom:2px;}
.prev-text{font-size:.6rem;color:var(--ink2);line-height:1.4;}
.hist-list,.sched-list{display:flex;flex-direction:column;gap:8px;}
.hist-item,.sched-item{background:var(--l2);border:1px solid var(--stroke);border-radius:10px;padding:10px 12px;display:flex;align-items:flex-start;justify-content:space-between;gap:8px;position:relative;overflow:hidden;}
.hist-item::before,.sched-item::before{content:'';position:absolute;top:0;right:0;bottom:0;width:3px;}
.hist-item.type-info::before{background:var(--gold1);}
.hist-item.type-ok::before{background:var(--green);}
.hist-item.type-err::before{background:#ff5555;}
.hist-item-body{flex:1;min-width:0;}
.hist-item-title{font-size:.65rem;font-weight:800;color:var(--ink);margin-bottom:2px;}
.hist-item-text{font-size:.58rem;color:var(--ink2);line-height:1.4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.hist-item-meta{display:flex;align-items:center;gap:6px;margin-top:5px;}
.hist-meta-chip{display:inline-flex;align-items:center;gap:3px;font-size:.5rem;font-weight:700;padding:2px 7px;border-radius:100px;}
.hist-meta-time{background:rgba(255,255,255,.05);color:var(--ink3);}
.hist-meta-views{background:rgba(200,168,75,.07);color:var(--gold2);}
.hist-resend{width:28px;height:28px;border-radius:8px;flex-shrink:0;background:rgba(200,168,75,.07);border:1px solid rgba(200,168,75,.15);display:flex;align-items:center;justify-content:center;cursor:pointer;color:var(--gold1);font-size:.6rem;transition:all .2s;}
.sched-item.done-item{opacity:.45;}
.sched-item-body{flex:1;min-width:0;}
.sched-item-title{font-size:.65rem;font-weight:800;color:var(--ink);margin-bottom:2px;}
.sched-item-text{font-size:.58rem;color:var(--ink2);line-height:1.4;}
.sched-time-badge{display:inline-flex;align-items:center;gap:4px;font-size:.5rem;font-weight:700;margin-top:5px;padding:2px 8px;border-radius:100px;background:rgba(200,168,75,.07);color:var(--gold2);}
.sched-time-badge.done-badge{background:rgba(0,200,90,.07);color:var(--green);}
.sched-del{width:26px;height:26px;border-radius:7px;flex-shrink:0;background:rgba(255,85,85,.07);border:1px solid rgba(255,85,85,.15);display:flex;align-items:center;justify-content:pointer;cursor:pointer;color:#ff5555;font-size:.58rem;align-items:center;justify-content:center;}
.hist-empty{text-align:center;padding:24px;color:var(--ink3);font-size:.65rem;}
.input-box{display:flex;align-items:center;background:var(--l2);border:1.5px solid var(--stroke);border-radius:var(--r-sm);overflow:hidden;transition:border-color .25s;}
.input-box:focus-within{border-color:rgba(200,168,75,.35);}
.input-box input{flex:1;background:none;border:none;outline:none;font-family:'Cairo',sans-serif;font-size:.82rem;font-weight:700;color:var(--ink);padding:11px 14px;direction:ltr;}
.input-box .ico{width:40px;text-align:center;color:var(--ink3);font-size:.75rem;}
::-webkit-scrollbar{width:3px;}::-webkit-scrollbar-track{background:var(--l1);}::-webkit-scrollbar-thumb{background:rgba(200,168,75,.3);border-radius:3px;}
</style>
</head>
<body>

<!-- SPLASH -->
<div id="s-splash">
  <div class="sp-stars" id="spStars"></div>
  <div class="sp-moon"></div>
  <div class="sp-lantern" style="top:8%;left:5%;--sw:5s;--sd:0s">
    <svg width="22" height="38" viewBox="0 0 22 38" fill="none">
      <line x1="11" y1="0" x2="11" y2="6" stroke="rgba(200,168,75,.5)" stroke-width="1.5"/>
      <rect x="3" y="6" width="16" height="22" rx="4" fill="rgba(200,168,75,.12)" stroke="rgba(200,168,75,.6)" stroke-width="1"/>
      <ellipse cx="11" cy="6" rx="5" ry="2" fill="rgba(200,168,75,.3)" stroke="rgba(200,168,75,.6)" stroke-width="1"/>
      <line x1="11" y1="28" x2="11" y2="36" stroke="rgba(200,168,75,.4)" stroke-width="1"/>
    </svg>
  </div>
  <div class="sp-lantern" style="top:6%;right:15%;--sw:7s;--sd:1.5s">
    <svg width="18" height="30" viewBox="0 0 18 30" fill="none">
      <line x1="9" y1="0" x2="9" y2="5" stroke="rgba(200,168,75,.4)" stroke-width="1.2"/>
      <rect x="2" y="5" width="14" height="17" rx="3" fill="rgba(200,168,75,.1)" stroke="rgba(200,168,75,.5)" stroke-width="1"/>
      <ellipse cx="9" cy="5" rx="4" ry="1.5" fill="rgba(200,168,75,.25)" stroke="rgba(200,168,75,.5)" stroke-width="1"/>
      <line x1="9" y1="22" x2="9" y2="28" stroke="rgba(200,168,75,.3)" stroke-width="1"/>
    </svg>
  </div>
  <div class="sp-arch"></div>
  <div class="sp-stage">
    <div class="sp-logo-wrap">
      <div class="sp-halo"></div>
      <div class="sp-spin-ring"></div>
      <div class="sp-icon">
        <img src="https://i.postimg.cc/PqxnBbpw/vodafone2.png" alt="Vodafone"
             onerror="this.style.display='none';this.parentElement.innerHTML+='<i class=\'fas fa-star\' style=\'font-size:2.5rem;color:#c8a84b\'></i>'"/>
      </div>
      <div class="sp-bolt"><i class="fas fa-star"></i></div>
    </div>
    <div class="sp-rk-badge"><i class="fas fa-star-and-crescent"></i>&nbsp;رمضان كريم</div>
    <div class="sp-name">
      <span class="sp-nl" style="--n:0">Y</span><span class="sp-nl" style="--n:1">N</span>
      <span class="sp-nl" style="--n:2">H</span><span class="sp-nl" style="--n:3">S</span>
      <span class="sp-nl" style="--n:4">A</span><span class="sp-nl" style="--n:5">L</span>
      <span class="sp-nl" style="--n:6">A</span><span class="sp-nl" style="--n:7">T</span>
    </div>
    <div class="sp-divider">
      <div class="sp-div-line"></div><div class="sp-div-gem"></div><div class="sp-div-line"></div>
    </div>
    <div class="sp-ramadan-label">كروت رمضان فودافون</div>
    <div class="sp-sub">نراكم في رمضان القادم</div>
  </div>
  <div class="sp-foot">
    <div class="sp-bar-track"><div class="sp-bar-fill"></div></div>
    <div class="sp-meta">
      <div class="sp-ver">v2.2 · Vodafone EG</div>
      <div class="sp-brand">
        <div class="sp-brand-dot"></div>
        <div class="sp-brand-txt">TALASHNY</div>
        <div class="sp-brand-dot"></div>
      </div>
    </div>
  </div>
</div>

<!-- MAIN APP -->
<div id="s-app" style="display:none;min-height:100vh">
  <div class="banner">
    <div class="banner-left">
      <div class="banner-logo">
        <img src="https://i.postimg.cc/PqxnBbpw/vodafone2.png" alt=""
             onerror="this.style.display='none';this.parentElement.innerHTML='<i class=\'fas fa-star\' style=\'color:var(--gold1);font-size:.9rem\'></i>'"/>
      </div>
      <div class="banner-letters">
        <span style="--i:0">Y</span><span style="--i:1">N</span><span style="--i:2">H</span>
        <span style="--i:3">S</span><span style="--i:4">A</span><span style="--i:5">L</span>
        <span style="--i:6">A</span><span style="--i:7">T</span>
      </div>
    </div>
    <div class="banner-right">
      <div class="banner-season">رمضان 2027</div>
      <div class="banner-tag">
        <div class="live-dot" id="liveDotBtn" onclick="handleLiveTap()"
             style="width:6px;height:6px;border-radius:50%;background:var(--green);animation:livePulse 2s infinite;cursor:pointer;flex-shrink:0;"></div>
        <span>قريباً إن شاء الله</span>
      </div>
    </div>
  </div>

  <div class="page-wrap">

    <div class="ended-card card-in" style="animation-delay:.0s">
      <span class="ended-moon-icon">🌙</span>
      <div class="ended-title">انتهت كروت رمضان 1446</div>
      <div class="ended-subtitle">شكراً لكل من استخدم TALASHNY هذا الموسم<br>كانت رحلة رائعة معكم 💛</div>
      <div class="ended-line"></div>
      <div class="ended-note">
        خدمة <b>شحن كروت رمضان فودافون</b> متاحة بس خلال شهر رمضان المبارك.<br>
        هنعود بشكل أقوى في <b>رمضان القادم 2027</b> إن شاء الله.
      </div>
      <div class="ended-line"></div>
      <div class="online-inline">
        <div class="online-inline-dot"></div>
        <span id="onlineCount">...</span>&nbsp;<span id="onlineLabel">متصل دلوقتي</span>
      </div>
    </div>

    <div class="countdown-card card-in" style="animation-delay:.08s">
      <div class="cd-label">
        <div class="cd-label-line"></div>
        <div class="cd-label-gem"></div>
        العد التنازلي لرمضان 1447
        <div class="cd-label-gem"></div>
        <div class="cd-label-line"></div>
      </div>
      <div class="cd-grid">
        <div class="cd-unit"><div class="cd-num" id="cd-days">---</div><div class="cd-lbl">يوم</div></div>
        <div class="cd-unit"><div class="cd-num" id="cd-hours">--</div><div class="cd-lbl">ساعة</div></div>
        <div class="cd-unit"><div class="cd-num" id="cd-mins">--</div><div class="cd-lbl">دقيقة</div></div>
        <div class="cd-unit"><div class="cd-num" id="cd-secs">--</div><div class="cd-lbl">ثانية</div></div>
      </div>
      <div class="cd-date-row">
        <div class="cd-date-chip"><i class="fas fa-calendar-star"></i>&nbsp;المتوقع: ~10 مارس 2027</div>
      </div>
    </div>

    <div class="progress-card card-in" style="animation-delay:.16s">
      <div class="prog-row">
        <div class="prog-label"><i class="fas fa-hourglass-half" style="color:var(--gold1);margin-left:5px"></i>الوقت المتبقي حتى رمضان</div>
        <div class="prog-pct" id="prog-pct">—%</div>
      </div>
      <div class="prog-track"><div class="prog-fill" id="prog-fill" style="width:0%"></div></div>
      <div class="prog-note" id="prog-note">جاري الحساب...</div>
    </div>

    <div class="status-card card-in" style="animation-delay:.22s">
      <div class="status-row">
        <div class="status-icon-wrap"><i class="fas fa-bell-slash"></i></div>
        <div>
          <div class="status-title">الخدمة متوقفة مؤقتاً</div>
          <div class="status-text">كروت رمضان من فودافون بتتاح بس خلال شهر رمضان المبارك.<br><b>هنعود قبل رمضان بإشعار فوري</b> — ابقى متابعنا!</div>
        </div>
      </div>
    </div>

    <div class="contact-title">تواصل معنا</div>
    <div class="contact-grid card-in" style="animation-delay:.3s">
      <a href="https://t.me/FY_TF" target="_blank" class="contact-btn tg">
        <div class="cb-icon"><i class="fab fa-telegram-plane"></i></div>
        <div class="cb-label">تيليجرام</div>
      </a>
      <a href="https://wa.me/message/U6AIKBGFCNCQK1" target="_blank" class="contact-btn wa">
        <div class="cb-icon"><i class="fab fa-whatsapp"></i></div>
        <div class="cb-label">واتساب</div>
      </a>
      <a href="https://www.facebook.com/VI808IV" target="_blank" class="contact-btn fb">
        <div class="cb-icon"><i class="fab fa-facebook-f"></i></div>
        <div class="cb-label">فيسبوك</div>
      </a>
    </div>

    <div class="footer">
      <div class="footer-brand">
        <div class="footer-dot"></div>
        <div class="footer-name">TALASHNY</div>
        <div class="footer-dot"></div>
      </div>
      <div class="footer-copy">© 2026 · كروت رمضان فودافون · نراكم العام القادم</div>
    </div>
  </div>

  <nav class="botnav">
    <a href="https://t.me/FY_TF" target="_blank" class="nav-link"><i class="fab fa-telegram-plane"></i><span>تيليجرام</span></a>
    <a href="https://wa.me/message/U6AIKBGFCNCQK1" target="_blank" class="nav-link"><i class="fab fa-whatsapp"></i><span>واتساب</span></a>
    <a href="https://www.facebook.com/VI808IV" target="_blank" class="nav-link"><i class="fab fa-facebook-f"></i><span>فيسبوك</span></a>
  </nav>
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
      <div class="auth-err" id="authErr">❌ كلمة المرور غلط</div>
      <div class="pw-field-wrap">
        <span class="ico"><i class="fas fa-key"></i></span>
        <input type="password" id="adminPwInput" placeholder="••••••••••" onkeydown="if(event.key==='Enter')checkAdminPw()"/>
      </div>
      <button class="btn-auth" onclick="checkAdminPw()"><i class="fas fa-unlock-keyhole"></i>&nbsp;دخول</button>
    </div>
    <div class="admin-content" id="adminContent">
      <div class="admin-tabs">
        <div class="admin-tab active" id="tab-send" onclick="switchTab('send')"><i class="fas fa-paper-plane"></i>&nbsp;إرسال</div>
        <div class="admin-tab" id="tab-schedule" onclick="switchTab('schedule')"><i class="fas fa-calendar-clock"></i>&nbsp;جدولة</div>
        <div class="admin-tab" id="tab-history" onclick="switchTab('history')"><i class="fas fa-clock-rotate-left"></i>&nbsp;السجل</div>
      </div>
      <div class="admin-tab-body" id="tabSend">
        <!-- إحصائيات مع عداد متصلين بارز -->
        <div class="admin-stats">
          <div class="adm-stat online-stat">
            <div class="adm-stat-val">
              <span id="adm-online">—</span>
              <div class="adm-online-dot"></div>
            </div>
            <div class="adm-stat-lbl">متصل دلوقتي</div>
          </div>
          <div class="adm-stat">
            <div class="adm-stat-val" id="adm-today">—</div>
            <div class="adm-stat-lbl">شحنات اليوم</div>
          </div>
          <div class="adm-stat">
            <div class="adm-stat-val" id="adm-views" style="color:var(--gold2)">—</div>
            <div class="adm-stat-lbl">شافوا الإشعار</div>
          </div>
        </div>
        <div class="admin-sep">نوع الإشعار</div>
        <div class="admin-type-grid">
          <div class="type-btn active-info" id="type-info" onclick="setType('info')"><i class="fas fa-circle-info" style="color:#80ccee"></i>معلومة</div>
          <div class="type-btn" id="type-ok" onclick="setType('ok')"><i class="fas fa-circle-check" style="color:var(--green)"></i>نجاح</div>
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
          <label class="admin-label">رابط أيقونة (اختياري)</label>
          <div class="input-box">
            <input type="url" id="notifIconInput" placeholder="https://..." style="direction:ltr" oninput="updatePreview()"/>
            <span class="ico"><i class="fas fa-link"></i></span>
          </div>
        </div>
        <div class="admin-field">
          <label class="admin-label">رابط زرار (اختياري)</label>
          <div class="input-box" style="margin-bottom:7px">
            <input type="url" id="notifLinkInput" placeholder="https://..." style="direction:ltr" oninput="updatePreview()"/>
            <span class="ico"><i class="fas fa-link"></i></span>
          </div>
          <div class="input-box">
            <input type="text" id="notifBtnInput" placeholder="نص الزرار..." oninput="updatePreview()"/>
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
          <div class="type-btn" id="stype-ok" onclick="setSchedType('ok')"><i class="fas fa-circle-check" style="color:var(--green)"></i>نجاح</div>
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
          <label class="admin-label">وقت الإرسال</label>
          <input type="datetime-local" id="schedTimeInput" class="admin-input" style="direction:ltr"/>
        </div>
        <div class="admin-field">
          <label class="admin-label">رابط زرار (اختياري)</label>
          <div class="input-box">
            <input type="url" id="schedLinkInput" placeholder="https://..." style="direction:ltr"/>
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

<style>
@keyframes livePulse{0%,100%{box-shadow:0 0 0 0 rgba(0,200,90,.5)}70%{box-shadow:0 0 0 5px rgba(0,200,90,0)}}
</style>

<script>
const _=id=>document.getElementById(id);
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function showToast(msg,t=''){const el=_('toastEl');el.textContent=msg;el.className='toast show'+(t?' '+t:'');clearTimeout(el._t);el._t=setTimeout(()=>el.classList.remove('show'),2800);}
document.addEventListener('contextmenu',e=>e.preventDefault());

// Stars
(function(){
  const wrap=_('spStars');
  for(let i=0;i<60;i++){
    const s=document.createElement('div');s.className='sp-star';
    const sz=Math.random()*2+0.5;
    s.style.cssText=`width:${sz}px;height:${sz}px;top:${Math.random()*100}%;left:${Math.random()*100}%;--dur:${(Math.random()*3+2).toFixed(1)}s;--delay:${(Math.random()*4).toFixed(1)}s;--min-op:${(Math.random()*0.15).toFixed(2)};--max-op:${(Math.random()*0.6+0.2).toFixed(2)};`;
    wrap.appendChild(s);
  }
})();

// Splash → App
setTimeout(()=>{
  const splash=_('s-splash');
  splash.classList.add('fade-out');
  setTimeout(()=>{
    splash.style.display='none';
    _('s-app').style.display='block';
    startCountdown();
    updateProgress();
    pollBroadcast();
    initSession();      // ← بدء الـ ping الحقيقي
  },800);
},3000);

// ═══════════════════════════════════════════════
// REAL ONLINE COUNTER — ping كل 20 ثانية
// ═══════════════════════════════════════════════
let myUid = null;

function initSession() {
  // أنشئ uid فريد لهذا المتصفح في هذه الجلسة
  myUid = sessionStorage.getItem('tlsh_uid');
  if (!myUid) {
    myUid = 'u_' + Math.random().toString(36).slice(2,10) + Date.now().toString(36);
    sessionStorage.setItem('tlsh_uid', myUid);
  }
  sendPing();                          // ping فوري عند الدخول
  setInterval(sendPing, 20000);        // ping كل 20 ثانية
  fetchOnlineCount();                  // اجلب العداد فوراً
  setInterval(fetchOnlineCount, 15000);// حدّث العداد كل 15 ثانية
}

async function sendPing() {
  try {
    await fetch('/ping', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({uid: myUid}),
      keepalive: true
    });
  } catch {}
}

async function fetchOnlineCount() {
  try {
    const r = await fetch('/online-count');
    const d = await r.json();
    const n = d.count || 1; // دايماً على الأقل 1 (الشخص اللي بيشوف)
    const countEl = _('onlineCount');
    const labelEl = _('onlineLabel');
    if (countEl) countEl.textContent = n;
    if (labelEl) {
      if (n === 1)      labelEl.textContent = 'متصل دلوقتي';
      else if (n === 2) labelEl.textContent = 'متصلين دلوقتي';
      else              labelEl.textContent = 'متصلين دلوقتي';
    }
    // حدّث الأدمن لو مفتوح
    const admEl = _('adm-online');
    if (admEl) admEl.textContent = n;
  } catch {}
}
// ════════════════════════════════════════════════

// Countdown to Ramadan 2026
const RAMADAN_TARGET=new Date('2027-03-10T00:00:00');
function pad(n){return String(n).padStart(2,'0');}
let prevSecs=-1;
function startCountdown(){
  function tick(){
    const now=new Date(),diff=RAMADAN_TARGET-now;
    if(diff<=0){['cd-days','cd-hours','cd-mins','cd-secs'].forEach(id=>_(id).textContent='00');return;}
    const days=Math.floor(diff/86400000);
    const hours=Math.floor((diff%86400000)/3600000);
    const mins=Math.floor((diff%3600000)/60000);
    const secs=Math.floor((diff%60000)/1000);
    _('cd-days').textContent=days;
    _('cd-hours').textContent=pad(hours);
    _('cd-mins').textContent=pad(mins);
    const secEl=_('cd-secs');
    if(secs!==prevSecs){prevSecs=secs;secEl.textContent=pad(secs);secEl.classList.remove('pop');void secEl.offsetWidth;secEl.classList.add('pop');}
  }
  tick();setInterval(tick,1000);
}

function updateProgress(){
  const start=new Date('2026-03-26T00:00:00'),end=RAMADAN_TARGET,now=new Date();
  const pct=Math.min(100,Math.max(0,Math.round((now-start)/(end-start)*100)));
  const remaining=Math.max(0,Math.floor((end-now)/86400000));
  _('prog-fill').style.width=pct+'%';
  _('prog-pct').textContent=pct+'%';
  let note='';
  if(remaining>180)note='لسه وقت كتير — استمتع بالأيام العادية 😄';
  else if(remaining>60)note='الوقت بيمشي بسرعة — متابعنا وهنعيد قريب!';
  else if(remaining>14)note='رمضان اقترب! جهّز نفسك 🌙';
  else note='رمضان على الأبواب! 🎉';
  _('prog-note').textContent=note;
}

// Broadcast polling
let lastBroadcastId='';
function pollBroadcast(){
  fetch('/broadcast-poll').then(r=>r.json()).then(d=>{
    if(d.broadcast?.text&&d.broadcast.id&&d.broadcast.id!==lastBroadcastId){
      lastBroadcastId=d.broadcast.id;
      fetch('/broadcast-view',{method:'POST'}).catch(()=>{});
      showNotif(d.broadcast.title||'TALASHNY',d.broadcast.text,d.broadcast.type||'info',Math.min((d.broadcast.duration||300)*1000,8000),d.broadcast.icon||'',d.broadcast.link||'',d.broadcast.btn_label||'افتح الرابط');
    }
  }).catch(()=>{});
  setTimeout(pollBroadcast,7000);
}

// Notification slide
let notifTimer=null,currentNotifLink='';
function notifClick(){if(currentNotifLink)window.open(currentNotifLink,'_blank');}
function showNotif(title,text,type='info',duration=5000,iconUrl='',linkUrl='',btnLabel=''){
  const el=_('notifSlide'),icon=_('notifIcon'),fill=_('notifBarFill');
  const icons={info:'fa-bell',ok:'fa-circle-check',err:'fa-circle-exclamation'};
  const colors={info:'var(--gold1)',ok:'var(--green)',err:'#ff5555'};
  const color=colors[type]||'var(--gold1)';
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

// Admin — tap live dot 5x
let tapCount=0,tapTimer=null;
function handleLiveTap(){
  tapCount++;
  clearTimeout(tapTimer);
  if(tapCount>=5){tapCount=0;openAdmin();}
  else tapTimer=setTimeout(()=>tapCount=0,2500);
}

const ADMIN_PW='1052003Mm$#@';let adminAuthed=false,selectedType='info',selectedDur=60;
function openAdmin(){_('adminOverlay').classList.add('open');if(!adminAuthed){_('adminAuth').style.display='';_('adminContent').classList.remove('visible');_('adminPwInput').value='';_('authErr').classList.remove('show');setTimeout(()=>_('adminPwInput').focus(),350);}else loadAdminStats();}
function closeAdmin(){_('adminOverlay').classList.remove('open');}
_('adminOverlay').addEventListener('click',function(e){if(e.target===this)closeAdmin();});
function checkAdminPw(){
  const val=_('adminPwInput').value;
  if(val===ADMIN_PW){adminAuthed=true;_('adminAuth').style.display='none';_('adminContent').classList.add('visible');loadAdminStats();}
  else{_('authErr').classList.add('show');setTimeout(()=>{_('authErr').classList.remove('show');_('adminPwInput').value='';},1200);}
}
async function loadAdminStats(){
  try{
    const r=await fetch('/admin-stats');const d=await r.json();
    if(d.ok){
      _('adm-online').textContent=d.online;
      _('adm-today').textContent=d.today;
      _('adm-views').textContent=d.views??'—';
    }
  }catch{}
  // حدث الأدمن كل 10 ثواني وهو مفتوح
  if(document.getElementById('adminOverlay').classList.contains('open')&&adminAuthed){
    setTimeout(loadAdminStats,10000);
  }
}
function setType(t){selectedType=t;['info','ok','err'].forEach(x=>{const b=_('type-'+x);b.className='type-btn';if(x===t)b.classList.add('active-'+x);});updatePreview();}
function setDur(el,sec){selectedDur=sec;document.querySelectorAll('.dur-btn').forEach(b=>b.classList.remove('active'));el.classList.add('active');}
function updatePreview(){
  const title=_('notifTitleInput').value||'TALASHNY',text=_('notifMsgInput').value||'نص الرسالة هيظهر هنا...';
  const icons={info:'fa-bell',ok:'fa-circle-check',err:'fa-circle-exclamation'};
  _('prevTitle').textContent=title;_('prevText').textContent=text;
  const pw=_('prevIconWrap');
  const iconUrl=_('notifIconInput').value.trim();
  if(iconUrl){pw.innerHTML=`<img src="${iconUrl}" style="width:28px;height:28px;border-radius:7px;object-fit:cover" onerror="this.outerHTML='<i class=\\'fas fa-bell\\'></i>'"/>`;}
  else{pw.innerHTML=`<i class="fas ${icons[selectedType]||'fa-bell'}"></i>`;}
  const prev=_('notifPreview');prev.className='notif-preview';if(selectedType==='ok')prev.classList.add('type-ok');if(selectedType==='err')prev.classList.add('type-err');
}
function switchTab(tab){
  ['send','schedule','history'].forEach(t=>{_('tab-'+t)?.classList.toggle('active',t===tab);});
  _('tabSend').style.display=tab==='send'?'':'none';
  _('tabSchedule').style.display=tab==='schedule'?'':'none';
  _('tabHistory').style.display=tab==='history'?'':'none';
  if(tab==='history')loadHistory();if(tab==='schedule'){initSchedTime();loadSchedule();}
}
async function sendNotif(){
  const title=_('notifTitleInput').value.trim()||'TALASHNY',text=_('notifMsgInput').value.trim();
  if(!text){showToast('اكتب رسالة الأول','err');return;}
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
        <div class="hist-resend" onclick='resendNotif(${JSON.stringify(h)})'><i class="fas fa-rotate-right"></i></div>
      </div>`).join('');
  }catch{}
}
function resendNotif(h){_('notifTitleInput').value=h.title||'TALASHNY';_('notifMsgInput').value=h.text||'';setType(h.type||'info');updatePreview();switchTab('send');showToast('✏️ تم تحميل الإشعار','ok');}
let selectedSchedType='info';
function setSchedType(t){selectedSchedType=t;['info','ok','err'].forEach(x=>{const b=_('stype-'+x);if(!b)return;b.className='type-btn';if(x===t)b.classList.add('active-'+x);});}
function initSchedTime(){const inp=_('schedTimeInput');if(!inp)return;const now=new Date();now.setMinutes(now.getMinutes()+5);inp.value=now.toISOString().slice(0,16);}
function fmtFireAt(ts){try{const d=new Date(parseFloat(ts)*1000);return d.toLocaleDateString('ar-EG',{month:'short',day:'numeric'})+' — '+d.toLocaleTimeString('ar-EG',{hour:'2-digit',minute:'2-digit'});}catch{return '—';}}
async function addSchedule(){
  const title=_('schedTitleInput').value.trim()||'TALASHNY',text=_('schedMsgInput').value.trim(),fireVal=_('schedTimeInput').value,link=_('schedLinkInput').value.trim();
  if(!text){showToast('اكتب نص الإشعار','err');return;}if(!fireVal){showToast('اختار وقت الإرسال','err');return;}
  const fireDate=new Date(fireVal),fireTs=Math.floor(fireDate.getTime()/1000);
  if(fireTs<=Math.floor(Date.now()/1000)){showToast('الوقت لازم يكون في المستقبل','err');return;}
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
    const items=d.items||[];
    if(!items.length){wrap.innerHTML='<div class="hist-empty">لا توجد إشعارات مجدولة</div>';return;}
    wrap.innerHTML=items.map(s=>`
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

# ─── ROUTES ─────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(PAGE)

# ✅ endpoint الـ ping الجديد — القلب الحقيقي للعداد
@app.route("/ping", methods=["POST"])
def ping():
    try:
        data = request.get_json(silent=True) or {}
        uid  = data.get("uid", "")
        if uid:
            ping_user(uid)
    except:
        pass
    return jsonify({"ok": True, "online": get_online_count()})

# ✅ endpoint اجلب عدد المتصلين بدون اي حاجة تانية
@app.route("/online-count")
def online_count():
    return jsonify({"ok": True, "count": get_online_count()})

@app.route("/broadcast-poll")
def broadcast_poll():
    check_schedule_and_fire()
    return jsonify({"broadcast": read_broadcast()})

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
    return jsonify({
        "ok":     True,
        "online": get_online_count(),   # ← العدد الحقيقي
        "today":  count,
        "views":  views
    })

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
    app.run(host="0.0.0.0", port=5000, debug=False)
