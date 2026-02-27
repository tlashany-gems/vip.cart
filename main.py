from flask import Flask, request, session, redirect, jsonify, render_template_string
import requests, time, os
from threading import Lock

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

BASE_H = {
    "User-Agent":"okhttp/4.11.0","x-agent-operatingsystem":"13",
    "clientId":"AnaVodafoneAndroid","Accept-Language":"ar",
    "x-agent-device":"Xiaomi 21061119AG","x-agent-version":"2025.10.3",
    "x-agent-build":"1050","digitalId":"28RI9U7ISU8SW",
    "device-id":"1df4efae59648ac3","Accept":"application/json",
}

def post(url, data, extra, js=False):
    try:
        h = {**BASE_H, **extra}
        r = requests.post(url, **(dict(json=data) if js else dict(data=data)), headers=h, timeout=15, verify=False)
        return r.json()
    except: return {}

def get(url, extra):
    try:
        r = requests.get(url, headers={**BASE_H, **extra}, timeout=15, verify=False)
        return r.json()
    except: return {}

def pw_login(num, pw):
    return post(
        "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token",
        {'grant_type':'password','username':num,'password':pw,
         'client_secret':'95fd95fb-7489-4958-8ae6-d31a525cd20a','client_id':'ana-vodafone-app'},
        {"Content-Type":"application/x-www-form-urlencoded"}
    )

def data_login(ip=None, ua=None):
    h1 = {"User-Agent":ua or "okhttp/4.12.0","Connection":"Keep-Alive",
          "Accept-Encoding":"gzip","x-agent-operatingsystem":"13",
          "clientId":"AnaVodafoneAndroid","Accept-Language":"ar",
          "x-agent-device":"Xiaomi 21061119AG","x-agent-version":"2025.10.3",
          "x-agent-build":"1050","digitalId":"28RI9U7ISU8SW","device-id":"1df4efae59648ac3"}
    if ip: h1["X-Forwarded-For"] = ip; h1["X-Real-IP"] = ip
    try:
        r1 = requests.get(
            "http://mobile.vodafone.com.eg/checkSeamless/realms/vf-realm/protocol/openid-connect/auth?client_id=cash-app",
            headers=h1, timeout=15, verify=False, allow_redirects=True)
        s1 = r1.json()
    except Exception as e: return {"error": f"فشل الاتصال: {e}"}
    tok = s1.get('seamlessToken',''); msisdn = s1.get('msisdn','')
    if not tok or not msisdn: return {"error":"تأكد إن الداتا شغالة على خط فودافون (مش واي فاي)"}
    h2 = {"Content-Type":"application/x-www-form-urlencoded","Accept":"application/json",
          "User-Agent":ua or "okhttp/4.12.0","silentLogin":"true","CRP":"false",
          "seamlessToken":tok,"firstTimeLogin":"true","x-agent-operatingsystem":"13",
          "clientId":"AnaVodafoneAndroid","Accept-Language":"ar",
          "x-agent-device":"Xiaomi 21061119AG","x-agent-version":"2025.10.3",
          "x-agent-build":"1050","digitalId":"","device-id":"1df4efae59648ac3"}
    try:
        r2 = requests.post(
            "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token",
            data={'grant_type':'password','client_secret':'b86e30a8-ae29-467a-a71f-65c73f2ff5e3','client_id':'cash-app'},
            headers=h2, timeout=15, verify=False)
        d = r2.json()
    except: return {"error":"فشل تبادل الـ token"}
    if d.get('access_token'): d['_number'] = '0' + str(msisdn)
    return d

def promos(tok, num):
    url = f"https://web.vodafone.com.eg/services/dxl/ramadanpromo/promotion?@type=RamadanHub&channel=website&msisdn={requests.utils.quote(num)}"
    data = get(url, {"Authorization":f"Bearer {tok}",
        "User-Agent":"Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/133.0.0.0 Mobile Safari/537.36",
        "clientId":"WebsiteConsumer","api-host":"PromotionHost","channel":"WEB",
        "msisdn":num,"Content-Type":"application/json","Referer":"https://web.vodafone.com.eg/ar/ramadan"})
    cards = []
    if not isinstance(data, list): return cards
    for item in data:
        if not isinstance(item,dict) or 'pattern' not in item: continue
        for pat in item['pattern']:
            for act in pat.get('action',[]):
                c = {ch['name']:str(ch['value']) for ch in act.get('characteristics',[])}
                s = c.get('CARD_SERIAL','').strip()
                if len(s) != 13: continue
                cards.append({'serial':s,'gift':int(c.get('GIFT_UNITS',0)),
                              'amount':int(c.get('amount',0)),'remaining':int(c.get('REMAINING_DEDICATIONS',0))})
    return sorted(cards, key=lambda x:-x['gift'])

def redeem(tok, num, serial):
    try:
        r = requests.post("https://web.vodafone.com.eg/services/dxl/ramadanpromo/promotion",
            json={"@type":"Promo","channel":{"id":"1"},"context":{"type":"RamadanRedeemFromHub"},
                  "pattern":[{"characteristics":[{"name":"cardSerial","value":serial}]}]},
            headers={"Authorization":f"Bearer {tok}","Content-Type":"application/json","Accept":"application/json",
                     "clientId":"WebsiteConsumer","channel":"WEB","msisdn":num,"Accept-Language":"AR",
                     "User-Agent":"Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/133.0.0.0 Mobile Safari/537.36",
                     "Origin":"https://web.vodafone.com.eg","Referer":"https://web.vodafone.com.eg/portal/hub"},
            timeout=15, verify=False)
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
        if time.time() >= session.get('token_exp',0):
            fn = data_login if session.get('login_method')=='data' else lambda: pw_login(session['number'],session['password'])
            res = fn()
            if res.get('access_token'):
                session['token'] = res['access_token']
                session['token_exp'] = int(time.time()) + int(res.get('expires_in',3600)) - 120
                if res.get('_number'): session['number'] = res['_number']
        cards = promos(session['token'], session['number'])
        return jsonify({'success':True,'promos':cards,'number':session['number'],'active_users':count()})
    if request.args.get('redeem') and session.get('logged_in'):
        serial = request.args.get('serial','').strip()
        target = request.args.get('target', session.get('number','')).strip()
        tok = session['token']
        if target != session.get('number',''):
            tp = request.args.get('tpass','').strip()
            if tp:
                r2 = pw_login(target, tp)
                if r2.get('access_token'): tok = r2['access_token']
        code = redeem(tok, target, serial)
        return jsonify({'success': code==200, 'code': code})
    if request.method=='POST' and request.form.get('action')=='login':
        method = request.form.get('method','password')
        if method=='data':
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            ua = request.headers.get('User-Agent','')
            res = data_login(ip=ip, ua=ua)
            if res.get('access_token'):
                session.update({'logged_in':True,'token':res['access_token'],
                    'token_exp':int(time.time())+int(res.get('expires_in',3600))-120,
                    'number':res.get('_number',''),'password':'','login_method':'data'})
                touch(session['number']); return redirect('/')
            err = res.get('error') or 'فشل — تأكد إن الداتا شغالة على خط فودافون مش واي فاي'
        else:
            num = request.form.get('number','').strip()
            pw = request.form.get('password','').strip()
            if num and pw:
                res = pw_login(num, pw)
                if res.get('access_token'):
                    session.update({'logged_in':True,'token':res['access_token'],
                        'token_exp':int(time.time())+int(res.get('expires_in',3600))-120,
                        'number':num,'password':pw,'login_method':'password'})
                    touch(num); return redirect('/')
                err = 'الرقم أو الباسورد غلط'
            else: err = 'ادخل الرقم والباسورد'
    return render_template_string(HTML,
        is_logged_in=session.get('logged_in',False),
        user_number=session.get('number',''),
        login_error=err,
        active_count=count() if session.get('logged_in') else 0,
        form_number=request.form.get('number','') if request.method=='POST' else '')

HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1,user-scalable=no"/>
<title>TALASHNY</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=Cairo:wght@400;500;600;700;900&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet"/>
<style>
:root{
  --red:#e60000;--red2:#9a0000;
  --g1:#c8a84b;--g2:#f5d070;--g3:#8a6820;--g4:rgba(200,168,75,.12);
  --bg:#07070a;--l1:#0d0d12;--l2:#121217;--l3:#18181f;--l4:#1f1f28;--l5:#26262f;
  --ink:#eeeae0;--ink2:#a09880;--ink3:#504e48;
  --stroke:rgba(200,168,75,.1);--stroke2:rgba(200,168,75,.22);
  --r:18px;--r-sm:12px;--r-xs:8px;
  --sp:cubic-bezier(.34,1.56,.64,1);--ease:cubic-bezier(.4,0,.2,1);
  --bh:82px;
}
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box;}
html{height:100%;-webkit-font-smoothing:antialiased;}
body{font-family:'Cairo',sans-serif;background:var(--bg);color:var(--ink);min-height:100vh;overflow-x:hidden;touch-action:manipulation;}
body::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background:radial-gradient(ellipse 80% 40% at 50% -5%,rgba(200,168,75,.11),transparent 65%),
  url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)' opacity='0.022'/%3E%3C/svg%3E");}

/* BANNER - curved bottom + tapered gold line */
.banner{
  position:fixed;top:0;left:0;right:0;height:var(--bh);
  background:linear-gradient(180deg,#000 0%,rgba(0,0,0,.95) 100%);
  border-radius:0 0 36px 36px;
  border-bottom:1px solid rgba(200,168,75,.14);
  box-shadow:0 6px 36px rgba(0,0,0,.85), inset 0 1px 0 rgba(200,168,75,.06);
  z-index:1000;display:flex;align-items:center;justify-content:center;
}
.banner::after{
  content:'';position:absolute;bottom:-2px;left:18%;right:18%;height:2px;
  background:linear-gradient(90deg,transparent,var(--g3) 20%,var(--g2) 50%,var(--g3) 80%,transparent);
  border-radius:2px;filter:blur(.4px);
}
.bc{display:flex;flex-direction:column;align-items:center;gap:4px;}
.bt{display:flex;font-size:2.1rem;font-weight:900;letter-spacing:8px;text-transform:uppercase;}
.bt span{
  background:linear-gradient(90deg,#888 0%,#fff 22%,#ddd 48%,#fff 74%,#888 100%);
  background-size:300% 100%;-webkit-background-clip:text;-webkit-text-fill-color:transparent;
  animation:chrome 4s linear infinite;animation-delay:calc(var(--i)*.14s);
}
@keyframes chrome{0%{background-position:300% center}100%{background-position:-300% center}}
.bon{display:flex;align-items:center;gap:5px;background:rgba(76,255,154,.06);
  border:1px solid rgba(76,255,154,.14);border-radius:20px;padding:3px 9px 3px 7px;}
.bdot{width:5px;height:5px;border-radius:50%;background:#4cff9a;box-shadow:0 0 5px #4cff9a;animation:blink 2s ease-in-out infinite;}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.35}}
.bnum{font-family:'JetBrains Mono',monospace;font-size:.6rem;font-weight:700;color:#4cff9a;}
.blbl{font-size:.58rem;color:rgba(76,255,154,.5);font-weight:600;}

/* PAGE */
.page{max-width:420px;margin:0 auto;padding:0 11px;position:relative;z-index:1;}
@keyframes up{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
.surface{background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r);}

/* LOGIN */
#LS{min-height:100vh;display:flex;align-items:center;justify-content:center;
  padding:calc(var(--bh) + 18px) 13px 80px;animation:up .5s var(--sp) both;}
.lw{width:100%;max-width:380px;display:flex;flex-direction:column;gap:11px;}
.lbrand{text-align:center;padding:6px 0 2px;}
.lico{width:46px;height:46px;border-radius:50%;margin:0 auto 7px;
  background:var(--l3);border:1px solid var(--stroke2);
  display:flex;align-items:center;justify-content:center;
  box-shadow:0 0 18px rgba(200,168,75,.13);}
.lico svg{width:19px;height:19px;stroke:var(--g1);stroke-width:1.8;fill:none;}
.lsup{font-size:.48rem;font-weight:700;letter-spacing:3.5px;text-transform:uppercase;color:var(--ink3);margin-bottom:3px;}
.lh{font-family:'Playfair Display',serif;font-size:1.12rem;color:var(--ink);}
.lh em{font-style:italic;color:transparent;background:linear-gradient(135deg,var(--g1),var(--g2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;}

/* tabs */
.tabs{display:flex;background:var(--l2);border:1px solid var(--stroke);border-radius:var(--r-sm);padding:3px;gap:3px;}
.tab{flex:1;padding:8px 5px;border-radius:var(--r-xs);text-align:center;font-size:.7rem;font-weight:700;
  color:var(--ink3);cursor:pointer;transition:all .22s var(--sp);display:flex;align-items:center;justify-content:center;gap:5px;}
.tab svg{width:12px;height:12px;stroke:currentColor;stroke-width:1.8;fill:none;}
.tab.on{background:var(--g4);color:var(--g2);border:1px solid rgba(200,168,75,.28);}
.tab:active{transform:scale(.95);}

/* form sections */
.fs{display:none;flex-direction:column;}
.fs.show{display:flex;}
.fc{background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r);overflow:hidden;}
.fr{display:flex;align-items:stretch;border-bottom:1px solid var(--stroke);position:relative;}
.fr:last-of-type{border-bottom:none;}
.fr:focus-within{background:rgba(200,168,75,.02);}
.fr::after{content:'';position:absolute;right:0;top:0;bottom:0;width:0;background:var(--g1);transition:width .18s;}
.fr:focus-within::after{width:2px;}
.fi{width:44px;display:flex;align-items:center;justify-content:center;border-left:1px solid var(--stroke);background:var(--l2);}
.fi svg{width:14px;height:14px;stroke:var(--ink3);stroke-width:1.6;fill:none;transition:stroke .2s;}
.fr:focus-within .fi svg{stroke:var(--g1);}
.fb{flex:1;padding:10px 12px;}
.fl{font-size:.46rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);margin-bottom:2px;transition:color .2s;}
.fr:focus-within .fl{color:var(--g1);}
.fin{background:transparent;border:none;outline:none;font-family:'Cairo',sans-serif;font-size:.88rem;font-weight:600;color:var(--ink);width:100%;}
.fin::placeholder{color:var(--ink3);font-weight:400;font-size:.76rem;}
.dinfo{display:flex;gap:8px;padding:12px 13px;background:rgba(200,168,75,.03);border-bottom:1px solid var(--stroke);}
.dinfo svg{width:14px;height:14px;stroke:var(--g1);stroke-width:1.6;fill:none;flex-shrink:0;margin-top:1px;}
.dinfo p{font-size:.67rem;color:var(--ink2);line-height:1.9;}
.dinfo strong{color:var(--g2);display:block;font-size:.68rem;margin-bottom:2px;}

/* button */
.bw{padding:12px;}
.gbtn{width:100%;padding:12px;border:none;border-radius:var(--r-xs);
  background:linear-gradient(135deg,var(--g3),var(--g1) 50%,var(--g2));
  color:#1a0e00;font-family:'Cairo',sans-serif;font-size:.85rem;font-weight:900;
  cursor:pointer;display:flex;align-items:center;justify-content:center;gap:7px;
  box-shadow:0 4px 18px rgba(200,168,75,.23);position:relative;overflow:hidden;
  transition:transform .18s var(--sp),box-shadow .18s;}
.gbtn::before{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(255,255,255,.13),transparent 55%);}
.gbtn::after{content:'';position:absolute;top:0;left:-120%;width:50%;height:100%;
  background:linear-gradient(105deg,transparent,rgba(255,255,255,.18),transparent);
  animation:sheen 4s ease-in-out infinite;}
@keyframes sheen{0%,100%{left:-120%}50%{left:160%}}
.gbtn svg,.gbtn span{position:relative;z-index:1;}
.gbtn svg{width:13px;height:13px;stroke:currentColor;stroke-width:2.2;fill:none;}
.gbtn:hover{transform:translateY(-2px);box-shadow:0 7px 24px rgba(200,168,75,.33);}
.gbtn:active{transform:scale(.97);}
.gbtn:disabled{opacity:.5;pointer-events:none;}
.bspin{width:13px;height:13px;border-radius:50%;border:2px solid rgba(26,14,0,.22);
  border-top-color:#1a0e00;animation:rspin .7s linear infinite;display:none;z-index:1;}
.gbtn.loading .bspin{display:block;}
.gbtn.loading .btxt{display:none;}
@keyframes rspin{to{transform:rotate(360deg)}}
.errbanner{display:flex;align-items:flex-start;gap:7px;
  background:rgba(230,0,0,.05);border:1px solid rgba(230,0,0,.17);border-radius:var(--r-xs);
  padding:10px 12px;font-size:.68rem;color:#ff8a80;font-weight:600;line-height:1.7;
  animation:up .3s var(--sp) both;}
.errbanner svg{width:13px;height:13px;stroke:#ff6b6b;stroke-width:2;fill:none;flex-shrink:0;margin-top:2px;}
.lnote{text-align:center;font-size:.57rem;color:var(--ink3);}

/* APP */
#APP{display:none;}
#APP.on{display:block;}
.ab{padding-top:calc(var(--bh) + 12px);padding-bottom:84px;}

/* user bar */
.ubar{display:flex;align-items:center;justify-content:space-between;
  padding:8px 12px;margin-bottom:10px;
  background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r-xs);}
.ul{display:flex;align-items:center;gap:7px;}
.udot{width:6px;height:6px;border-radius:50%;background:var(--g2);box-shadow:0 0 6px var(--g1);}
.unum{font-family:'JetBrains Mono',monospace;font-size:.76rem;font-weight:700;color:var(--g2);}
.ur{display:flex;align-items:center;gap:7px;}
/* online pill */
.upill{display:flex;align-items:center;gap:4px;
  background:rgba(76,255,154,.05);border:1px solid rgba(76,255,154,.13);
  border-radius:20px;padding:4px 9px;}
.updot{width:5px;height:5px;border-radius:50%;background:#4cff9a;animation:blink 2s ease-in-out infinite;}
.upn{font-family:'JetBrains Mono',monospace;font-size:.6rem;font-weight:700;color:#4cff9a;}
.upl{font-size:.57rem;color:rgba(76,255,154,.45);font-weight:600;}
.bout{display:flex;align-items:center;gap:4px;padding:4px 10px;
  background:transparent;border:1px solid rgba(230,0,0,.15);border-radius:var(--r-xs);
  font-family:'Cairo',sans-serif;font-size:.62rem;font-weight:700;color:rgba(230,0,0,.42);
  cursor:pointer;transition:all .18s;text-decoration:none;}
.bout:hover{color:#ff7070;border-color:rgba(230,0,0,.35);background:rgba(230,0,0,.04);}
.bout svg{width:9px;height:9px;stroke:currentColor;stroke-width:2;fill:none;}

/* SEARCH */
#US{display:flex;flex-direction:column;gap:11px;animation:up .4s var(--sp) both;}
.ushead{padding:5px 2px 2px;}
.useye{display:inline-flex;align-items:center;gap:5px;font-size:.5rem;font-weight:700;
  letter-spacing:3px;text-transform:uppercase;color:var(--g1);opacity:.7;margin-bottom:4px;}
.useye i{width:4px;height:4px;border-radius:50%;background:var(--g2);}
.ush{font-family:'Playfair Display',serif;font-size:1.45rem;font-weight:700;line-height:1.3;margin-bottom:3px;}
.ush em{font-style:italic;color:transparent;background:linear-gradient(135deg,var(--g1),var(--g2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.ussub{font-size:.7rem;color:var(--ink2);line-height:1.8;}

/* scard */
.scard{overflow:hidden;background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r);}
.sh{padding:8px 12px 2px;font-size:.52rem;font-weight:700;letter-spacing:2.5px;
  text-transform:uppercase;color:var(--ink3);display:flex;align-items:center;gap:6px;}
.sh::before{content:'';display:block;width:11px;height:1px;background:linear-gradient(90deg,transparent,var(--g1));}

/* units */
.urow{display:flex;align-items:stretch;border-bottom:1px solid var(--stroke);position:relative;}
.urow:focus-within{background:rgba(200,168,75,.02);}
.urow::after{content:'';position:absolute;right:0;top:0;bottom:0;width:0;background:var(--g1);transition:width .18s;}
.urow:focus-within::after{width:2px;}
.uico{width:46px;display:flex;align-items:center;justify-content:center;border-left:1px solid var(--stroke);background:var(--l2);}
.uico svg{width:16px;height:16px;stroke:var(--ink3);stroke-width:1.6;fill:none;transition:stroke .2s;}
.urow:focus-within .uico svg{stroke:var(--g1);}
.uright{flex:1;padding:12px 0;display:flex;flex-direction:column;align-items:center;}
.ulbl{font-family:'Playfair Display',serif;font-size:.52rem;font-weight:700;letter-spacing:2px;
  text-transform:uppercase;color:var(--ink3);margin-bottom:3px;transition:color .2s;}
.urow:focus-within .ulbl{color:var(--g1);}
.uinp{background:transparent;border:none;outline:none;font-family:'Playfair Display',serif;
  font-size:1.75rem;font-weight:700;color:var(--ink);text-align:center;max-width:150px;}
.uinp::placeholder{font-family:'Cairo',sans-serif;color:var(--ink3);font-size:.8rem;font-weight:400;}

/* chips */
.qsect{padding:9px 12px 11px;border-bottom:1px solid var(--stroke);}
.qlbl{font-size:.5rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;
  color:var(--ink3);margin-bottom:7px;display:flex;align-items:center;gap:5px;}
.qlbl::before{content:'';display:block;width:10px;height:1px;background:linear-gradient(90deg,transparent,var(--g1));}
.chips{display:flex;gap:4px;}
.chip{flex:1;padding:7px 2px;background:var(--l2);border:1px solid var(--stroke);
  border-radius:var(--r-xs);text-align:center;font-family:'Playfair Display',serif;
  font-size:.82rem;font-weight:700;color:var(--ink2);cursor:pointer;transition:all .18s var(--sp);}
.chip:hover{border-color:var(--stroke2);color:var(--g2);}
.chip.on{background:var(--g4);border-color:rgba(200,168,75,.38);color:var(--g2);}
.chip:active{transform:scale(.9);}

/* charge mode */
.cmsect{padding:11px 12px;border-bottom:1px solid var(--stroke);}
.cmlbl{font-size:.5rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;
  color:var(--ink3);margin-bottom:8px;display:flex;align-items:center;gap:5px;}
.cmlbl::before{content:'';display:block;width:10px;height:1px;background:linear-gradient(90deg,transparent,var(--g1));}
.cmbtns{display:flex;gap:6px;}
.cmbtn{flex:1;padding:12px 6px;background:var(--l2);border:1px solid var(--stroke);
  border-radius:var(--r-sm);text-align:center;cursor:pointer;transition:all .18s var(--sp);}
.cmbtn.ol.on{background:rgba(230,0,0,.05);border-color:rgba(230,0,0,.28);}
.cmbtn.dl.on{background:var(--g4);border-color:rgba(200,168,75,.28);}
.cmbtn:active{transform:scale(.96);}
.cmico{width:25px;height:25px;margin:0 auto 5px;border-radius:50%;display:flex;align-items:center;justify-content:center;}
.cmico svg{width:13px;height:13px;stroke-width:1.8;fill:none;}
.cmbtn.ol .cmico{background:rgba(230,0,0,.07);border:1px solid rgba(230,0,0,.16);}
.cmbtn.ol .cmico svg{stroke:var(--red);}
.cmbtn.dl .cmico{background:rgba(200,168,75,.07);border:1px solid rgba(200,168,75,.16);}
.cmbtn.dl .cmico svg{stroke:var(--g2);}
.cmbtn strong{display:block;font-family:'Cairo',sans-serif;font-size:.7rem;font-weight:700;color:var(--ink);margin-bottom:1px;}
.cmbtn small{font-size:.56rem;color:var(--ink3);}

/* target */
.tgsect{padding:0 12px;max-height:0;overflow:hidden;transition:max-height .32s var(--ease),padding .28s;}
.tgsect.open{max-height:195px;padding:11px 12px;}
.tglbl{font-size:.5rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;
  color:var(--ink3);margin-bottom:7px;display:flex;align-items:center;gap:5px;}
.tglbl::before{content:'';display:block;width:10px;height:1px;background:linear-gradient(90deg,transparent,var(--g1));}
.tgbtns{display:flex;gap:5px;}
.tgbtn{flex:1;padding:8px 5px;background:var(--l2);border:1px solid var(--stroke);
  border-radius:var(--r-xs);text-align:center;font-family:'Cairo',sans-serif;
  font-size:.66rem;font-weight:700;color:var(--ink2);cursor:pointer;transition:all .18s var(--sp);}
.tgbtn.on{background:var(--g4);border-color:rgba(200,168,75,.35);color:var(--g2);}
.tgbtn:active{transform:scale(.93);}
.otf{margin-top:8px;display:none;flex-direction:column;gap:5px;}
.otf.show{display:flex;}
.ofield{display:flex;align-items:stretch;border:1px solid var(--stroke);border-radius:var(--r-xs);overflow:hidden;}
.ofic{width:36px;display:flex;align-items:center;justify-content:center;background:var(--l2);border-left:1px solid var(--stroke);}
.ofic svg{width:12px;height:12px;stroke:var(--ink3);stroke-width:1.6;fill:none;}
.ofield input{flex:1;background:transparent;border:none;outline:none;padding:8px 10px;
  font-family:'Cairo',sans-serif;font-size:.8rem;font-weight:600;color:var(--ink);}
.ofield input::placeholder{color:var(--ink3);font-size:.73rem;font-weight:400;}

/* go */
.gosect{padding:12px;}
.gobtn{width:100%;padding:14px;border:none;border-radius:var(--r-sm);
  background:linear-gradient(135deg,var(--red2),var(--red) 60%,#ff1f1f);
  color:#fff;font-family:'Cairo',sans-serif;font-size:.87rem;font-weight:900;
  cursor:pointer;display:flex;align-items:center;justify-content:center;gap:7px;
  box-shadow:0 5px 22px rgba(230,0,0,.28);position:relative;overflow:hidden;
  transition:transform .18s var(--sp),box-shadow .18s;}
.gobtn::before{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(255,255,255,.09),transparent 50%);}
.gobtn::after{content:'';position:absolute;top:0;left:-120%;width:50%;height:100%;
  background:linear-gradient(105deg,transparent,rgba(255,255,255,.09),transparent);
  animation:sheen 4s ease-in-out infinite;}
.gobtn svg,.gobtn span{position:relative;z-index:1;}
.gobtn svg{width:15px;height:15px;stroke:#fff;stroke-width:2.2;fill:none;}
.gobtn:hover{transform:translateY(-2px);box-shadow:0 8px 28px rgba(230,0,0,.38);}
.gobtn:active{transform:scale(.97);}

/* CARDS SCREEN */
#CS{display:none;flex-direction:column;gap:9px;animation:up .32s var(--sp) both;}
.csbar{display:flex;align-items:center;justify-content:space-between;padding:10px 13px;
  background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r);}
.csi{font-family:'Playfair Display',serif;font-size:.76rem;color:var(--ink2);}
.csi strong{color:var(--g2);}
.csback{display:flex;align-items:center;gap:4px;background:var(--l3);border:1px solid var(--stroke);
  border-radius:var(--r-xs);padding:5px 11px;font-family:'Cairo',sans-serif;
  font-size:.64rem;font-weight:700;color:var(--ink2);cursor:pointer;transition:all .18s;}
.csback:hover{color:var(--ink);border-color:var(--stroke2);}
.csback svg{width:9px;height:9px;stroke:currentColor;stroke-width:2.5;fill:none;}

/* timer */
.tcard{padding:13px 15px;background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r);}
.ttop{display:flex;align-items:center;justify-content:space-between;margin-bottom:9px;}
.ttl{display:flex;align-items:center;gap:7px;}
.tdot{width:6px;height:6px;border-radius:50%;background:var(--red);animation:ping 1.5s ease-in-out infinite;}
@keyframes ping{0%{box-shadow:0 0 0 0 rgba(230,0,0,.4)}70%{box-shadow:0 0 0 6px transparent}100%{box-shadow:0 0 0 0 transparent}}
.ttxt{font-family:'Playfair Display',serif;font-size:.64rem;font-weight:700;color:var(--ink2);}
.tnum{font-family:'Playfair Display',serif;font-size:1.85rem;font-weight:700;color:var(--ink);font-variant-numeric:tabular-nums;transition:color .3s;}
.tnum.hot{color:var(--red);}
.tbar{height:2px;background:var(--l5);border-radius:3px;overflow:hidden;}
.tprog{height:100%;border-radius:3px;background:linear-gradient(90deg,var(--g3),var(--g1),var(--g2));transition:width 1s linear;}

/* toggle */
.tgl{display:flex;align-items:center;justify-content:space-between;padding:11px 13px;cursor:pointer;
  background:var(--l1);border:1px solid var(--stroke);border-radius:var(--r);}
.tgl-t strong{display:block;font-family:'Playfair Display',serif;font-size:.72rem;font-weight:700;color:var(--ink);margin-bottom:1px;}
.tgl-t small{font-size:.58rem;color:var(--ink2);}
.sw{position:relative;width:38px;height:21px;flex-shrink:0;}
.sw input{opacity:0;width:0;height:0;position:absolute;}
.sw-tr{position:absolute;inset:0;border-radius:30px;background:var(--l4);border:1px solid var(--stroke);cursor:pointer;transition:all .28s;}
.sw-tr::before{content:'';position:absolute;width:15px;height:15px;border-radius:50%;background:#666;top:2px;right:2px;box-shadow:0 1px 3px rgba(0,0,0,.5);transition:transform .28s var(--sp),background .28s;}
.sw input:checked+.sw-tr{background:linear-gradient(135deg,var(--g3),var(--g1));border-color:rgba(200,168,75,.28);}
.sw input:checked+.sw-tr::before{transform:translateX(-17px);background:#fff;}

/* cards */
.cl{display:flex;flex-direction:column;gap:8px;}
.pc{border-radius:var(--r);position:relative;animation:cardIn .38s var(--sp) both;animation-delay:calc(var(--i,0)*.055s);}
@keyframes cardIn{from{opacity:0;transform:translateY(7px) scale(.97)}to{opacity:1;transform:none}}
.pc::after{content:'';position:absolute;inset:-1px;border-radius:calc(var(--r) + 1px);
  border:1px solid rgba(200,168,75,.2);pointer-events:none;z-index:10;}
.pc.best::after{border:1.5px solid rgba(200,168,75,.55);box-shadow:0 0 10px rgba(200,168,75,.13);}
.pc.best::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;z-index:11;
  border-radius:var(--r) var(--r) 0 0;
  background:linear-gradient(90deg,transparent 5%,var(--g3) 25%,var(--g2) 50%,var(--g3) 75%,transparent 95%);}
.pcbg{position:absolute;inset:0;background:linear-gradient(150deg,rgba(5,5,10,.97),rgba(11,8,16,.82));border-radius:var(--r);}
.pcin{border-radius:var(--r);overflow:hidden;position:relative;}
.pcbadge{position:absolute;top:10px;left:10px;z-index:4;font-size:.48rem;font-weight:900;
  letter-spacing:1.5px;text-transform:uppercase;padding:2px 8px;border-radius:4px;
  color:#1a0e00;background:linear-gradient(135deg,var(--g2),var(--g1));box-shadow:0 2px 7px rgba(200,168,75,.28);}
.pcbody{position:relative;z-index:2;padding:8px 10px 9px;}
.pc.best .pcbody{padding-top:17px;}
.stats{display:flex;align-items:center;justify-content:center;margin-bottom:7px;}
.stat{flex:1;display:flex;flex-direction:column;align-items:center;gap:1px;padding:0 2px;}
.stat:not(:last-child){border-left:1px solid rgba(255,255,255,.05);}
.stico svg{width:10px;height:10px;fill:none;stroke-width:1.8;}
.iamt svg{stroke:#ff8a80;}.igift svg{stroke:var(--g2);}.irem svg{stroke:#82b1ff;}
.stv{font-family:'Playfair Display',serif;font-size:.78rem;font-weight:700;color:#fff;line-height:1;margin-top:1px;}
.stl{font-size:.44rem;color:rgba(255,255,255,.22);}
.srow{display:flex;justify-content:center;margin-bottom:6px;}
.spill{display:inline-flex;align-items:center;gap:6px;
  background:rgba(0,0,0,.32);border-radius:6px;padding:5px 6px 5px 8px;
  border:1px solid rgba(200,168,75,.09);}
.sn{font-family:'JetBrains Mono',monospace;font-size:.82rem;font-weight:700;color:#fff;letter-spacing:2px;white-space:nowrap;}
.scopy{width:21px;height:21px;border-radius:5px;border:1px solid rgba(200,168,75,.12);
  background:rgba(200,168,75,.03);display:flex;align-items:center;justify-content:center;
  cursor:pointer;transition:all .18s var(--sp);}
.scopy svg{width:9px;height:9px;stroke:rgba(200,168,75,.35);stroke-width:2;fill:none;}
.scopy:hover{background:rgba(200,168,75,.1);border-color:rgba(200,168,75,.3);}
.scopy:active{transform:scale(.84);}
.pca{display:flex;align-items:center;justify-content:center;gap:6px;flex-wrap:wrap;}
.bcharge{display:inline-flex;align-items:center;gap:4px;padding:5px 12px;
  background:rgba(230,0,0,.08);border:1px solid rgba(230,0,0,.22);border-radius:16px;
  font-family:'Cairo',sans-serif;font-size:.68rem;font-weight:700;color:#ff8a80;
  cursor:pointer;transition:all .18s var(--sp);}
.bcharge svg{width:9px;height:9px;stroke:currentColor;stroke-width:2;fill:none;}
.bcharge:hover{background:rgba(230,0,0,.14);border-color:rgba(230,0,0,.38);}
.bcharge.loading{opacity:.52;pointer-events:none;}
.bdial{display:inline-flex;align-items:center;gap:4px;text-decoration:none;
  color:rgba(200,168,75,.45);font-family:'Cairo',sans-serif;font-size:.68rem;font-weight:700;
  padding:5px 12px;border:1px solid rgba(200,168,75,.09);border-radius:16px;
  background:rgba(200,168,75,.03);transition:all .18s;}
.bdial svg{width:9px;height:9px;stroke:currentColor;stroke-width:2;fill:none;}
.bdial:hover{color:rgba(200,168,75,.75);border-color:rgba(200,168,75,.26);}
.ls{display:flex;flex-direction:column;align-items:center;gap:9px;padding:40px 18px;}
.spinner{width:26px;height:26px;border-radius:50%;border:2px solid rgba(200,168,75,.07);
  border-top-color:var(--g1);animation:rspin .8s linear infinite;}
.slbl{font-family:'Playfair Display',serif;font-size:.68rem;color:var(--ink2);font-weight:700;}
.es{text-align:center;padding:30px 18px;font-family:'Playfair Display',serif;font-size:.76rem;color:var(--ink2);line-height:2.1;}
.es svg{width:22px;height:22px;stroke:var(--ink3);stroke-width:1.5;fill:none;margin-bottom:8px;}

/* toast */
.toast{position:fixed;bottom:88px;left:50%;transform:translateX(-50%) translateY(14px);
  background:rgba(10,10,16,.97);border:1px solid var(--stroke);border-radius:26px;
  padding:8px 16px;font-family:'Cairo',sans-serif;font-size:.71rem;font-weight:700;
  color:var(--ink);opacity:0;pointer-events:none;transition:all .28s var(--sp);z-index:9999;white-space:nowrap;}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0);}
.toast.ok{border-color:rgba(0,200,100,.26);color:#4cff9a;}
.toast.err{border-color:rgba(230,0,0,.26);color:#ff8a80;}

/* nav */
.nav{position:fixed;bottom:0;left:0;right:0;z-index:200;
  display:flex;justify-content:space-around;align-items:center;padding:8px 0 15px;
  background:rgba(4,4,7,.97);backdrop-filter:blur(22px);border-top:1px solid var(--stroke);}
.nav a{text-decoration:none;color:var(--ink3);display:flex;align-items:center;padding:5px 16px;
  border-radius:9px;transition:color .18s,transform .2s var(--sp);}
.nav a:hover{color:var(--g1);transform:translateY(-3px);}
.nav a svg{width:19px;height:19px;stroke:currentColor;stroke-width:1.6;fill:none;}
::-webkit-scrollbar{width:3px;}::-webkit-scrollbar-track{background:var(--l1);}::-webkit-scrollbar-thumb{background:var(--l4);border-radius:3px;}
</style>
</head>
<body oncontextmenu="return false">

<!-- BANNER -->
<div class="banner">
  <div class="bc">
    <div class="bt">
      <span style="--i:0">Y</span><span style="--i:1">N</span><span style="--i:2">H</span>
      <span style="--i:3">S</span><span style="--i:4">A</span><span style="--i:5">L</span>
      <span style="--i:6">A</span><span style="--i:7">T</span>
    </div>
    {% if is_logged_in %}
    <div class="bon">
      <div class="bdot"></div>
      <span class="bnum" id="BN">{{ active_count }}</span>
      <span class="blbl">متصل الآن</span>
    </div>
    {% endif %}
  </div>
</div>

{% if not is_logged_in %}
<div id="LS">
  <div class="lw">
    <div class="lbrand">
      <div class="lico"><svg viewBox="0 0 24 24"><polyline points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg></div>
      <div class="lsup">Premium Access</div>
      <div class="lh">أهلاً في <em>TALASHNY</em></div>
    </div>
    {% if login_error %}
    <div class="errbanner">
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
          <div class="fi"><svg viewBox="0 0 24 24"><rect x="5" y="2" width="14" height="20" rx="2"/><circle cx="12" cy="17" r="1" fill="currentColor" stroke="none"/></svg></div>
          <div class="fb"><div class="fl">رقم الموبايل</div><input class="fin" type="tel" name="number" placeholder="01XXXXXXXXX" inputmode="tel" autocomplete="tel" required value="{{ form_number }}"></div>
        </div>
        <div class="fr">
          <div class="fi"><svg viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg></div>
          <div class="fb"><div class="fl">الباسورد</div><input class="fin" type="password" name="password" placeholder="••••••••" autocomplete="current-password" required></div>
        </div>
        <div class="bw"><button type="submit" class="gbtn"><svg viewBox="0 0 24 24"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg><span class="btxt">دخـول</span><div class="bspin"></div></button></div>
      </div>
    </form>
    <form method="POST" id="FD" class="fs">
      <input type="hidden" name="action" value="login">
      <input type="hidden" name="method" value="data">
      <div class="fc">
        <div class="dinfo">
          <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          <p><strong>تسجيل دخول بداتا الجهاز</strong>لازم تكون متصل بداتا فودافون مش واي فاي. السيستم بيجيب بياناتك تلقائياً من الشبكة.</p>
        </div>
        <div class="bw"><button type="submit" class="gbtn"><svg viewBox="0 0 24 24"><path d="M1 6s0-2 2-2 2 2 2 2v8s0 2 2 2 2-2 2-2V6s0-2 2-2 2 2 2 2v8s0 2 2 2 2-2 2-2V6s0-2 2-2 2 2 2 2"/></svg><span class="btxt">دخول بالداتا</span><div class="bspin"></div></button></div>
      </div>
    </form>
    <div class="lnote">بياناتك محمية ومش بتتحفظ على السيرفر</div>
  </div>
</div>
{% else %}
<div id="APP" class="on">
  <div class="ab">
    <div class="page">
      <div id="US">
        <div class="ushead">
          <div class="useye"><i></i>Premium<i></i></div>
          <div class="ush">ابحث عن<br><em>ㅤأنسب كارت</em></div>
          <div class="ussub">حدد الوحدات وطريقة الشحن</div>
        </div>
        <div class="ubar">
          <div class="ul"><div class="udot"></div><span class="unum">{{ user_number }}</span></div>
          <div class="ur">
            <div class="upill"><div class="updot"></div><span class="upn" id="UON">{{ active_count }}</span><span class="upl">متصل</span></div>
            <a href="/?logout=1" class="bout"><svg viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>خروج</a>
          </div>
        </div>
        <div class="scard">
          <div class="sh">فئة الكارت — وحدات</div>
          <div class="urow">
            <div class="uico"><svg viewBox="0 0 24 24"><polyline points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg></div>
            <div class="uright"><span class="ulbl">الحد الأدنى</span><input class="uinp" type="number" id="UI" placeholder="أدخل الوحدات" min="1" inputmode="numeric"></div>
          </div>
          <div class="qsect">
            <div class="qlbl">اختيار سريع</div>
            <div class="chips">
              <button class="chip" onclick="setU(100,this)">100</button>
              <button class="chip" onclick="setU(300,this)">300</button>
              <button class="chip" onclick="setU(500,this)">500</button>
              <button class="chip" onclick="setU(700,this)">700</button>
              <button class="chip" onclick="setU(900,this)">900</button>
            </div>
          </div>
          <div class="cmsect">
            <div class="cmlbl">طريقة الشحن</div>
            <div class="cmbtns">
              <div class="cmbtn ol on" id="CMO" onclick="setMode('online')">
                <div class="cmico"><svg viewBox="0 0 24 24"><polyline points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg></div>
                <strong>أونلاين</strong><small>شحن مباشر</small>
              </div>
              <div class="cmbtn dl" id="CMD" onclick="setMode('dial')">
                <div class="cmico"><svg viewBox="0 0 24 24"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 13a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 2.24h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 9.91a16 16 0 0 0 6.09 6.09l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg></div>
                <strong>اتصال</strong><small>عبر لوحة الأرقام</small>
              </div>
            </div>
          </div>
          <div class="tgsect open" id="TGS">
            <div class="tglbl">شحن على رقم</div>
            <div class="tgbtns">
              <div class="tgbtn on" id="TGM" onclick="setTg('mine')">رقمي</div>
              <div class="tgbtn" id="TGO" onclick="setTg('other')">رقم تاني</div>
            </div>
            <div class="otf" id="OTF">
              <div class="ofield"><div class="ofic"><svg viewBox="0 0 24 24"><rect x="5" y="2" width="14" height="20" rx="2"/></svg></div><input type="tel" id="OTN" placeholder="01XXXXXXXXX" inputmode="tel"></div>
              <div class="ofield"><div class="ofic"><svg viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg></div><input type="password" id="OTP" placeholder="باسورد الرقم التاني"></div>
            </div>
          </div>
          <div class="gosect">
            <button class="gobtn" onclick="startApp()">
              <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <span>ابدأ البحث</span>
            </button>
          </div>
        </div>
      </div>
      <div id="CS">
        <div class="csbar">
          <div class="csi">بحث عن <strong id="IU">—</strong></div>
          <button class="csback" onclick="goBack()"><svg viewBox="0 0 24 24"><polyline points="9 18 15 12 9 6"/></svg>تغيير</button>
        </div>
        <div class="tcard">
          <div class="ttop">
            <div class="ttl"><div class="tdot"></div><span class="ttxt">جاري التحديث</span></div>
            <span class="tnum" id="TN">—</span>
          </div>
          <div class="tbar"><div class="tprog" id="TPROG" style="width:100%"></div></div>
        </div>
        <div class="tgl" onclick="document.getElementById('CC').click()">
          <div class="tgl-t"><strong>استمرار البحث بعد الشحن</strong><small id="TH">مفعّل — يكمل البحث بعد الشحن</small></div>
          <div class="sw"><input type="checkbox" id="CC" checked onchange="onTgl()"><div class="sw-tr"></div></div>
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
function toast(m,t=''){const el=document.getElementById('TOAST');el.textContent=m;el.className='toast show'+(t?' '+t:'');clearTimeout(el._t);el._t=setTimeout(()=>el.classList.remove('show'),2700);}
function sw(t){
  document.getElementById('TP').classList.toggle('on',t==='pass');
  document.getElementById('TD').classList.toggle('on',t==='data');
  document.getElementById('FP').classList.toggle('show',t==='pass');
  document.getElementById('FD').classList.toggle('show',t==='data');
}
document.querySelectorAll('form.fs').forEach(f=>{
  f.addEventListener('submit',function(){const b=this.querySelector('.gbtn');if(b){b.classList.add('loading');b.disabled=true;}});
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
  if(v<1){const i=document.getElementById('UI');i.focus();i.closest('.urow').style.background='rgba(230,0,0,.05)';setTimeout(()=>i.closest('.urow').style.background='',750);return;}
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
async function fetchC(){try{const d=await(await fetch('/?fetch=1&_='+Date.now())).json();if(d.active_users!=null)updOn(d.active_users);return d;}catch{return{success:false,promos:[]};}}
function findBest(ps){return ps.find(p=>parseInt(p.gift)>=units)||null;}
async function doCharge(serial){
  let url='/?redeem=1&serial='+encodeURIComponent(serial);
  if(tg==='other'){url+='&target='+encodeURIComponent(document.getElementById('OTN').value.trim())+'&tpass='+encodeURIComponent(document.getElementById('OTP').value.trim());}
  const btn=document.querySelector('.bcharge[data-s="'+serial+'"]');if(btn)btn.classList.add('loading');
  try{const d=await(await fetch(url)).json();if(d.success){toast('تم شحن الكارت ✅','ok');charged=true;if(!document.getElementById('CC').checked)setTimeout(goBack,1400);}else toast('فشل الشحن ❌','err');}
  catch{toast('خطأ في الاتصال ❌','err');}
  if(btn)btn.classList.remove('loading');
}
function renderCards(data){
  const panel=document.getElementById('CP');
  if(!data?.success||!data.promos?.length){
    if(!panel.querySelector('.cl'))panel.innerHTML='<div class="es surface"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>لا يوجد كروت الآن<br><small style="font-family:Cairo;font-size:.58rem;color:var(--ink3)">جاري البحث...</small></div>';
    return false;
  }
  const b=findBest(data.promos);
  let h='<div class="cl">';
  data.promos.forEach((p,i)=>{
    const iB=b&&p.serial===b.serial;
    const tel='tel:'+encodeURIComponent('*858*'+p.serial.replace(/\\s/g,'')+'#');
    h+=`<div class="pc${iB?' best':''}" style="--i:${i}"><div class="pcbg"></div><div class="pcin">
      ${iB?'<div class="pcbadge">✦ أفضل كارت</div>':''}
      <div class="pcbody">
        <div class="stats">
          <div class="stat"><div class="stico iamt"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 6v12M8 10h6a2 2 0 0 1 0 4H8"/></svg></div><span class="stv">${esc(p.amount)}</span><span class="stl">جنيه</span></div>
          <div class="stat"><div class="stico igift"><svg viewBox="0 0 24 24"><polyline points="20 12 20 22 4 22 4 12"/><rect x="2" y="7" width="20" height="5"/><path d="M12 22V7M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7zM12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/></svg></div><span class="stv">${esc(p.gift)}</span><span class="stl">وحدة</span></div>
          <div class="stat"><div class="stico irem"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></div><span class="stv">${esc(p.remaining)}</span><span class="stl">متبقي</span></div>
        </div>
        <div class="srow"><div class="spill"><span class="sn">${esc(p.serial)}</span><button class="scopy" data-s="${esc(p.serial)}"><svg viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button></div></div>
        <div class="pca">
          ${iB&&mode==='online'?`<button class="bcharge" data-s="${esc(p.serial)}" onclick="doCharge('${esc(p.serial)}')"><svg viewBox="0 0 24 24"><polyline points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>شحن أونلاين</button>`:''}
          ${iB&&mode==='dial'?`<a href="${tel}" class="bdial"><svg viewBox="0 0 24 24"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 13a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 2.24h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 9.91a16 16 0 0 0 6.09 6.09l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>اتصل للشحن</a>`:''}
        </div>
      </div>
    </div></div>`;
  });
  h+='</div>';panel.innerHTML=h;
  if(b&&mode==='online'&&!charged){const btn=document.querySelector('.bcharge[data-s="'+b.serial+'"]');if(btn)setTimeout(()=>doCharge(b.serial),700);}
  if(b&&mode==='dial'){const lnk=document.querySelector('.bdial');if(lnk&&!charged)setTimeout(()=>lnk.click(),600);}
  return !!b;
}
function showLoad(){const p=document.getElementById('CP');if(!p.querySelector('.cl')&&!p.querySelector('.es'))p.innerHTML='<div class="ls surface" style="background:var(--l1);border-radius:var(--r)"><div class="spinner"></div><div class="slbl">جاري تحديث الكروت</div></div>';}
async function run(){if(running)return;running=true;while(!stopped){showLoad();const d=await fetchC();if(stopped)break;const f=renderCards(d);if(f&&!document.getElementById('CC').checked){running=false;stopT();return;}await startTimer(SECS);if(stopped)break;}running=false;stopT();}
document.addEventListener('click',e=>{
  const btn=e.target.closest('.scopy');if(!btn)return;const s=btn.dataset.s;
  const flash=()=>{btn.style.background='rgba(200,168,75,.16)';btn.innerHTML='<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#f5d070" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>';setTimeout(()=>{btn.style.background='';btn.innerHTML='<svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="rgba(200,168,75,.35)" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';},1700);toast('تم نسخ الكود','ok');};
  if(navigator.clipboard&&window.isSecureContext)navigator.clipboard.writeText(s).then(flash).catch(()=>{const a=document.createElement('textarea');a.value=s;a.style.cssText='position:fixed;opacity:0;';document.body.appendChild(a);a.select();try{document.execCommand('copy');}catch(e){}document.body.removeChild(a);flash();});
  else{const a=document.createElement('textarea');a.value=s;a.style.cssText='position:fixed;opacity:0;';document.body.appendChild(a);a.select();try{document.execCommand('copy');}catch(e){}document.body.removeChild(a);flash();}
});
document.getElementById('UI')?.addEventListener('keydown',e=>{if(e.key==='Enter')startApp();});
{% endif %}
</script></body></html>"""

if __name__ == '__main__':
    import urllib3; urllib3.disable_warnings()
    app.run(host='0.0.0.0', port=5000, debug=False)
