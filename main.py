from flask import Flask, request, session, jsonify, redirect, url_for, render_template_string
import requests
import urllib3
import time
import threading

urllib3.disable_warnings()

app = Flask(__name__)
app.secret_key = 'talashny_vf_2025_key'

# ── CONNECTED USERS COUNTER ──
connected_users = {}
connected_lock = threading.Lock()

def update_presence(sid):
    with connected_lock:
        connected_users[sid] = time.time()

def cleanup_presence():
    while True:
        now = time.time()
        with connected_lock:
            to_del = [k for k, v in connected_users.items() if now - v > 20]
            for k in to_del:
                del connected_users[k]
        time.sleep(5)

def get_active_count():
    with connected_lock:
        now = time.time()
        return sum(1 for v in connected_users.values() if now - v < 20)

threading.Thread(target=cleanup_presence, daemon=True).start()

# ── HELPERS ──
HEADERS_BASE = {
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

def login_by_password(number, password):
    try:
        r = requests.post(
            "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token",
            data={
                'grant_type': 'password',
                'username': number,
                'password': password,
                'client_secret': '95fd95fb-7489-4958-8ae6-d31a525cd20a',
                'client_id': 'ana-vodafone-app',
            },
            headers={**HEADERS_BASE, "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
            timeout=15, verify=False
        )
        return r.json()
    except:
        return {}

def get_promos(token, number):
    try:
        url = f"https://web.vodafone.com.eg/services/dxl/ramadanpromo/promotion?@type=RamadanHub&channel=website&msisdn={number}"
        r = requests.get(url, headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/133.0.0.0 Mobile Safari/537.36",
            "Accept": "application/json",
            "clientId": "WebsiteConsumer",
            "api-host": "PromotionHost",
            "channel": "WEB",
            "Accept-Language": "ar",
            "msisdn": number,
            "Content-Type": "application/json",
            "Referer": "https://web.vodafone.com.eg/ar/ramadan",
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
        r = requests.post(
            "https://web.vodafone.com.eg/services/dxl/ramadanpromo/promotion",
            json={
                "@type": "Promo",
                "channel": {"id": "1"},
                "context": {"type": "RamadanRedeemFromHub"},
                "pattern": [{"characteristics": [{"name": "cardSerial", "value": serial}]}],
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/133.0.0.0 Mobile Safari/537.36",
                "clientId": "WebsiteConsumer",
                "channel": "WEB",
                "msisdn": number,
                "Accept-Language": "AR",
                "Origin": "https://web.vodafone.com.eg",
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
    error = ''
    if request.method == 'POST':
        number = request.form.get('number', '').strip()
        password = request.form.get('password', '').strip()
        if number and password:
            res = login_by_password(number, password)
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

    if request.args.get('logout'):
        session.clear()
        return redirect('/')

    return render_template_string(HTML_TEMPLATE, error=error, logged_in=session.get('logged_in'), number=session.get('number', ''))

@app.route('/ping')
def ping():
    sid = request.args.get('sid', request.remote_addr)
    update_presence(sid)
    return jsonify({'count': get_active_count()})

@app.route('/fetch')
def fetch():
    if not session.get('logged_in'):
        return jsonify({'success': False})
    
    sid = request.args.get('sid', request.remote_addr)
    update_presence(sid)

    if int(time.time()) >= session.get('token_exp', 0):
        res = login_by_password(session['number'], session['password'])
        if res.get('access_token'):
            session['token'] = res['access_token']
            session['token_exp'] = int(time.time()) + int(res.get('expires_in', 3600)) - 120

    cards = get_promos(session['token'], session['number'])
    return jsonify({'success': True, 'promos': cards, 'number': session['number'], 'active': get_active_count()})

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
            res2 = login_by_password(target, tpass)
            if res2.get('access_token'):
                use_token = res2['access_token']

    code = redeem_card(use_token, target, serial)
    return jsonify({'success': code == 200, 'code': code})

# ── HTML TEMPLATE ──
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no"/>
<title>TALASHNY — فودافون</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Cairo:wght@400;500;600;700;900&family=JetBrains+Mono:wght@400;500;700&family=Cinzel:wght@400;700;900&display=swap" rel="stylesheet"/>
<style>
:root{
  --red:#e60000;--red2:#7a0000;--red3:#c00;
  --g1:#c8a84b;--g2:#f5d070;--g3:#8a6820;--g4:rgba(200,168,75,.12);
  --bg:#050508;--l1:#0a0a0f;--l2:#0f0f16;--l3:#14141c;--l4:#1a1a24;--l5:#20202c;
  --ink:#f0ede5;--ink2:#9a9080;--ink3:#45433e;
  --stroke:rgba(200,168,75,.08);--stroke2:rgba(200,168,75,.2);--stroke3:rgba(200,168,75,.35);
  --r:18px;--r-sm:12px;--r-xs:8px;
  --spring:cubic-bezier(.34,1.56,.64,1);--ease:cubic-bezier(.4,0,.2,1);
}
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box;}
html{height:100%;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;}
body{
  font-family:'Cairo',sans-serif;background:var(--bg);color:var(--ink);
  min-height:100vh;overflow-x:hidden;touch-action:manipulation;
}
body::before{
  content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background:
    radial-gradient(ellipse 80% 40% at 50% -5%,rgba(200,168,75,.12) 0%,transparent 70%),
    radial-gradient(ellipse 40% 30% at 80% 80%,rgba(230,0,0,.04) 0%,transparent 60%),
    radial-gradient(ellipse 30% 20% at 10% 90%,rgba(200,168,75,.04) 0%,transparent 60%);
}
body::after{
  content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)' opacity='0.022'/%3E%3C/svg%3E");
}

/* ── BANNER ── */
.banner{
  position:fixed;top:0;left:0;right:0;height:88px;z-index:1000;
  background:rgba(5,5,8,.95);backdrop-filter:blur(20px);
  border-bottom:1px solid var(--stroke2);
  display:flex;align-items:center;justify-content:center;
  box-shadow:0 1px 0 rgba(200,168,75,.06),0 8px 40px rgba(0,0,0,.6);
}
.banner-inner{display:flex;align-items:center;gap:14px;}
.banner-logo{
  width:36px;height:36px;border-radius:10px;
  background:linear-gradient(135deg,#1a1208,#2a2010);
  border:1px solid var(--stroke3);
  display:flex;align-items:center;justify-content:center;
  box-shadow:0 0 16px rgba(200,168,75,.15);
}
.banner-logo svg{width:16px;height:16px;stroke:var(--g1);stroke-width:2;fill:none;}
.banner-wordmark{
  font-family:'Bebas Neue',sans-serif;font-size:2.1rem;letter-spacing:8px;
  background:linear-gradient(90deg,var(--g3) 0%,var(--g1) 30%,var(--g2) 50%,var(--g1) 70%,var(--g3) 100%);
  background-size:300% 100%;-webkit-background-clip:text;-webkit-text-fill-color:transparent;
  animation:goldShimmer 4s linear infinite;
}
@keyframes goldShimmer{0%{background-position:100% center}100%{background-position:-200% center}}
.banner-badge{
  padding:3px 8px;background:rgba(200,168,75,.08);border:1px solid var(--stroke2);
  border-radius:5px;font-size:.48rem;font-weight:700;letter-spacing:2.5px;
  text-transform:uppercase;color:var(--g1);
}

/* ── PAGE LAYOUT ── */
.page{max-width:420px;margin:0 auto;padding:0 12px;position:relative;z-index:1;}
@keyframes up{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}

/* ── SURFACE SYSTEM ── */
.s-glass{
  background:rgba(10,10,15,.8);
  border:1px solid var(--stroke2);
  border-radius:var(--r);
  backdrop-filter:blur(10px);
  box-shadow:0 4px 24px rgba(0,0,0,.4),inset 0 1px 0 rgba(200,168,75,.05);
}
.s-dark{
  background:var(--l1);
  border:1px solid var(--stroke);
  border-radius:var(--r);
  box-shadow:0 2px 12px rgba(0,0,0,.3);
}

/* ══════════════ LOGIN ══════════════ */
#LOGIN_SCREEN{
  min-height:100vh;display:flex;align-items:center;justify-content:center;
  padding:100px 0 80px;animation:up .6s var(--spring) both;
}
.login-wrap{width:100%;max-width:360px;display:flex;flex-direction:column;gap:16px;}

.login-hero{text-align:center;padding:24px 0 8px;}
.login-emblem{
  width:64px;height:64px;border-radius:20px;margin:0 auto 14px;
  background:linear-gradient(135deg,var(--l3),var(--l5));
  border:1px solid var(--stroke3);
  display:flex;align-items:center;justify-content:center;
  box-shadow:0 0 0 6px rgba(200,168,75,.04),0 0 32px rgba(200,168,75,.15),0 8px 24px rgba(0,0,0,.5);
  position:relative;
}
.login-emblem::before{
  content:'';position:absolute;inset:-1px;border-radius:21px;
  background:linear-gradient(135deg,rgba(200,168,75,.3),transparent,rgba(200,168,75,.1));
  pointer-events:none;
}
.login-emblem svg{width:26px;height:26px;stroke:var(--g1);stroke-width:1.8;fill:none;}
.login-eyebrow{font-size:.52rem;font-weight:700;letter-spacing:4px;text-transform:uppercase;color:var(--ink3);margin-bottom:8px;}
.login-headline{font-family:'Cinzel',serif;font-size:1.3rem;font-weight:700;color:var(--ink);line-height:1.4;}
.login-headline em{font-style:normal;color:transparent;background:linear-gradient(135deg,var(--g1),var(--g2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;}

/* login card */
.login-card{overflow:hidden;}
.login-card-header{
  padding:14px 18px 12px;border-bottom:1px solid var(--stroke);
  background:linear-gradient(180deg,rgba(200,168,75,.04),transparent);
  display:flex;align-items:center;gap:8px;
}
.lch-dot{width:6px;height:6px;border-radius:50%;background:var(--g1);box-shadow:0 0 6px var(--g2);}
.lch-txt{font-size:.62rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);}

.lf-field{
  display:flex;align-items:stretch;
  border-bottom:1px solid var(--stroke);
  transition:background .2s;position:relative;overflow:hidden;
}
.lf-field:last-of-type{border-bottom:none;}
.lf-field:focus-within{background:rgba(200,168,75,.02);}
.lf-field::after{
  content:'';position:absolute;right:0;top:0;bottom:0;width:0;
  background:linear-gradient(0deg,var(--g1),var(--g2));
  transition:width .25s var(--ease);
}
.lf-field:focus-within::after{width:2px;}

.lf-ic{
  width:52px;display:flex;align-items:center;justify-content:center;
  border-left:1px solid var(--stroke);background:rgba(0,0,0,.2);
}
.lf-ic svg{width:15px;height:15px;stroke:var(--ink3);stroke-width:1.7;fill:none;transition:stroke .25s;}
.lf-field:focus-within .lf-ic svg{stroke:var(--g1);}
.lf-body{flex:1;padding:12px 14px;display:flex;flex-direction:column;gap:2px;}
.lf-lbl{font-size:.48rem;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:var(--ink3);transition:color .25s;}
.lf-field:focus-within .lf-lbl{color:var(--g1);}
.lf-inp{
  background:transparent;border:none;outline:none;
  font-family:'Cairo',sans-serif;font-size:.9rem;font-weight:600;color:var(--ink);
}
.lf-inp::placeholder{color:var(--ink3);font-weight:400;font-size:.78rem;}

.login-submit{padding:14px 16px 16px;}
.btn-submit{
  width:100%;padding:13px;border:none;border-radius:var(--r-sm);cursor:pointer;
  background:linear-gradient(135deg,var(--g3) 0%,var(--g1) 40%,var(--g2) 60%,var(--g1) 80%,var(--g3) 100%);
  background-size:300% 100%;
  color:#1a0c00;font-family:'Cairo',sans-serif;font-size:.88rem;font-weight:900;
  display:flex;align-items:center;justify-content:center;gap:8px;
  box-shadow:0 4px 20px rgba(200,168,75,.3),0 1px 0 rgba(255,255,255,.1) inset;
  transition:transform .2s var(--spring),box-shadow .25s,background-position .4s;
  position:relative;overflow:hidden;
}
.btn-submit::before{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(255,255,255,.12) 0%,transparent 50%);}
.btn-submit:hover{transform:translateY(-2px);box-shadow:0 8px 32px rgba(200,168,75,.4);background-position:100% center;}
.btn-submit:active{transform:scale(.97);}
.btn-submit:disabled{opacity:.5;cursor:wait;}
.btn-submit svg{width:14px;height:14px;stroke:currentColor;stroke-width:2.2;fill:none;position:relative;z-index:1;}
.btn-submit span{position:relative;z-index:1;}
.btn-spin{width:14px;height:14px;border-radius:50%;border:2px solid rgba(26,12,0,.2);border-top-color:#1a0c00;animation:rot .7s linear infinite;display:none;position:relative;z-index:1;}
.btn-submit.loading .btn-spin{display:block;}
.btn-submit.loading .btn-label{display:none;}
@keyframes rot{to{transform:rotate(360deg)}}

.err-box{
  display:flex;align-items:center;gap:9px;
  background:rgba(230,0,0,.05);border:1px solid rgba(230,0,0,.18);
  border-radius:var(--r-xs);padding:11px 14px;
  font-size:.7rem;color:#ff7070;font-weight:600;
  animation:up .3s var(--spring) both;
}
.err-box svg{width:13px;height:13px;stroke:#ff5555;stroke-width:2;fill:none;flex-shrink:0;}

.login-note{
  text-align:center;font-size:.58rem;color:var(--ink3);
  display:flex;align-items:center;justify-content:center;gap:6px;
}
.login-note::before,.login-note::after{content:'';display:block;height:1px;width:24px;background:var(--stroke2);}

/* ══════════════ APP ══════════════ */
#APP{display:none;}
#APP.active{display:block;}
.app-body{padding-top:100px;padding-bottom:90px;}

/* user bar */
.user-bar{
  display:flex;align-items:center;justify-content:space-between;
  padding:10px 14px;margin-bottom:14px;
  background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r-xs);
  box-shadow:0 2px 12px rgba(0,0,0,.3);
}
.ub-left{display:flex;align-items:center;gap:10px;}
.ub-status{position:relative;width:8px;height:8px;}
.ub-dot{width:8px;height:8px;border-radius:50%;background:#22c55e;box-shadow:0 0 0 0 rgba(34,197,94,.4);animation:statusPing 2s ease-in-out infinite;}
@keyframes statusPing{0%,100%{box-shadow:0 0 0 0 rgba(34,197,94,.4)}50%{box-shadow:0 0 0 6px rgba(34,197,94,0)}}
.ub-num{font-family:'JetBrains Mono',monospace;font-size:.82rem;font-weight:700;color:var(--g2);}
.ub-logout{
  display:flex;align-items:center;gap:5px;background:transparent;
  border:1px solid rgba(230,0,0,.15);border-radius:6px;
  padding:5px 12px;font-family:'Cairo',sans-serif;font-size:.64rem;font-weight:700;
  color:rgba(230,0,0,.45);cursor:pointer;transition:all .2s;
  text-decoration:none;
}
.ub-logout:hover{color:#ff6b6b;border-color:rgba(230,0,0,.35);background:rgba(230,0,0,.04);}
.ub-logout svg{width:10px;height:10px;stroke:currentColor;stroke-width:2;fill:none;}

/* search screen */
#US{display:flex;flex-direction:column;gap:14px;animation:up .5s var(--spring) both;}
.us-heading{padding:8px 2px 6px;}
.us-eyebrow{
  display:inline-flex;align-items:center;gap:7px;
  font-size:.52rem;font-weight:700;letter-spacing:3.5px;text-transform:uppercase;
  color:var(--g1);opacity:.85;margin-bottom:10px;
}
.us-eyebrow::before,.us-eyebrow::after{content:'';display:block;width:5px;height:1px;background:var(--g1);}
.us-title{font-family:'Cinzel',serif;font-size:1.55rem;font-weight:700;line-height:1.35;margin-bottom:6px;}
.us-title em{font-style:normal;color:transparent;background:linear-gradient(135deg,var(--g1),var(--g2),var(--g1));-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.us-sub{font-size:.72rem;color:var(--ink2);line-height:1.85;}

/* main search card */
.search-card{overflow:hidden;}

/* section label */
.sc-label{
  padding:11px 16px 4px;
  display:flex;align-items:center;gap:8px;
  font-size:.52rem;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:var(--ink3);
}
.sc-label::before{content:'';display:block;width:16px;height:1px;background:linear-gradient(90deg,transparent,var(--g1) 80%);}
.sc-divider{height:1px;background:linear-gradient(90deg,transparent,var(--stroke2) 30%,var(--stroke2) 70%,transparent);}

/* units field */
.unit-field{
  display:flex;align-items:stretch;border-bottom:1px solid var(--stroke);
  position:relative;transition:background .2s;
}
.unit-field:focus-within{background:rgba(200,168,75,.02);}
.unit-field::after{content:'';position:absolute;right:0;top:0;bottom:0;width:0;background:linear-gradient(0deg,var(--g1),var(--g2));transition:width .25s;}
.unit-field:focus-within::after{width:2px;}
.uf-ic{
  width:54px;display:flex;align-items:center;justify-content:center;
  border-left:1px solid var(--stroke);background:rgba(0,0,0,.15);
}
.uf-ic svg{width:18px;height:18px;fill:none;transition:stroke .25s;}
.unit-field:focus-within .uf-ic svg{stroke:var(--g1) !important;}
.uf-body{flex:1;padding:14px 0;display:flex;flex-direction:column;align-items:center;}
.uf-lbl{font-family:'Cinzel',serif;font-size:.52rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);margin-bottom:4px;transition:color .25s;}
.unit-field:focus-within .uf-lbl{color:var(--g1);}
.uf-inp{
  background:transparent;border:none;outline:none;
  font-family:'Bebas Neue',sans-serif;font-size:2.2rem;letter-spacing:3px;
  color:var(--ink);text-align:center;max-width:180px;
}
.uf-inp::placeholder{font-family:'Cairo',sans-serif;color:var(--ink3);font-size:.83rem;font-weight:400;letter-spacing:0;}

/* quick chips */
.chips-area{padding:12px 16px 14px;border-bottom:1px solid var(--stroke);}
.chips-lbl{font-size:.52rem;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:var(--ink3);margin-bottom:9px;display:flex;align-items:center;gap:7px;}
.chips-lbl::before{content:'';display:block;width:14px;height:1px;background:linear-gradient(90deg,transparent,var(--g1));}
.chips-row{display:flex;gap:6px;}
.chip{
  flex:1;padding:9px 4px;
  background:rgba(0,0,0,.25);border:1px solid var(--stroke);
  border-radius:8px;text-align:center;
  font-family:'Bebas Neue',sans-serif;font-size:1rem;letter-spacing:2px;color:var(--ink2);
  cursor:pointer;transition:all .2s var(--spring);
}
.chip:hover{border-color:var(--stroke2);color:var(--g2);}
.chip.sel{background:var(--g4);border-color:rgba(200,168,75,.4);color:var(--g2);}
.chip:active{transform:scale(.88);}

/* charge mode */
.mode-area{padding:14px 16px;border-bottom:1px solid var(--stroke);}
.mode-lbl{font-size:.52rem;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:var(--ink3);margin-bottom:10px;display:flex;align-items:center;gap:7px;}
.mode-lbl::before{content:'';display:block;width:14px;height:1px;background:linear-gradient(90deg,transparent,var(--g1));}
.mode-btns{display:flex;gap:9px;}
.mode-btn{
  flex:1;padding:14px 10px;
  background:rgba(0,0,0,.2);border:1px solid var(--stroke);
  border-radius:var(--r-sm);text-align:center;cursor:pointer;
  transition:all .22s var(--spring);position:relative;overflow:hidden;
}
.mode-btn::before{content:'';position:absolute;inset:0;opacity:0;transition:opacity .3s;}
.mode-btn.online::before{background:radial-gradient(ellipse at 50% 0%,rgba(230,0,0,.08),transparent 70%);}
.mode-btn.dial::before{background:radial-gradient(ellipse at 50% 0%,rgba(200,168,75,.08),transparent 70%);}
.mode-btn.sel::before{opacity:1;}
.mode-btn.online.sel{border-color:rgba(230,0,0,.3);}
.mode-btn.dial.sel{border-color:rgba(200,168,75,.3);}
.mode-btn:active{transform:scale(.95);}
.mb-icon{
  width:30px;height:30px;border-radius:50%;margin:0 auto 8px;
  display:flex;align-items:center;justify-content:center;
}
.mode-btn.online .mb-icon{background:rgba(230,0,0,.08);border:1px solid rgba(230,0,0,.15);}
.mode-btn.online .mb-icon svg{stroke:var(--red);width:15px;height:15px;stroke-width:2;fill:none;}
.mode-btn.dial .mb-icon{background:rgba(200,168,75,.08);border:1px solid rgba(200,168,75,.15);}
.mode-btn.dial .mb-icon svg{stroke:var(--g2);width:15px;height:15px;stroke-width:2;fill:none;}
.mb-title{display:block;font-family:'Cairo',sans-serif;font-size:.75rem;font-weight:700;color:var(--ink);margin-bottom:2px;}
.mb-sub{display:block;font-size:.58rem;color:var(--ink3);}

/* online target */
.target-area{
  overflow:hidden;max-height:0;transition:max-height .35s var(--ease),padding .3s;
  padding:0 16px;border-bottom:1px solid var(--stroke);
}
.target-area.open{max-height:240px;padding:14px 16px;}
.target-lbl{font-size:.52rem;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:var(--ink3);margin-bottom:9px;display:flex;align-items:center;gap:7px;}
.target-lbl::before{content:'';display:block;width:14px;height:1px;background:linear-gradient(90deg,transparent,var(--g1));}
.target-btns{display:flex;gap:7px;}
.target-btn{
  flex:1;padding:10px;background:rgba(0,0,0,.2);
  border:1px solid var(--stroke);border-radius:8px;
  text-align:center;font-family:'Cairo',sans-serif;font-size:.72rem;
  font-weight:700;color:var(--ink2);cursor:pointer;transition:all .2s var(--spring);
}
.target-btn.sel{background:var(--g4);border-color:rgba(200,168,75,.35);color:var(--g2);}
.target-btn:active{transform:scale(.92);}
.other-fields{margin-top:10px;display:none;flex-direction:column;gap:6px;}
.other-fields.show{display:flex;}
.of-wrap{
  display:flex;align-items:stretch;
  background:rgba(0,0,0,.2);border:1px solid var(--stroke);
  border-radius:8px;overflow:hidden;
}
.of-ic{width:38px;display:flex;align-items:center;justify-content:center;border-left:1px solid var(--stroke);background:rgba(0,0,0,.15);}
.of-ic svg{width:13px;height:13px;stroke:var(--ink3);stroke-width:1.7;fill:none;}
.of-wrap input{
  flex:1;background:transparent;border:none;outline:none;
  padding:10px 12px;font-family:'Cairo',sans-serif;
  font-size:.82rem;font-weight:600;color:var(--ink);
}
.of-wrap input::placeholder{color:var(--ink3);font-weight:400;font-size:.75rem;}

/* GO */
.go-area{padding:15px 16px 16px;}
.btn-go{
  width:100%;padding:15px;border:none;border-radius:var(--r-sm);cursor:pointer;
  background:linear-gradient(135deg,var(--red2),var(--red),#ff2020,var(--red));
  background-size:300% 100%;
  color:#fff;font-family:'Cairo',sans-serif;font-size:.9rem;font-weight:900;
  display:flex;align-items:center;justify-content:center;gap:9px;
  box-shadow:0 5px 28px rgba(230,0,0,.35),0 1px 0 rgba(255,255,255,.08) inset;
  transition:transform .2s var(--spring),box-shadow .25s,background-position .4s;
  position:relative;overflow:hidden;
}
.btn-go::before{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(255,255,255,.1) 0%,transparent 50%);}
.btn-go:hover{transform:translateY(-2px);box-shadow:0 10px 38px rgba(230,0,0,.45);background-position:100% center;}
.btn-go:active{transform:scale(.97);}
.btn-go svg{width:17px;height:17px;stroke:#fff;stroke-width:2.2;fill:none;position:relative;z-index:1;}
.btn-go span{position:relative;z-index:1;}

/* ══════════════ CARDS SCREEN ══════════════ */
#CS{display:none;flex-direction:column;gap:11px;animation:up .4s var(--spring) both;}

.cs-header{
  display:flex;align-items:center;justify-content:space-between;
  padding:11px 14px;
}
.cs-info{font-family:'JetBrains Mono',monospace;font-size:.72rem;color:var(--ink2);}
.cs-info strong{color:var(--g2);}
.cs-back{
  display:flex;align-items:center;gap:5px;
  background:var(--l3);border:1px solid var(--stroke);
  border-radius:7px;padding:6px 13px;
  font-family:'Cairo',sans-serif;font-size:.68rem;font-weight:700;
  color:var(--ink2);cursor:pointer;transition:all .2s;
}
.cs-back:hover{color:var(--ink);border-color:var(--stroke2);}
.cs-back svg{width:10px;height:10px;stroke:currentColor;stroke-width:2.5;fill:none;}

/* timer panel */
.timer-panel{padding:16px 18px;}
.timer-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;}
.timer-left-group{display:flex;align-items:center;gap:10px;}
.live-badge{
  display:flex;align-items:center;gap:5px;
  background:rgba(230,0,0,.06);border:1px solid rgba(230,0,0,.15);
  border-radius:20px;padding:4px 10px;
}
.live-dot{width:6px;height:6px;border-radius:50%;background:var(--red);box-shadow:0 0 0 0 rgba(230,0,0,.4);animation:livePing 1.3s ease-in-out infinite;}
@keyframes livePing{0%,100%{box-shadow:0 0 0 0 rgba(230,0,0,.4)}50%{box-shadow:0 0 0 6px rgba(230,0,0,0)}}
.live-txt{font-size:.55rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--red);opacity:.85;}

/* TIMER COUNT WITH USERS BADGE */
.timer-right{display:flex;flex-direction:column;align-items:flex-end;gap:4px;}
.timer-num{
  font-family:'Bebas Neue',sans-serif;font-size:2.6rem;letter-spacing:4px;
  color:var(--ink);transition:color .3s;line-height:1;
}
.timer-num.hot{color:var(--red);}
.users-badge{
  display:flex;align-items:center;gap:5px;
  background:rgba(200,168,75,.06);border:1px solid rgba(200,168,75,.12);
  border-radius:20px;padding:3px 9px;
}
.users-ic svg{width:10px;height:10px;stroke:var(--g1);stroke-width:2;fill:none;}
.users-count{font-family:'JetBrains Mono',monospace;font-size:.65rem;font-weight:700;color:var(--g1);}
.users-lbl{font-size:.5rem;color:var(--ink3);}

.timer-track{height:2px;background:var(--l4);border-radius:4px;overflow:hidden;}
.timer-fill{height:100%;border-radius:4px;background:linear-gradient(90deg,var(--g3),var(--g1),var(--g2));transition:width 1s linear;box-shadow:0 0 6px rgba(200,168,75,.3);}

/* toggle */
.tgl-row{
  display:flex;align-items:center;justify-content:space-between;
  padding:13px 16px;cursor:pointer;
}
.tgl-info strong{display:block;font-family:'Cinzel',serif;font-size:.75rem;font-weight:700;color:var(--ink);margin-bottom:2px;}
.tgl-info small{font-size:.6rem;color:var(--ink2);}
.sw{position:relative;width:40px;height:22px;flex-shrink:0;}
.sw input{position:absolute;opacity:0;width:0;height:0;}
.sw-track{
  position:absolute;inset:0;border-radius:20px;
  background:var(--l4);border:1px solid var(--stroke);
  cursor:pointer;transition:all .3s;
}
.sw-track::before{
  content:'';position:absolute;width:16px;height:16px;border-radius:50%;
  background:#555;top:2px;right:2px;
  box-shadow:0 1px 4px rgba(0,0,0,.5);
  transition:transform .3s var(--spring),background .3s;
}
.sw input:checked+.sw-track{background:linear-gradient(135deg,var(--g3),var(--g1));border-color:rgba(200,168,75,.3);}
.sw input:checked+.sw-track::before{transform:translateX(-18px);background:#fff;}

/* cards */
.cards-list{display:flex;flex-direction:column;gap:12px;}

.promo-card{
  border-radius:var(--r);
  position:relative;
  animation:cardIn .45s var(--spring) both;
  animation-delay:calc(var(--i,0)*.07s);
}
@keyframes cardIn{from{opacity:0;transform:translateY(12px) scale(.96)}to{opacity:1;transform:none}}

/* Glass layers */
.pc-shell{
  border-radius:var(--r);
  overflow:hidden;
  background:linear-gradient(145deg,rgba(14,12,20,.96),rgba(8,8,14,.98));
  border:1px solid rgba(200,168,75,.12);
  box-shadow:0 8px 32px rgba(0,0,0,.5),0 1px 0 rgba(200,168,75,.06) inset;
  position:relative;
}
.promo-card.best .pc-shell{
  border-color:rgba(200,168,75,.35);
  box-shadow:0 8px 40px rgba(0,0,0,.6),0 0 0 1px rgba(200,168,75,.1),0 1px 0 rgba(200,168,75,.15) inset;
}
/* gold line on top for best */
.promo-card.best .pc-shell::before{
  content:'';position:absolute;top:0;left:0;right:0;height:1.5px;z-index:5;
  background:linear-gradient(90deg,transparent 5%,var(--g3) 20%,var(--g2) 50%,var(--g3) 80%,transparent 95%);
  box-shadow:0 0 12px rgba(200,168,75,.3);
}
/* subtle interior gradient */
.pc-shell::after{
  content:'';position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(ellipse 70% 50% at 50% -10%,rgba(200,168,75,.04),transparent 70%);
}

.pc-best-badge{
  position:absolute;top:12px;left:12px;z-index:10;
  font-size:.5rem;font-weight:900;letter-spacing:1.5px;text-transform:uppercase;
  padding:3px 9px;border-radius:4px;color:#1a0800;
  background:linear-gradient(135deg,var(--g2),var(--g1));
  box-shadow:0 2px 10px rgba(200,168,75,.4);
}

.pc-body{position:relative;z-index:2;padding:10px 14px 12px;}
.pc-best-body{padding-top:22px;}

/* stats row */
.pc-stats{display:flex;gap:0;margin-bottom:10px;}
.stat-block{
  flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;
  padding:8px 6px;position:relative;
}
.stat-block:not(:last-child)::after{
  content:'';position:absolute;left:0;top:20%;bottom:20%;width:1px;
  background:linear-gradient(0deg,transparent,rgba(255,255,255,.06),transparent);
}
.stat-icon{
  width:26px;height:26px;border-radius:8px;
  display:flex;align-items:center;justify-content:center;margin-bottom:4px;
}
.stat-icon svg{width:12px;height:12px;stroke-width:1.8;fill:none;}
.si-amount .stat-icon{background:rgba(255,138,128,.06);border:1px solid rgba(255,138,128,.12);}
.si-amount .stat-icon svg{stroke:#ff9090;}
.si-gift .stat-icon{background:rgba(200,168,75,.08);border:1px solid rgba(200,168,75,.15);}
.si-gift .stat-icon svg{stroke:var(--g2);}
.si-remain .stat-icon{background:rgba(130,177,255,.06);border:1px solid rgba(130,177,255,.12);}
.si-remain .stat-icon svg{stroke:#90b8ff;}

.stat-val{font-family:'Bebas Neue',sans-serif;font-size:1.1rem;letter-spacing:2px;color:#fff;line-height:1;}
.stat-lbl{font-size:.44rem;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:rgba(255,255,255,.25);}

/* serial */
.serial-row{
  display:flex;align-items:center;justify-content:center;
  gap:8px;margin-bottom:9px;
}
.serial-pill{
  display:flex;align-items:center;gap:0;
  background:rgba(0,0,0,.4);border:1px solid rgba(200,168,75,.1);
  border-radius:10px;overflow:hidden;
}
.sn-code{
  font-family:'JetBrains Mono',monospace;font-size:.9rem;font-weight:700;
  color:#fff;letter-spacing:3px;padding:7px 12px;
}
.sn-copy{
  width:34px;height:100%;display:flex;align-items:center;justify-content:center;
  background:rgba(200,168,75,.04);border-left:1px solid rgba(200,168,75,.08);
  cursor:pointer;transition:all .2s var(--spring);padding:7px 0;
}
.sn-copy svg{width:12px;height:12px;stroke:rgba(200,168,75,.35);stroke-width:2;fill:none;}
.sn-copy:hover{background:rgba(200,168,75,.12);border-color:rgba(200,168,75,.25);}
.sn-copy:active{transform:scale(.85);}

/* action row */
.pc-actions{display:flex;justify-content:center;gap:8px;}
.btn-redeem{
  display:none;align-items:center;gap:6px;
  padding:7px 16px;border-radius:20px;border:1px solid rgba(230,0,0,.25);
  background:rgba(230,0,0,.07);color:#ff8888;
  font-family:'Cairo',sans-serif;font-size:.7rem;font-weight:700;
  cursor:pointer;transition:all .2s var(--spring);
}
.btn-redeem svg{width:11px;height:11px;stroke:currentColor;stroke-width:2;fill:none;}
.btn-redeem:hover{background:rgba(230,0,0,.14);border-color:rgba(230,0,0,.4);}
.btn-redeem.loading{opacity:.5;pointer-events:none;}
.btn-dial{
  display:none;align-items:center;gap:6px;
  text-decoration:none;padding:7px 16px;border-radius:20px;
  border:1px solid rgba(200,168,75,.12);background:rgba(200,168,75,.04);
  color:rgba(200,168,75,.55);font-family:'Cairo',sans-serif;font-size:.7rem;font-weight:700;
  transition:all .2s;
}
.btn-dial svg{width:11px;height:11px;stroke:currentColor;stroke-width:2;fill:none;}
.btn-dial:hover{color:rgba(200,168,75,.85);border-color:rgba(200,168,75,.3);}

/* ── NAV ── */
.bnav{
  position:fixed;bottom:0;left:0;right:0;z-index:200;
  display:flex;justify-content:space-around;align-items:center;
  padding:10px 0 20px;
  background:rgba(5,5,8,.96);backdrop-filter:blur(20px);
  border-top:1px solid var(--stroke2);
}
.bnav a{
  text-decoration:none;color:var(--ink3);
  display:flex;flex-direction:column;align-items:center;gap:3px;
  padding:5px 20px;border-radius:10px;transition:all .2s var(--spring);
}
.bnav a:hover{color:var(--g1);transform:translateY(-3px);}
.bnav a svg{width:20px;height:20px;stroke:currentColor;stroke-width:1.7;fill:none;}
.bnav a span{font-size:.48rem;font-weight:700;letter-spacing:1px;text-transform:uppercase;}

/* states */
.loading-state{
  display:flex;flex-direction:column;align-items:center;gap:12px;
  padding:44px 20px;animation:up .35s var(--spring) both;
}
.loader{
  width:32px;height:32px;border-radius:50%;
  border:2px solid rgba(200,168,75,.08);border-top-color:var(--g1);
  animation:rot .8s linear infinite;
}
.loader-txt{font-family:'Cinzel',serif;font-size:.7rem;color:var(--ink2);}
.empty-state{
  text-align:center;padding:40px 20px;
  font-family:'Cinzel',serif;font-size:.78rem;color:var(--ink2);line-height:2.2;
}
.empty-state svg{width:28px;height:28px;stroke:var(--ink3);stroke-width:1.4;fill:none;margin-bottom:12px;}

/* toast */
.toast{
  position:fixed;bottom:92px;left:50%;
  transform:translateX(-50%) translateY(16px);
  background:rgba(12,12,18,.97);border:1px solid var(--stroke2);
  border-radius:24px;padding:10px 20px;
  font-family:'Cairo',sans-serif;font-size:.74rem;font-weight:700;color:var(--ink);
  opacity:0;pointer-events:none;transition:all .3s var(--spring);
  z-index:999;white-space:nowrap;backdrop-filter:blur(12px);
  box-shadow:0 8px 24px rgba(0,0,0,.5);
}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0);}
.toast.ok{border-color:rgba(34,197,94,.3);color:#4ade80;}
.toast.err{border-color:rgba(230,0,0,.3);color:#f87171;}

::-webkit-scrollbar{width:3px;}
::-webkit-scrollbar-track{background:var(--bg);}
::-webkit-scrollbar-thumb{background:var(--l5);border-radius:4px;}
</style>
</head>
<body oncontextmenu="return false;">

<!-- BANNER -->
<div class="banner">
  <div class="banner-inner">
    <div class="banner-logo">
      <svg viewBox="0 0 24 24"><polyline points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
    </div>
    <div class="banner-wordmark">TALASHNY</div>
    <div class="banner-badge">VF · EG</div>
  </div>
</div>

{% if not logged_in %}
<!-- ══ LOGIN SCREEN ══ -->
<div id="LOGIN_SCREEN">
  <div class="page">
    <div class="login-wrap">
      <div class="login-hero">
        <div class="login-emblem">
          <svg viewBox="0 0 24 24"><polyline points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
        </div>
        <div class="login-eyebrow">Premium Access</div>
        <div class="login-headline">أهلاً في <em>TALASHNY</em></div>
      </div>

      {% if error %}
      <div class="err-box">
        <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
        {{ error }}
      </div>
      {% endif %}

      <form method="POST" class="s-glass login-card" id="LOGIN_FORM">
        <div class="login-card-header">
          <div class="lch-dot"></div>
          <span class="lch-txt">بيانات الدخول</span>
        </div>

        <div class="lf-field">
          <div class="lf-ic">
            <svg viewBox="0 0 24 24"><rect x="5" y="2" width="14" height="20" rx="2"/><circle cx="12" cy="17" r="1" fill="currentColor" stroke="none"/></svg>
          </div>
          <div class="lf-body">
            <span class="lf-lbl">رقم الموبايل</span>
            <input class="lf-inp" type="tel" name="number" placeholder="01XXXXXXXXX" inputmode="tel" autocomplete="tel" required value="{{ request.form.get('number', '') }}">
          </div>
        </div>

        <div class="lf-field">
          <div class="lf-ic">
            <svg viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
          </div>
          <div class="lf-body">
            <span class="lf-lbl">الباسورد</span>
            <input class="lf-inp" type="password" name="password" placeholder="••••••••" autocomplete="current-password" required>
          </div>
        </div>

        <div class="login-submit">
          <button type="submit" class="btn-submit" id="BTN_SUB">
            <svg viewBox="0 0 24 24"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>
            <span class="btn-label">دخـول</span>
            <div class="btn-spin"></div>
          </button>
        </div>
      </form>

      <div class="login-note">بياناتك محمية ومش بتتحفظ على السيرفر</div>
    </div>
  </div>
</div>

{% else %}
<!-- ══ APP SCREEN ══ -->
<div id="APP" class="active">
  <div class="app-body">
    <div class="page">

      <!-- SEARCH SCREEN -->
      <div id="US">
        <div class="us-heading">
          <div class="us-eyebrow">Premium Tools</div>
          <div class="us-title">ابحث عن<br><em>أنسب كارت</em></div>
          <div class="us-sub">حدد الوحدات المطلوبة واختار طريقة الشحن المناسبة</div>
        </div>

        <div class="user-bar">
          <div class="ub-left">
            <div class="ub-status"><div class="ub-dot"></div></div>
            <span class="ub-num">{{ number }}</span>
          </div>
          <a href="/?logout=1" class="ub-logout">
            <svg viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
            خروج
          </a>
        </div>

        <div class="s-glass search-card">
          <!-- UNITS -->
          <div class="sc-label">فئة الكارت</div>
          <div class="unit-field">
            <div class="uf-ic">
              <svg viewBox="0 0 24 24" style="stroke:var(--ink3);stroke-width:1.7;fill:none;"><polyline points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            </div>
            <div class="uf-body">
              <span class="uf-lbl">الحد الأدنى</span>
              <input class="uf-inp" type="number" id="UI" placeholder="وحدات" min="1" inputmode="numeric" autofocus>
            </div>
          </div>
          <div class="sc-divider"></div>

          <div class="chips-area">
            <div class="chips-lbl">اختيار سريع</div>
            <div class="chips-row">
              <button class="chip" onclick="setU(100,this)">100</button>
              <button class="chip" onclick="setU(300,this)">300</button>
              <button class="chip" onclick="setU(500,this)">500</button>
              <button class="chip" onclick="setU(700,this)">700</button>
              <button class="chip" onclick="setU(900,this)">900</button>
            </div>
          </div>

          <!-- MODE -->
          <div class="mode-area">
            <div class="mode-lbl">طريقة الشحن</div>
            <div class="mode-btns">
              <div class="mode-btn online sel" id="CM_ONLINE" onclick="setMode('online')">
                <div class="mb-icon"><svg viewBox="0 0 24 24"><polyline points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg></div>
                <span class="mb-title">شحن أونلاين</span>
                <span class="mb-sub">تلقائي مباشر</span>
              </div>
              <div class="mode-btn dial" id="CM_DIAL" onclick="setMode('dial')">
                <div class="mb-icon"><svg viewBox="0 0 24 24"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 13a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 2.24h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 9.91a16 16 0 0 0 6.09 6.09l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg></div>
                <span class="mb-title">شحن عادي</span>
                <span class="mb-sub">لوحة الاتصال</span>
              </div>
            </div>
          </div>

          <!-- TARGET -->
          <div class="target-area open" id="OT_AREA">
            <div class="target-lbl">شحن على رقم</div>
            <div class="target-btns">
              <div class="target-btn sel" id="OT_MINE" onclick="setTarget('mine')">رقمي</div>
              <div class="target-btn" id="OT_OTHER" onclick="setTarget('other')">رقم تاني</div>
            </div>
            <div class="other-fields" id="OTHER_FIELDS">
              <div class="of-wrap">
                <div class="of-ic"><svg viewBox="0 0 24 24"><rect x="5" y="2" width="14" height="20" rx="2"/></svg></div>
                <input type="tel" id="OT_NUM" placeholder="رقم التاني 01XXXXXXXXX" inputmode="tel">
              </div>
              <div class="of-wrap">
                <div class="of-ic"><svg viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg></div>
                <input type="password" id="OT_PASS" placeholder="باسورد الرقم التاني">
              </div>
            </div>
          </div>

          <div class="go-area">
            <button class="btn-go" onclick="startSearch()">
              <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <span>ابدأ البحث</span>
            </button>
          </div>
        </div>
      </div>

      <!-- CARDS SCREEN -->
      <div id="CS">
        <div class="s-glass cs-header">
          <div class="cs-info">بحث عن <strong id="IU">—</strong></div>
          <button class="cs-back" onclick="goBack()">
            <svg viewBox="0 0 24 24"><polyline points="9 18 15 12 9 6"/></svg>
            تغيير
          </button>
        </div>

        <div class="s-glass timer-panel">
          <div class="timer-top">
            <div class="timer-left-group">
              <div class="live-badge">
                <div class="live-dot"></div>
                <span class="live-txt">Live</span>
              </div>
            </div>
            <div class="timer-right">
              <div class="timer-num" id="TN">—</div>
              <div class="users-badge">
                <div class="users-ic"><svg viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg></div>
                <span class="users-count" id="UC">—</span>
                <span class="users-lbl">متصل</span>
              </div>
            </div>
          </div>
          <div class="timer-track"><div class="timer-fill" id="TP" style="width:100%"></div></div>
        </div>

        <div class="s-glass tgl-row" onclick="document.getElementById('CC').click()">
          <div class="tgl-info">
            <strong>استمرار البحث بعد الشحن</strong>
            <small id="TH">مفعّل — يكمل البحث بعد الشحن</small>
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
    <span>Telegram</span>
  </a>
  <a href="https://wa.me/message/U6AIKBGFCNCQK1" target="_blank">
    <svg viewBox="0 0 24 24"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
    <span>WhatsApp</span>
  </a>
  <a href="https://www.facebook.com/VI808IV" target="_blank">
    <svg viewBox="0 0 24 24"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/></svg>
    <span>Facebook</span>
  </a>
</nav>

<div class="toast" id="TOAST"></div>

<script>
// ── Login form handler ──
document.getElementById('LOGIN_FORM')?.addEventListener('submit', function(){
  const btn = document.getElementById('BTN_SUB');
  btn.classList.add('loading');
  btn.disabled = true;
});

{% if logged_in %}
// ── STATE ──
const SECS = 7;
const SID  = Math.random().toString(36).slice(2);
let units = 0, chargeMode = 'online', targetMode = 'mine';
let running = false, stop = false, ti = null, ct = null, charged = false;

// ── PRESENCE PING ──
setInterval(() => fetch('/ping?sid='+SID).then(r=>r.json()).then(d=>{
  const uc = document.getElementById('UC');
  if(uc) uc.textContent = d.count;
}).catch(()=>{}), 8000);
// Initial ping
fetch('/ping?sid='+SID).then(r=>r.json()).then(d=>{const uc=document.getElementById('UC');if(uc)uc.textContent=d.count;});

function toast(msg,t=''){
  const el=document.getElementById('TOAST');
  el.textContent=msg;el.className='toast show'+(t?' '+t:'');
  clearTimeout(el._t);el._t=setTimeout(()=>el.classList.remove('show'),2800);
}

function onTgl(){
  const on=document.getElementById('CC').checked;
  document.getElementById('TH').textContent=on?'مفعّل — يكمل البحث بعد الشحن':'معطّل — يتوقف بعد أول شحن';
}
function setU(n,b){
  document.getElementById('UI').value=n;
  document.querySelectorAll('.chip').forEach(x=>x.classList.remove('sel'));
  b.classList.add('sel');
}
function setMode(m){
  chargeMode=m;
  document.getElementById('CM_ONLINE').classList.toggle('sel',m==='online');
  document.getElementById('CM_DIAL').classList.toggle('sel',m==='dial');
  document.getElementById('OT_AREA').classList.toggle('open',m==='online');
}
function setTarget(t){
  targetMode=t;
  document.getElementById('OT_MINE').classList.toggle('sel',t==='mine');
  document.getElementById('OT_OTHER').classList.toggle('sel',t==='other');
  document.getElementById('OTHER_FIELDS').classList.toggle('show',t==='other');
}

function startSearch(){
  const v=parseInt(document.getElementById('UI').value)||0;
  if(v<1){
    const inp=document.getElementById('UI');
    inp.focus();
    inp.closest('.unit-field').style.background='rgba(230,0,0,.05)';
    setTimeout(()=>inp.closest('.unit-field').style.background='',900);
    return;
  }
  if(chargeMode==='online'&&targetMode==='other'){
    if(!document.getElementById('OT_NUM').value.trim()||!document.getElementById('OT_PASS').value.trim()){
      toast('ادخل رقم وباسورد الرقم التاني','err');return;
    }
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
  try{const r=await fetch('/fetch?t='+Date.now()+'&sid='+SID);const d=await r.json();
    const uc=document.getElementById('UC');if(uc&&d.active)uc.textContent=d.active;
    return d;}catch{return{success:false,promos:[]};}
}

function findBest(promos){return promos.find(p=>parseInt(p.gift)>=units)||null;}

async function doRedeem(serial){
  let url='/redeem?serial='+encodeURIComponent(serial);
  if(targetMode==='other'){
    url+='&target='+encodeURIComponent(document.getElementById('OT_NUM').value.trim());
    url+='&tpass='+encodeURIComponent(document.getElementById('OT_PASS').value.trim());
  }
  const btn=document.querySelector('.btn-redeem[data-s="'+serial+'"]');
  if(btn)btn.classList.add('loading');
  try{
    const r=await fetch(url);const d=await r.json();
    if(d.success){toast('✅ تم شحن الكارت بنجاح','ok');charged=true;
      if(!document.getElementById('CC').checked)setTimeout(()=>goBack(),1500);
    }else{toast('❌ فشل الشحن — حاول تاني','err');}
  }catch{toast('❌ خطأ في الاتصال','err');}
  if(btn)btn.classList.remove('loading');
}

function renderCards(data){
  const panel=document.getElementById('CP');
  if(!data?.success||!data.promos?.length){
    if(!panel.querySelector('.cards-list')){
      panel.innerHTML=`<div class="empty-state s-glass"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>لا يوجد كروت مناسبة الآن<br><small style="font-family:Cairo,sans-serif;font-size:.62rem;color:var(--ink3)">جاري البحث...</small></div>`;
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
    <div class="promo-card${isBest?' best':''}" style="--i:${i}">
      <div class="pc-shell">
        ${isBest?'<div class="pc-best-badge">✦ أفضل كارت</div>':''}
        <div class="pc-body${isBest?' pc-best-body':''}">
          <div class="pc-stats">
            <div class="stat-block si-amount">
              <div class="stat-icon"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 6v12M8 10h6a2 2 0 0 1 0 4H8"/></svg></div>
              <span class="stat-val">${p.amount}</span>
              <span class="stat-lbl">جنيه</span>
            </div>
            <div class="stat-block si-gift">
              <div class="stat-icon"><svg viewBox="0 0 24 24"><polyline points="20 12 20 22 4 22 4 12"/><rect x="2" y="7" width="20" height="5"/><path d="M12 22V7M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7zM12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/></svg></div>
              <span class="stat-val">${p.gift}</span>
              <span class="stat-lbl">وحدة</span>
            </div>
            <div class="stat-block si-remain">
              <div class="stat-icon"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></div>
              <span class="stat-val">${p.remaining}</span>
              <span class="stat-lbl">متبقي</span>
            </div>
          </div>
          <div class="serial-row">
            <div class="serial-pill">
              <span class="sn-code">${p.serial}</span>
              <button class="sn-copy" data-serial="${p.serial}">
                <svg viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
              </button>
            </div>
          </div>
          <div class="pc-actions">
            ${isBest&&chargeMode==='online'?`<button class="btn-redeem" data-s="${p.serial}" style="display:inline-flex" onclick="doRedeem('${p.serial}')">
              <svg viewBox="0 0 24 24"><polyline points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>شحن أونلاين
            </button>`:''}
            ${isBest&&chargeMode==='dial'?`<a href="${tel}" class="btn-dial" style="display:inline-flex">
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
    setTimeout(()=>doRedeem(best.serial),700);
  }
  if(best&&chargeMode==='dial'&&!charged){
    const link=document.querySelector('.btn-dial');
    if(link)setTimeout(()=>link.click(),600);
  }
  return !!best;
}

function showLoading(){
  const p=document.getElementById('CP');
  if(!p.querySelector('.cards-list')&&!p.querySelector('.empty-state')){
    p.innerHTML=`<div class="loading-state s-glass"><div class="loader"></div><div class="loader-txt">جاري تحديث الكروت</div></div>`;
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

// ── COPY SERIAL ──
document.addEventListener('click',e=>{
  const btn=e.target.closest('.sn-copy');
  if(!btn)return;
  const serial=btn.dataset.serial;
  const flash=()=>{
    btn.style.background='rgba(200,168,75,.18)';
    btn.innerHTML=`<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#f5d070" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>`;
    setTimeout(()=>{btn.style.background='';btn.innerHTML=`<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="rgba(200,168,75,.35)" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`;},1800);
    toast('تم نسخ الكود','ok');
  };
  if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(serial).then(flash).catch(()=>fallback());}
  else{fallback();}
  function fallback(){const ta=document.createElement('textarea');ta.value=serial;ta.style.cssText='position:fixed;top:0;left:0;width:1px;height:1px;opacity:0;';document.body.appendChild(ta);ta.focus();ta.select();try{document.execCommand('copy');}catch(ex){}document.body.removeChild(ta);flash();}
});

document.getElementById('UI')?.addEventListener('keydown',e=>{if(e.key==='Enter')startSearch();});
{% endif %}
</script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
