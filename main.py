from flask import Flask, request, session, jsonify, redirect, render_template_string
import requests as req
import urllib3
import time
import threading

urllib3.disable_warnings()

app = Flask(__name__)
app.secret_key = 'talashny_vf_2025_xsecret'

# ── CONNECTED USERS TRACKER ──
_presence = {}
_lock = threading.Lock()

def _ping_user(sid):
    with _lock:
        _presence[sid] = time.time()

def _get_count():
    with _lock:
        now = time.time()
        return sum(1 for v in _presence.values() if now - v < 20)

def _cleanup():
    while True:
        now = time.time()
        with _lock:
            dead = [k for k, v in _presence.items() if now - v > 25]
            for k in dead:
                del _presence[k]
        time.sleep(5)

threading.Thread(target=_cleanup, daemon=True).start()

# ── VODAFONE HELPERS ──
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

def login_password(number, password):
    try:
        r = req.post(
            "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token",
            data={
                'grant_type': 'password', 'username': number, 'password': password,
                'client_secret': '95fd95fb-7489-4958-8ae6-d31a525cd20a',
                'client_id': 'ana-vodafone-app',
            },
            headers={**_VF_HDRS, "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
            timeout=15, verify=False
        )
        return r.json()
    except:
        return {}

def get_promos(token, number):
    try:
        url = f"https://web.vodafone.com.eg/services/dxl/ramadanpromo/promotion?@type=RamadanHub&channel=website&msisdn={number}"
        r = req.get(url, headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/133.0.0.0 Mobile Safari/537.36",
            "Accept": "application/json", "clientId": "WebsiteConsumer", "api-host": "PromotionHost",
            "channel": "WEB", "Accept-Language": "ar", "msisdn": number,
            "Content-Type": "application/json", "Referer": "https://web.vodafone.com.eg/ar/ramadan",
        }, timeout=15, verify=False)
        data = r.json()
    except:
        return []
    cards = []
    if not isinstance(data, list):
        return cards
    for item in data:
        if not isinstance(item, dict) or 'pattern' not in item:
            continue
        for pat in item.get('pattern', []):
            for act in pat.get('action', []):
                c = {ch['name']: str(ch['value']) for ch in act.get('characteristics', [])}
                if not c:
                    continue
                serial = c.get('CARD_SERIAL', '').strip()
                if len(serial) != 13:
                    continue
                cards.append({
                    'serial': serial,
                    'gift': int(c.get('GIFT_UNITS', 0)),
                    'amount': int(c.get('amount', 0)),
                    'remaining': int(c.get('REMAINING_DEDICATIONS', 0)),
                })
    cards.sort(key=lambda x: x['gift'], reverse=True)
    return cards

def redeem_card(token, number, serial):
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
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/133.0.0.0 Mobile Safari/537.36",
                "clientId": "WebsiteConsumer", "channel": "WEB", "msisdn": number,
                "Accept-Language": "AR", "Origin": "https://web.vodafone.com.eg",
                "Referer": "https://web.vodafone.com.eg/portal/hub",
            },
            timeout=15, verify=False
        )
        return r.status_code
    except:
        return 500

# ── ROUTES ──
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.args.get('logout'):
        session.clear()
        return redirect('/')

    error = ''
    if request.method == 'POST':
        number = request.form.get('number', '').strip()
        password = request.form.get('password', '').strip()
        if number and password:
            res = login_password(number, password)
            if res.get('access_token'):
                session['logged_in'] = True
                session['token'] = res['access_token']
                session['token_exp'] = int(time.time()) + int(res.get('expires_in', 3600)) - 120
                session['number'] = number
                session['password'] = password
                return redirect('/')
            else:
                error = 'الرقم أو الباسورد غلط، حاول تاني'
        else:
            error = 'من فضلك ادخل الرقم والباسورد'

    return render_template_string(
        TEMPLATE,
        error=error,
        logged_in=session.get('logged_in', False),
        number=session.get('number', '')
    )

@app.route('/ping')
def ping():
    sid = request.args.get('sid', request.remote_addr)
    _ping_user(sid)
    return jsonify({'count': _get_count()})

@app.route('/fetch')
def fetch():
    if not session.get('logged_in'):
        return jsonify({'success': False})
    sid = request.args.get('sid', request.remote_addr)
    _ping_user(sid)
    if int(time.time()) >= session.get('token_exp', 0):
        res = login_password(session['number'], session['password'])
        if res.get('access_token'):
            session['token'] = res['access_token']
            session['token_exp'] = int(time.time()) + int(res.get('expires_in', 3600)) - 120
    cards = get_promos(session['token'], session['number'])
    return jsonify({'success': True, 'promos': cards, 'number': session['number'], 'active': _get_count()})

@app.route('/redeem')
def redeem():
    if not session.get('logged_in'):
        return jsonify({'success': False})
    serial = request.args.get('serial', '').strip()
    target = request.args.get('target', session['number'])
    use_token = session['token']
    if target != session['number']:
        tpass = request.args.get('tpass', '').strip()
        if tpass:
            res2 = login_password(target, tpass)
            if res2.get('access_token'):
                use_token = res2['access_token']
    code = redeem_card(use_token, target, serial)
    return jsonify({'success': code == 200, 'code': code})

# ══════════════════════════════════════════════════════
#  HTML TEMPLATE  — نسخة طبق الأصل من الـ PHP
# ══════════════════════════════════════════════════════
TEMPLATE = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no"/>
<title>TALASHNY — فودافون</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=Cairo:wght@400;500;600;700;900&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet"/>
<style>
:root{
  --red:#e60000;--red2:#9a0000;--red-glow:rgba(230,0,0,.25);--red-dim:rgba(230,0,0,.08);
  --g1:#c8a84b;--g2:#f5d070;--g3:#8a6820;--g4:rgba(200,168,75,.12);
  --bg:#07070a;--l1:#0d0d12;--l2:#121217;--l3:#18181f;--l4:#1f1f28;--l5:#26262f;
  --ink:#eeeae0;--ink2:#a09880;--ink3:#504e48;
  --stroke:rgba(200,168,75,.1);--stroke2:rgba(200,168,75,.22);
  --r:20px;--r-sm:13px;--r-xs:9px;
  --spring:cubic-bezier(.34,1.56,.64,1);--ease:cubic-bezier(.4,0,.2,1);
}
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box;}
html{height:100%;-webkit-font-smoothing:antialiased;}
body{
  font-family:'Cairo',sans-serif;background:var(--bg);color:var(--ink);
  min-height:100vh;overflow-x:hidden;touch-action:manipulation;
  background-image:
    radial-gradient(ellipse 70% 35% at 50% 0%,rgba(200,168,75,.13) 0%,rgba(200,168,75,.04) 40%,transparent 70%),
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='300' height='300' filter='url(%23n)' opacity='0.025'/%3E%3C/svg%3E");
}

/* ── BANNER ── */
.banner{position:fixed;top:0;left:0;right:0;height:90px;background:rgba(0,0,0,.97);display:flex;justify-content:center;align-items:center;z-index:1000;border-bottom:1px solid var(--stroke);box-shadow:0 4px 30px rgba(0,0,0,.8);}
.banner-letters{display:flex;gap:0;font-size:2.6rem;font-weight:900;letter-spacing:7px;text-transform:uppercase;}
.banner-letters span{display:inline-block;color:transparent;background:linear-gradient(90deg,#b0b0b0 0%,#fff 20%,#e0e0e0 40%,#fff 60%,#a0a0a0 80%,#c0c0c0 100%);background-size:400% 100%;-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:chrome 4s linear infinite;animation-delay:calc(var(--i)*.18s);}
@keyframes chrome{0%{background-position:400% center}100%{background-position:-400% center}}

/* ── PAGE ── */
.page{max-width:430px;margin:0 auto;padding:0 10px;}
@keyframes up{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:none}}

/* ── SURFACE ── */
.surface{background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r);}

/* ══════════════ LOGIN ══════════════ */
#LOGIN_SCREEN{min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:110px 16px 70px;animation:up .5s var(--spring) both;}
.login-page{width:100%;max-width:390px;display:flex;flex-direction:column;gap:14px;}

.login-brand{display:flex;flex-direction:column;align-items:center;gap:8px;margin-bottom:4px;}
.login-logo{width:52px;height:52px;border-radius:50%;background:linear-gradient(135deg,var(--l3),var(--l5));border:1px solid var(--stroke2);display:flex;align-items:center;justify-content:center;box-shadow:0 0 24px rgba(200,168,75,.15),0 4px 12px rgba(0,0,0,.5);}
.login-logo svg{width:22px;height:22px;fill:none;stroke:var(--g1);stroke-width:1.6;}
.login-eyebrow{font-size:.55rem;font-weight:700;letter-spacing:4px;text-transform:uppercase;color:var(--ink3);}
.login-title{font-family:'Playfair Display',serif;font-size:1.2rem;font-weight:700;color:var(--ink);text-align:center;}
.login-title em{font-style:italic;color:transparent;background:linear-gradient(135deg,var(--g1),var(--g2),var(--g1));-webkit-background-clip:text;-webkit-text-fill-color:transparent;}

/* forms */
.lf-row{display:flex;align-items:stretch;border-bottom:1px solid var(--stroke);position:relative;}
.lf-row:last-of-type{border-bottom:none;}
.lf-row:focus-within{background:rgba(200,168,75,.025);}
.lf-icon{width:48px;flex-shrink:0;display:flex;align-items:center;justify-content:center;border-left:1px solid var(--stroke);background:var(--l2);}
.lf-icon svg{width:16px;height:16px;stroke:var(--ink3);stroke-width:1.6;fill:none;transition:stroke .3s;}
.lf-row:focus-within .lf-icon svg{stroke:var(--g1);}
.lf-body{flex:1;padding:12px 14px;display:flex;flex-direction:column;}
.lf-lbl{font-size:.5rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);margin-bottom:3px;transition:color .3s;}
.lf-row:focus-within .lf-lbl{color:var(--g1);}
.lf-input{background:transparent;border:none;outline:none;font-family:'Cairo',sans-serif;font-size:.93rem;font-weight:600;color:var(--ink);width:100%;}
.lf-input::placeholder{color:var(--ink3);font-weight:400;font-size:.8rem;}
.lf-row::after{content:'';position:absolute;right:0;top:0;bottom:0;width:0;background:var(--g1);transition:width .25s;}
.lf-row:focus-within::after{width:3px;}

/* login btn */
.btn-wrap{padding:14px;}
.btn-login{width:100%;padding:14px;border:none;border-radius:var(--r-sm);background:linear-gradient(135deg,var(--g3),var(--g1),var(--g2));color:#1a0e00;font-family:'Cairo',sans-serif;font-size:.88rem;font-weight:900;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:9px;box-shadow:0 5px 22px rgba(200,168,75,.28),0 2px 8px rgba(0,0,0,.4);transition:transform .2s var(--spring),box-shadow .25s;position:relative;overflow:hidden;}
.btn-login::before{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(255,255,255,.15) 0%,transparent 55%);}
.btn-login::after{content:'';position:absolute;top:0;left:-100%;width:60%;height:100%;background:linear-gradient(105deg,transparent,rgba(255,255,255,.18),transparent);animation:shine 3.5s ease-in-out infinite;}
@keyframes shine{0%,100%{left:-100%}50%{left:150%}}
.btn-login svg{width:15px;height:15px;stroke:currentColor;stroke-width:2.2;fill:none;position:relative;z-index:1;}
.btn-login span{position:relative;z-index:1;}
.btn-login:hover{transform:translateY(-2px);box-shadow:0 9px 30px rgba(200,168,75,.4);}
.btn-login:active{transform:scale(.97);}
.btn-login:disabled{opacity:.5;cursor:wait;}
.btn-spin{width:15px;height:15px;border-radius:50%;border:2px solid rgba(26,14,0,.25);border-top-color:#1a0e00;animation:rotate .7s linear infinite;display:none;position:relative;z-index:1;}
.btn-login.loading .btn-spin{display:block;}
.btn-login.loading .btn-txt{display:none;}
@keyframes rotate{to{transform:rotate(360deg)}}

.error-banner{display:flex;align-items:center;gap:9px;background:rgba(230,0,0,.06);border:1px solid rgba(230,0,0,.2);border-radius:var(--r-xs);padding:11px 14px;font-size:.7rem;color:#ff8a80;font-weight:600;animation:up .3s var(--spring) both;}
.error-banner svg{width:14px;height:14px;stroke:#ff6b6b;stroke-width:2;fill:none;flex-shrink:0;}
.login-note{text-align:center;font-size:.6rem;color:var(--ink3);}

/* ══════════════ APP ══════════════ */
#APP{display:none;}
#APP.active{display:block;}
.app-body{padding-top:110px;padding-bottom:88px;}

/* user pill */
.user-pill{display:flex;align-items:center;justify-content:space-between;padding:10px 14px;margin-bottom:12px;background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r-xs);}
.pill-info{display:flex;align-items:center;gap:8px;}
.pill-dot{width:7px;height:7px;border-radius:50%;background:var(--g1);box-shadow:0 0 6px var(--g2);}
.pill-num{font-family:'JetBrains Mono',monospace;font-size:.8rem;font-weight:700;color:var(--g2);}
.btn-logout{display:flex;align-items:center;gap:5px;background:transparent;border:1px solid rgba(230,0,0,.18);border-radius:var(--r-xs);padding:5px 12px;font-family:'Cairo',sans-serif;font-size:.65rem;font-weight:700;color:rgba(230,0,0,.5);cursor:pointer;transition:all .2s;text-decoration:none;}
.btn-logout:hover{color:#ff6b6b;border-color:rgba(230,0,0,.4);background:rgba(230,0,0,.05);}
.btn-logout svg{width:11px;height:11px;stroke:currentColor;stroke-width:2;fill:none;}

/* search screen */
#US{display:flex;flex-direction:column;gap:14px;animation:up .5s var(--spring) both;}
.us-head{padding:8px 0 4px;}
.us-eyebrow{display:inline-flex;align-items:center;gap:6px;font-size:.57rem;font-weight:700;letter-spacing:3.5px;text-transform:uppercase;color:var(--g1);opacity:.8;margin-bottom:7px;}
.us-eyebrow i{width:5px;height:5px;border-radius:50%;background:var(--g2);box-shadow:0 0 5px var(--g2);}
.us-title{font-family:'Playfair Display',serif;font-size:1.6rem;font-weight:700;line-height:1.35;margin-bottom:5px;}
.us-title em{font-style:italic;color:transparent;background:linear-gradient(135deg,var(--g1),var(--g2),var(--g1));-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.us-sub{font-size:.75rem;color:var(--ink2);line-height:1.8;}

.us-card{overflow:hidden;}
.card-sect{border-bottom:1px solid var(--stroke);}
.card-sect-head{padding:10px 14px 4px;font-family:'Playfair Display',serif;font-size:.58rem;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:var(--ink3);display:flex;align-items:center;gap:7px;}
.card-sect-head::before{content:'';display:block;width:14px;height:1px;background:linear-gradient(90deg,transparent,var(--g1));}

/* unit field */
.field-row{display:flex;align-items:stretch;position:relative;transition:background .25s;}
.field-row:focus-within{background:rgba(200,168,75,.025);}
.field-icon{width:50px;flex-shrink:0;display:flex;align-items:center;justify-content:center;border-left:1px solid var(--stroke);background:var(--l2);}
.field-icon svg{width:18px;height:18px;stroke:var(--ink3);stroke-width:1.6;fill:none;transition:stroke .3s;}
.field-row:focus-within .field-icon svg{stroke:var(--g1);}
.field-right{flex:1;padding:14px 0;display:flex;flex-direction:column;align-items:center;}
.field-lbl{font-family:'Playfair Display',serif;font-size:.58rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);margin-bottom:4px;transition:color .3s;}
.field-row:focus-within .field-lbl{color:var(--g1);}
.field-input{background:transparent;border:none;outline:none;font-family:'Playfair Display',serif;font-size:1.9rem;font-weight:700;color:var(--ink);text-align:center;max-width:160px;}
.field-input::placeholder{font-family:'Cairo',sans-serif;color:var(--ink3);font-size:.85rem;font-weight:400;}
.field-row::after{content:'';position:absolute;right:0;top:0;bottom:0;width:0;background:var(--g1);transition:width .25s;}
.field-row:focus-within::after{width:3px;}

/* quick chips */
.quick-section{padding:12px 16px 14px;border-bottom:1px solid var(--stroke);}
.quick-lbl{font-size:.57rem;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:var(--ink3);margin-bottom:10px;display:flex;align-items:center;gap:7px;}
.quick-lbl::before{content:'';display:block;width:12px;height:1px;background:linear-gradient(90deg,transparent,var(--g1));}
.quick-chips{display:flex;gap:6px;}
.chip{flex:1;padding:9px 4px;background:var(--l2);border:1px solid var(--stroke);border-radius:var(--r-xs);text-align:center;font-family:'Playfair Display',serif;font-size:.88rem;font-weight:700;color:var(--ink2);cursor:pointer;transition:all .2s var(--spring);}
.chip:hover{border-color:var(--stroke2);color:var(--g2);}
.chip.sel{background:var(--g4);border-color:rgba(200,168,75,.45);color:var(--g2);}
.chip:active{transform:scale(.9);}

/* charge mode */
.charge-mode-section{padding:14px 16px;border-bottom:1px solid var(--stroke);}
.charge-mode-lbl{font-size:.57rem;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:var(--ink3);margin-bottom:10px;display:flex;align-items:center;gap:7px;}
.charge-mode-lbl::before{content:'';display:block;width:12px;height:1px;background:linear-gradient(90deg,transparent,var(--g1));}
.cm-btns{display:flex;gap:8px;}
.cm-btn{flex:1;padding:14px 8px;background:var(--l2);border:1px solid var(--stroke);border-radius:var(--r-sm);text-align:center;cursor:pointer;transition:all .2s var(--spring);}
.cm-btn.sel{background:rgba(230,0,0,.06);border-color:rgba(230,0,0,.35);}
.cm-btn:active{transform:scale(.96);}
.cm-btn-icon{width:28px;height:28px;margin:0 auto 7px;border-radius:50%;display:flex;align-items:center;justify-content:center;}
.cm-btn-icon svg{width:16px;height:16px;stroke-width:1.8;fill:none;}
.cm-btn.online .cm-btn-icon{background:rgba(230,0,0,.1);border:1px solid rgba(230,0,0,.2);}
.cm-btn.online .cm-btn-icon svg{stroke:var(--red);}
.cm-btn.dial .cm-btn-icon{background:rgba(200,168,75,.1);border:1px solid rgba(200,168,75,.2);}
.cm-btn.dial .cm-btn-icon svg{stroke:var(--g2);}
.cm-btn strong{display:block;font-family:'Cairo',sans-serif;font-size:.75rem;font-weight:700;color:var(--ink);margin-bottom:3px;}
.cm-btn small{font-size:.6rem;color:var(--ink3);}

/* online target */
.online-target-section{padding:0 16px;max-height:0;overflow:hidden;transition:max-height .35s var(--ease),padding .35s;}
.online-target-section.open{max-height:220px;padding:14px 16px;}
.ot-lbl{font-size:.57rem;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:var(--ink3);margin-bottom:10px;display:flex;align-items:center;gap:7px;}
.ot-lbl::before{content:'';display:block;width:12px;height:1px;background:linear-gradient(90deg,transparent,var(--g1));}
.ot-btns{display:flex;gap:7px;}
.ot-btn{flex:1;padding:10px 7px;background:var(--l2);border:1px solid var(--stroke);border-radius:var(--r-xs);text-align:center;font-family:'Cairo',sans-serif;font-size:.7rem;font-weight:700;color:var(--ink2);cursor:pointer;transition:all .2s var(--spring);}
.ot-btn.sel{background:var(--g4);border-color:rgba(200,168,75,.4);color:var(--g2);}
.ot-btn:active{transform:scale(.93);}
.other-num-form{margin-top:10px;display:none;flex-direction:column;gap:6px;}
.other-num-form.visible{display:flex;}
.ofield{display:flex;align-items:stretch;border:1px solid var(--stroke);border-radius:var(--r-xs);overflow:hidden;}
.ofield-icon{width:40px;display:flex;align-items:center;justify-content:center;background:var(--l2);border-left:1px solid var(--stroke);}
.ofield-icon svg{width:14px;height:14px;stroke:var(--ink3);stroke-width:1.6;fill:none;}
.ofield input{flex:1;background:transparent;border:none;outline:none;padding:10px 12px;font-family:'Cairo',sans-serif;font-size:.85rem;font-weight:600;color:var(--ink);}
.ofield input::placeholder{color:var(--ink3);font-weight:400;font-size:.78rem;}

/* GO btn */
.go-section{padding:16px;}
.btn-go{width:100%;padding:16px;border:none;border-radius:var(--r-sm);background:linear-gradient(135deg,var(--red2),var(--red),#ff1a1a);color:#fff;font-family:'Cairo',sans-serif;font-size:.9rem;font-weight:900;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:9px;box-shadow:0 6px 28px rgba(230,0,0,.35),0 2px 8px rgba(0,0,0,.5);transition:transform .2s var(--spring),box-shadow .25s;position:relative;overflow:hidden;}
.btn-go::before{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(255,255,255,.12) 0%,transparent 50%);}
.btn-go::after{content:'';position:absolute;top:0;left:-100%;width:60%;height:100%;background:linear-gradient(105deg,transparent,rgba(255,255,255,.1),transparent);animation:shine 3.5s ease-in-out infinite;}
.btn-go svg{width:17px;height:17px;stroke:#fff;stroke-width:2.2;fill:none;position:relative;z-index:1;}
.btn-go span{position:relative;z-index:1;}
.btn-go:hover{transform:translateY(-2px);box-shadow:0 10px 36px rgba(230,0,0,.45);}
.btn-go:active{transform:scale(.97);}

/* ══════ CARDS SCREEN ══════ */
#CS{display:none;flex-direction:column;gap:11px;animation:up .4s var(--spring) both;}
.cs-top{display:flex;align-items:center;justify-content:space-between;padding:12px 16px;}
.cs-info{font-family:'Playfair Display',serif;font-size:.8rem;color:var(--ink2);}
.cs-info strong{color:var(--g2);}
.cs-back{display:flex;align-items:center;gap:5px;background:var(--l3);border:1px solid var(--stroke);border-radius:var(--r-xs);padding:7px 14px;font-family:'Cairo',sans-serif;font-size:.7rem;font-weight:700;color:var(--ink2);cursor:pointer;transition:all .2s;}
.cs-back:hover{color:var(--ink);border-color:var(--stroke2);}
.cs-back svg{width:11px;height:11px;stroke:currentColor;stroke-width:2.5;fill:none;}

/* timer — الجديد: عداد الثواني في النص مع عداد المتصلين تحته */
.timer-wrap{padding:16px 18px;}
.timer-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:11px;}
.timer-left{display:flex;align-items:center;gap:9px;}
.timer-dot{width:7px;height:7px;border-radius:50%;background:var(--red);box-shadow:0 0 0 0 var(--red-glow);animation:ping 1.4s ease-in-out infinite;}
@keyframes ping{0%{box-shadow:0 0 0 0 var(--red-glow)}70%{box-shadow:0 0 0 8px rgba(230,0,0,0)}100%{box-shadow:0 0 0 0 transparent}}
.timer-text{font-family:'Playfair Display',serif;font-size:.7rem;font-weight:700;color:var(--ink2);}

/* الوسط: الثواني + المتصلين مرصوصين فوق بعض */
.timer-center{display:flex;flex-direction:column;align-items:center;gap:4px;}
.timer-count{font-family:'Playfair Display',serif;font-size:2rem;font-weight:700;color:var(--ink);transition:color .3s;font-variant-numeric:tabular-nums;line-height:1;}
.timer-count.hot{color:var(--red);}
/* badge المتصلين — تحت الرقم مباشرة */
.users-online-badge{
  display:inline-flex;align-items:center;gap:5px;
  background:rgba(200,168,75,.07);
  border:1px solid rgba(200,168,75,.18);
  border-radius:20px;padding:3px 10px;
}
.uob-dot{width:5px;height:5px;border-radius:50%;background:var(--g2);box-shadow:0 0 4px var(--g2);animation:uobPulse 2s ease-in-out infinite;}
@keyframes uobPulse{0%,100%{opacity:1}50%{opacity:.4}}
.uob-count{font-family:'JetBrains Mono',monospace;font-size:.65rem;font-weight:700;color:var(--g2);}
.uob-lbl{font-size:.52rem;font-weight:700;color:var(--ink3);letter-spacing:.5px;}

.timer-bar{height:3px;background:var(--l5);border-radius:4px;overflow:hidden;}
.timer-prog{height:100%;border-radius:4px;background:linear-gradient(90deg,var(--g3),var(--g1),var(--g2));transition:width 1s linear;box-shadow:0 0 8px rgba(200,168,75,.3);}

/* continue toggle */
.tgl-row{display:flex;align-items:center;justify-content:space-between;padding:13px 16px;cursor:pointer;}
.tgl-txt strong{display:block;font-family:'Playfair Display',serif;font-size:.77rem;font-weight:700;color:var(--ink);margin-bottom:2px;}
.tgl-txt small{font-size:.62rem;color:var(--ink2);}
.sw{position:relative;width:42px;height:24px;flex-shrink:0;}
.sw input{opacity:0;width:0;height:0;position:absolute;}
.sw-track{position:absolute;inset:0;border-radius:30px;background:var(--l4);border:1px solid var(--stroke);cursor:pointer;transition:all .3s;}
.sw-track::before{content:'';position:absolute;width:18px;height:18px;border-radius:50%;background:#888;top:2px;right:2px;box-shadow:0 1px 4px rgba(0,0,0,.5);transition:transform .3s var(--spring),background .3s;}
.sw input:checked+.sw-track{background:linear-gradient(135deg,var(--g3),var(--g1));border-color:rgba(200,168,75,.35);}
.sw input:checked+.sw-track::before{transform:translateX(-18px);background:#fff;}

/* ═══ CARDS ═══ */
.cards-list{display:flex;flex-direction:column;gap:10px;}
.pc{border-radius:var(--r);overflow:visible;position:relative;animation:cardIn .45s var(--spring) both;animation-delay:calc(var(--i,0)*.07s);}
@keyframes cardIn{from{opacity:0;transform:translateY(10px) scale(.97)}to{opacity:1;transform:none}}

/* الحدود الخارجية */
.pc::after{content:'';position:absolute;inset:-1px;border-radius:calc(var(--r) + 1px);border:1px solid rgba(200,168,75,.28);pointer-events:none;z-index:10;}
.pc.best::after{border:1.5px solid rgba(200,168,75,.65);box-shadow:0 0 14px rgba(200,168,75,.18);}
/* الخط الذهبي العلوي للأفضل */
.pc.best::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;z-index:11;border-radius:var(--r) var(--r) 0 0;background:linear-gradient(90deg,transparent 5%,var(--g3) 20%,var(--g2) 50%,var(--g3) 80%,transparent 95%);}

.pc-bg{position:absolute;inset:0;background:linear-gradient(150deg,rgba(5,5,10,.97) 0%,rgba(10,8,15,.8) 100%);border-radius:var(--r);}
.pc-inner{border-radius:var(--r);overflow:hidden;position:relative;}
.pc-badge{position:absolute;top:13px;left:13px;z-index:4;font-size:.52rem;font-weight:900;letter-spacing:1.5px;text-transform:uppercase;padding:3px 10px;border-radius:5px;color:#1a0e00;background:linear-gradient(135deg,var(--g2),var(--g1));box-shadow:0 2px 10px rgba(200,168,75,.35);}

.pc-content{position:relative;z-index:2;padding:10px 12px 11px;}
.pc-stats{display:flex;align-items:center;justify-content:center;gap:0;margin-bottom:9px;}
.pc.best .pc-stats{padding-top:12px;}
.pc-stat{flex:1;display:flex;flex-direction:column;align-items:center;gap:1px;padding:0 4px;}
.pc-stat:not(:last-child){border-left:1px solid rgba(255,255,255,.07);}
.pc-stat-icon svg{width:12px;height:12px;fill:none;stroke-width:1.8;}
.ic-amt svg{stroke:#ff8a80;}.ic-gift svg{stroke:var(--g2);}.ic-rem svg{stroke:#82b1ff;}
.pc-stat-val{font-family:'Playfair Display',serif;font-size:.82rem;font-weight:700;color:#fff;line-height:1;margin-top:1px;}
.pc-stat-lbl{font-size:.48rem;color:rgba(255,255,255,.28);}

.pc-serial-wrap{display:flex;justify-content:center;margin-bottom:8px;}
.pc-serial{display:inline-flex;align-items:center;gap:8px;background:rgba(0,0,0,.38);border-radius:8px;padding:6px 8px 6px 10px;border:1px solid rgba(200,168,75,.12);}
.serial-num{font-family:'JetBrains Mono',monospace;font-size:.88rem;font-weight:700;color:#fff;letter-spacing:2px;white-space:nowrap;}
.serial-copy{width:25px;height:25px;border-radius:6px;border:1px solid rgba(200,168,75,.15);background:rgba(200,168,75,.05);display:flex;align-items:center;justify-content:center;cursor:pointer;transition:all .2s var(--spring);}
.serial-copy svg{width:11px;height:11px;stroke:rgba(200,168,75,.4);stroke-width:2;fill:none;}
.serial-copy:hover{background:rgba(200,168,75,.14);border-color:rgba(200,168,75,.38);}
.serial-copy:active{transform:scale(.86);}

.pc-action{display:flex;align-items:center;justify-content:center;gap:8px;flex-wrap:wrap;}
.btn-online-charge{display:none;align-items:center;gap:6px;padding:7px 16px;background:rgba(230,0,0,.1);border:1px solid rgba(230,0,0,.28);border-radius:20px;font-family:'Cairo',sans-serif;font-size:.72rem;font-weight:700;color:#ff8a80;cursor:pointer;transition:all .2s var(--spring);}
.btn-online-charge svg{width:11px;height:11px;stroke:currentColor;stroke-width:2;fill:none;}
.btn-online-charge:hover{background:rgba(230,0,0,.18);border-color:rgba(230,0,0,.45);}
.btn-online-charge.loading{opacity:.6;pointer-events:none;}
.btn-dial-link{display:none;align-items:center;gap:6px;text-decoration:none;color:rgba(200,168,75,.5);font-family:'Cairo',sans-serif;font-size:.72rem;font-weight:700;padding:7px 16px;border:1px solid rgba(200,168,75,.12);border-radius:20px;background:rgba(200,168,75,.04);transition:all .2s;}
.btn-dial-link svg{width:11px;height:11px;stroke:currentColor;stroke-width:2;fill:none;}
.btn-dial-link:hover{color:rgba(200,168,75,.8);border-color:rgba(200,168,75,.3);}

/* toast */
.toast{position:fixed;bottom:96px;left:50%;transform:translateX(-50%) translateY(20px);background:rgba(15,15,20,.97);border:1px solid var(--stroke);border-radius:30px;padding:10px 20px;font-family:'Cairo',sans-serif;font-size:.75rem;font-weight:700;color:var(--ink);opacity:0;pointer-events:none;transition:all .3s var(--spring);z-index:999;white-space:nowrap;}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0);}
.toast.ok{border-color:rgba(0,200,100,.3);color:#4cff9a;}
.toast.err{border-color:rgba(230,0,0,.3);color:#ff8a80;}

/* loading / empty */
.loading-wrap{display:flex;flex-direction:column;align-items:center;gap:12px;padding:48px 20px;animation:up .35s var(--spring) both;}
.spin{width:30px;height:30px;border-radius:50%;border:2px solid rgba(200,168,75,.1);border-top-color:var(--g1);animation:rotate .8s linear infinite;}
.spin-lbl{font-family:'Playfair Display',serif;font-size:.73rem;color:var(--ink2);font-weight:700;}
.empty-wrap{text-align:center;padding:36px 20px;font-family:'Playfair Display',serif;font-size:.8rem;color:var(--ink2);line-height:2;}
.empty-wrap svg{width:26px;height:26px;stroke:var(--ink3);stroke-width:1.5;fill:none;margin-bottom:10px;}

/* NAV */
.bnav{position:fixed;bottom:0;left:0;right:0;z-index:200;display:flex;justify-content:space-around;align-items:center;padding:10px 0 18px;background:rgba(7,7,10,.97);backdrop-filter:blur(28px);border-top:1px solid var(--stroke);}
.bnav a{text-decoration:none;color:var(--ink3);display:flex;flex-direction:column;align-items:center;padding:6px 20px;border-radius:12px;transition:color .2s,transform .25s var(--spring);}
.bnav a:hover{color:var(--g1);transform:translateY(-3px);}
.bnav a svg{width:22px;height:22px;stroke:currentColor;stroke-width:1.6;fill:none;}
::-webkit-scrollbar{width:4px;}::-webkit-scrollbar-track{background:var(--l1);}::-webkit-scrollbar-thumb{background:var(--l5);border-radius:4px;}
</style>
</head>
<body oncontextmenu="return false;">

<!-- BANNER -->
<div class="banner">
  <div class="banner-letters">
    <span style="--i:0">Y</span><span style="--i:1">N</span><span style="--i:2">H</span>
    <span style="--i:3">S</span><span style="--i:4">A</span><span style="--i:5">L</span>
    <span style="--i:6">A</span><span style="--i:7">T</span>
  </div>
</div>

{% if not logged_in %}
<!-- ══ LOGIN ══ -->
<div id="LOGIN_SCREEN">
  <div class="login-page">
    <div class="login-brand">
      <div class="login-logo">
        <svg viewBox="0 0 24 24"><polyline points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
      </div>
      <div class="login-eyebrow">Premium Access</div>
      <div class="login-title">أهلاً في <em>TALASHNY</em></div>
    </div>

    {% if error %}
    <div class="error-banner">
      <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
      {{ error }}
    </div>
    {% endif %}

    <form method="POST" id="LOGIN_FORM">
      <div class="surface">
        <div class="lf-row">
          <div class="lf-icon">
            <svg viewBox="0 0 24 24"><rect x="5" y="2" width="14" height="20" rx="2"/><circle cx="12" cy="17" r="1" fill="currentColor" stroke="none"/></svg>
          </div>
          <div class="lf-body">
            <span class="lf-lbl">رقم الموبايل</span>
            <input class="lf-input" type="tel" name="number" placeholder="01XXXXXXXXX" inputmode="tel" autocomplete="tel" required value="{{ request.form.get('number', '') }}">
          </div>
        </div>
        <div class="lf-row">
          <div class="lf-icon">
            <svg viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
          </div>
          <div class="lf-body">
            <span class="lf-lbl">الباسورد</span>
            <input class="lf-input" type="password" name="password" placeholder="••••••••" autocomplete="current-password" required>
          </div>
        </div>
        <div class="btn-wrap">
          <button type="submit" class="btn-login" id="BTN_LOGIN">
            <svg viewBox="0 0 24 24"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>
            <span class="btn-txt">دخـول</span>
            <div class="btn-spin"></div>
          </button>
        </div>
      </div>
    </form>

    <div class="login-note">بياناتك محمية ومش بتتحفظ على السيرفر</div>
  </div>
</div>

{% else %}
<!-- ══ APP ══ -->
<div id="APP" class="active">
  <div class="app-body">
    <div class="page">

      <!-- SEARCH -->
      <div id="US">
        <div class="us-head">
          <div class="us-eyebrow"><i></i>Premium<i></i></div>
          <div class="us-title">ابحث عن<br><em>ㅤأنسب كارت</em></div>
          <div class="us-sub">حدد الوحدات المطلوبة وطريقة الشحن</div>
        </div>

        <div class="user-pill">
          <div class="pill-info">
            <div class="pill-dot"></div>
            <span class="pill-num">{{ number }}</span>
          </div>
          <a href="/?logout=1" class="btn-logout">
            <svg viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
            خروج
          </a>
        </div>

        <div class="surface us-card">
          <div class="card-sect">
            <div class="card-sect-head">فئة الكارت (وحدات)</div>
            <div class="field-row">
              <div class="field-icon">
                <svg viewBox="0 0 24 24"><polyline points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
              </div>
              <div class="field-right">
                <span class="field-lbl">الحد الأدنى</span>
                <input class="field-input" type="number" id="UI" placeholder="عدد الوحدات" min="1" inputmode="numeric" autofocus>
              </div>
            </div>
            <div class="quick-section" style="border-bottom:none;">
              <div class="quick-lbl">اختيار سريع</div>
              <div class="quick-chips">
                <button class="chip" onclick="setU(100,this)">100</button>
                <button class="chip" onclick="setU(300,this)">300</button>
                <button class="chip" onclick="setU(500,this)">500</button>
                <button class="chip" onclick="setU(700,this)">700</button>
                <button class="chip" onclick="setU(900,this)">900</button>
              </div>
            </div>
          </div>

          <div class="charge-mode-section card-sect">
            <div class="charge-mode-lbl">طريقة الشحن</div>
            <div class="cm-btns">
              <div class="cm-btn online sel" id="CM_ONLINE" onclick="setMode('online')">
                <div class="cm-btn-icon">
                  <svg viewBox="0 0 24 24"><polyline points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                </div>
                <strong>شحن أونلاين</strong>
                <small>شحن تلقائي مباشر</small>
              </div>
              <div class="cm-btn dial" id="CM_DIAL" onclick="setMode('dial')">
                <div class="cm-btn-icon">
                  <svg viewBox="0 0 24 24"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 13a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 2.24h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 9.91a16 16 0 0 0 6.09 6.09l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
                </div>
                <strong>شحن عادي</strong>
                <small>عبر لوحة الاتصال</small>
              </div>
            </div>
          </div>

          <div class="online-target-section open card-sect" id="OT_SECTION">
            <div class="ot-lbl">شحن على رقم</div>
            <div class="ot-btns">
              <div class="ot-btn sel" id="OT_MINE" onclick="setTarget('mine')">رقمي</div>
              <div class="ot-btn" id="OT_OTHER" onclick="setTarget('other')">رقم تاني</div>
            </div>
            <div class="other-num-form" id="OTHER_FORM">
              <div class="ofield">
                <div class="ofield-icon"><svg viewBox="0 0 24 24"><rect x="5" y="2" width="14" height="20" rx="2"/></svg></div>
                <input type="tel" id="OT_NUM" placeholder="رقم التاني 01XXXXXXXXX" inputmode="tel">
              </div>
              <div class="ofield">
                <div class="ofield-icon"><svg viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg></div>
                <input type="password" id="OT_PASS" placeholder="باسورد الرقم التاني">
              </div>
            </div>
          </div>

          <div class="go-section">
            <button class="btn-go" onclick="startApp()">
              <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <span>ابدأ البحث</span>
            </button>
          </div>
        </div>
      </div>

      <!-- CARDS SCREEN -->
      <div id="CS">
        <div class="surface cs-top">
          <div class="cs-info">بحث عن <strong id="IU">—</strong></div>
          <button class="cs-back" onclick="goBack()">
            <svg viewBox="0 0 24 24"><polyline points="9 18 15 12 9 6"/></svg>
            تغيير
          </button>
        </div>

        <div class="surface timer-wrap">
          <div class="timer-header">
            <div class="timer-left">
              <div class="timer-dot"></div>
              <span class="timer-text">جاري التحديث</span>
            </div>
            <!-- الوسط: الثواني فوق + المتصلين تحت -->
            <div class="timer-center">
              <span class="timer-count" id="TN">—</span>
              <div class="users-online-badge">
                <div class="uob-dot"></div>
                <span class="uob-count" id="UC">—</span>
                <span class="uob-lbl">متصل</span>
              </div>
            </div>
          </div>
          <div class="timer-bar"><div class="timer-prog" id="TP" style="width:100%"></div></div>
        </div>

        <div class="surface tgl-row" onclick="document.getElementById('CC').click()">
          <div class="tgl-txt">
            <strong>استمرار البحث بعد الشحن</strong>
            <small id="TH">مفعّل — يكمل البحث حتى بعد الشحن</small>
          </div>
          <div class="sw">
            <input type="checkbox" id="CC" checked onchange="onTgl()">
            <div class="sw-track"></div>
          </div>
        </div>

        <div id="CP"></div>
      </div>

    </div>
  </div>
</div>
{% endif %}

<!-- NAV -->
<nav class="bnav">
  <a href="https://t.me/FY_TF" target="_blank">
    <svg viewBox="0 0 24 24"><path d="M21.5 2.5L2.5 10.5l7 2.5 2.5 7 3-4.5 4.5 3.5 2-16z"/></svg>
  </a>
  <a href="https://wa.me/message/U6AIKBGFCNCQK1" target="_blank">
    <svg viewBox="0 0 24 24"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
  </a>
  <a href="https://www.facebook.com/VI808IV" target="_blank">
    <svg viewBox="0 0 24 24"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/></svg>
  </a>
</nav>

<div class="toast" id="TOAST"></div>

<script>
// ── utils ──
function showToast(msg, type=''){
  const t=document.getElementById('TOAST');
  t.textContent=msg;t.className='toast show'+(type?' '+type:'');
  clearTimeout(t._t);t._t=setTimeout(()=>t.classList.remove('show'),2800);
}

document.getElementById('LOGIN_FORM')?.addEventListener('submit',function(){
  const btn=document.getElementById('BTN_LOGIN');
  if(btn){btn.classList.add('loading');btn.disabled=true;}
});

{% if logged_in %}
// ── STATE ──
const SECS=7;
const SID=Math.random().toString(36).slice(2)+Date.now().toString(36);
let units=0,chargeMode='online',targetMode='mine';
let running=false,stop=false,ti=null,ct=null,charged=false;

// ── PRESENCE PING ──
function pingPresence(){
  fetch('/ping?sid='+SID).then(r=>r.json()).then(d=>{
    const el=document.getElementById('UC');
    if(el) el.textContent=d.count;
  }).catch(()=>{});
}
pingPresence();
setInterval(pingPresence, 8000);

function onTgl(){
  const on=document.getElementById('CC').checked;
  document.getElementById('TH').textContent=on?'مفعّل — يكمل البحث حتى بعد الشحن':'معطّل — يتوقف بعد أول كارت مناسب';
}
function setU(n,b){
  document.getElementById('UI').value=n;
  document.querySelectorAll('.chip').forEach(x=>x.classList.remove('sel'));
  b.classList.add('sel');
}
function setMode(mode){
  chargeMode=mode;
  document.getElementById('CM_ONLINE').classList.toggle('sel',mode==='online');
  document.getElementById('CM_DIAL').classList.toggle('sel',mode==='dial');
  document.getElementById('OT_SECTION').classList.toggle('open',mode==='online');
}
function setTarget(t){
  targetMode=t;
  document.getElementById('OT_MINE').classList.toggle('sel',t==='mine');
  document.getElementById('OT_OTHER').classList.toggle('sel',t==='other');
  document.getElementById('OTHER_FORM').classList.toggle('visible',t==='other');
}
function startApp(){
  const v=parseInt(document.getElementById('UI').value)||0;
  if(v<1){
    const inp=document.getElementById('UI');inp.focus();
    inp.closest('.field-row').style.background='rgba(230,0,0,.06)';
    setTimeout(()=>inp.closest('.field-row').style.background='',900);
    return;
  }
  if(chargeMode==='online'&&targetMode==='other'){
    const on=document.getElementById('OT_NUM').value.trim();
    const op=document.getElementById('OT_PASS').value.trim();
    if(!on||!op){showToast('ادخل رقم وباسورد الرقم التاني','err');return;}
  }
  units=v;stop=false;charged=false;
  document.getElementById('IU').textContent=v+' وحدة';
  document.getElementById('US').style.display='none';
  document.getElementById('CS').style.display='flex';
  runCycle();
}
function goBack(){
  stop=true;clearInterval(ti);clearTimeout(ct);stopTimer();
  document.getElementById('CS').style.display='none';
  document.getElementById('US').style.display='flex';
  document.getElementById('CP').innerHTML='';
  running=false;
}
function startTimer(s){
  return new Promise(res=>{
    clearInterval(ti);let r=s;updTimer(r,s);
    ti=setInterval(()=>{r--;updTimer(r,s);if(r<=0){clearInterval(ti);res();}},1000);
    ct=setTimeout(res,s*1000+200);
  });
}
function updTimer(r,t){
  const n=document.getElementById('TN'),p=document.getElementById('TP');
  if(!n||!p)return;
  n.textContent=Math.max(r,0);
  p.style.width=Math.max(0,r/t*100)+'%';
  n.classList.toggle('hot',r<=2);
}
function stopTimer(){
  clearInterval(ti);
  const n=document.getElementById('TN'),p=document.getElementById('TP');
  if(n)n.textContent='—';if(p)p.style.width='0%';
}
async function fetchCards(){
  try{
    const r=await fetch('/fetch?t='+Date.now()+'&sid='+SID);
    const d=await r.json();
    if(d.active){const el=document.getElementById('UC');if(el)el.textContent=d.active;}
    return d;
  }catch{return{success:false,promos:[]};}
}
function findBest(promos){return promos.find(p=>parseInt(p.gift)>=units)||null;}
async function doOnlineCharge(serial){
  let url='/redeem?serial='+encodeURIComponent(serial);
  if(targetMode==='other'){
    url+='&target='+encodeURIComponent(document.getElementById('OT_NUM').value.trim());
    url+='&tpass='+encodeURIComponent(document.getElementById('OT_PASS').value.trim());
  }
  const btn=document.querySelector('.btn-online-charge[data-serial="'+serial+'"]');
  if(btn)btn.classList.add('loading');
  try{
    const r=await fetch(url);const d=await r.json();
    if(d.success){showToast('✅ تم شحن الكارت بنجاح','ok');charged=true;
      if(!document.getElementById('CC').checked){setTimeout(()=>goBack(),1500);}
    }else{showToast('❌ فشل الشحن — حاول تاني','err');}
  }catch{showToast('❌ خطأ في الاتصال','err');}
  if(btn)btn.classList.remove('loading');
}
function renderCards(data){
  const panel=document.getElementById('CP');
  if(!data?.success||!data.promos?.length){
    if(!panel.querySelector('.cards-list')){
      panel.innerHTML=`<div class="empty-wrap surface"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>لا يوجد كروت مناسبة الآن<br><small style="font-family:Cairo,sans-serif;font-size:.63rem;color:var(--ink3)">جاري البحث...</small></div>`;
    }
    return false;
  }
  const best=findBest(data.promos);
  let html='<div class="cards-list">';
  data.promos.forEach((p,i)=>{
    const isBest=best&&p.serial===best.serial;
    const ussd='*858*'+p.serial.replace(/\s/g,'')+'#';
    const tel='tel:'+encodeURIComponent(ussd);
    html+=`
    <div class="pc${isBest?' best':''}" style="--i:${i}">
      <div class="pc-bg"></div>
      <div class="pc-inner">
        ${isBest?'<div class="pc-badge">✦ أفضل كارت</div>':''}
        <div class="pc-content">
          <div class="pc-stats">
            <div class="pc-stat">
              <div class="pc-stat-icon ic-amt"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 6v12M8 10h6a2 2 0 0 1 0 4H8"/></svg></div>
              <span class="pc-stat-val">${p.amount}</span>
              <span class="pc-stat-lbl">جنيه</span>
            </div>
            <div class="pc-stat">
              <div class="pc-stat-icon ic-gift"><svg viewBox="0 0 24 24"><polyline points="20 12 20 22 4 22 4 12"/><rect x="2" y="7" width="20" height="5"/><path d="M12 22V7M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7zM12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/></svg></div>
              <span class="pc-stat-val">${p.gift}</span>
              <span class="pc-stat-lbl">وحدة</span>
            </div>
            <div class="pc-stat">
              <div class="pc-stat-icon ic-rem"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></div>
              <span class="pc-stat-val">${p.remaining}</span>
              <span class="pc-stat-lbl">متبقي</span>
            </div>
          </div>
          <div class="pc-serial-wrap">
            <div class="pc-serial">
              <span class="serial-num">${p.serial}</span>
              <button class="serial-copy" data-serial="${p.serial}">
                <svg viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
              </button>
            </div>
          </div>
          <div class="pc-action">
            ${isBest&&chargeMode==='online'?`<button class="btn-online-charge" data-serial="${p.serial}" style="display:inline-flex" onclick="doOnlineCharge('${p.serial}')">
              <svg viewBox="0 0 24 24"><polyline points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>شحن أونلاين
            </button>`:''}
            ${isBest&&chargeMode==='dial'?`<a href="${tel}" class="btn-dial-link" style="display:inline-flex;">
              <svg viewBox="0 0 24 24"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 13a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 2.24h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 9.91a16 16 0 0 0 6.09 6.09l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>اتصل للشحن
            </a>`:''}
          </div>
        </div>
      </div>
    </div>`;
  });
  html+='</div>';
  panel.innerHTML=html;

  if(best&&chargeMode==='online'&&!charged){
    setTimeout(()=>doOnlineCharge(best.serial),700);
  }
  if(best&&chargeMode==='dial'){
    const link=document.querySelector('.btn-dial-link');
    if(link&&!charged)setTimeout(()=>link.click(),600);
  }
  return !!best;
}
function showLoading(){
  const panel=document.getElementById('CP');
  if(!panel.querySelector('.cards-list')&&!panel.querySelector('.empty-wrap')){
    panel.innerHTML=`<div class="loading-wrap surface"><div class="spin"></div><div class="spin-lbl">جاري تحديث الكروت</div></div>`;
  }
}
async function runCycle(){
  if(running)return;running=true;
  while(!stop){
    showLoading();
    const d=await fetchCards();
    if(stop)break;
    const found=renderCards(d);
    if(found&&!document.getElementById('CC').checked){end();return;}
    await startTimer(SECS);
    if(stop)break;
  }
  end();
}
function end(){running=false;stopTimer();}

// ── copy serial ──
document.addEventListener('click',e=>{
  const btn=e.target.closest('.serial-copy');
  if(!btn)return;
  const serial=btn.dataset.serial;
  const flash=()=>{
    btn.style.background='rgba(200,168,75,.2)';btn.style.borderColor='rgba(200,168,75,.55)';
    btn.innerHTML=`<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#f5d070" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>`;
    setTimeout(()=>{btn.style.background='';btn.style.borderColor='';btn.innerHTML=`<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="rgba(200,168,75,.4)" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`;},1800);
    showToast('تم نسخ الكود','ok');
  };
  if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(serial).then(flash).catch(()=>fallback());}
  else{fallback();}
  function fallback(){const ta=document.createElement('textarea');ta.value=serial;ta.style.cssText='position:fixed;top:0;left:0;width:1px;height:1px;opacity:0;';document.body.appendChild(ta);ta.focus();ta.select();try{document.execCommand('copy');}catch(ex){}document.body.removeChild(ta);flash();}
});

document.getElementById('UI')?.addEventListener('keydown',e=>{if(e.key==='Enter')startApp();});
{% endif %}
</script>
</body>
</html>"""

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
