from flask import Flask, request, session, redirect, jsonify, render_template_string
import requests, time, os, json
from threading import Lock
import urllib3
urllib3.disable_warnings()

app = Flask(__name__)
app.secret_key = os.urandom(24)

active_users = {}
alock = Lock()
TIMEOUT = 300

def touch(n):
    with alock: active_users[n] = time.time()

def count():
    now = time.time()
    with alock:
        dead = [k for k,v in active_users.items() if v < now - TIMEOUT]
        for k in dead: del active_users[k]
        return len(active_users)

def drop(n):
    with alock: active_users.pop(n, None)

def pw_login(num, pw):
    url = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
    payload = {
        'grant_type': "password",
        'username': num,
        'password': pw,
        'client_secret': "95fd95fb-7489-4958-8ae6-d31a525cd20a",
        'client_id': "ana-vodafone-app"
    }
    headers = {
        'User-Agent': "okhttp/4.12.0",
        'Accept': "application/json, text/plain, */*",
        'Accept-Encoding': "gzip",
        'silentLogin': "true",
        'x-agent-operatingsystem': "13",
        'clientId': "AnaVodafoneAndroid",
        'Accept-Language': "ar",
        'x-agent-device': "Xiaomi 21061119AG",
        'x-agent-version': "2025.10.3",
        'x-agent-build': "1050",
        'digitalId': "28RI9U7ISU8SW",
        'device-id': "1df4efae59648ac3"
    }
    try:
        r = requests.post(url, data=payload, headers=headers, timeout=15, verify=False)
        return r.json()
    except: return {}

def data_login():
    # Step 1: GET seamless auth - كشف الرقم من الشبكة
    url = "http://mobile.vodafone.com.eg/checkSeamless/realms/vf-realm/protocol/openid-connect/auth"
    params = {'client_id': "cash-app"}
    headers = {
        'User-Agent': "okhttp/4.12.0",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'x-agent-operatingsystem': "13",
        'clientId': "AnaVodafoneAndroid",
        'Accept-Language': "ar",
        'x-agent-device': "Xiaomi 21061119AG",
        'x-agent-version': "2025.10.3",
        'x-agent-build': "1050",
        'digitalId': "28RI9U7ISU8SW",
        'device-id': "1df4efae59648ac3"
    }
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15, verify=False)
        resp_json = response.json()
        nuber = resp_json.get('msisdn') or resp_json.get('MSISDN') or resp_json.get('phoneNumber')
        if not nuber:
            return {"error": "تأكد إن الداتا شغالة على خط فودافون مش واي فاي"}
        number = f"0{nuber}" if not str(nuber).startswith('0') else str(nuber)
        fox = resp_json.get("seamlessToken") or resp_json.get("token") or resp_json.get("access_token")
        if not fox:
            return {"error": "مش قادر يجيب الـ token من الشبكة — تأكد من الداتا"}
    except Exception as e:
        return {"error": f"تأكد إن الداتا شغالة على خط فودافون مش واي فاي"}

    # Step 2: Token exchange
    url2 = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
    payload2 = {
        'grant_type': "password",
        'client_secret': "b86e30a8-ae29-467a-a71f-65c73f2ff5e3",
        'client_id': "cash-app"
    }
    headers2 = {
        'User-Agent': "okhttp/4.12.0",
        'Accept': "application/json, text/plain, */*",
        'Accept-Encoding': "gzip",
        'silentLogin': "true",
        'CRP': "false",
        'seamlessToken': fox,
        'firstTimeLogin': "true",
        'x-agent-operatingsystem': "13",
        'clientId': "AnaVodafoneAndroid",
        'Accept-Language': "ar",
        'x-agent-device': "Xiaomi 21061119AG",
        'x-agent-version': "2025.10.3",
        'x-agent-build': "1050",
        'digitalId': "",
        'device-id': "1df4efae59648ac3"
    }
    try:
        response2 = requests.post(url2, data=payload2, headers=headers2, timeout=15, verify=False)
        d = response2.json()
        if d.get('access_token'):
            d['_number'] = number
        elif d.get('error'):
            return {"error": f"فشل تبادل الـ token: {d.get('error_description', d.get('error'))}"}
        return d
    except Exception as e:
        return {"error": "فشل تبادل الـ token"}

def get_promos(tok, num):
    url = "https://web.vodafone.com.eg/services/dxl/ramadanpromo/promotion"
    params = {
        '@type': "RamadanHub",
        'channel': "website",
        'msisdn': num,
    }
    headers = {
        'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Mobile Safari/537.36",
        'Accept': "application/json",
        'Accept-Encoding': "gzip, deflate, br, zstd",
        'Authorization': f"Bearer {tok}",
        'Accept-Language': "AR",
        'msisdn': num,
        'clientId': "WebsiteConsumer",
        'api-host': "PromotionHost",
        'channel': "APP_PORTAL",
        'Content-Type': "application/json",
        'Referer': "https://web.vodafone.com.eg/portal/hub",
    }
    cards = []
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15, verify=False)
        data = response.json()
    except: return cards
    if not isinstance(data, list): return cards
    try:
        s = data[1]['pattern']
    except: return cards
    printed = set()
    for x in s:
        try:
            ch = x['action'][0]['characteristics']
            amount = str(ch[0]['value'])
            units_val = str(ch[1]['value'])
            card = str(ch[3]['value'])
            remaining = str(ch[2]['value']) if len(ch) > 2 else "0"
            if card.startswith(('014','01')): continue
            if card in printed: continue
            if float(units_val) <= 1: continue
            printed.add(card)
            cards.append({
                'serial': card,
                'gift': int(float(units_val)),
                'amount': int(float(amount)),
                'remaining': remaining,
            })
        except: continue
    return sorted(cards, key=lambda x: -x['gift'])

def do_redeem(tok, num, serial):
    try:
        payload = {
            "@type": "Promo",
            "channel": {"id": "1"},
            "context": {"type": "RamadanRedeemFromHub"},
            "pattern": [{"characteristics": [{"name": "cardSerial", "value": serial}]}]
        }
        headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Mobile Safari/537.36",
            'Accept': "application/json",
            'Accept-Encoding': "gzip, deflate, br, zstd",
            'Content-Type': "application/json",
            'Authorization': f"Bearer {tok}",
            'Accept-Language': "AR",
            'msisdn': num,
            'clientId': "WebsiteConsumer",
            'channel': "WEB",
            'Origin': "https://web.vodafone.com.eg",
            'Referer': "https://web.vodafone.com.eg/portal/hub",
        }
        r = requests.post("https://web.vodafone.com.eg/services/dxl/ramadanpromo/promotion",
                          data=json.dumps(payload), headers=headers, timeout=15, verify=False)
        return r.status_code
    except: return 500

@app.route('/', methods=['GET','POST'])
def index():
    err = ''
    if request.args.get('logout'):
        drop(session.get('number',''))
        session.clear(); return redirect('/')
    if request.args.get('ping') and session.get('logged_in'):
        touch(session.get('number',''))
        return jsonify({'active_users': count()})
    if request.args.get('fetch') and session.get('logged_in'):
        touch(session.get('number',''))
        if time.time() >= session.get('token_exp', 0):
            if session.get('login_method') == 'data':
                res = data_login()
            else:
                res = pw_login(session['number'], session['password'])
            if res.get('access_token'):
                session['token'] = res['access_token']
                session['token_exp'] = int(time.time()) + int(res.get('expires_in', 3600)) - 120
                if res.get('_number'): session['number'] = res['_number']
        cards = get_promos(session['token'], session['number'])
        return jsonify({'success': True, 'promos': cards, 'number': session['number'], 'active_users': count()})
    if request.args.get('redeem') and session.get('logged_in'):
        serial = request.args.get('serial', '').strip()
        target = request.args.get('target', session.get('number', '')).strip()
        tok = session['token']
        if target != session.get('number', ''):
            tp = request.args.get('tpass', '').strip()
            if tp:
                r2 = pw_login(target, tp)
                if r2.get('access_token'): tok = r2['access_token']
        code = do_redeem(tok, target, serial)
        return jsonify({'success': code == 200, 'code': code})
    if request.method == 'POST' and request.form.get('action') == 'login':
        method = request.form.get('method', 'password')
        if method == 'data':
            res = data_login()
            if res.get('access_token'):
                session.update({'logged_in': True, 'token': res['access_token'],
                    'token_exp': int(time.time()) + int(res.get('expires_in', 3600)) - 120,
                    'number': res.get('_number', ''), 'password': '', 'login_method': 'data'})
                touch(session['number']); return redirect('/')
            err = res.get('error') or 'فشل — تأكد إن الداتا شغالة على خط فودافون مش واي فاي'
        else:
            num = request.form.get('number', '').strip()
            pw = request.form.get('password', '').strip()
            if num and pw:
                res = pw_login(num, pw)
                if res.get('access_token'):
                    session.update({'logged_in': True, 'token': res['access_token'],
                        'token_exp': int(time.time()) + int(res.get('expires_in', 3600)) - 120,
                        'number': num, 'password': pw, 'login_method': 'password'})
                    touch(num); return redirect('/')
                err = 'الرقم أو الباسورد غلط'
            else: err = 'ادخل الرقم والباسورد'
    return render_template_string(HTML,
        is_logged_in=session.get('logged_in', False),
        user_number=session.get('number', ''),
        login_error=err,
        active_count=count() if session.get('logged_in') else 0,
        form_number=request.form.get('number', '') if request.method == 'POST' else '')

HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1,user-scalable=no"/>
<title>TALASHNY</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;900&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet"/>
<style>
:root{
  --red:#e60000;--red2:#9a0000;
  --g1:#c8a84b;--g2:#f5d070;--g3:#8a6820;
  --bg:#07070a;--l1:#0d0d12;--l2:#111116;--l3:#17171e;--l4:#1e1e26;
  --ink:#eeeae0;--ink2:#9a9080;--ink3:#4a4840;
  --st:rgba(200,168,75,.1);--st2:rgba(200,168,75,.22);
  --r:16px;--rx:10px;--rs:8px;
  --sp:cubic-bezier(.34,1.56,.64,1);--ease:cubic-bezier(.4,0,.2,1);
  --bh:74px;
}
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box;}
html{-webkit-font-smoothing:antialiased;}
body{font-family:'Cairo',sans-serif;background:var(--bg);color:var(--ink);min-height:100vh;overflow-x:hidden;}
body::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background:radial-gradient(ellipse 70% 35% at 50% -8%,rgba(200,168,75,.09),transparent 60%);}

/* ── BANNER ── */
.banner{
  position:fixed;top:0;left:0;right:0;height:var(--bh);z-index:1000;
  background:linear-gradient(175deg,#000 0%,rgba(2,2,4,.97) 100%);
  border-radius:0 0 32px 32px;
  border-bottom:1px solid rgba(200,168,75,.12);
  box-shadow:0 4px 30px rgba(0,0,0,.8);
  display:flex;align-items:center;
  padding:0 18px;gap:10px;
}
.banner::after{
  content:'';position:absolute;bottom:-1.5px;left:12%;right:12%;height:1.5px;
  background:linear-gradient(90deg,transparent,var(--g3) 25%,var(--g2) 50%,var(--g3) 75%,transparent);
  border-radius:2px;
}
.btitle{
  flex:1;display:flex;font-size:1.85rem;font-weight:900;letter-spacing:7px;
  text-transform:uppercase;
}
.btitle span{
  background:linear-gradient(90deg,#777 0%,#fff 22%,#ccc 46%,#fff 72%,#777 100%);
  background-size:300% 100%;-webkit-background-clip:text;-webkit-text-fill-color:transparent;
  animation:chrome 4s linear infinite;animation-delay:calc(var(--i)*.13s);
}
@keyframes chrome{0%{background-position:300% center}100%{background-position:-300% center}}

/* عداد المتصلين في البانر — يسار بجانب الاسم */
.bonline{
  display:flex;align-items:center;gap:5px;
  background:rgba(76,255,154,.05);
  border:1px solid rgba(76,255,154,.13);
  border-radius:18px;padding:4px 10px 4px 8px;
  flex-shrink:0;order:-1;
}
.bonline .dot{width:5px;height:5px;border-radius:50%;background:#4cff9a;
  box-shadow:0 0 5px #4cff9a;animation:blink 2s ease-in-out infinite;}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.bonline .num{font-family:'JetBrains Mono',monospace;font-size:.65rem;font-weight:700;color:#4cff9a;}
.bonline .lbl{font-size:.6rem;color:rgba(76,255,154,.45);font-weight:600;}

/* ── PAGE ── */
.page{max-width:420px;margin:0 auto;padding:0 11px;position:relative;z-index:1;}
@keyframes up{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}

/* ── LOGIN ── */
#LS{min-height:100vh;display:flex;align-items:center;justify-content:center;
  padding:calc(var(--bh)+20px) 13px 80px;animation:up .45s var(--sp) both;}
.lw{width:100%;max-width:370px;display:flex;flex-direction:column;gap:10px;}
.lbrand{text-align:center;padding:4px 0;}
.lico{width:44px;height:44px;border-radius:50%;margin:0 auto 7px;
  background:var(--l3);border:1px solid var(--st2);
  display:flex;align-items:center;justify-content:center;}
.lico svg{width:18px;height:18px;stroke:var(--g1);stroke-width:1.8;fill:none;}
.lsup{font-size:.47rem;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:var(--ink3);margin-bottom:2px;}
.lh{font-size:1.05rem;font-weight:700;color:var(--ink);}
.lh em{font-style:normal;color:transparent;background:linear-gradient(135deg,var(--g1),var(--g2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;}

/* tabs */
.tabs{display:flex;background:var(--l2);border:1px solid var(--st);border-radius:var(--rx);padding:3px;gap:3px;}
.tab{flex:1;padding:8px 4px;border-radius:var(--rs);text-align:center;font-size:.68rem;font-weight:700;
  color:var(--ink3);cursor:pointer;transition:all .2s;display:flex;align-items:center;justify-content:center;gap:4px;}
.tab svg{width:11px;height:11px;stroke:currentColor;stroke-width:1.8;fill:none;}
.tab.on{background:rgba(200,168,75,.1);color:var(--g2);border:1px solid rgba(200,168,75,.25);}
.tab:active{transform:scale(.95);}

/* form */
.fs{display:none;flex-direction:column;}
.fs.show{display:flex;}
.fc{background:var(--l1);border:1px solid var(--st);border-radius:var(--r);overflow:hidden;}
.fr{display:flex;align-items:stretch;border-bottom:1px solid var(--st);position:relative;}
.fr:last-of-type{border-bottom:none;}
.fr::before{content:'';position:absolute;right:0;top:0;bottom:0;width:0;background:var(--g1);transition:width .15s;}
.fr:focus-within::before{width:2px;}
.fi{width:42px;display:flex;align-items:center;justify-content:center;border-left:1px solid var(--st);background:var(--l2);}
.fi svg{width:13px;height:13px;stroke:var(--ink3);stroke-width:1.6;fill:none;transition:stroke .2s;}
.fr:focus-within .fi svg{stroke:var(--g1);}
.fb{flex:1;padding:10px 11px;}
.fl{font-size:.44rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);margin-bottom:2px;transition:color .2s;}
.fr:focus-within .fl{color:var(--g1);}
.fin{background:transparent;border:none;outline:none;font-family:'Cairo',sans-serif;font-size:.86rem;font-weight:600;color:var(--ink);width:100%;}
.fin::placeholder{color:var(--ink3);font-weight:400;font-size:.74rem;}
.dinfo{display:flex;gap:8px;padding:11px 12px;background:rgba(200,168,75,.025);border-bottom:1px solid var(--st);}
.dinfo svg{width:13px;height:13px;stroke:var(--g1);stroke-width:1.6;fill:none;flex-shrink:0;margin-top:2px;}
.dinfo p{font-size:.65rem;color:var(--ink2);line-height:1.8;}
.dinfo strong{color:var(--g2);display:block;font-size:.67rem;margin-bottom:1px;}

/* login button */
.bw{padding:11px;}
.lbtn{width:100%;padding:12px;border:none;border-radius:var(--rs);
  background:linear-gradient(135deg,var(--g3),var(--g1) 50%,var(--g2));
  color:#1a0e00;font-family:'Cairo',sans-serif;font-size:.84rem;font-weight:900;
  cursor:pointer;display:flex;align-items:center;justify-content:center;gap:7px;
  box-shadow:0 4px 16px rgba(200,168,75,.22);position:relative;overflow:hidden;
  transition:transform .18s var(--sp),box-shadow .18s;}
.lbtn::before{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(255,255,255,.12),transparent 55%);}
.lbtn::after{content:'';position:absolute;top:0;left:-110%;width:50%;height:100%;
  background:linear-gradient(105deg,transparent,rgba(255,255,255,.16),transparent);
  animation:sh 4s ease-in-out infinite;}
@keyframes sh{0%,100%{left:-110%}50%{left:150%}}
.lbtn svg,.lbtn span{position:relative;z-index:1;}
.lbtn svg{width:13px;height:13px;stroke:currentColor;stroke-width:2.2;fill:none;}
.lbtn:hover{transform:translateY(-1px);box-shadow:0 6px 20px rgba(200,168,75,.3);}
.lbtn:active{transform:scale(.97);}
.lbtn:disabled{opacity:.5;pointer-events:none;}
.bspin{width:13px;height:13px;border-radius:50%;border:2px solid rgba(26,14,0,.2);border-top-color:#1a0e00;animation:rspin .7s linear infinite;display:none;z-index:1;}
.lbtn.loading .bspin{display:block;}
.lbtn.loading .btxt{display:none;}
@keyframes rspin{to{transform:rotate(360deg)}}
.err{display:flex;align-items:flex-start;gap:7px;
  background:rgba(230,0,0,.04);border:1px solid rgba(230,0,0,.16);
  border-radius:var(--rs);padding:9px 11px;
  font-size:.66rem;color:#ff8a80;font-weight:600;line-height:1.7;animation:up .3s both;}
.err svg{width:12px;height:12px;stroke:#ff6060;stroke-width:2;fill:none;flex-shrink:0;margin-top:2px;}
.lnote{text-align:center;font-size:.55rem;color:var(--ink3);}

/* ── APP ── */
#APP{display:none;}
#APP.on{display:block;}
.ab{padding-top:calc(var(--bh)+12px);padding-bottom:82px;}

/* user bar */
.ubar{display:flex;align-items:center;justify-content:space-between;
  padding:7px 11px;margin-bottom:10px;
  background:var(--l1);border:1px solid var(--st);border-radius:var(--rs);}
.ul{display:flex;align-items:center;gap:6px;}
.udot{width:5px;height:5px;border-radius:50%;background:var(--g2);}
.unum{font-family:'JetBrains Mono',monospace;font-size:.74rem;font-weight:700;color:var(--g2);}
.upill{display:flex;align-items:center;gap:4px;
  background:rgba(76,255,154,.05);border:1px solid rgba(76,255,154,.12);
  border-radius:16px;padding:3px 8px;}
.updot{width:4px;height:4px;border-radius:50%;background:#4cff9a;animation:blink 2s ease-in-out infinite;}
.upn{font-family:'JetBrains Mono',monospace;font-size:.6rem;font-weight:700;color:#4cff9a;}
.upl{font-size:.56rem;color:rgba(76,255,154,.42);font-weight:600;}
.bout{display:flex;align-items:center;gap:3px;padding:4px 9px;
  border:1px solid rgba(230,0,0,.14);border-radius:var(--rs);
  font-family:'Cairo',sans-serif;font-size:.61rem;font-weight:700;
  color:rgba(230,0,0,.38);cursor:pointer;transition:all .18s;text-decoration:none;background:transparent;}
.bout:hover{color:#ff6060;border-color:rgba(230,0,0,.3);}
.bout svg{width:8px;height:8px;stroke:currentColor;stroke-width:2;fill:none;}

/* ── SEARCH ── */
#US{display:flex;flex-direction:column;gap:10px;animation:up .4s var(--sp) both;}
.scard{overflow:hidden;background:var(--l1);border:1px solid var(--st);border-radius:var(--r);}
.sh{padding:7px 12px 2px;font-size:.5rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;
  color:var(--ink3);display:flex;align-items:center;gap:5px;}
.sh::before{content:'';display:block;width:10px;height:1px;background:linear-gradient(90deg,transparent,var(--g1));}

/* units input */
.urow{display:flex;align-items:stretch;border-bottom:1px solid var(--st);position:relative;}
.urow::before{content:'';position:absolute;right:0;top:0;bottom:0;width:0;background:var(--g1);transition:width .15s;}
.urow:focus-within::before{width:2px;}
.uico{width:44px;display:flex;align-items:center;justify-content:center;border-left:1px solid var(--st);background:var(--l2);}
.uico svg{width:15px;height:15px;stroke:var(--ink3);stroke-width:1.6;fill:none;transition:stroke .2s;}
.urow:focus-within .uico svg{stroke:var(--g1);}
.uright{flex:1;padding:11px 0;display:flex;flex-direction:column;align-items:center;}
.ulbl{font-size:.48rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);margin-bottom:3px;}
.uinp{background:transparent;border:none;outline:none;font-family:'JetBrains Mono',monospace;
  font-size:1.7rem;font-weight:700;color:var(--ink);text-align:center;max-width:140px;}
.uinp::placeholder{font-family:'Cairo',sans-serif;color:var(--ink3);font-size:.76rem;font-weight:400;}

/* chips */
.qs{padding:8px 11px 10px;border-bottom:1px solid var(--st);}
.qlbl{font-size:.48rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;
  color:var(--ink3);margin-bottom:6px;display:flex;align-items:center;gap:5px;}
.qlbl::before{content:'';display:block;width:9px;height:1px;background:linear-gradient(90deg,transparent,var(--g1));}
.chips{display:flex;gap:4px;}
.chip{flex:1;padding:6px 2px;background:var(--l2);border:1px solid var(--st);border-radius:var(--rs);
  text-align:center;font-family:'JetBrains Mono',monospace;font-size:.78rem;font-weight:700;
  color:var(--ink2);cursor:pointer;transition:all .18s var(--sp);}
.chip:hover{border-color:var(--st2);color:var(--g2);}
.chip.on{background:rgba(200,168,75,.1);border-color:rgba(200,168,75,.35);color:var(--g2);}
.chip:active{transform:scale(.9);}

/* charge mode */
.cms{padding:10px 11px;border-bottom:1px solid var(--st);}
.cml{font-size:.48rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;
  color:var(--ink3);margin-bottom:7px;display:flex;align-items:center;gap:5px;}
.cml::before{content:'';display:block;width:9px;height:1px;background:linear-gradient(90deg,transparent,var(--g1));}
.cmbs{display:flex;gap:6px;}
.cmb{flex:1;padding:11px 5px;background:var(--l2);border:1px solid var(--st);
  border-radius:var(--rx);text-align:center;cursor:pointer;transition:all .18s var(--sp);}
.cmb.ol.on{background:rgba(230,0,0,.05);border-color:rgba(230,0,0,.28);}
.cmb.dl.on{background:rgba(200,168,75,.07);border-color:rgba(200,168,75,.28);}
.cmb:active{transform:scale(.96);}
.cmico{width:24px;height:24px;margin:0 auto 5px;border-radius:50%;display:flex;align-items:center;justify-content:center;}
.cmico svg{width:12px;height:12px;stroke-width:1.8;fill:none;}
.cmb.ol .cmico{background:rgba(230,0,0,.07);border:1px solid rgba(230,0,0,.15);}
.cmb.ol .cmico svg{stroke:var(--red);}
.cmb.dl .cmico{background:rgba(200,168,75,.07);border:1px solid rgba(200,168,75,.15);}
.cmb.dl .cmico svg{stroke:var(--g2);}
.cmb strong{display:block;font-size:.68rem;font-weight:700;color:var(--ink);margin-bottom:1px;}
.cmb small{font-size:.54rem;color:var(--ink3);}

/* target */
.tgs{padding:0 11px;max-height:0;overflow:hidden;transition:max-height .3s var(--ease),padding .28s;}
.tgs.open{max-height:185px;padding:10px 11px;}
.tgl{font-size:.48rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;
  color:var(--ink3);margin-bottom:6px;display:flex;align-items:center;gap:5px;}
.tgl::before{content:'';display:block;width:9px;height:1px;background:linear-gradient(90deg,transparent,var(--g1));}
.tgbs{display:flex;gap:5px;}
.tgb{flex:1;padding:7px 4px;background:var(--l2);border:1px solid var(--st);
  border-radius:var(--rs);text-align:center;font-size:.65rem;font-weight:700;
  color:var(--ink2);cursor:pointer;transition:all .18s var(--sp);}
.tgb.on{background:rgba(200,168,75,.08);border-color:rgba(200,168,75,.3);color:var(--g2);}
.tgb:active{transform:scale(.93);}
.otf{margin-top:7px;display:none;flex-direction:column;gap:4px;}
.otf.show{display:flex;}
.ofl{display:flex;align-items:stretch;border:1px solid var(--st);border-radius:var(--rs);overflow:hidden;}
.ofic{width:34px;display:flex;align-items:center;justify-content:center;background:var(--l2);border-left:1px solid var(--st);}
.ofic svg{width:11px;height:11px;stroke:var(--ink3);stroke-width:1.6;fill:none;}
.ofl input{flex:1;background:transparent;border:none;outline:none;padding:7px 10px;
  font-family:'Cairo',sans-serif;font-size:.78rem;font-weight:600;color:var(--ink);}
.ofl input::placeholder{color:var(--ink3);font-size:.7rem;font-weight:400;}

/* go */
.gos{padding:11px;}
.gobtn{width:100%;padding:13px;border:none;border-radius:var(--rx);
  background:linear-gradient(135deg,var(--red2),var(--red) 60%,#ff1818);
  color:#fff;font-family:'Cairo',sans-serif;font-size:.86rem;font-weight:900;
  cursor:pointer;display:flex;align-items:center;justify-content:center;gap:7px;
  box-shadow:0 4px 20px rgba(230,0,0,.26);position:relative;overflow:hidden;
  transition:transform .18s var(--sp),box-shadow .18s;}
.gobtn::before{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(255,255,255,.08),transparent 50%);}
.gobtn::after{content:'';position:absolute;top:0;left:-110%;width:50%;height:100%;
  background:linear-gradient(105deg,transparent,rgba(255,255,255,.09),transparent);animation:sh 4s ease-in-out infinite;}
.gobtn svg,.gobtn span{position:relative;z-index:1;}
.gobtn svg{width:14px;height:14px;stroke:#fff;stroke-width:2.2;fill:none;}
.gobtn:hover{transform:translateY(-1px);box-shadow:0 7px 24px rgba(230,0,0,.35);}
.gobtn:active{transform:scale(.97);}

/* ── CARDS SCREEN ── */
#CS{display:none;flex-direction:column;gap:8px;animation:up .3s var(--sp) both;}
.csbar{display:flex;align-items:center;justify-content:space-between;padding:9px 12px;
  background:var(--l1);border:1px solid var(--st);border-radius:var(--r);}
.csi{font-size:.74rem;color:var(--ink2);}
.csi strong{color:var(--g2);}
.csbk{display:flex;align-items:center;gap:3px;background:var(--l3);border:1px solid var(--st);
  border-radius:var(--rs);padding:5px 10px;font-size:.62rem;font-weight:700;color:var(--ink2);
  cursor:pointer;transition:all .18s;}
.csbk:hover{color:var(--ink);}
.csbk svg{width:8px;height:8px;stroke:currentColor;stroke-width:2.5;fill:none;}

/* timer */
.tc{padding:11px 14px;background:var(--l1);border:1px solid var(--st);border-radius:var(--r);}
.tt{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;}
.ttl{display:flex;align-items:center;gap:6px;}
.trd{width:5px;height:5px;border-radius:50%;background:var(--red);animation:ping 1.5s ease-in-out infinite;}
@keyframes ping{0%{box-shadow:0 0 0 0 rgba(230,0,0,.4)}70%{box-shadow:0 0 0 6px transparent}100%{box-shadow:0 0 0 0 transparent}}
.ttxt{font-size:.62rem;color:var(--ink2);}
.tnum{font-family:'JetBrains Mono',monospace;font-size:1.8rem;font-weight:700;color:var(--ink);transition:color .3s;}
.tnum.hot{color:var(--red);}
.tbar{height:2px;background:var(--l4);border-radius:2px;overflow:hidden;}
.tprog{height:100%;border-radius:2px;background:linear-gradient(90deg,var(--g3),var(--g2));transition:width 1s linear;}

/* toggle */
.tgl2{display:flex;align-items:center;justify-content:space-between;padding:10px 12px;
  cursor:pointer;background:var(--l1);border:1px solid var(--st);border-radius:var(--r);}
.tgl2 strong{display:block;font-size:.7rem;font-weight:700;color:var(--ink);margin-bottom:1px;}
.tgl2 small{font-size:.57rem;color:var(--ink2);}
.sw{position:relative;width:36px;height:20px;flex-shrink:0;}
.sw input{opacity:0;width:0;height:0;position:absolute;}
.sw-t{position:absolute;inset:0;border-radius:20px;background:var(--l4);border:1px solid var(--st);cursor:pointer;transition:all .25s;}
.sw-t::before{content:'';position:absolute;width:14px;height:14px;border-radius:50%;background:#555;top:2px;right:2px;box-shadow:0 1px 3px rgba(0,0,0,.5);transition:transform .25s var(--sp),background .25s;}
.sw input:checked+.sw-t{background:linear-gradient(135deg,var(--g3),var(--g1));border-color:rgba(200,168,75,.25);}
.sw input:checked+.sw-t::before{transform:translateX(-16px);background:#fff;}

/* ══════════════════════════════════════════
   كروت جديدة — تصميم horizontal مختلف
   ══════════════════════════════════════════ */
.cl{display:flex;flex-direction:column;gap:8px;}

.pc{
  border-radius:var(--r);
  background:var(--l1);
  border:1px solid rgba(255,255,255,.05);
  overflow:hidden;
  position:relative;
  animation:cardIn .35s var(--sp) both;
  animation-delay:calc(var(--i,0)*.06s);
  transition:transform .2s var(--sp),box-shadow .2s;
}
.pc:active{transform:scale(.99);}

@keyframes cardIn{from{opacity:0;transform:translateY(8px) scale(.98)}to{opacity:1;transform:none}}

/* الشريط الجانبي الملون */
.pc-stripe{
  position:absolute;right:0;top:0;bottom:0;width:3px;
  background:linear-gradient(180deg,transparent,var(--g3) 30%,var(--g2) 60%,transparent);
  opacity:.5;
}
.pc.best .pc-stripe{opacity:1;width:4px;}

/* كارت الأفضل */
.pc.best{
  background:linear-gradient(135deg,#0d0d12 0%,rgba(200,168,75,.04) 100%);
  border-color:rgba(200,168,75,.25);
  box-shadow:0 2px 20px rgba(200,168,75,.06);
}
/* خط ذهبي علوي للأفضل */
.pc.best::after{
  content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent 5%,rgba(200,168,75,.5) 40%,rgba(245,208,112,.7) 60%,rgba(200,168,75,.5) 80%,transparent 95%);
}

/* الجزء العلوي: سيريال + بادجات */
.pc-top{
  display:flex;align-items:center;justify-content:space-between;
  padding:9px 14px 0;
}
.pc-serial{
  font-family:'JetBrains Mono',monospace;
  font-size:.98rem;font-weight:700;
  color:var(--ink);letter-spacing:2px;
}
.pc-badges{display:flex;align-items:center;gap:5px;}
.badge-best{
  font-size:.45rem;font-weight:900;letter-spacing:1.5px;text-transform:uppercase;
  color:#0a0600;
  background:linear-gradient(135deg,var(--g1),var(--g2));
  padding:2px 7px;border-radius:4px;
}
.badge-rank{
  font-family:'JetBrains Mono',monospace;font-size:.55rem;font-weight:700;
  color:var(--ink3);background:var(--l3);
  border:1px solid var(--st);padding:2px 6px;border-radius:4px;
}

/* الوسط: 3 أعمدة Stats */
.pc-stats{
  display:flex;align-items:stretch;
  padding:8px 14px 0;
  gap:0;
}
.pstat{
  flex:1;display:flex;flex-direction:column;align-items:center;
  padding:8px 4px;
  position:relative;
}
.pstat:not(:last-child)::after{
  content:'';position:absolute;left:0;top:20%;bottom:20%;width:1px;
  background:linear-gradient(180deg,transparent,rgba(255,255,255,.06),transparent);
}
.pstat-val{
  font-family:'JetBrains Mono',monospace;
  font-size:1.15rem;font-weight:700;
  line-height:1;margin-bottom:3px;
}
.pstat-val.v-gold{color:var(--g2);}
.pstat-val.v-red{color:#ff7070;}
.pstat-val.v-blue{color:#7eb3ff;}
.pstat-lbl{
  font-size:.42rem;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;
  color:var(--ink3);
}

/* الجزء السفلي: أزرار */
.pc-actions{
  display:flex;align-items:center;justify-content:space-between;
  padding:8px 12px 9px;
  border-top:1px solid rgba(255,255,255,.04);
  margin-top:6px;
}
.pc-copy{
  display:flex;align-items:center;gap:4px;
  padding:5px 10px;
  background:var(--l3);border:1px solid var(--st);border-radius:var(--rs);
  font-size:.6rem;font-weight:700;color:var(--ink3);
  cursor:pointer;transition:all .18s var(--sp);
}
.pc-copy svg{width:9px;height:9px;stroke:currentColor;stroke-width:2;fill:none;}
.pc-copy:hover{color:var(--g2);border-color:rgba(200,168,75,.3);}
.pc-copy:active{transform:scale(.9);}

.bcharge{
  display:inline-flex;align-items:center;gap:5px;
  padding:6px 14px;
  background:linear-gradient(135deg,rgba(230,0,0,.15),rgba(230,0,0,.08));
  border:1px solid rgba(230,0,0,.3);border-radius:14px;
  font-family:'Cairo',sans-serif;font-size:.68rem;font-weight:700;color:#ff8a80;
  cursor:pointer;transition:all .2s var(--sp);
}
.bcharge svg{width:10px;height:10px;stroke:currentColor;stroke-width:2;fill:none;}
.bcharge:hover{background:rgba(230,0,0,.22);box-shadow:0 2px 12px rgba(230,0,0,.2);}
.bcharge:active{transform:scale(.94);}
.bcharge.loading{opacity:.4;pointer-events:none;}

.bdial{
  display:inline-flex;align-items:center;gap:5px;text-decoration:none;
  padding:6px 14px;
  background:rgba(200,168,75,.07);
  border:1px solid rgba(200,168,75,.2);border-radius:14px;
  font-family:'Cairo',sans-serif;font-size:.68rem;font-weight:700;color:rgba(200,168,75,.7);
  transition:all .2s;
}
.bdial svg{width:10px;height:10px;stroke:currentColor;stroke-width:2;fill:none;}
.bdial:hover{background:rgba(200,168,75,.13);color:var(--g2);}

/* loading/empty */
.ls{display:flex;flex-direction:column;align-items:center;gap:8px;
  padding:36px 16px;background:var(--l1);border:1px solid var(--st);border-radius:var(--r);}
.spinner{width:24px;height:24px;border-radius:50%;border:2px solid var(--st);
  border-top-color:var(--g1);animation:rspin .8s linear infinite;}
.slbl{font-size:.65rem;color:var(--ink2);}
.es{text-align:center;padding:28px 16px;font-size:.72rem;color:var(--ink2);
  background:var(--l1);border:1px solid var(--st);border-radius:var(--r);}
.es svg{width:20px;height:20px;stroke:var(--ink3);stroke-width:1.5;fill:none;margin-bottom:7px;display:block;margin-inline:auto;}

/* toast */
.toast{position:fixed;bottom:86px;left:50%;transform:translateX(-50%) translateY(12px);
  background:rgba(10,10,16,.97);border:1px solid var(--st);border-radius:24px;
  padding:7px 15px;font-family:'Cairo',sans-serif;font-size:.7rem;font-weight:700;
  color:var(--ink);opacity:0;pointer-events:none;transition:all .25s var(--sp);
  z-index:9999;white-space:nowrap;}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0);}
.toast.ok{border-color:rgba(76,255,154,.25);color:#4cff9a;}
.toast.err{border-color:rgba(230,0,0,.25);color:#ff8a80;}

/* nav */
.nav{position:fixed;bottom:0;left:0;right:0;z-index:200;
  display:flex;justify-content:space-around;align-items:center;
  padding:8px 0 14px;background:rgba(3,3,6,.97);
  backdrop-filter:blur(20px);border-top:1px solid var(--st);}
.nav a{text-decoration:none;color:var(--ink3);display:flex;align-items:center;
  padding:5px 15px;border-radius:8px;transition:color .18s,transform .2s var(--sp);}
.nav a:hover{color:var(--g1);transform:translateY(-3px);}
.nav a svg{width:18px;height:18px;stroke:currentColor;stroke-width:1.6;fill:none;}
::-webkit-scrollbar{width:2px;}::-webkit-scrollbar-track{background:var(--l1);}::-webkit-scrollbar-thumb{background:var(--l4);}
</style>
</head>
<body oncontextmenu="return false">

<!-- BANNER -->
<div class="banner">
  {% if is_logged_in %}
  <div class="bonline">
    <div class="dot"></div>
    <span class="num" id="BN">{{ active_count }}</span>
    <span class="lbl">متصل</span>
  </div>
  {% endif %}
  <div class="btitle">
    <span style="--i:0">Y</span><span style="--i:1">N</span><span style="--i:2">H</span>
    <span style="--i:3">S</span><span style="--i:4">A</span><span style="--i:5">L</span>
    <span style="--i:6">A</span><span style="--i:7">T</span>
  </div>
</div>

{% if not is_logged_in %}
<div id="LS">
  <div class="lw">
    <div class="lbrand">
      <div class="lico"><svg viewBox="0 0 24 24"><polyline points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg></div>
      <div class="lsup">TALASHNY — Premium</div>
      <div class="lh">أهلاً في <em>TALASHNY</em></div>
    </div>
    {% if login_error %}
    <div class="err">
      <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
      {{ login_error }}
    </div>
    {% endif %}
    <div class="tabs">
      <div class="tab on" id="TP" onclick="sw('pass')">
        <svg viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>رقم وباسورد
      </div>
      <div class="tab" id="TD" onclick="sw('data')">
        <svg viewBox="0 0 24 24"><rect x="5" y="2" width="14" height="20" rx="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>بيانات الجهاز
      </div>
    </div>
    <form method="POST" id="FP" class="fs show">
      <input type="hidden" name="action" value="login">
      <input type="hidden" name="method" value="password">
      <div class="fc">
        <div class="fr">
          <div class="fi"><svg viewBox="0 0 24 24"><rect x="5" y="2" width="14" height="20" rx="2"/></svg></div>
          <div class="fb"><div class="fl">رقم الموبايل</div><input class="fin" type="tel" name="number" placeholder="01XXXXXXXXX" inputmode="tel" autocomplete="tel" required value="{{ form_number }}"></div>
        </div>
        <div class="fr">
          <div class="fi"><svg viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg></div>
          <div class="fb"><div class="fl">الباسورد</div><input class="fin" type="password" name="password" placeholder="••••••••" autocomplete="current-password" required></div>
        </div>
        <div class="bw"><button type="submit" class="lbtn"><svg viewBox="0 0 24 24"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg><span class="btxt">دخـول</span><div class="bspin"></div></button></div>
      </div>
    </form>
    <form method="POST" id="FD" class="fs">
      <input type="hidden" name="action" value="login">
      <input type="hidden" name="method" value="data">
      <div class="fc">
        <div class="dinfo">
          <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          <p><strong>تسجيل دخول بداتا الجهاز</strong>لازم تكون متصل بداتا فودافون مش واي فاي — النظام بيجيب بياناتك تلقائياً من الشبكة.</p>
        </div>
        <div class="bw"><button type="submit" class="lbtn"><svg viewBox="0 0 24 24"><path d="M1 6s0-2 2-2 2 2 2 2v8s0 2 2 2 2-2 2-2V6s0-2 2-2 2 2 2 2v8s0 2 2 2 2-2 2-2V6s0-2 2-2 2 2 2 2"/></svg><span class="btxt">دخول بالداتا</span><div class="bspin"></div></button></div>
      </div>
    </form>
    <div class="lnote">بياناتك محمية ومش بتتحفظ على السيرفر</div>
  </div>
</div>
{% else %}
<div id="APP" class="on">
  <div class="ab">
    <div class="page">
      <!-- SEARCH -->
      <div id="US">
        <div class="ubar">
          <div class="ul"><div class="udot"></div><span class="unum">{{ user_number }}</span></div>
          <div style="display:flex;align-items:center;gap:6px;">
            <div class="upill"><div class="updot"></div><span class="upn" id="UON">{{ active_count }}</span><span class="upl">متصل</span></div>
            <a href="/?logout=1" class="bout"><svg viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>خروج</a>
          </div>
        </div>
        <div class="scard">
          <div class="sh">فئة الكارت — وحدات</div>
          <div class="urow">
            <div class="uico"><svg viewBox="0 0 24 24"><polyline points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg></div>
            <div class="uright"><span class="ulbl">الحد الأدنى</span><input class="uinp" type="number" id="UI" placeholder="الوحدات" min="1" inputmode="numeric"></div>
          </div>
          <div class="qs">
            <div class="qlbl">اختيار سريع</div>
            <div class="chips">
              <button class="chip" onclick="setU(100,this)">100</button>
              <button class="chip" onclick="setU(300,this)">300</button>
              <button class="chip" onclick="setU(500,this)">500</button>
              <button class="chip" onclick="setU(700,this)">700</button>
              <button class="chip" onclick="setU(900,this)">900</button>
            </div>
          </div>
          <div class="cms">
            <div class="cml">طريقة الشحن</div>
            <div class="cmbs">
              <div class="cmb ol on" id="CMO" onclick="setMode('online')">
                <div class="cmico"><svg viewBox="0 0 24 24"><polyline points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg></div>
                <strong>أونلاين</strong><small>شحن مباشر</small>
              </div>
              <div class="cmb dl" id="CMD" onclick="setMode('dial')">
                <div class="cmico"><svg viewBox="0 0 24 24"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 13a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 2.24h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 9.91a16 16 0 0 0 6.09 6.09l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg></div>
                <strong>اتصال</strong><small>لوحة الأرقام</small>
              </div>
            </div>
          </div>
          <div class="tgs open" id="TGS">
            <div class="tgl">شحن على رقم</div>
            <div class="tgbs">
              <div class="tgb on" id="TGM" onclick="setTg('mine')">رقمي</div>
              <div class="tgb" id="TGO" onclick="setTg('other')">رقم تاني</div>
            </div>
            <div class="otf" id="OTF">
              <div class="ofl"><div class="ofic"><svg viewBox="0 0 24 24"><rect x="5" y="2" width="14" height="20" rx="2"/></svg></div><input type="tel" id="OTN" placeholder="01XXXXXXXXX" inputmode="tel"></div>
              <div class="ofl"><div class="ofic"><svg viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg></div><input type="password" id="OTP" placeholder="باسورد الرقم التاني"></div>
            </div>
          </div>
          <div class="gos">
            <button class="gobtn" onclick="startApp()">
              <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <span>ابدأ البحث</span>
            </button>
          </div>
        </div>
      </div>
      <!-- CARDS -->
      <div id="CS">
        <div class="csbar">
          <div class="csi">بحث عن <strong id="IU">—</strong></div>
          <button class="csbk" onclick="goBack()"><svg viewBox="0 0 24 24"><polyline points="9 18 15 12 9 6"/></svg>تغيير</button>
        </div>
        <div class="tc">
          <div class="tt">
            <div class="ttl"><div class="trd"></div><span class="ttxt">تحديث كل 7 ثواني</span></div>
            <span class="tnum" id="TN">—</span>
          </div>
          <div class="tbar"><div class="tprog" id="TPROG" style="width:100%"></div></div>
        </div>
        <div class="tgl2" onclick="document.getElementById('CC').click()">
          <div><strong>استمرار البحث بعد الشحن</strong><small id="TH">مفعّل — يكمل البحث بعد الشحن</small></div>
          <div class="sw"><input type="checkbox" id="CC" checked onchange="onTgl()"><div class="sw-t"></div></div>
        </div>
        <div id="CP"></div>
      </div>
    </div>
  </div>
</div>
{% endif %}

<nav class="nav">
  <a href="https://t.me/FY_TF" target="_blank"><svg viewBox="0 0 24 24"><path d="M21.5 2.5L2.5 10.5l7 2.5 2.5 7 3-4.5 4.5 3.5 2-16z"/></svg></a>
  <a href="https://wa.me/message/U6AIKBGFCNCQK1" target="_blank"><svg viewBox="0 0 24 24"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg></a>
  <a href="https://www.facebook.com/VI808IV" target="_blank"><svg viewBox="0 0 24 24"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/></svg></a>
</nav>
<div class="toast" id="TOAST"></div>

<script>
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function toast(m,t=''){const el=document.getElementById('TOAST');el.textContent=m;el.className='toast show'+(t?' '+t:'');clearTimeout(el._t);el._t=setTimeout(()=>el.classList.remove('show'),2600);}
function sw(t){
  document.getElementById('TP').classList.toggle('on',t==='pass');
  document.getElementById('TD').classList.toggle('on',t==='data');
  document.getElementById('FP').classList.toggle('show',t==='pass');
  document.getElementById('FD').classList.toggle('show',t==='data');
}
document.querySelectorAll('form.fs').forEach(f=>{
  f.addEventListener('submit',function(){const b=this.querySelector('.lbtn');if(b){b.classList.add('loading');b.disabled=true;}});
});

{% if is_logged_in %}
const SECS=7;
let units=0,mode='online',tg='mine',running=false,stopped=false,ti=null,ct=null,charged=false;

setInterval(async()=>{try{const d=await(await fetch('/?ping=1&_='+Date.now())).json();if(d.active_users!=null)updOn(d.active_users);}catch(e){}},60000);
function updOn(n){['BN','UON'].forEach(id=>{const el=document.getElementById(id);if(el)el.textContent=n;});}

function setU(n,b){document.getElementById('UI').value=n;document.querySelectorAll('.chip').forEach(x=>x.classList.remove('on'));b.classList.add('on');}
function setMode(m){mode=m;document.getElementById('CMO').classList.toggle('on',m==='online');document.getElementById('CMD').classList.toggle('on',m==='dial');document.getElementById('TGS').classList.toggle('open',m==='online');}
function setTg(t){tg=t;document.getElementById('TGM').classList.toggle('on',t==='mine');document.getElementById('TGO').classList.toggle('on',t==='other');document.getElementById('OTF').classList.toggle('show',t==='other');}
function onTgl(){const on=document.getElementById('CC').checked;document.getElementById('TH').textContent=on?'مفعّل — يكمل البحث بعد الشحن':'معطّل — يتوقف بعد أول كارت';}

function startApp(){
  const v=parseInt(document.getElementById('UI').value)||0;
  if(v<1){document.getElementById('UI').focus();return;}
  if(mode==='online'&&tg==='other'&&(!document.getElementById('OTN').value.trim()||!document.getElementById('OTP').value.trim())){toast('ادخل رقم وباسورد الرقم التاني','err');return;}
  units=v;stopped=false;charged=false;
  document.getElementById('IU').textContent=v+' وحدة';
  document.getElementById('US').style.display='none';
  document.getElementById('CS').style.display='flex';
  run();
}
function goBack(){stopped=true;clearInterval(ti);clearTimeout(ct);document.getElementById('CS').style.display='none';document.getElementById('US').style.display='flex';document.getElementById('CP').innerHTML='';running=false;stopT();}
function startTimer(s){return new Promise(r=>{clearInterval(ti);let rem=s;updT(rem,s);ti=setInterval(()=>{rem--;updT(rem,s);if(rem<=0){clearInterval(ti);r();}},1000);ct=setTimeout(r,s*1000+300);});}
function updT(r,t){const n=document.getElementById('TN'),p=document.getElementById('TPROG');if(!n||!p)return;n.textContent=Math.max(r,0);p.style.width=Math.max(0,r/t*100)+'%';n.classList.toggle('hot',r<=2);}
function stopT(){clearInterval(ti);const n=document.getElementById('TN'),p=document.getElementById('TPROG');if(n)n.textContent='—';if(p)p.style.width='0%';}

async function fetchC(){
  try{const d=await(await fetch('/?fetch=1&_='+Date.now())).json();
  if(d.active_users!=null)updOn(d.active_users);return d;}
  catch{return{success:false,promos:[]};}
}
function findBest(ps){return ps.find(p=>parseInt(p.gift)>=units)||null;}

async function doCharge(serial){
  let url='/?redeem=1&serial='+encodeURIComponent(serial);
  if(tg==='other'){url+='&target='+encodeURIComponent(document.getElementById('OTN').value.trim())+'&tpass='+encodeURIComponent(document.getElementById('OTP').value.trim());}
  const btn=document.querySelector('.bcharge[data-s="'+serial+'"]');if(btn)btn.classList.add('loading');
  try{
    const d=await(await fetch(url)).json();
    if(d.success){toast('تم شحن الكارت ✅','ok');charged=true;if(!document.getElementById('CC').checked)setTimeout(goBack,1300);}
    else toast('فشل الشحن ❌','err');
  }catch{toast('خطأ في الاتصال','err');}
  if(btn)btn.classList.remove('loading');
}

function renderCards(data){
  const panel=document.getElementById('CP');
  if(!data?.success||!data.promos?.length){
    if(!panel.querySelector('.cl'))panel.innerHTML='<div class="es"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>لا توجد كروت الآن<br><span style="font-size:.58rem;color:var(--ink3)">جاري البحث...</span></div>';
    return false;
  }
  const b=findBest(data.promos);
  let h='<div class="cl">';
  data.promos.forEach((p,i)=>{
    const iB=b&&p.serial===b.serial;
    const tel='tel:'+encodeURIComponent('*858*'+p.serial+'#');
    h+=`<div class="pc${iB?' best':''}" style="--i:${i}">
      <div class="pc-stripe"></div>
      <div class="pc-top">
        <span class="pc-serial">${esc(p.serial)}</span>
        <div class="pc-badges">
          ${iB?'<span class="badge-best">✦ أفضل</span>':''}
          <span class="badge-rank">#${i+1}</span>
        </div>
      </div>
      <div class="pc-stats">
        <div class="pstat">
          <span class="pstat-val v-gold">${esc(p.gift)}</span>
          <span class="pstat-lbl">وحدة</span>
        </div>
        <div class="pstat">
          <span class="pstat-val v-red">${esc(p.amount)}</span>
          <span class="pstat-lbl">جنيه</span>
        </div>
        <div class="pstat">
          <span class="pstat-val v-blue">${esc(p.remaining)}</span>
          <span class="pstat-lbl">متبقي</span>
        </div>
      </div>
      <div class="pc-actions">
        <button class="pc-copy" data-s="${esc(p.serial)}">
          <svg viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
          نسخ
        </button>
        ${iB&&mode==='online'?`<button class="bcharge" data-s="${esc(p.serial)}" onclick="doCharge('${esc(p.serial)}')"><svg viewBox="0 0 24 24"><polyline points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>شحن تلقائي</button>`:''}
        ${iB&&mode==='dial'?`<a href="${tel}" class="bdial"><svg viewBox="0 0 24 24"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 13a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 2.24h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 9.91a16 16 0 0 0 6.09 6.09l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>اتصال</a>`:''}
      </div>
    </div>`;
  });
  h+='</div>';panel.innerHTML=h;
  if(b&&mode==='online'&&!charged){const btn=document.querySelector('.bcharge[data-s="'+b.serial+'"]');if(btn)setTimeout(()=>doCharge(b.serial),600);}
  if(b&&mode==='dial'){const lnk=document.querySelector('.bdial');if(lnk&&!charged)setTimeout(()=>lnk.click(),500);}
  return !!b;
}
function showLoad(){const p=document.getElementById('CP');if(!p.querySelector('.cl')&&!p.querySelector('.es'))p.innerHTML='<div class="ls"><div class="spinner"></div><div class="slbl">جاري تحديث الكروت</div></div>';}
async function run(){if(running)return;running=true;while(!stopped){showLoad();const d=await fetchC();if(stopped)break;const f=renderCards(d);if(f&&!document.getElementById('CC').checked){running=false;stopT();return;}await startTimer(SECS);if(stopped)break;}running=false;stopT();}

// copy — يشتغل لكل الكروت مش بس الأفضل
document.addEventListener('click',e=>{
  const btn=e.target.closest('.pc-copy');if(!btn)return;const s=btn.dataset.s;
  const flash=()=>{
    const orig=btn.innerHTML;
    btn.style.borderColor='rgba(200,168,75,.4)';btn.style.color='var(--g2)';
    btn.innerHTML='<svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="var(--g2)" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg> تم';
    setTimeout(()=>{btn.style.borderColor='';btn.style.color='';btn.innerHTML=orig;},1600);
    toast('تم النسخ ✓','ok');
  };
  if(navigator.clipboard&&window.isSecureContext)navigator.clipboard.writeText(s).then(flash).catch(()=>{fb(s,flash);});
  else fb(s,flash);
  function fb(s,cb){const a=document.createElement('textarea');a.value=s;a.style.cssText='position:fixed;opacity:0;';document.body.appendChild(a);a.select();try{document.execCommand('copy');}catch(e){}document.body.removeChild(a);cb();}
});
document.getElementById('UI')?.addEventListener('keydown',e=>{if(e.key==='Enter')startApp();});
{% endif %}
</script>
</body>
</html>"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
